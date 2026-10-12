import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SKIP={'checks','reports','__pycache__','.pytest_cache','.git'}


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description='自包含Skill文件集合/哈希核验，不联网')
    p.add_argument('--write',action='store_true',help='维护时刷新清单；默认只核验')
    args=p.parse_args()
    try:
        files={}
        for directory,dirs,names in os.walk(ROOT):
            dirs[:]=sorted(d for d in dirs if d not in SKIP)
            for d in dirs:
                if not (Path(directory)/d).resolve().is_relative_to(ROOT):raise ValueError('external directory link')
            for name in sorted(names):
                path=Path(directory)/name
                if name=='package-manifest.json' or path.suffix in ('.pyc','.pyo'):continue
                if not path.resolve().is_relative_to(ROOT):raise ValueError('external file link')
                files[path.relative_to(ROOT).as_posix()]=path
        manifest=ROOT/'package-manifest.json'
        if args.write:
            data={'schema_version':'1.0','files':[{'path':rel,'bytes':path.stat().st_size,'sha256':digest(path)} for rel,path in files.items()]}
            manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        data=json.loads(manifest.read_text(encoding='utf-8'))
        if {x['path'] for x in data['files']}!=set(files) or len(data['files'])!=len(files):raise ValueError('package file set differs')
        for item in data['files']:
            path=files[item['path']]
            if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:raise ValueError('hash mismatch: '+item['path'])
        print(json.dumps({'status':'PACKAGE_OK','files':len(files),'bytes':sum(x['bytes'] for x in data['files'])},ensure_ascii=False))
        return 0
    except Exception as e:
        print(str(e),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
