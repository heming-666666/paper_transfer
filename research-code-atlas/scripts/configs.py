import ast
from pathlib import Path
import re
from common import read, write, safe_path, InputError, sha_bytes


def literal(node):
    if node is None: return None
    try: return ast.literal_eval(node)
    except (ValueError, TypeError): return {'expression': ast.unparse(node), 'status': 'unknown'}


def flatten(data, prefix=''):
    if isinstance(data, dict):
        for key, value in data.items():
            yield from flatten(value, prefix + '.' + str(key) if prefix else str(key))
    else: yield prefix, data


def config_index(run_dir):
    run = Path(run_dir).resolve()
    request, structure = read(run / 'request.json'), read(run / 'structure.json')
    output = run / 'config-index.json'
    if output.exists(): raise InputError('config-index already exists; reuse existing facts')
    items = []
    files = {x['file']: x for x in read(run / 'inventory.json')['indexed_files']}
    sources = {rel: safe_path(run / 'sources', rel).read_text(encoding='utf-8') for rel in files}
    def containing(rel, line):
        owners = [s for s in structure['symbols'] if s['file']==rel and s['definition_range'][0]<=line<=s['definition_range'][1]]
        return min(owners,key=lambda s:s['definition_range'][1]-s['definition_range'][0])['id'] if owners else None
    for rel, src in sources.items():
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
                flags = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                if not flags: continue
                kwargs = {k.arg:k.value for k in node.keywords if k.arg}
                dest = literal(kwargs.get('dest')) or next((f for f in flags if f.startswith('--')), flags[0]).lstrip('-').replace('-', '_')
                items.append({'id': dest, 'kind': 'argparse', 'flags': flags, 'default': literal(kwargs.get('default')),
                              'type': ast.unparse(kwargs['type']) if 'type' in kwargs else None, 'choices': literal(kwargs.get('choices')),
                              'help': literal(kwargs.get('help')), 'file': rel, 'line': node.lineno, 'status': 'confirmed_source', 'symbol_id': containing(rel,node.lineno)})
            elif isinstance(node, ast.ClassDef) and (node.name=='Config' or any('dataclass' in ast.unparse(d) for d in node.decorator_list)):
                for statement in node.body:
                    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                        for target in targets:
                            if isinstance(target, ast.Name): items.append({'id': target.id, 'kind':'class-config','default':literal(statement.value),'file':rel,'line':statement.lineno,'status':'confirmed_source','symbol_id':containing(rel,statement.lineno)})
    configured = sorted({c for e in request['entries'] for c in e.get('configs', [])})
    config_sources = []
    for rel in configured:
        p = safe_path(request['project_root'], rel)
        if p.stat().st_size>1024*1024: raise InputError('config exceeds 1MiB')
        text=p.read_text(encoding='utf-8'); suffix=p.suffix.lower(); status='confirmed_source'
        if suffix == '.json':
            import json
            data=json.loads(text)
        elif suffix == '.toml':
            try:
                import tomllib
                data=tomllib.loads(text)
            except ImportError: raise InputError('TOML needs Python>=3.11')
        elif suffix in ('.yaml','.yml'):
            try:
                import yaml
                data=yaml.safe_load(text)
            except ImportError:
                status='inferred';data={};stack=[]
                for line in text.splitlines():
                    match=re.match(r'^(\s*)([\w.-]+)\s*:\s*(.*?)\s*$',line)
                    if not match:continue
                    indent=len(match[1]);key,value=match[2],match[3]
                    while stack and stack[-1][0]>=indent:stack.pop()
                    qualified='.'.join([x[1] for x in stack]+[key]);data[qualified]=value
                    if not value:stack.append((indent,key))
        else:
            raise InputError('config files support JSON/YAML/TOML; Python configs are AST facts, not executed')
        for key,value in flatten(data or {}):
            leaf=key.split('.')[-1]
            line=next((i for i,t in enumerate(text.splitlines(),1) if re.search(r'\b'+re.escape(leaf)+r'\b',t)),1)
            items.append({'id':key,'kind':suffix.lstrip('.'),'default':value,'file':rel,'line':line,'status':status,'symbol_id':None,
                          'line_reason':'近似文本定位；配置值安全解析，不求Hydra/OmegaConf插值'})
        snapshot=safe_path(run/'sources',rel);snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_text(text,encoding='utf-8',newline='\n')
        config_sources.append({'file':rel,'sha256':sha_bytes(text.encode('utf-8')),'original_sha256':sha_bytes(p.read_bytes()),'line_count':max(1,len(text.splitlines()))})
    for item in items:
        leaf=item['id'].split('.')[-1]
        pattern=re.compile(r'(?:\b(?:args|cfg|config)\.'+re.escape(leaf)+r'\b|\[\s*[\'\"]'+re.escape(leaf)+r'[\'\"]\s*\]|\.get\(\s*[\'\"]'+re.escape(leaf)+r'[\'\"])')
        item['consumers']=[]
        for rel,src in sources.items():
            for index,line in enumerate(src.splitlines(),1):
                if pattern.search(line):item['consumers'].append({'file':rel,'line':index,'text':line.strip(),'symbol_id':containing(rel,index),'status':'candidate'})
        item['consumption']='candidate_consumers' if item['consumers'] else 'defined_not_consumed'
        item['selected_values']=[]
        for entry in request['entries']:
            selected,reason=None,'实际配置加载/覆盖顺序未知；不把默认值当最终值'
            args=entry.get('args',[])
            for flag in item.get('flags',[]):
                for i,arg in enumerate(args):
                    if arg==flag and i+1<len(args):selected=args[i+1];reason=f'request参数线索 {flag} {selected}；是否随后改写须Agent核对'
                    elif isinstance(arg,str) and arg.startswith(flag+'='):selected=arg.split('=',1)[1];reason='request参数线索；最终消费仍需核对'
            item['selected_values'].append({'entry_id':entry['entry_id'],'value':selected,'status':'inferred' if selected is not None else 'unknown','reason':reason})
    result={'schema_version':'1.0','items':items,'config_sources':config_sources,'limitations':['消费者是静态候选，不能证明运行时采用；插值/环境变量不求值']}
    write(output,result)
    return result
