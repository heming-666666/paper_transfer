import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class ExtractionTests(unittest.TestCase):
    def test_spec_ground_truth(self):
        try:
            from pyextract import extract_project
        except ImportError:
            self.fail('pyextract not implemented yet')
        request = {'project_root': str(ROOT / 'tests/fixtures/mini_proj'),
                   'entries': [{'entry_id': 'entry:train', 'path': 'train.py', 'scenario': 'train'},
                               {'entry_id': 'entry:eval', 'path': 'eval.py', 'scenario': 'eval'}],
                   'limits': {'max_depth': 8, 'max_symbols': 300}}
        graph, inventory, sources = extract_project(request)
        truth = json.loads((ROOT / 'tests/ground_truth.json').read_text(encoding='utf-8'))
        actual = {(e['caller'], e['callee'], e['relation'], e['resolution']) for e in graph['edges']}
        for edge in truth['required']:
            with self.subTest(edge=edge):
                self.assertIn(tuple(edge), actual)
        for caller, expr in truth['unresolved']:
            self.assertTrue(any(e['caller'] == caller and e['expression'] == expr and e['resolution'] == 'unresolved' for e in graph['edges']))
        self.assertFalse(any(e['callee'] == 'sym:utils/helpers.py:compute_default:function' and 'decorated' in e['caller'] for e in graph['edges']))
        self.assertFalse(any(e['callee'] == 'sym:losses.py:normalize:function' and 'Block.run' in e['caller'] for e in graph['edges']))
        self.assertFalse(any(e['callee'] and e['callee'].startswith('ext:builtins.') for e in graph['edges']))
        head = 'sym:models/net.py:Net.head:method'
        self.assertEqual({e['callee'] for e in graph['edges'] if e['caller'] == head}, {'sym:models/net.py:Net.head.scale:function'})
        by_id = {s['id']: s for s in graph['symbols']}
        self.assertEqual(by_id['sym:models/net.py:Net.head.scale:function']['parent'], head)
        self.assertEqual(len(by_id['sym:utils/helpers.py:seed_all:function']['step_skeleton']), 2)
        self.assertTrue(any(s['kind'] == 'if' and s['children'] for s in by_id['sym:utils/helpers.py:normalize:function']['step_skeleton']))
        self.assertEqual(by_id['sym:losses.py:total_loss:function']['returns'][0]['expression'], 'sum(parts.values()), parts')
        closures = {e['entry_id']: set(e['closure']) for e in graph['entries']}
        self.assertNotIn('sym:models/net.py:Net.forward:method', closures['entry:train'])
        self.assertIn('sym:models/net.py:Net.forward:method', closures['entry:eval'])
        self.assertIn('sym:losses.py:total_loss:function', closures['entry:train'] & closures['entry:eval'])
        edge = next(e for e in graph['edges'] if 'losses.total_loss' in e['expression'] and e['caller'] == 'sym:train.py:main:function')
        self.assertTrue(any('for epoch' in c for c in edge['conditions']))
        self.assertTrue(any('if epoch % 2 == 0' in c for c in edge['conditions']))
        self.assertTrue(any(e['expression'].startswith('net.forward(') and e['resolution'] == 'candidate' and e['callee'] == 'sym:models/net.py:Net.forward:method' for e in graph['edges']))

    def test_branch_step_ids_unique(self):
        from pyextract import Collector
        import ast
        source='def f(x):\n    if x:\n        a()\n    else:\n        b()\n'
        collector=Collector('sample.py',source);collector.visit(ast.parse(source))
        function=next(s for s in collector.symbols if s['qualname']=='f')
        ids=[]
        def collect(steps):
            for step in steps:ids.append(step['id']);collect(step['children'])
        collect(function['step_skeleton'])
        self.assertEqual(len(ids),len(set(ids)))


if __name__ == '__main__':
    unittest.main()
