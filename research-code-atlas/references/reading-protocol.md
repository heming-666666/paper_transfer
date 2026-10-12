# 小批次函数深读

每次只解释notes/todo当前批的symbol_id。完整读definition_range及已知调用者/被调用者签名；有必要再读类__init__、消费行、相关配置与论文，不通读无关仓库。

填写role、summary、purpose、inputs/outputs、side_effects、exceptions、steps、paper_refs/config_refs、scenario_contracts、change_notes。prefilled由脚本给，不许改signature/行号/调用事实。

steps保留id、order、source_range、kind、calls、children；只补title/action/why/inputs/outputs。相邻同级步骤可用merged_ids合并，范围与calls必须是原步骤并集；没有证据不可创造新的调用或分支。每条确定IO/副作用要写 `file:start-end`。

shape查证顺序：类型注解/dataclass→getitem/collate→assert/reshape/view/permute→实际消费者→配置维度。参数名不是shape依据；非tensor的容器长度也要说明性质。无法确定shape用null+reason，不复制示例模型维度。

分别解释return分支、tuple/dict、yield/generator、async、原地修改、隐式None；mse等变量名不证明实现了同名数学目标。一个函数多入口不同输入写scenario_contracts，不能覆盖通用卡片。

analysis_status=done要求完整summary/purpose/steps和输入输出字段；partial必须说明needs_context。论文/配置引用必须已存在。notes是合法JSON，不加Markdown或尾逗号；check按JSON路径报错，只修本批，不删校验条件。

核心排序：入口控制→数据构造→forward→loss→循环/评估→论文创新实现→工具。排序只为学习，未覆盖项保留pending；不把所有脚本骨架都称为“已解释”。
