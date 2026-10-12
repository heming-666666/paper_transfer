"""Prepare the documented fixture's reviewed Chinese cards; not a generic auto-explainer."""
from pathlib import Path
import argparse
import copy
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common import read,write

MEANINGS={
('train.py','build'):('model','读取cfg[dim]构造Net，返回模型对象。','把入口的配置字典转成具体构造；main保存返回值供loss使用。','映射/支持键访问对象','Net对象'),
('train.py','main'):('entry','解析演示参数，设置种子，按epoch奇偶选择loss分支，然后有一次动态调用。','组织示例入口；没有optimizer、backward或数据集，不把循环称为完整训练。','无参数','fact(3)的返回；动态fn执行可能先抛异常'),
('eval.py','evaluate'):('eval','构造Net(8)、显式forward，再把输出交给total_loss，返回指标字典。','演示第二入口与共享loss；这是静态代码，不是已运行评估。','无参数','dict(total,n)'),
('models/net.py','Net.__init__'):('model','构造Block并保存dim。','初始化组合属性，供forward通过self.block调用。','dim（未验证类型）','None；构造表达式的结果是新Net对象'),
('models/net.py','Net.forward'):('model','经Block.run获得h，再送入head。','把归一化块与缩放头串接；block.run由属性初始化候选解析。','可迭代数值特征x','head返回的list'),
('models/net.py','Net.head'):('model','定义内部scale，再对h逐元素乘2，返回列表。','缩放Block特征；与测试论文的乘3冲突。','可迭代h','list，元素为scale(v)'),
('models/net.py','Net.head.scale'):('util','把v乘以2。','仅在head的列表推导中使用；非head外层的其他函数调用。','支持乘法的v','v*2'),
('models/net.py','Net.__call__'):('model','可调用对象接口转发到forward。','让Net实例可像函数使用；total_loss的参数model仍静态未解析。','x','forward返回值'),
('models/blocks.py','Block.__init__'):('model','保存dim。','记录构造参数；run未消费这个维度，不据dim=4猜输入shape。','dim','None'),
('models/blocks.py','Block.run'):('model','调用utils.helpers.normalize处理输入。','测试论文归一化块的直接实现路径；不是losses.normalize。','x（可求和并除法的迭代容器）','零和时原输入，否则归一化list'),
('utils/helpers.py','seed_all'):('util','设置Python random种子并修改模块_STATE。','为演示输入设置随机状态；未涉及torch/numpy种子。','seed','None'),
('utils/helpers.py','normalize'):('data','求输入和；和为0时直接返回x，否则逐项除以和。','让非零和特征的输出和为1；零和分支不满足此归一化结论。','可迭代且支持求和/除法的x','原输入或list[number]'),
('utils/helpers.py','compute_default'):('util','返回常量1。','在decorated定义时用作默认值表达式。','无参数','int，字面常量1'),
('utils/helpers.py','deco'):('util','原样返回f。','在定义decorated时作为装饰器被外层模块调用。','f对象','同一f对象'),
('utils/helpers.py','decorated'):('util','直接返回x，默认值表达式在定义时计算。','演示默认值和装饰器的执行归属，不把compute_default算为本函数调用。','x，默认表达式compute_default()','x'),
('utils/helpers.py','fact'):('util','n<=1返回1，否则递归乘n。','演示可导航递归；main传3，但源码没有整数/范围校验。','n，意图为整数；未验证','数值，递归结果'),
('utils/helpers.py','dyn_x'):('util','返回字符串dynamic。','getattr可能选中的候选，但图中fn()不能据字符串拼接冒充已解析调用。','无参数','str'),
('losses.py','normalize'):('loss','逐元素取abs并生成列表。','为total_loss的reg计数提供列表；不是归一化到和1。','支持abs的可迭代v','list'),
('losses.py','total_loss'):('loss','调用未知参数model，计算sum(out)和abs列表长度，返回总和与分项。','两个入口共享的演示损失；mse名字不表示源码真的计算了均方误差。','model可调用对象、batch','tuple(总和,dict(mse,reg))')}


def io(name,type_text,ev,reason,shape=None,status='inferred',default=None):
    return {'name':name,'container_path':[name],'type':type_text,'shape':shape,'dimensions':{},'dtype':None,'device':None,'units':None,'default':default,'constraints':[],
            'status':status,'evidence':[ev],'reason':reason}


def build(run):
    run=Path(run).resolve();structure=read(run/'structure.json');symbols={s['id']:s for s in structure['symbols']}
    def ref(s):return f"{s['file']}:{s['definition_range'][0]}-{s['definition_range'][1]}"
    for path in sorted((run/'notes/todo').glob('batch_*.json')):
        data=read(path)
        for note in data['items']:
            s=symbols[note['symbol_id']];role,summary,purpose,input_text,output_text=MEANINGS[(s['file'],s['qualname'])];ev=ref(s)
            note.update(role=role,summary=summary,purpose=purpose,analysis_status='done',needs_context=[],change_notes='保持返回容器与分支语义；未运行目标，实际shape/类型仍需对应样例验证。')
            note['inputs']=[io(p['name'],input_text,ev,'源码未提供tensor shape；fixture是Python数值/容器，不是张量模型',default=p['default']) for p in s['params'] if p['name']!='self']
            note['outputs']=[io('return',output_text,ev,'依据return表达式/消费者静态说明；没有运行观测，不虚构tensor shape')]
            def explain_steps(steps):
                for step in steps:
                    step.update(title=step['first_line_text'],action='执行源码中的'+step['kind']+'语句：'+step['first_line_text'],why='这一语句属于当前函数；条件/循环与返回路径见源码。',inputs=[],outputs=[])
                    explain_steps(step['children'])
            explain_steps(note['steps'])
            if s['qualname']=='seed_all':note['side_effects']=[{'text':'修改random全局状态与模块_STATE[seed]','status':'confirmed_source','evidence':[ev]}]
            elif s['qualname'].endswith('__init__'):note['side_effects']=[{'text':'写入实例属性；不影响原项目文件','status':'confirmed_source','evidence':[ev]}]
            if s['file']=='models/blocks.py' and s['qualname']=='Block.run' or s['file']=='utils/helpers.py' and s['qualname']=='normalize':note['paper_refs']=['c2']
            if s['qualname'] in ('Net.head','Net.head.scale'):note['paper_refs']=['c1']
            if s['file']=='train.py' and s['qualname']=='main':note['config_refs']=['lr','epochs','unused_flag']
            if s['id']=='sym:losses.py:total_loss:function':
                for entry_id,shape,meaning in [('entry:train',[2],'调用行明确传[1.0,2.0]；这是示意列表长度，不是运行tensor shape'),('entry:eval',None,'来自net.forward的out；具体形状未运行确认')]:
                    edge=next(e for e in s['callers'] if e['caller'].startswith('sym:train.py:' if entry_id=='entry:train' else 'sym:eval.py:'))
                    line=edge['callsite']['line'];site=f"{edge['callsite']['file']}:{line}-{line}"
                    note['scenario_contracts'].append({'entry_id':entry_id,'callsite':edge['callsite'],'conditions':edge['conditions'],
                         'inputs':[io('batch','literal list' if shape else 'forward输出',site,meaning,shape)],'outputs':note['outputs'],'evidence':[site]})
        write(run/'notes'/path.name,data)
    for entry in structure['entries']:
        root=entry['root_symbol'];main='sym:train.py:main:function' if entry['scenario']=='train' else 'sym:eval.py:evaluate:function'
        core=[main,'sym:losses.py:total_loss:function','sym:losses.py:normalize:function','sym:utils/helpers.py:normalize:function','sym:models/net.py:Net.forward:method','sym:models/net.py:Net.head:method']
        core=[sid for sid in core if sid in entry['closure']]
        overview={'entry_id':entry['entry_id'],'summary':'自有教学fixture：'+('参数→种子→构造→交替loss→动态调用→递归返回；不是真实训练。' if entry['scenario']=='train' else '构造Net→显式forward→共享loss→指标字典；未执行。'),
                  'stages':[{'order':1,'title':'入口控制与构造','description':'静态入口和参数/构造源码，未运行。','symbols':[main]},
                            {'order':2,'title':'计算与结果','description':'只展示已解析/候选关系；参数可调用model仍未知。','symbols':core[1:]}],
                  'core_symbols':[{'id':sid,'reason':'入口闭包中的控制/模型/loss关键函数'} for sid in core], 'learning_path':core,
                  'dataflow':[{'order':1,'symbol_id':'sym:losses.py:total_loss:function','line_ref':ref(symbols['sym:losses.py:total_loss:function']),
                               'variable':'batch → model(batch) → parts → (total,parts)','container_path':['batch'],'shape':None,
                               'meaning':'示意静态流程；model是参数，未知实际可调用对象。mse字段只是sum(out)，不是均方误差公式。',
                               'status':'unknown','reason':'缺运行样例及参数可调用对象的确认','evidence':[ref(symbols['sym:losses.py:total_loss:function'])]}]}
        write(run/'notes'/('overview_'+entry['entry_id'].replace(':','_')+'.json'),overview)
    def contribution(cid,claim,quote,compared,mechanism,mappings,conflicts):
        return {'id':cid,'claim':claim,'compared_to':compared,'mechanism':mechanism,'paper_evidence':[{'page':2 if cid!='c3' else 1,'quote':quote}],
                'code_mappings':mappings,'key_configs':[],'io_change':'fixture数值列表；不是张量观测','modification_constraints':'保持原论文/源码冲突，不擅自裁决或改项目','conflicts':conflicts}
    def mapping(sid,status,paper_step,code_step):
        return {'symbol_id':sid,'evidence':[ref(symbols[sid])],'status':status,'step_alignment':[{'paper_step':paper_step,'code_step':code_step,'note':'fixture逐步源码对照'}],'on_entry_path':None}
    pmap={'status':'available','paper':{'title':'Mini Paper（测试材料，非真实论文）','source':str(ROOT/'tests/fixtures/mini_paper.md'),'pages':3},'contributions':[
        contribution('c1','缩放头（存在冲突）','The head multiplies each feature by 3.',None,'论文乘3，代码内部scale乘2。',[mapping('sym:models/net.py:Net.head.scale:function','conflict','逐项乘3','s1')],['论文×3与源码×2不一致']),
        contribution('c2','归一化块','The block normalizes the input so that it sums to one.',None,'非零和分支归一化；零和早退是适用边界。',[mapping('sym:models/blocks.py:Block.run:method','direct','调用归一化','s1'),mapping('sym:utils/helpers.py:normalize:function','direct','逐元素除以和','s3')],[]),
        contribution('c3','对比记忆库未找到','(3) a contrastive memory bank.',None,'教学代码中未实现记忆库。',[{'symbol_id':None,'evidence':[],'status':'not_found','step_alignment':[],'on_entry_path':None}],[])]}
    write(run/'paper-map.json',pmap)
    conf=read(run/'config-index.json');bykey={c['id']:c for c in conf['items']};experiments=[]
    for key,paper_value,quote,status,title in [('lr','3e-4','a learning rate of 3e-4','mismatch','学习率'),('epochs',2,'We train for 2 epochs','match','epoch次数'),('unused_flag',None,None,'defined_not_consumed','未消费标志'),('batch_size',64,'batch size 64.','paper_only','批大小')]:
        c=bykey.get(key);ev=f"{c['file']}:{c['line']}-{c['line']}" if c else None
        # The batch-size quote is shorter than15 chars; use the contiguous context in the actual page.
        if key=='batch_size':quote='and batch size 64.'
        experiments.append({'id':key,'entry_id':'entry:train','setting':title,
             'paper_value':{'value':paper_value,'evidence':[{'page':3,'quote':quote}] if quote else []},
             'repo_default':{'value':c['default'] if c else None,'evidence':[ev] if ev else []},
             'selected_value':{'value':c['default'] if c else None,'source':'源码argparse默认，fixture未指定覆盖；并非运行结果','status':'confirmed_source' if c else 'unknown',
                               'evidence':[ev] if ev else [],'reason':'测试请求没有覆盖线索' if c else '无代码批大小定义/消费'},
             'precedence':'fixture只有argparse，没有YAML加载/覆盖；真实启动参数仍需提供',
             'consumed_by':[{'evidence':f"{x['file']}:{x['line']}-{x['line']}",'symbol_id':x['symbol_id'],'how':x['text']} for x in c['consumers']] if c else [],
             'status':status,'impact':'消费者按源码核对；lr只print，不声称传入优化器。'})
    write(run/'experiment-settings.json',experiments)
    write(run/'change-impacts.json',[{'target':'sym:models/net.py:Net.head.scale:function','goal':'理解把缩放因子2改为其他值的候选影响（不改源码）','entry_ids':['entry:eval'],
          'why_here':'实际乘法位于head内部scale函数；论文乘3与代码乘2冲突', 'upstream':['sym:models/net.py:Net.head:method'],'downstream':[],
          'affected_contracts':['head返回list长度应保持'],'config_consumers':[],'paper_constraints':['保留论文×3与源码×2的冲突说明'],
          'suggested_checks':['列表长度与数值变换','Block零和早退','total_loss分项','eval返回指标'],'limitations':['model(batch)未解析；候选影响不等于必然损坏。']}])
    print('REVIEWED_FIXTURE_CARDS',sum(len(read(p)['items']) for p in (run/'notes').glob('batch_*.json')))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='只填已人工深读的指定教学fixture，不泛化到用户项目')
    parser.add_argument('--run-dir',required=True)
    build(parser.parse_args().run_dir)
