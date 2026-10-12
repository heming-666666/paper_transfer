# 运行流程

1. 整理request：至少1入口，scene=train/eval/infer/other，论文可选。输出在项目外、新空目录，参数仅线索。
2. inspect先确认路径、版本、预算、解析器；失败不继续。
3. extract产生inventory/structure/source snapshots/manifest；configs/paper产生安全配置与分页原文。
4. 读coverage：索引范围、排除/解析失败、truncated、未解析、入口闭包。大仓库先深读预算内核心/论文相关函数，其他保持pending。
5. 有论文先读标题/摘要/明确贡献、方法/公式、实验/附录；写paper-map并check，缺定位留空/未知。
6. batches按入口BFS深度优先（非闭包后置），最多request的max_symbols；--size建议4，复杂函数一次1个。
7. 按reading-protocol逐批填写原骨架，另存notes，check。未解决上下文写partial+needs_context，不能编shape。
8. 每入口overview包含阶段、core_symbols、learning_path和有证据dataflow。补论文映射、实验实际消费/优先级、候选change-impact；每份check。
9. assemble→validate→render。atlas是全部页面唯一数据来源；sources是离线源码。缺必需引用或确定证据失败，合理未知允许。
10. file://打开，点关键函数/调用点/步骤/论文/消费行核对。用户问后续先复用已有symbol/node/evidence；需更新时新run，不覆盖旧报告。

PyTorch注意：调用图≠named_modules包含树≠张量数据流≠反向图；loss.backward不画成调用forward。train/eval、no_grad、AMP、detach、冻结参数、DDP等按实际源码解释，没找到就未知；本文fixture没有真实PyTorch/优化器。

没有运行观测：静态来源不证明任何分支实际执行。报告freshness初始not_rechecked；validate --recheck-source获得matched/stale/unknown，只对应当时哈希，不持续监视原项目。
