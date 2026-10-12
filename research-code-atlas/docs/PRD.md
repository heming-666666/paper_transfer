# Research Code Atlas 需求与实施计划

来源：references/source-spec/prompt_final.md 为唯一实施规格，其他草案保留不改。用户最新指令指定完整迁移单元为本目录，覆盖规格中的 tools、全局安装与包外报告默认位置。

目标：只读静态分析 Python 项目和 train/eval/infer 多入口，脚本提供符号/精确源码/证据，Agent 分小批补解释；输出双击即可用的中文 HTML，包含调用图、层级树、步骤、契约、论文创新/配置消费者与候选修改影响。

用户：学习研究代码或修改前理解依赖的 Agent 和读者。不得导入/运行目标、训练、改原项目、臆造 shape/论文引文/运行记录。未知允许存在，确定结论缺证据必须报错。

实现：scripts/atlas.py CLI；pyextract/resolve 静态作用域与四级调用解析；configs/paper 读配置和分页；checks/batches/assemble 验证与统一 atlas；render 原生 HTML/JS/CSS+本地图形库+安全数据 JS；tests 包含指定原样 fixture 和19条 ground truth。

阶段与验收：
0. 预检版本/目录/边界；本机 Python 实测3.11.5，不沿用草案中的旧3.8结论；嵌入式3.11.9在包内。
1. 按规格原样建立 fixture、19条边与禁止/未解析项，unittest 先观察缺实现失败。
2. AST、作用域、条件、默认值/装饰器、别名/相对导入/候选、闭包与预算；ground truth全部通过才进入后续。
3. batches和严格check；逐函数深读fixture全部卡片；坏行号、坏symbol、确定但无证据都拦截。
4. 论文页文本/quote核验、direct/conflict/not_found和实验match/mismatch/defined_not_consumed；假引文失败。
5. assemble、validate、源重验及原项目哈希；输出与引用一致，过期明确stale。
6. 双击离线页面的全部交互、注入安全、hash历史、窄屏、控制台/断网；复用已存在库而不下载新包。
7. Skill入口、渐进参考和参数README；官方validator与实际CLI全部执行。
8. 明确fixture验收；新Agent会话发现/执行与未提供的真实研究项目分别说明，不能代填通过。
9. 不全局安装；唯一完整包+哈希清单+迁移烟测；按工作区要求Claude差异/经验评估/Capture→Check，不commit/push。

选定兼容性：已有Cytoscape3.34.3+cytoscape-dagre2.5.0+dagre0.8.5可在本机完成同一离线图功能，采用完整本地发行文件并保留MIT许可，代替另行下载规格默认4.0.1。运行时无需Node、其他Skill、任何API key。Python标准库可在非Windows>=3.10运行，YAML缺依赖明确inferred；Windows自带Python/PyYAML。PDF解析优先可用本地工具，补齐包内解析闭包后注明覆盖边界。

风险：静态调用候选并非运行路径；source snapshots与原源码哈希分开；输出不得位于原项目；论文文本质量不保证、扫描页需人工。安全/事实校验不能为了简单删掉。
