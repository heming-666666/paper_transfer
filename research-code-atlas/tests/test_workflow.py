import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from common import read,write,EvidenceError,InputError,sha_bytes
from atlas import extract,batches
from configs import config_index
from paper import extract_paper,find_quote
from checks import Checker
from assemble import assemble,validate
from render import render
from build_demo import build


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'checks').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'checks');self.root=Path(self.temp.name)
        self.project=self.root/'project';shutil.copytree(ROOT/'tests/fixtures/mini_proj',self.project)
        self.run=self.root/'run'
        self.request=self.root/'request.json'
        write(self.request,{'schema_version':'1.0','project_root':str(self.project),'output_dir':str(self.run),
            'entries':[{'entry_id':'entry:train','path':'train.py','scenario':'train','args':[]},{'entry_id':'entry:eval','path':'eval.py','scenario':'eval','args':[]}],
            'paper':{'path':str(ROOT/'tests/fixtures/mini_paper.md')},'limits':{'max_depth':8,'max_symbols':300}})
        extract(self.request);config_index(self.run);extract_paper(self.run);batches(self.run,4)

    def tearDown(self):self.temp.cleanup()

    def test_full_pipeline_and_source_hash(self):
        build(self.run);result=assemble(self.run);self.assertEqual(result['explained'],19)
        self.assertEqual(validate(self.run)['status'],'passed')
        for s in read(self.run/'inventory.json')['indexed_files']:
            self.assertEqual(sha_bytes((self.run/'sources'/s['file']).read_bytes()),s['sha256'])
        self.assertEqual(validate(self.run,True)['freshness']['status'],'matched')
        file=self.project/'models/net.py';file.write_text(file.read_text(encoding='utf-8')+'\n# own temporary fixture change\n',encoding='utf-8')
        self.assertEqual(validate(self.run,True)['freshness']['status'],'stale')
        self.assertTrue(Path(render(self.run)['index']).exists())
        data=(self.run/'viewer/atlas-sources.js').read_text(encoding='utf-8')
        self.assertNotIn('</script>',data);self.assertIn('\\u003c/script>',data)

    def test_bad_evidence_precise_paths(self):
        build(self.run)
        batch=read(next((self.run/'notes').glob('batch_*.json')))
        variants=[]
        bad=copy.deepcopy(batch);bad['items'][0]['symbol_id']='sym:no.py:missing:function';variants.append((bad,'.symbol_id'))
        bad=copy.deepcopy(batch);bad['items'][0]['steps'][0]['source_range']=[999,1000];variants.append((bad,'.source_range'))
        bad=copy.deepcopy(batch);bad['items'][0]['outputs'][0].update(status='confirmed_source',evidence=[]);variants.append((bad,'.evidence'))
        for bad,expected in variants:
            with self.subTest(expected=expected),self.assertRaises(EvidenceError) as error:Checker(self.run).check(bad,'notes')
            self.assertIn(expected,str(error.exception))
        pmap=read(self.run/'paper-map.json');pmap['contributions'][0]['paper_evidence'][0]['quote']='this fabricated sentence never appears on any fixture page'
        with self.assertRaisesRegex(EvidenceError,'quote not found'):Checker(self.run).check(pmap,'paper-map')

    def test_configs_and_per_entry_contracts(self):
        items={x['id']:x for x in read(self.run/'config-index.json')['items']}
        self.assertEqual(items['unused_flag']['consumption'],'defined_not_consumed')
        self.assertTrue(any('args.lr' in x['text'] for x in items['lr']['consumers']))
        build(self.run);assemble(self.run);atlas=read(self.run/'atlas.json')
        total=next(s for s in atlas['symbols'] if s['qualname']=='total_loss')
        contracts=total['note']['scenario_contracts']
        self.assertEqual({c['entry_id'] for c in contracts},{'entry:train','entry:eval'})
        self.assertEqual(contracts[0]['inputs'][0]['shape'],[2]);self.assertIsNone(contracts[1]['inputs'][0]['shape'])
        statuses={m['status'] for c in atlas['paper']['contributions'] for m in c['code_mappings']}
        self.assertEqual(statuses,{'direct','conflict','not_found'})
        self.assertEqual({e['status'] for e in atlas['experiments']},{'match','mismatch','defined_not_consumed','paper_only'})

    def test_corrupt_and_unknown_not_executed(self):
        from pyextract import extract_project
        (self.project/'broken.py').write_text('def invalid(:\n',encoding='utf-8')
        (self.project/'never.py').write_text("raise RuntimeError('must not import')\n",encoding='utf-8')
        graph,inventory,sources=extract_project(read(self.run/'request.json'))
        self.assertTrue(any(x['file']=='broken.py' for x in inventory['parse_failures']))
        self.assertIn('never.py',sources)
        request=read(self.request);request['output_dir']=str(self.root/'run-small');request['limits']={'max_depth':1,'max_symbols':2};write(self.root/'small.json',request)
        extract(self.root/'small.json')
        self.assertTrue(read(self.root/'run-small/structure.json')['coverage']['truncated'])
        with self.assertRaises(InputError):extract(self.request)

    def test_no_paper_and_pdf_reader(self):
        request=read(self.request);request['paper']=None;request['output_dir']=str(self.root/'no-paper');write(self.root/'no-paper.json',request)
        extract(self.root/'no-paper.json');self.assertEqual(extract_paper(self.root/'no-paper')['status'],'missing')
        from pypdf import PdfWriter
        document=PdfWriter();document.add_blank_page(width=300,height=400);pdf=self.root/'blank.pdf'
        with pdf.open('wb') as f:document.write(f)
        request['output_dir']=str(self.root/'pdf-run');request['paper']={'path':str(pdf)};write(self.root/'pdf.json',request)
        extract(self.root/'pdf.json');status=extract_paper(self.root/'pdf-run')
        self.assertEqual(status['pages'],1);self.assertTrue(status['warnings'])
        self.assertTrue(find_quote('the\n learn-\ning rule','the learning rule'))

    def test_pdf_text_pages_and_quote(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
        document=PdfWriter()
        for text in ['Original method normalizes each feature with a verified page quote.', 'Experiments use a learning rate of 3e-4 and twenty epochs in this fixture.']:
            page=document.add_blank_page(width=300,height=400)
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):document._add_object(font)})})
            stream=DecodedStreamObject();stream.set_data(f'BT /F1 10 Tf 20 200 Td ({text}) Tj ET'.encode('ascii'))
            page[NameObject('/Contents')]=document._add_object(stream)
        pdf=self.root/'text.pdf'
        with pdf.open('wb') as f:document.write(f)
        request=read(self.request);request['paper']={'path':str(pdf)};request['output_dir']=str(self.root/'text-pdf-run');write(self.root/'text-pdf.json',request)
        extract(self.root/'text-pdf.json');status=extract_paper(self.root/'text-pdf-run')
        self.assertEqual(status['pages'],2)
        self.assertTrue(find_quote((self.root/'text-pdf-run/paper/pages/page_002.txt').read_text(encoding='utf-8'),'a learning rate of 3e-4'))


if __name__=='__main__':unittest.main()
