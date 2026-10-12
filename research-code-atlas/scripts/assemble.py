import datetime
from pathlib import Path
import subprocess
from common import read, write, sha_bytes, safe_path, InputError, EvidenceError
from checks import Checker, kind_for


def assemble(run_dir):
    run=Path(run_dir).resolve()
    request,structure,manifest=read(run/'request.json'),read(run/'structure.json'),read(run/'manifest.json')
    if sha_bytes((run/'structure.json').read_bytes())!=manifest['structure_sha256']:raise EvidenceError('structure.json changed since extraction')
    notes,overviews,paper_map,experiments,impacts,evidence={},{},{'status':'missing','contributions':[]},[],[],{}
    paths=sorted((run/'notes').glob('batch_*.json'))+sorted((run/'notes').glob('overview_*.json'))
    paths += [run/name for name in ('paper-map.json','experiment-settings.json','change-impacts.json') if (run/name).exists()]
    for path in paths:
        data=read(path);kind=kind_for(path,data);checker=Checker(run);checker.check(data,kind);evidence.update(checker.evidence)
        if kind=='notes':
            for note in data['items']:
                if note['symbol_id'] in notes:raise EvidenceError('duplicate notes across batches: '+note['symbol_id'])
                notes[note['symbol_id']]=note
        elif kind=='overview':
            if data['entry_id'] in overviews:raise EvidenceError('duplicate entry overview')
            overviews[data['entry_id']]=data
        elif kind=='paper-map':paper_map=data
        elif kind=='experiments':experiments=data
        else:impacts=data
    functions=[s for s in structure['symbols'] if s['kind'] not in ('module','class')]
    pending=[s['id'] for s in functions if notes.get(s['id'],{}).get('analysis_status')!='done']
    for entry in structure['entries']:
        if entry['entry_id'] not in overviews:raise EvidenceError('missing overview for '+entry['entry_id'])
    paper_status=read(run/'paper/status.json') if (run/'paper/status.json').exists() else {'status':'missing','reason':'paper command not run'}
    if paper_status['status']=='available' and not (run/'paper-map.json').exists():raise EvidenceError('paper available but no checked paper-map.json')
    if paper_status['status']=='missing' and paper_map.get('status')=='available':raise EvidenceError('missing paper cannot be mapped as available')
    contributions={c['id'] for c in paper_map.get('contributions',[])}
    config_index=read(run/'config-index.json') if (run/'config-index.json').exists() else {'items':[],'config_sources':[]}
    config_ids={c['id'] for c in config_index['items']}|{e['id'] for e in experiments}
    for note in notes.values():
        if any(x not in contributions for x in note['paper_refs']):raise EvidenceError('dangling paper_refs')
        if any(x not in config_ids for x in note['config_refs']):raise EvidenceError('dangling config_refs')
    for contribution in paper_map.get('contributions',[]):
        for mapping in contribution.get('code_mappings',[]):
            mapping['on_entry_path']={e['entry_id']:mapping.get('symbol_id') in e['closure'] for e in structure['entries']}
    symbols=[{**s,'note':notes.get(s['id'])} for s in structure['symbols']]
    freshness=read(run/'freshness.json') if (run/'freshness.json').exists() else {'snapshot_at':manifest['snapshot_at'],'rechecked_at':None,'status':'not_rechecked'}
    commit,dirty=None,None
    try:
        command=['git','-C',request['project_root']]
        root=subprocess.run(command+['rev-parse','--show-toplevel'],capture_output=True,text=True,encoding='utf-8')
        if root.returncode==0 and Path(root.stdout.strip()).resolve()==Path(request['project_root']).resolve():
            commit=subprocess.check_output(command+['rev-parse','HEAD'],text=True,encoding='utf-8').strip()
            dirty=bool(subprocess.check_output(command+['status','--porcelain'],text=True,encoding='utf-8'))
    except (OSError,subprocess.CalledProcessError):pass
    data={'schema_version':'1.0','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'project':{'name':Path(request['project_root']).name,'root':request['project_root'],'git_commit_or_null':commit,'worktree_dirty_or_null':dirty},
          'request':request,'coverage':{**structure['coverage'],'analyzed_files':sorted({s['file'] for s in symbols if s['note']}),'pending_symbols':pending},
          'sources':read(run/'inventory.json')['indexed_files']+config_index.get('config_sources',[]),
          'symbols':symbols,'edges':structure['edges'],'file_edges':structure['file_edges'],'class_edges':structure['class_edges'],
          'entries':structure['entries'],'overviews':list(overviews.values()),'paper':{**paper_status,**paper_map},
          'experiments':experiments,'config_index':config_index,'change_impacts':impacts,'evidence':evidence,'freshness':freshness}
    write(run/'atlas.json',data)
    return {'atlas':str(run/'atlas.json'),'explained':len(functions)-len(pending),'pending':len(pending),'paper':data['paper']['status']}


def validate(run_dir,recheck=False):
    run=Path(run_dir).resolve();atlas=read(run/'atlas.json');structure=read(run/'structure.json');manifest=read(run/'manifest.json')
    if sha_bytes((run/'structure.json').read_bytes())!=manifest['structure_sha256']:raise EvidenceError('structure manifest mismatch')
    ids=[s['id'] for s in atlas['symbols']]
    if len(ids)!=len(set(ids)):raise EvidenceError('duplicate symbol ID')
    pool=set(ids)
    for edge in atlas['edges']:
        if edge['caller'] not in pool or (edge['callee'] and not edge['callee'].startswith('ext:') and edge['callee'] not in pool) or any(s not in pool for s in edge['candidates']):raise EvidenceError('dangling graph edge')
    for entry in atlas['entries']:
        if entry['root_symbol'] not in pool or any(s not in pool for s in entry['closure']):raise EvidenceError('dangling entry closure')
    for record in atlas['sources']:
        path=safe_path(run/'sources',record['file'])
        if not path.is_file() or sha_bytes(path.read_bytes())!=record['sha256']:raise EvidenceError('source snapshot hash mismatch: '+record['file'])
    checker=Checker(run)
    for symbol in atlas['symbols']:
        if symbol['note']:checker.notes({'items':[symbol['note']]})
    for overview in atlas['overviews']:checker.overview(overview)
    checker.paper_map(atlas['paper']);checker.experiments(atlas['experiments']);checker.impacts(atlas['change_impacts'])
    if checker.errors:raise EvidenceError('\n'.join(checker.errors))
    if recheck:
        root=Path(atlas['project']['root']);changes=[];missing=[]
        for record in atlas['sources']:
            try:
                path=safe_path(root,record['file'])
                if not path.is_file():missing.append(record['file'])
                elif sha_bytes(path.read_bytes())!=record['original_sha256']:changes.append(record['file'])
            except (OSError,InputError):missing.append(record['file'])
        freshness={'snapshot_at':manifest['snapshot_at'],'rechecked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'status':'stale' if changes else 'unknown' if missing else 'matched','changed_files':changes,'unavailable_files':missing}
        write(run/'freshness.json',freshness);atlas['freshness']=freshness;write(run/'atlas.json',atlas)
    result={'status':'passed','symbols':len(ids),'explained':sum(s['note'] is not None and s['note']['analysis_status']=='done' for s in atlas['symbols']),
            'freshness':atlas['freshness'],'runtime':'not implemented; static only'}
    write(run/'validation.json',result)
    return result
