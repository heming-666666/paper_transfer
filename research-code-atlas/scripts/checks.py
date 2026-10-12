"""Evidence references and immutable facts are validated separately from Agent reasoning."""
import copy
from pathlib import Path
import re
from common import read, write, safe_path, InputError, EvidenceError, STATUSES
from paper import find_quote


def prefilled(symbol):
    keys = ('signature', 'definition_range', 'docstring', 'callers', 'callees', 'returns', 'yields', 'raises', 'asserts', 'shape_hints', 'step_skeleton')
    return {k: copy.deepcopy(symbol[k]) for k in keys}


class Checker:
    def __init__(self, run):
        self.run = Path(run).resolve()
        self.structure = read(self.run / 'structure.json')
        self.symbols = {s['id']: s for s in self.structure['symbols']}
        self.entries = {e['entry_id']: e for e in self.structure['entries']}
        self.files = {s['file']: s for s in read(self.run / 'inventory.json')['indexed_files']}
        self.configs = read(self.run / 'config-index.json') if (self.run / 'config-index.json').exists() else {'items': [], 'config_sources': []}
        self.files.update({s['file']:s for s in self.configs.get('config_sources', [])})
        self.evidence, self.errors = {}, []

    def error(self, path, message): self.errors.append(f'{path}: {message}')

    def symbol(self, sid, path):
        if sid not in self.symbols: self.error(path, f'unknown symbol_id {sid}')
        return self.symbols.get(sid)

    def source(self, value, path):
        if not isinstance(value, str):
            self.error(path, 'source evidence must be file:start-end string'); return None
        match = re.fullmatch(r'(.+):(\d+)-(\d+)', value)
        if not match:
            self.error(path, 'expected file:start-end, 1-based inclusive'); return None
        file, lo, hi = match[1], int(match[2]), int(match[3])
        record = self.files.get(file)
        if record is None or not 1 <= lo <= hi <= record['line_count']:
            self.error(path, f'evidence file/range missing or out of bounds: {value}'); return None
        eid = f'ev:src:{file}:{lo}-{hi}'
        self.evidence[eid] = {'id': eid, 'kind': 'source', 'file': file, 'start_line': lo, 'end_line': hi, 'file_sha256': record['sha256']}
        return eid

    def paper_evidence(self, value, path):
        if not isinstance(value, dict) or not isinstance(value.get('page'), int) or not isinstance(value.get('quote'), str):
            self.error(path, 'paper evidence needs integer PDF page and quote'); return
        page, quote = value['page'], value['quote']
        if not 15 <= len(quote) <= 200:
            self.error(path + '.quote', 'quote length must be 15..200 characters'); return
        page_path = self.run / 'paper/pages' / f'page_{page:03}.txt'
        if not page_path.is_file() or not find_quote(page_path.read_text(encoding='utf-8'), quote):
            self.error(path, f'quote not found on PDF page {page}'); return
        import hashlib
        eid = f'ev:paper:{page}:' + hashlib.sha256(quote.encode('utf-8')).hexdigest()[:16]
        self.evidence[eid] = {'id': eid, 'kind': 'paper', **value}

    def recursive(self, value, path='$'):
        if isinstance(value, list):
            for i, item in enumerate(value): self.recursive(item, f'{path}[{i}]')
        elif isinstance(value, dict):
            if value.get('symbol_id') is not None: self.symbol(value['symbol_id'], path + '.symbol_id')
            if 'entry_id' in value and value['entry_id'] not in self.entries: self.error(path + '.entry_id', 'unknown entry_id')
            if 'container_path' in value and ('name' in value or '.inputs[' in path or '.outputs[' in path):
                for field in ('name', 'type', 'shape', 'dimensions', 'status', 'reason', 'evidence'):
                    if field not in value: self.error(path + '.' + field, 'missing IO field')
                if not isinstance(value.get('container_path'), list): self.error(path + '.container_path', 'must be array')
                shape = value.get('shape')
                if shape is not None and (not isinstance(shape,list) or any(not (d is None or isinstance(d,(int,str))) or isinstance(d,bool) for d in shape)):
                    self.error(path + '.shape', 'dimensions must be integer/symbol/null')
                if shape is None and not value.get('reason'): self.error(path + '.reason', 'unknown shape needs reason')
                if value.get('status') not in STATUSES:self.error(path+'.status','invalid IO evidence status')
            if value.get('status') in STATUSES:
                status = value['status']
                if status == 'observed_runtime': self.error(path + '.status', 'runtime capture not implemented; no runtime claims allowed')
                if status in ('unknown', 'inferred') and not value.get('reason'): self.error(path + '.reason', f'{status} needs reason')
                if status == 'confirmed_source' and not value.get('evidence') and not self.request_fact(value):
                    self.error(path + '.evidence', 'confirmed_source requires evidence')
            if isinstance(value.get('page'), int) and 'quote' in value: self.paper_evidence(value,path)
            for key, item in value.items():
                at = path + '.' + key
                if key in ('prefilled',): continue
                if key == 'evidence':
                    for index, ref in enumerate(item if isinstance(item,list) else [item]):
                        if isinstance(ref,str): self.source(ref,f'{at}[{index}]')
                        elif isinstance(ref,dict): self.paper_evidence(ref,f'{at}[{index}]')
                        else: self.error(at,'invalid evidence type')
                else: self.recursive(item,at)

    def request_fact(self,value):
        source=str(value.get('source',''))
        match=re.fullmatch(r'request\.entries\[(\d+)\]\.args\s+(--?[\w-]+)',source)
        if not match:return False
        entries=read(self.run/'request.json')['entries'];index=int(match[1]);flag=match[2]
        if index>=len(entries):return False
        args=entries[index].get('args',[])
        for i,arg in enumerate(args):
            if arg==flag and i+1<len(args) and str(value.get('value'))==str(args[i+1]):return True
            if str(arg).startswith(flag+'=') and str(value.get('value'))==str(arg).split('=',1)[1]:return True
        return False

    def steps(self, supplied, skeleton, path, symbol_range):
        if not isinstance(supplied,list): self.error(path,'steps must be list'); return
        all_skeleton = {}
        def gather(steps):
            for step in steps:
                all_skeleton[step['id']] = step; gather(step['children'])
        gather(skeleton)
        def inspect(steps,p):
            for i,step in enumerate(steps):
                at=f'{p}[{i}]'; lo,hi=step.get('source_range',[0,0])
                if not symbol_range[0] <= lo <= hi <= symbol_range[1]: self.error(at+'.source_range','outside function definition_range')
                original=all_skeleton.get(step.get('id'))
                if original is None:
                    merged=step.get('merged_ids',[])
                    originals=[all_skeleton[k] for k in merged if k in all_skeleton]
                    if len(originals)!=len(merged) or not originals:
                        self.error(at+'.id','unknown step ID; merged_ids must name actual adjacent steps')
                    else:
                        ranges=sorted(x['source_range'] for x in originals)
                        expected=[ranges[0][0],ranges[-1][1]]
                        if [lo,hi]!=expected or any(b[0]>a[1]+1 for a,b in zip(ranges,ranges[1:])):self.error(at+'.source_range','not contiguous skeleton union')
                        calls=list(dict.fromkeys(c for x in originals for c in x['calls']))
                        if step.get('calls')!=calls:self.error(at+'.calls','merged calls changed')
                else:
                    for key in ('source_range','kind','calls'):
                        if step.get(key)!=original[key]:self.error(at+'.'+key,'script-provided fact changed')
                inspect(step.get('children',[]),at+'.children')
        inspect(supplied,path)

    def notes(self, data):
        if not isinstance(data,dict) or not isinstance(data.get('items'),list):self.error('$','batch must contain items list');return
        seen=set()
        for i,item in enumerate(data['items']):
            path=f'$.items[{i}]'; symbol=self.symbol(item.get('symbol_id'),path+'.symbol_id')
            if item.get('symbol_id') in seen:self.error(path,'duplicate symbol in batch')
            seen.add(item.get('symbol_id'))
            required=('prefilled','role','summary','purpose','inputs','outputs','side_effects','exceptions','steps','paper_refs','config_refs','scenario_contracts','change_notes','needs_context','analysis_status')
            for key in required:
                if key not in item:self.error(path+'.'+key,'missing field')
            if item.get('role') not in ('entry','config','data','model','loss','train_loop','optim','eval','io','util','other'):self.error(path+'.role','invalid role')
            if item.get('analysis_status') not in ('done','partial','pending'):self.error(path+'.analysis_status','invalid analysis status')
            if symbol:
                if item.get('prefilled')!=prefilled(symbol):self.error(path+'.prefilled','script-generated facts changed')
                self.steps(item.get('steps',[]),symbol['step_skeleton'],path+'.steps',symbol['definition_range'])
            if item.get('analysis_status')=='done':
                for key in ('summary','purpose','steps'):
                    if not item.get(key):self.error(path+'.'+key,'done requires nonempty field')
            if item.get('analysis_status')=='partial' and not item.get('needs_context'):self.error(path+'.needs_context','partial must explain missing context')
            self.recursive(item,path)
            for i2, contract in enumerate(item.get('scenario_contracts',[])):
                if not all(k in contract for k in ('entry_id','callsite','conditions','inputs','outputs','evidence')):self.error(path+f'.scenario_contracts[{i2}]','missing contract fields')

    def overview(self,data):
        for key in ('entry_id','summary','stages','core_symbols','learning_path','dataflow'):
            if key not in data:self.error('$.'+key,'missing overview field')
        self.recursive(data)
        for i,row in enumerate(data.get('core_symbols',[])):self.symbol(row.get('id'),f'$.core_symbols[{i}].id')
        for i,sid in enumerate(data.get('learning_path',[])):self.symbol(sid,f'$.learning_path[{i}]')
        for i,stage in enumerate(data.get('stages',[])):
            for j,sid in enumerate(stage.get('symbols',[])):self.symbol(sid,f'$.stages[{i}].symbols[{j}]')

    def paper_map(self,data):
        if data.get('status') not in ('available','missing'):self.error('$.status','invalid paper status')
        if data.get('status')=='missing' and data.get('contributions'):self.error('$.contributions','missing paper cannot have contributions')
        ids=set()
        for i,c in enumerate(data.get('contributions',[])):
            path=f'$.contributions[{i}]'
            for key in ('id','claim','compared_to','mechanism','paper_evidence','code_mappings','key_configs','io_change','modification_constraints','conflicts'):
                if key not in c:self.error(path+'.'+key,'missing contribution field')
            if c.get('id') in ids:self.error(path+'.id','duplicate contribution ID')
            ids.add(c.get('id'))
            if not c.get('paper_evidence'):self.error(path+'.paper_evidence','contribution requires original paper evidence')
            for j,m in enumerate(c.get('code_mappings',[])):
                at=f'{path}.code_mappings[{j}]'
                if m.get('status') not in ('direct','inferred','not_found','conflict'):self.error(at+'.status','invalid mapping status')
                if m.get('status')!='not_found':
                    symbol=self.symbol(m.get('symbol_id'),at+'.symbol_id')
                    if not m.get('evidence'):self.error(at+'.evidence','code mapping needs source evidence')
                    if symbol:
                        step_ids=set()
                        def collect(steps):
                            for s in steps:step_ids.add(s['id']);collect(s['children'])
                        collect(symbol['step_skeleton'])
                        for a in m.get('step_alignment',[]):
                            if a.get('code_step') not in step_ids:self.error(at+'.step_alignment','unknown code step')
            self.recursive(c,path)

    def experiments(self,data):
        if not isinstance(data,list):self.error('$','experiments must be list');return
        for i,item in enumerate(data):
            path=f'$[{i}]'
            for key in ('id','entry_id','setting','paper_value','repo_default','selected_value','precedence','consumed_by','status','impact'):
                if key not in item:self.error(path+'.'+key,'missing experiment field')
            if item.get('status') not in ('match','mismatch','unknown','paper_only','code_only','defined_not_consumed'):self.error(path+'.status','invalid experiment status')
            if item.get('status')=='defined_not_consumed' and item.get('consumed_by'):self.error(path+'.consumed_by','defined_not_consumed cannot claim consumers')
            self.recursive(item,path)

    def impacts(self,data):
        if not isinstance(data,list):self.error('$','impacts must be list');return
        for i,item in enumerate(data):
            self.symbol(item.get('target'),f'$[{i}].target')
            for field in ('upstream','downstream'):
                for sid in item.get(field,[]):self.symbol(sid,f'$[{i}].{field}')
            self.recursive(item,f'$[{i}]')

    def check(self,data,kind):
        {'notes':self.notes,'overview':self.overview,'paper-map':self.paper_map,'experiments':self.experiments,'change-impacts':self.impacts}[kind](data)
        if self.errors:raise EvidenceError('\n'.join(self.errors[:60]))
        return {'status':'passed','kind':kind,'evidence':self.evidence}


def kind_for(path,data):
    name=Path(path).name
    if isinstance(data,dict) and 'items' in data:return 'notes'
    if isinstance(data,dict) and 'stages' in data:return 'overview'
    if name=='paper-map.json' or isinstance(data,dict) and 'contributions' in data:return 'paper-map'
    if name=='experiment-settings.json' or isinstance(data,list) and data and 'setting' in data[0]:return 'experiments'
    if name=='change-impacts.json' or isinstance(data,list) and data and 'target' in data[0]:return 'change-impacts'
    raise InputError('unknown semantic JSON type')


def check_file(run_dir,path):
    path=Path(path).resolve()
    data=read(path)
    checker=Checker(run_dir)
    result=checker.check(data,kind_for(path,data))
    result['file']=str(path)
    directory=Path(run_dir)/'checks';directory.mkdir(exist_ok=True)
    write(directory/(path.stem+'-check.json'),result)
    return result
