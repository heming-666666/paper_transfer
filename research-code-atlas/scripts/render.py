import json
from pathlib import Path
import shutil
import subprocess
from common import ROOT, read, safe_path, write, InputError
from assemble import validate


def safe_js(data):
    return json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')


def render(run_dir):
    run=Path(run_dir).resolve();validate(run)
    atlas=read(run/'atlas.json');directory=run/'viewer';directory.mkdir(exist_ok=True)
    for source in (ROOT/'assets/viewer').rglob('*'):
        if source.is_file():
            target=directory/source.relative_to(ROOT/'assets/viewer');target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    sources={s['file']:safe_path(run/'sources',s['file']).read_text(encoding='utf-8') for s in atlas['sources']}
    pages={p.name:p.read_text(encoding='utf-8') for p in (run/'paper/pages').glob('*.txt')} if (run/'paper/pages').exists() else {}
    atlas['paper_pages']=pages
    (directory/'atlas-data.js').write_text('window.ATLAS_DATA = '+safe_js(atlas)+';\n',encoding='utf-8')
    (directory/'atlas-sources.js').write_text('window.ATLAS_SOURCES = '+safe_js(sources)+';\n',encoding='utf-8')
    node=shutil.which('node')
    smoke={'status':'not_available','reason':'Node not required at runtime; unavailable for optional JS smoke'}
    if node:
        command=[node,'-e',"global.window={};require('./atlas-data.js');require('./atlas-sources.js');console.log('DATA_JS_OK',window.ATLAS_DATA.symbols.length)"]
        result=subprocess.run(command,cwd=directory,capture_output=True,text=True,encoding='utf-8')
        smoke={'command':command,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        if result.returncode:raise InputError('data JS smoke failed: '+result.stderr)
    write(run/'render-validation.json',smoke)
    return {'index':str(directory/'index.html'),'file_url':(directory/'index.html').as_uri(),'js_smoke':smoke}
