"""Conservative lexical/import/type resolution. A candidate is never promoted to observed."""
import builtins
from collections import deque
from pathlib import PurePosixPath
from common import InputError

GENERAL_METHODS = {'append', 'get', 'items', 'keys', 'values', 'update', 'to', 'cuda', 'cpu', 'item', 'numpy', 'detach', 'format', 'join', 'split', 'strip'}


class Resolver:
    def __init__(self, collectors):
        self.collectors = collectors
        self.symbols = [s for c in collectors for s in c.symbols]
        self.by_id = {s['id']: s for s in self.symbols}
        self.modules = {}
        self.module_of = {}
        self.imports = [i for c in collectors for i in c.imports]
        self.assigns = [a for c in collectors for a in c.assigns]
        self.builtins = 0
        for c in collectors:
            name = c.rel[:-3].replace('/', '.')
            if name.endswith('.__init__'): name = name[:-9]
            if name == '__init__': name = ''
            self.modules[name] = c.rel
            if name.startswith('src.'): self.modules[name[4:]] = c.rel
            self.module_of[c.rel] = name

    def children(self, parent, name):
        return [s for s in self.symbols if s['parent'] == parent and s['qualname'].split('.')[-1] == name]

    def import_target(self, record):
        module = record['module']
        if record['level']:
            package = self.module_of[record['file']].split('.')
            if not record['file'].endswith('__init__.py'): package = package[:-1]
            remove = record['level'] - 1
            if remove: package = package[:-remove]
            module = '.'.join(package + ([module] if module else []))
        return module

    def module_member(self, module, name, depth=0):
        if depth > 3: return ('unresolved', None, [])
        rel = self.modules.get(module)
        if rel:
            matches = self.children(f'sym:{rel}:<module>:module', name)
            if len(matches) == 1: return ('symbol', matches[0]['id'], [])
            if len(matches) > 1: return ('candidate', None, [s['id'] for s in matches])
            submodule = module + '.' + name if module else name
            if submodule in self.modules: return ('module', submodule, [])
            aliases = [i for i in self.imports if i['file'] == rel and i['scope'] == f'sym:{rel}:<module>:module' and i['alias'] == name]
            if aliases:
                imp = aliases[-1]
                target = self.import_target(imp)
                if imp['name']: return self.module_member(target, imp['name'], depth+1)
                return ('module', target, [])
            return ('unresolved', None, [])
        return ('external', f'ext:{module}.{name}'.strip('.'), [])

    def lookup(self, caller, name, line=None):
        cur = self.by_id[caller]
        while cur:
            nested = self.children(cur['id'], name)
            if len(nested) == 1: return ('symbol', nested[0]['id'], [])
            if len(nested) > 1: return ('candidate', None, [s['id'] for s in nested])
            imports = [i for i in self.imports if i['scope'] == cur['id'] and i['alias'] == name]
            if imports:
                imp = imports[-1]
                target = self.import_target(imp)
                if imp['name']: return self.module_member(target, imp['name'])
                if target in self.modules: return ('module', target, [])
                # import a.b without alias binds a, not the full submodule.
                bound = target if imp['alias'] != target.split('.')[0] else target.split('.')[0]
                if bound in self.modules: return ('module', bound, [])
                return ('external', f'ext:{bound}', [])
            if name in {p['name'] for p in cur['params']} or name in cur['locals']:
                assignments = [a for a in self.assigns if a['scope'] == cur['id'] and a['target'] == name and a['constructor'] and (line is None or a['line'] < line)]
                if assignments:
                    a = assignments[-1]
                    constructor = self.resolve_descriptor(cur['id'], a['constructor'], a['line'], constructing=True)
                    if constructor[0] == 'symbol' and self.by_id.get(constructor[1], {}).get('kind') == 'class':
                        return ('instance', constructor[1], [])
                return ('local', None, [])
            # Do not use class attributes as unqualified names inside a method.
            cur = self.by_id.get(cur['parent'])
            if cur and cur['kind'] == 'class': cur = self.by_id.get(cur['parent'])
        if hasattr(builtins, name): return ('builtin', None, [])
        return ('unresolved', None, [])

    def owner_class(self, caller):
        s = self.by_id.get(caller)
        while s:
            if s['kind'] == 'class': return s
            s = self.by_id.get(s['parent'])
        return None

    def class_method(self, cls, method, seen=None):
        seen = set(seen or [])
        if cls in seen: return ('unresolved', None, [])
        seen.add(cls)
        found = self.children(cls, method)
        if len(found) == 1: return ('symbol', found[0]['id'], [])
        if found: return ('candidate', None, [x['id'] for x in found])
        c = self.by_id[cls]
        for base in c['bases']:
            resolved = self.resolve_descriptor(c['parent'], base, constructing=True)
            if resolved[0] == 'symbol' and self.by_id.get(resolved[1], {}).get('kind') == 'class':
                result = self.class_method(resolved[1], method, seen)
                if result[1] or result[2]: return ('inherited', result[1], result[2])
        return ('unresolved', None, [])

    def self_attribute(self, cls, attr):
        matches = [a for a in self.assigns if a['target'] == 'self.' + attr and a['constructor'] and self.owner_class(a['scope']) and self.owner_class(a['scope'])['id'] == cls]
        if matches:
            a = matches[-1]
            result = self.resolve_descriptor(a['scope'], a['constructor'], a['line'], constructing=True)
            if result[0] == 'symbol' and self.by_id.get(result[1], {}).get('kind') == 'class': return result[1]
        return None

    def resolve_descriptor(self, caller, desc, line=None, constructing=False):
        kind = desc['kind']
        if kind == 'name': return self.lookup(caller, desc['name'], line)
        if kind != 'attr': return ('dynamic', None, [])
        base, attr = desc['base'], desc['attr']
        cls = self.owner_class(caller)
        if base == ['self'] and cls:
            result = self.class_method(cls['id'], attr)
            if result[0] != 'unresolved': return result
            instance = self.self_attribute(cls['id'], attr)
            if instance: return ('instance', instance, [])
        if len(base) == 2 and base[0] == 'self' and cls:
            instance = self.self_attribute(cls['id'], base[1])
            if instance:
                result = self.class_method(instance, attr)
                if result[1] or result[2]: return ('instance_method', result[1], result[2])
        result = self.lookup(caller, base[0], line)
        if result[0] == 'module':
            module = '.'.join([result[1], *base[1:]])
            return self.module_member(module, attr)
        if result[0] == 'external': return ('external', result[1] + '.' + '.'.join(base[1:] + [attr]), [])
        if result[0] == 'instance' and len(base) == 1:
            method = self.class_method(result[1], attr)
            if method[1] or method[2]: return ('instance_method', method[1], method[2])
        if attr not in GENERAL_METHODS:
            methods = [s['id'] for s in self.symbols if s['kind'] == 'method' and s['qualname'].split('.')[-1] == attr]
            if 0 < len(methods) <= 5: return ('candidate', None, methods)
        return ('unresolved', None, [])

    def edge(self, call, index):
        result = self.resolve_descriptor(call['caller'], call['func'], call['line'])
        kind, target, candidates = result
        relation, resolution, note = 'calls', 'resolved_static', ''
        if kind == 'builtin':
            self.builtins += 1
            return None
        if kind == 'symbol' and self.by_id[target]['kind'] == 'class':
            relation = 'constructs'
            init = self.class_method(target, '__init__')
            if init[1]: target = init[1]
        elif kind == 'instance':
            method = self.class_method(target, '__call__')
            if not method[1]:
                method = self.class_method(target, 'forward')
                relation = 'module_call'
            target, candidates, resolution = method[1], method[2], 'candidate'
            note = '由同函数内类构造/初始化属性推断；不是运行观测'
            if target is None and not candidates: resolution = 'unresolved'
        elif kind in ('instance_method', 'inherited', 'candidate'):
            resolution = 'candidate'
            note = '由实例属性/局部构造/基类/同名方法推断；动态分派可能不同'
        elif kind == 'external': resolution, note = 'external', '项目外调用，未解析其内部实现'
        elif kind in ('local', 'dynamic', 'unresolved', 'module'):
            resolution, target, note = 'unresolved', None, '调用参数/局部变量中的可调用对象或动态调用，静态无法确定'
        if call['definition_time']: relation = 'definition_time'
        return {'id': f'e:{index}:{call["caller"]}@{call["file"]}:{call["line"]}', 'caller': call['caller'],
                'callee': target, 'candidates': candidates, 'relation': relation, 'resolution': resolution,
                'callsite': {'file': call['file'], 'line': call['line'], 'end_line': call['end_line']},
                'expression': call['expression'], 'conditions': call['conditions'], 'note': note}


def resolve_graph(collectors, request):
    resolver = Resolver(collectors)
    edges = []
    for c in collectors:
        for call in c.calls:
            edge = resolver.edge(call, len(edges))
            if edge: edges.append(edge)
    for symbol in resolver.symbols:
        symbol['callers'] = [e for e in edges if e['callee'] == symbol['id'] or symbol['id'] in e['candidates']]
        symbol['callees'] = [e for e in edges if e['caller'] == symbol['id']]
        def attach(steps):
            for step in steps:
                lo, hi = step['source_range']
                step['calls'] = [e['callee'] or e['expression'] for e in symbol['callees'] if lo <= e['callsite']['line'] <= hi]
                attach(step['children'])
        attach(symbol['step_skeleton'])
    entries, truncated = [], []
    limits = request.get('limits', {})
    max_depth, max_symbols = limits.get('max_depth', 8), limits.get('max_symbols', 300)
    for entry in request['entries']:
        path = entry['path'].replace('\\', '/')
        roots = [s for s in resolver.symbols if s['file'] == path and (s['qualname'] == entry.get('symbol') if entry.get('symbol') else s['kind'] == 'module')]
        if len(roots) != 1: raise InputError(f'entry root symbol missing or ambiguous: {path}:{entry.get("symbol")}')
        root = roots[0]['id']
        depths, queue = {root: 0}, deque([root])
        while queue:
            caller = queue.popleft()
            for edge in edges:
                if edge['caller'] != caller or edge['relation'] not in ('calls', 'constructs', 'module_call') or edge['resolution'] not in ('resolved_static', 'candidate'): continue
                for target in ([edge['callee']] if edge['callee'] else edge['candidates']):
                    if target not in resolver.by_id or target in depths: continue
                    if depths[caller] >= max_depth or len(depths) >= max_symbols:
                        truncated.append({'entry_id': entry['entry_id'], 'from': caller, 'target': target, 'reason': 'depth/symbol budget'})
                        continue
                    depths[target] = depths[caller] + 1
                    queue.append(target)
        entries.append({**entry, 'root_symbol': root, 'closure': list(depths), 'depth_of': depths})
    for s in resolver.symbols: s['in_entries'] = [e['entry_id'] for e in entries if s['id'] in e['closure']]
    file_edges = []
    for imp in resolver.imports:
        module = resolver.import_target(imp)
        rel = resolver.modules.get(module)
        if rel: file_edges.append({'source': imp['file'], 'target': rel, 'relation': 'imports', 'line': imp['line']})
    class_edges = []
    for s in resolver.symbols:
        if s['kind'] == 'class':
            for base in s['bases']:
                result = resolver.resolve_descriptor(s['parent'], base, constructing=True)
                class_edges.append({'source': s['id'], 'target': result[1], 'relation': 'inherits', 'resolution': result[0]})
    return {'schema_version': '1.0', 'symbols': resolver.symbols, 'edges': edges, 'entries': entries, 'file_edges': file_edges,
            'class_edges': class_edges, 'control_regions': [x for c in collectors for x in c.controls],
            'coverage': {'builtin_calls': resolver.builtins, 'unresolved_calls': sum(e['resolution'] == 'unresolved' for e in edges),
                         'truncated': truncated, 'limitations': ['Python静态解析；候选调用不是已观察路径；不导入目标']}}
