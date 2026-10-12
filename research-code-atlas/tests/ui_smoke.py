"""Real file:// Chromium checks, with no nonlocal network and explicit event waits."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common import write
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime/browsers')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args();run=Path(args.run_dir).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    checks,errors=[],[]
    def check(name,observed,expected=True):
        passed=observed==expected;checks.append({'name':name,'expected':expected,'observed':observed,'passed':passed})
        if not passed:raise AssertionError(name+': '+str(observed))
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1550,'height':1100})
            def route(route):
                if route.request.url.startswith(('file:','http://127.0.0.1:','http://localhost:')):route.continue_()
                else:errors.append({'kind':'external','url':route.request.url});route.abort()
            context.route('**/*',route)
            page=context.new_page();page.on('pageerror',lambda e:errors.append({'kind':'pageerror','message':str(e)}))
            page.on('console',lambda m:errors.append({'kind':'console','message':m.text}) if m.type=='error' else None)
            page.on('requestfailed',lambda r:errors.append({'kind':'request','url':r.url}))
            page.goto((run/'viewer/index.html').as_uri());page.wait_for_selector('body[data-ready="true"]')
            check('file URL offline ready',page.url.startswith('file:'))
            check('19 reviewed functions', '19/19' in page.locator('#coverage').inner_text())
            def select(sid):
                page.get_by_test_id('search').fill(sid.split(':')[-2].split('.')[-1])
                page.locator(f'#search-results button[data-symbol="{sid}"]').click()
                page.wait_for_function('(sid)=>window.atlasState.selected===sid',arg=sid)
            select('sym:losses.py:normalize:function');check('loss normalize exact source','losses.py' in page.get_by_test_id('source-heading').inner_text())
            select('sym:utils/helpers.py:normalize:function');check('helper normalize exact source','utils/helpers.py' in page.get_by_test_id('source-heading').inner_text())
            page.go_back();page.wait_for_function('window.atlasState.selected==="sym:losses.py:normalize:function"')
            check('browser back restores exact symbol','losses.py' in page.get_by_test_id('source-heading').inner_text())
            page.go_forward();page.wait_for_function('window.atlasState.selected==="sym:utils/helpers.py:normalize:function"')
            check('browser forward restores exact symbol','utils/helpers.py' in page.get_by_test_id('source-heading').inner_text())
            select('sym:models/net.py:Net.forward:method')
            page.locator('#card button[data-symbol="sym:models/net.py:Net.head:method"]').first.click()
            page.wait_for_function('window.atlasState.selected==="sym:models/net.py:Net.head:method"')
            check('card callee navigates exact function','Net.head' in page.get_by_test_id('card-title').inner_text())
            page.locator('#card button[data-symbol="sym:models/net.py:Net.forward:method"]').first.click()
            page.wait_for_function('window.atlasState.selected==="sym:models/net.py:Net.forward:method"')
            check('card caller navigates exact function','Net.forward' in page.get_by_test_id('card-title').inner_text())
            page.locator('[data-view="flow"]').click();page.wait_for_selector('#flow:not([hidden])')
            page.locator('#flow button[data-symbol]').first.click()
            check('internal step source highlight',page.locator('#code .hl').count()>0)
            page.locator('[data-view="tree"]').click();page.wait_for_selector('#tree:not([hidden])')
            check('recursion ends with marker','↻' in page.locator('#tree').text_content())
            page.locator('[data-view="graph"]').click();page.wait_for_selector('#graph-panel:not([hidden])')
            page.wait_for_function('window.atlasState.cy && window.atlasState.cy.nodes().length>0')
            check('local dagre call graph',page.evaluate('window.atlasState.cy.nodes().length>3'))
            check('unresolved dotted edges',page.evaluate('window.atlasState.cy.edges().some(e=>e.data("resolution")==="unresolved")'))
            page.locator('#resolution').select_option('candidate')
            check('resolution filter actual graph',page.evaluate('window.atlasState.cy.edges().every(e=>e.data("resolution")==="candidate")'))
            page.locator('#resolution').select_option('all')
            page.locator('[data-tab="paper"]').click();page.wait_for_selector('#paper:not([hidden])')
            check('paper direct/conflict/not found',all(page.locator('#paper .'+x).count()>0 for x in ('direct','conflict','not_found')))
            page.locator('#paper button[data-symbol="sym:models/net.py:Net.head.scale:function"]').first.click()
            page.wait_for_function('window.atlasState.selected==="sym:models/net.py:Net.head.scale:function"')
            check('paper mapping accurate definition','models/net.py' in page.get_by_test_id('source-heading').inner_text())
            page.locator('[data-tab="experiments"]').click();page.wait_for_selector('#experiments:not([hidden])')
            check('experiment mismatch and unused','mismatch' in page.locator('#experiments').inner_text() and 'defined_not_consumed' in page.locator('#experiments').inner_text())
            page.locator('#experiments button[data-symbol="sym:train.py:main:function"]').first.click()
            page.wait_for_function('window.atlasState.selected==="sym:train.py:main:function"')
            check('config consumer exact source','train.py' in page.get_by_test_id('source-heading').inner_text())
            select('sym:losses.py:total_loss:function');check('train scenario literal batch','[2]' in page.get_by_test_id('card').inner_text())
            page.get_by_test_id('entry').select_option('entry:eval');page.wait_for_function('window.atlasState.entry==="entry:eval"')
            select('sym:losses.py:total_loss:function');check('eval scenario preserved','来自net.forward' in page.get_by_test_id('card').inner_text())
            select('sym:models/net.py:Net.head.scale:function')
            page.locator('[data-tab="impact"]').click();page.wait_for_selector('#impact:not([hidden])')
            check('candidate impact warning','动态调用' in page.locator('#impact').inner_text())
            page.locator('#impact button[data-symbol="sym:models/net.py:Net.head:method"]').first.click()
            page.wait_for_function('window.atlasState.selected==="sym:models/net.py:Net.head:method"')
            check('impact chain exact source','models/net.py' in page.get_by_test_id('source-heading').inner_text())
            before=page.url;page.reload();page.wait_for_selector('body[data-ready="true"]');check('hash restored',page.url==before and page.evaluate('window.atlasState.selected==="sym:models/net.py:Net.head:method"'))
            select('sym:models/blocks.py:Block.run:method');check('script injection absent',page.evaluate('typeof window.__x==="undefined"'))
            check('attack text shown as text','</script><script>window.__x=1</script>' in page.get_by_test_id('source').inner_text())
            page.screenshot(path=str(out/'desktop.png'),full_page=True)
            page.set_viewport_size({'width':650,'height':900})
            check('narrow cards accessible',page.get_by_test_id('card-title').is_visible())
            check('narrow page no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'))
            page.screenshot(path=str(out/'narrow.png'),full_page=True)
            check('no console/page/nonlocal errors',errors,[])
            no_paper=ROOT/'examples/demo-no-paper/viewer/index.html'
            if no_paper.exists():
                page.goto(no_paper.as_uri());page.wait_for_selector('body[data-ready="true"]')
                page.locator('[data-tab="paper"]').click();page.wait_for_selector('#paper:not([hidden])')
                check('no paper viewer remains usable','未提供论文' in page.locator('#paper').inner_text())
            browser.close()
        return 0
    except Exception as exc:
        errors.append({'kind':'test','message':str(exc)});return 3
    finally:
        write(out/'browser-validation.json',{'status':'passed' if checks and not errors else 'failed','checks':checks,'errors':errors})
        print(json.dumps({'checks':len(checks),'errors':errors},ensure_ascii=False))


if __name__=='__main__':sys.exit(main())
