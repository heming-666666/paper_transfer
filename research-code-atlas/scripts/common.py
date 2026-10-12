import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime/windows/site-packages'))
STATUSES = {'confirmed_source', 'observed_runtime', 'inferred', 'unknown', 'conflict', 'not_applicable'}


class InputError(ValueError):
    pass


class EvidenceError(ValueError):
    pass


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise InputError(f'unsafe relative path: {relative}')
    p = (root / relative).resolve()
    if not p.is_relative_to(root):
        raise InputError(f'path escapes root: {relative}')
    return p


def request_at(path, check_output=False):
    path = Path(path).resolve()
    data = read(path)
    if data.get('schema_version', '1.0') != '1.0':
        raise InputError('request.schema_version must be 1.0')
    root = (path.parent / data.get('project_root', '')).resolve()
    if not data.get('project_root') or not root.is_dir():
        raise InputError('project_root must be an existing directory')
    data['project_root'] = str(root)
    entries = data.get('entries', [])
    if not entries or len({x.get('entry_id') for x in entries}) != len(entries):
        raise InputError('entries must be nonempty with unique entry_id')
    for entry in entries:
        if not entry.get('entry_id') or entry.get('scenario', 'other') not in ('train', 'eval', 'infer', 'other'):
            raise InputError('invalid entry id/scenario')
        if not safe_path(root, entry['path']).is_file():
            raise InputError(f"entry missing: {entry['path']}")
        for conf in entry.get('configs', []):
            if not safe_path(root, conf).is_file():
                raise InputError(f'config missing: {conf}')
        for key in ('args', 'overrides'):
            if not isinstance(entry.get(key, []), list):
                raise InputError(f'entries.{key} must be an array; never executed')
    paper = data.get('paper') or {}
    if paper.get('path'):
        p = (path.parent / paper['path']).resolve()
        if not p.is_file() or p.suffix.lower() not in ('.pdf', '.md', '.txt'):
            raise InputError('paper path must be an existing PDF/MD/TXT')
        paper['path'] = str(p)
    data['paper'] = paper
    if not data.get('output_dir'):
        raise InputError('output_dir is required')
    out = (path.parent / data['output_dir']).resolve()
    if out.is_relative_to(root):
        raise InputError('output_dir must be outside the read-only project')
    if check_output and out.exists() and any(out.iterdir()):
        raise InputError('output_dir already nonempty; use a new run directory')
    data['output_dir'] = str(out)
    limits = data.setdefault('limits', {})
    for key, default in [('max_depth', 8), ('max_symbols', 300)]:
        limits.setdefault(key, default)
        if not isinstance(limits[key], int) or limits[key] < 1:
            raise InputError(f'limits.{key} must be a positive integer')
    if data.get('runtime', {}).get('enabled'):
        raise InputError('runtime capture is not implemented; static tool never executes project code')
    return data
