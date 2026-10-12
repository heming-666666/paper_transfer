"""Standalone static atlas CLI: never imports or executes the analyzed project."""
from pathlib import Path
import argparse
import datetime
import functools
import http.server
import importlib.util
import json
import os
import shutil
import sys
import traceback
import urllib.parse

if sys.version_info < (3, 10):
    sys.stderr.write('需要 Python >= 3.10；使用包内 Windows Python 或现有兼容解释器\n')
    sys.exit(2)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, InputError, EvidenceError, read, write, request_at, safe_path, sha_bytes


def load_run(path):
    path = Path(path).resolve()
    return path, read(path / 'request.json'), read(path / 'structure.json')


def inspect(request_path):
    request = request_at(request_path, check_output=True)
    return {'ready': True, 'python': sys.version.split()[0], 'project_root': request['project_root'],
            'entries': request['entries'], 'pyyaml': importlib.util.find_spec('yaml') is not None,
            'pdf_parser': 'bundled pypdf' if importlib.util.find_spec('pypdf') else shutil.which('pdftotext'),
            'runtime': 'not implemented; never executes target', 'output_dir': request['output_dir']}


def extract(request_path):
    request = request_at(request_path, check_output=True)
    from pyextract import extract_project
    structure, inventory, sources = extract_project(request)
    run = Path(request['output_dir'])
    run.mkdir(parents=True, exist_ok=True)
    write(run / 'request.json', request)
    write(run / 'inventory.json', inventory)
    write(run / 'structure.json', structure)
    for rel, source in sources.items():
        p = safe_path(run / 'sources', rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(source, encoding='utf-8', newline='\n')
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(run / 'manifest.json', {'schema_version': '1.0', 'snapshot_at': timestamp, 'files': inventory['indexed_files'],
                                'request_sha256': sha_bytes((run / 'request.json').read_bytes()),
                                'structure_sha256': sha_bytes((run / 'structure.json').read_bytes())})
    return {'run_dir': str(run), 'symbols': len(structure['symbols']), 'edges': len(structure['edges']), 'coverage': structure['coverage']}


def batches(run_dir, size):
    if not 1 <= size <= 20:
        raise InputError('--size must be 1..20')
    run, request, structure = load_run(run_dir)
    selected = sorted(structure['symbols'], key=lambda s: (min([e['depth_of'][s['id']] for e in structure['entries'] if s['id'] in e['depth_of']] or [999]), s['id']))
    functions = [s for s in selected if s['kind'] not in ('module', 'class')][:request['limits']['max_symbols']]
    directory = run / 'notes/todo'
    if directory.exists() and any(directory.iterdir()):
        raise InputError('todo batches already exist; reuse instead of overwriting')
    from checks import prefilled
    count = 0
    for index in range(0, len(functions), size):
        count += 1
        items = []
        for s in functions[index:index+size]:
            items.append({'symbol_id': s['id'], 'prefilled': prefilled(s), 'role': 'other', 'summary': '', 'purpose': '',
                          'inputs': [], 'outputs': [], 'side_effects': [], 'exceptions': [], 'steps': s['step_skeleton'],
                          'paper_refs': [], 'config_refs': [], 'scenario_contracts': [], 'change_notes': '',
                          'needs_context': ['待Agent按reading-protocol深读'], 'analysis_status': 'pending'})
        write(directory / f'batch_{count:03}.json', {'schema_version': '1.0', 'items': items})
    return {'batches': count, 'functions': len(functions), 'todo': str(directory)}


def serve(run_dir, port):
    if not 0 <= port <= 65535:
        raise InputError('--port must be 0..65535')
    directory = Path(run_dir).resolve() / 'viewer'
    if not (directory / 'index.html').is_file():
        raise InputError('render the viewer first')
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            raw = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            # A single leading slash is HTTP-root syntax; reject path traversal/drive/links.
            if '\\' in raw or '..' in raw.split('/') or raw.startswith('//') or ':' in raw:
                self.send_error(400); return
            p = (directory / raw.lstrip('/')).resolve()
            if not p.is_relative_to(directory):
                self.send_error(403); return
            return super().do_GET()
        def log_message(self, fmt, *args):
            pass
    handler = functools.partial(Handler, directory=str(directory))
    try:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    except OSError:
        if port == 0: raise
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}', 'directory': str(directory), 'stop': 'Ctrl+C'}, ensure_ascii=False), flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


def parser():
    p = argparse.ArgumentParser(description='Research Code Atlas：只读静态Python、论文/配置对照、双击离线HTML')
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'extract'):
        command = sub.add_parser(name)
        command.add_argument('--request', required=True)
    for name in ('configs', 'paper', 'batches', 'check', 'assemble', 'validate', 'render', 'serve'):
        command = sub.add_parser(name)
        command.add_argument('--run-dir', required=True)
        if name == 'batches': command.add_argument('--size', type=int, default=4)
        if name == 'check': command.add_argument('--file', required=True)
        if name == 'validate': command.add_argument('--recheck-source', action='store_true')
        if name == 'serve': command.add_argument('--port', type=int, default=0)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'inspect': result = inspect(args.request)
        elif args.command == 'extract': result = extract(args.request)
        elif args.command == 'batches': result = batches(args.run_dir, args.size)
        elif args.command == 'configs':
            from configs import config_index
            result = config_index(args.run_dir)
        elif args.command == 'paper':
            from paper import extract_paper
            result = extract_paper(args.run_dir)
        elif args.command == 'check':
            from checks import check_file
            result = check_file(args.run_dir, args.file)
        elif args.command == 'assemble':
            from assemble import assemble
            result = assemble(args.run_dir)
        elif args.command == 'validate':
            from assemble import validate
            result = validate(args.run_dir, args.recheck_source)
        elif args.command == 'render':
            from render import render
            result = render(args.run_dir)
        elif args.command == 'serve': return serve(args.run_dir, args.port)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except InputError as exc:
        print(f'[ERROR] {exc}', file=sys.stderr); return 2
    except EvidenceError as exc:
        print(f'[ERROR] {exc}', file=sys.stderr); return 3
    except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        print(f'[ERROR] input/schema: {exc}', file=sys.stderr); return 2
    except KeyboardInterrupt:
        return 130
    except Exception:
        traceback.print_exc(); return 1


if __name__ == '__main__':
    sys.exit(main())
