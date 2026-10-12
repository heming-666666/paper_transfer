# research-code-atlas 完整离线 Skill

把整个目录交给其他 Agent，让它读取 [SKILL.md](SKILL.md)。程序、源码/论文证据流程、图库、示例、Python/YAML/PDF依赖及Windows浏览器验收资源全部包含，不需要另一个Skill或Node构建。

直接双击查看：[有论文教学示例](examples/demo/viewer/index.html) · [无论文示例](examples/demo-no-paper/viewer/index.html)。两者都是本任务的自有fixture，不是作者项目/论文复现。

## 直接运行

Windows x64在本目录打开终端：

```powershell
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' --help
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\verify_bundle.py'
& '.\runtime\windows\python.exe' -X utf8 -m unittest discover -s '.\tests' -v
```

新分析从request开始；[examples/request-demo.json](examples/request-demo.json) 是可迁移相对路径模板。将output_dir改成新的空目录（不能在被分析项目内），再执行：

```powershell
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' inspect --request '.\examples\request-demo.json'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' extract --request '.\examples\request-demo.json'
```

报告目录已存在会拒绝覆盖，这是预期行为。随后configs→paper→batches→Agent小批深读/check→assemble→validate→render；全部参数与完整流程见 [脚本说明](scripts/README.md)、[workflow](references/workflow.md)。

## 给 Agent 的使用方式

单入口：

```text
读取 research-code-atlas/SKILL.md。
项目：我的本地项目目录；入口：train.py（train）。
论文：本地PDF/MD（没有则明确无论文）；配置：实际配置；参数仅作线索。
解释主流程、核心函数、每个函数的输入输出/步骤，生成可点击源码的离线HTML。
只静态分析，不运行项目，不训练。
```

多入口：提供train.py/evaluate.py/infer.py及各自配置和args，保留scenario_contracts，区别共享函数与入口专属路径，不合并成一次运行。

修改前：给已有RUN_DIR及目标函数/改动意图，定位最小位置，展示上游/下游/配置/loss/论文约束与最小检查；暂不修改源码，影响始终称候选。

源码变更：`validate --run-dir DIR --recheck-source`；stale后新目录extract，核对文件hash再复用未变说明。页面只读快照，不持续监视原源码。

## 操作页面

先总览→核心函数→调用层级/图→内部流程→源码。图节点、列表、调用者/被调用者、步骤、论文映射与配置消费者都能定位页内源码；同名函数按文件和限定名区分。图深度/边关系/证据过滤，递归显示↻，hash刷新/前进/后退恢复选择。

论文看direct/inferred/not_found/conflict及当前入口路径；实验分别看论文值、默认值、本次值、覆盖顺序和消费行。unknown有原因，灰色/虚线不会冒充确定。窄屏三个区域按顺序排列，键盘可聚焦按钮。

file://直接可用，不需要服务。需要HTTP：`atlas.py serve --run-dir DIR --port 0`，只127.0.0.1，输出实际URL，Ctrl+C停止。

## 迁移与边界

[portability.md](references/portability.md) · [HANDOFF.md](HANDOFF.md) · [第三方许可](assets/viewer/vendor/LICENSES.md)。

Windows x64自带解释器和本地依赖；其他平台使用已有Python>=3.10（TOML需3.11），实际非Windows环境尚未验证。深度解析只支持Python；动态调用/注册表/参数callable不能静态确认。没有runtime capture，不编shape或引文。扫描PDF无文本需人工，不自动OCR。

自动发现可按目标宿主实际路径放完整目录，或继续显式读入口；没有全局安装/热刷新证明。真实研究项目未提供，样例验收不代替真实模型/论文验证。

以后可选：Understand-Anything兼容图导出、Pyan3交叉核查、明确授权的运行观测；本期均不做运行依赖。
