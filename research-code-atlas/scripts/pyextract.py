"""Read-only AST facts. Lexical scopes are kept separate from containment and dataflow."""
import ast
from collections import deque
import os
from pathlib import Path
import re
import tokenize
from common import InputError, sha_bytes

SKIP = {'.git', '.venv', 'venv', 'env', '__pycache__', 'node_modules', 'build', 'dist', '.idea', '.vscode', 'wandb', 'outputs', 'logs', 'checkpoints', 'data', 'datasets', '.pytest_cache'}
BINARY = {'.pt', '.pth', '.ckpt', '.safetensors', '.bin'}


def describe(node):
    if isinstance(node, ast.Name):
        return {'kind': 'name', 'name': node.id}
    chain = []
    cur = node
    while isinstance(cur, ast.Attribute):
        chain.insert(0, cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name) and chain:
        return {'kind': 'attr', 'base': [cur.id] + chain[:-1], 'attr': chain[-1]}
    return {'kind': 'dynamic', 'text': ast.unparse(node)}


class Collector(ast.NodeVisitor):
    def __init__(self, rel, src):
        self.rel, self.src = rel, src
        self.symbols, self.calls, self.imports, self.assigns, self.class_edges, self.controls = [], [], [], [], [], []
        self.scope, self.conds, self.deftime = [], [], False
        sid = f'sym:{rel}:<module>:module'
        module = {'id': sid, 'file': rel, 'qualname': '<module>', 'kind': 'module', 'definition_range': [1, max(1, len(src.splitlines()))], 'body_start': 1,
                  'parent': None, 'signature': '<module>', 'decorators': [], 'docstring': None, 'params': [], 'locals': [], 'bases': [],
                  'returns': [], 'yields': [], 'raises': [], 'asserts': [], 'shape_hints': [], 'step_skeleton': []}
        self.symbols.append(module)
        self.scope.append(module)

    def seg(self, node):
        return ast.get_source_segment(self.src, node) or ast.unparse(node)

    def current(self):
        return self.scope[-1]

    def visit_Module(self, node):
        self.current()['step_skeleton'] = self.steps(node.body)
        for statement in node.body:
            self.visit(statement)

    def parameters(self, args):
        result = []
        positional = args.posonlyargs + args.args
        defaults = [None] * (len(positional) - len(args.defaults)) + args.defaults
        for index, (arg, default) in enumerate(zip(positional, defaults)):
            result.append({'name': arg.arg, 'kind': 'posonly' if index < len(args.posonlyargs) else 'positional', 'annotation': ast.unparse(arg.annotation) if arg.annotation else None, 'default': self.seg(default) if default else None})
        if args.vararg:
            result.append({'name': args.vararg.arg, 'kind': 'vararg', 'annotation': ast.unparse(args.vararg.annotation) if args.vararg.annotation else None, 'default': None})
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            result.append({'name': arg.arg, 'kind': 'kwonly', 'annotation': ast.unparse(arg.annotation) if arg.annotation else None, 'default': self.seg(default) if default else None})
        if args.kwarg:
            result.append({'name': args.kwarg.arg, 'kind': 'kwarg', 'annotation': ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None, 'default': None})
        return result

    def definition_expr(self, node, decorator=False):
        old, self.deftime = self.deftime, True
        if decorator and not isinstance(node, ast.Call):
            self.calls.append(self.call_record(node, '@' + self.seg(node), node))
        self.visit(node)
        self.deftime = old

    def define(self, node, kind):
        for decorator in node.decorator_list:
            self.definition_expr(decorator, True)
        if not isinstance(node, ast.ClassDef):
            for default in node.args.defaults + [x for x in node.args.kw_defaults if x is not None]:
                self.definition_expr(default)
        else:
            for base in node.bases:
                self.definition_expr(base)
        parent = self.current()
        if kind == 'function' and parent['kind'] == 'class':
            kind = 'method'
        qual = '.'.join(s['qualname'].split('.')[-1] for s in self.scope[1:])
        qual = (qual + '.' if qual else '') + node.name
        base_id = f'sym:{self.rel}:{qual}:{kind}'
        sid, occurrence = base_id, 1
        existing = {s['id'] for s in self.symbols}
        while sid in existing:
            occurrence += 1
            sid = f'{base_id}#{occurrence}'
        if kind == 'class':
            params, signature = [], node.name
        else:
            params = self.parameters(node.args)
            signature = f'{node.name}({ast.unparse(node.args)})'
            if node.returns:
                signature += ' -> ' + ast.unparse(node.returns)
        record = {'id': sid, 'file': self.rel, 'qualname': qual, 'kind': kind,
                  'definition_range': [node.lineno, node.end_lineno], 'body_start': node.body[0].lineno,
                  'parent': parent['id'], 'signature': signature, 'decorators': [self.seg(d) for d in node.decorator_list],
                  'docstring': ast.get_docstring(node), 'params': params, 'locals': [],
                  'bases': [describe(b) for b in node.bases] if kind == 'class' else [],
                  'returns': [], 'yields': [], 'raises': [], 'asserts': [], 'shape_hints': [],
                  'step_skeleton': self.steps(node.body), 'return_annotation': ast.unparse(node.returns) if kind != 'class' and node.returns else None}
        self.symbols.append(record)
        self.scope.append(record)
        saved, self.conds = self.conds, []
        for statement in node.body:
            self.visit(statement)
        self.conds = saved
        self.scope.pop()

    def visit_FunctionDef(self, node): self.define(node, 'function')
    def visit_AsyncFunctionDef(self, node): self.define(node, 'async_function')
    def visit_ClassDef(self, node): self.define(node, 'class')

    def visit_Lambda(self,node):
        # Lambda body is not executed when the lambda object is constructed.
        for default in node.args.defaults + [x for x in node.args.kw_defaults if x is not None]:
            self.definition_expr(default)

    def call_record(self, node, expression=None, func=None):
        return {'caller': self.current()['id'], 'func': describe(func or node.func), 'expression': expression or self.seg(node),
                'file': self.rel, 'line': node.lineno, 'end_line': node.end_lineno, 'conditions': self.conds[:], 'definition_time': self.deftime}

    def visit_Call(self, node):
        self.calls.append(self.call_record(node))
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({'file': self.rel, 'scope': self.current()['id'], 'module': alias.name, 'name': None, 'alias': alias.asname or alias.name.split('.')[0], 'level': 0, 'line': node.lineno})

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imports.append({'file': self.rel, 'scope': self.current()['id'], 'module': node.module or '', 'name': alias.name, 'alias': alias.asname or alias.name, 'level': node.level, 'line': node.lineno})

    def visit_Assign(self, node):
        for target in node.targets:
            for value in ast.walk(target):
                if isinstance(value, ast.Name) and isinstance(value.ctx, ast.Store) and value.id not in self.current()['locals']:
                    self.current()['locals'].append(value.id)
            if isinstance(target, ast.Name) or isinstance(target, ast.Attribute):
                self.assigns.append({'scope': self.current()['id'], 'file': self.rel, 'target': ast.unparse(target),
                                     'constructor': describe(node.value.func) if isinstance(node.value, ast.Call) else None,
                                     'expression': self.seg(node.value), 'line': node.lineno})
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.current()['locals'].append(node.target.id)
        self.generic_visit(node)

    def visit_Return(self, node):
        self.current()['returns'].append({'line': node.lineno, 'expression': self.seg(node.value) if node.value else None})
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.current()['yields'].append({'line': node.lineno, 'expression': self.seg(node.value) if node.value else None})
        self.generic_visit(node)
    visit_YieldFrom = visit_Yield

    def visit_Raise(self, node):
        self.current()['raises'].append({'line': node.lineno, 'expression': self.seg(node.exc) if node.exc else None})
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.current()['asserts'].append({'line': node.lineno, 'text': self.seg(node)})
        self.generic_visit(node)

    def region(self, label, body):
        self.conds.append(label)
        for statement in body: self.visit(statement)
        self.conds.pop()

    def visit_If(self, node):
        self.visit(node.test)
        self.region('if ' + self.seg(node.test), node.body)
        if node.orelse: self.region('else (not ' + self.seg(node.test) + ')', node.orelse)
        if self.current()['kind'] == 'module' and '__name__' in self.seg(node.test):
            self.controls.append({'file': self.rel, 'source_range': [node.lineno, node.end_lineno], 'test': self.seg(node.test)})

    def visit_For(self, node):
        self.visit(node.iter)
        self.region(f'for {self.seg(node.target)} in {self.seg(node.iter)}', node.body)
        if node.orelse: self.region('for else', node.orelse)
    visit_AsyncFor = visit_For

    def visit_While(self, node):
        self.visit(node.test); self.region('while ' + self.seg(node.test), node.body)
        if node.orelse: self.region('while else', node.orelse)

    def visit_With(self, node):
        for item in node.items: self.visit(item.context_expr)
        self.region('with ' + ', '.join(self.seg(i.context_expr) for i in node.items), node.body)
    visit_AsyncWith = visit_With

    def visit_Try(self, node):
        self.region('try', node.body)
        for handler in node.handlers:
            self.region('except ' + (self.seg(handler.type) if handler.type else 'all'), handler.body)
        if node.orelse: self.region('try else', node.orelse)
        if node.finalbody: self.region('finally', node.finalbody)
    visit_TryStar = visit_Try

    def steps(self, body, prefix='s', depth=0):
        result = []
        for index, statement in enumerate(body):
            children = []
            if depth < 3 and not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for tag, label, nested in [('b', '是/循环体', getattr(statement, 'body', [])), ('o', '否/else', getattr(statement, 'orelse', [])), ('f', 'finally', getattr(statement, 'finalbody', []))]:
                    if nested:
                        children += [{**s, 'branch': label} for s in self.steps(nested, f'{prefix}{index+1}.{tag}.', depth+1)]
                for j, handler in enumerate(getattr(statement, 'handlers', [])):
                    children += [{**s, 'branch': f'except {j+1}'} for s in self.steps(handler.body, f'{prefix}{index+1}.e{j}.', depth+1)]
            result.append({'id': f'{prefix}{index+1}', 'order': index+1, 'kind': type(statement).__name__.lower(),
                           'source_range': [statement.lineno, statement.end_lineno], 'first_line_text': self.src.splitlines()[statement.lineno-1].strip(),
                           'calls': [], 'children': children})
        return result


def extract_project(request):
    root = Path(request['project_root']).resolve()
    inventory = {'indexed_files': [], 'non_python_files': [], 'excluded': [], 'parse_failures': []}
    sources, collectors = {}, []
    visited = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        valid_dirs = []
        for name in sorted(dirs):
            path = Path(directory) / name
            if name in SKIP or not path.resolve().is_relative_to(root) or path.is_symlink():
                inventory['excluded'].append({'path': path.relative_to(root).as_posix(), 'reason': 'excluded directory or symlink'})
            else: valid_dirs.append(name)
        dirs[:] = valid_dirs
        for name in sorted(files):
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            if not path.resolve().is_relative_to(root) or path.is_symlink() or path.suffix.lower() in BINARY or path.stat().st_size > 1024*1024:
                inventory['excluded'].append({'path': rel, 'reason': 'unsafe link, binary or >1MiB'})
                continue
            if path.suffix != '.py':
                inventory['non_python_files'].append(rel)
                continue
            try:
                with tokenize.open(path) as stream: src = stream.read()
                tree = ast.parse(src, filename=rel)
            except (OSError, UnicodeError, SyntaxError, LookupError) as exc:
                inventory['parse_failures'].append({'file': rel, 'error': str(exc), 'line': getattr(exc, 'lineno', None)})
                continue
            collector = Collector(rel, src)
            collector.visit(tree)
            for s in collector.symbols:
                begin, end = s['definition_range']
                s['shape_hints'] = [{'line': i+1, 'text': line.strip()} for i, line in enumerate(src.splitlines()) if begin <= i+1 <= end and re.search(r'\.(view|reshape|permute|transpose|unsqueeze|squeeze|flatten|shape|size)\b|\b(cat|stack|rearrange|einsum)\s*\(', line)]
                s['source_sha256'] = sha_bytes(src.encode('utf-8'))
            collectors.append(collector)
            sources[rel] = src
            inventory['indexed_files'].append({'file': rel, 'sha256': sha_bytes(src.encode('utf-8')), 'original_sha256': sha_bytes(path.read_bytes()), 'line_count': max(1, len(src.splitlines()))})
    from resolve import resolve_graph
    graph = resolve_graph(collectors, request)
    graph['coverage'].update(inventory)
    return graph, inventory, sources
