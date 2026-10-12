---
name: research-code-atlas
description: 静态理解 Python 研究项目的入口流程、核心函数、调用关系、输入输出与内部步骤，生成可双击离线打开并精确跳转源码的中文 HTML，结合可选论文创新点、实验设置和候选修改影响。用于理解训练/评估/推理代码或修改前分析；不修改项目、不执行训练。
---

# 论文与代码执行图谱

本文件所在目录是完整迁移单元 `SK`。程序、参考流程、原始规格、示例页面、本地图库、Windows Python/YAML/PDF解析和浏览器验收资源均在这里。不要依赖源机盘符、旁边的其他 Skill、CDN 或 API key；直接让任何 Agent 读取本入口即可用。自动发现/全局安装需用户另行指定，不把文件存在当新会话发现性证据。

## 准备输入

取得项目根目录、至少一个入口（train/eval/infer/other）、可选本地论文PDF/MD/TXT、配置/启动参数线索、学习或改动重点。只读 README、启动脚本、argparse 和必要配置；从文件能确认的事实不反问。入口或论文有决定性歧义时问一个问题。

解析自身绝对路径。Windows x64优先 `SK/runtime/windows/python.exe`（3.11.9，包内依赖，无需安装）；其他平台使用已有 Python>=3.10，TOML需3.11。源码解析只用标准库，PDF/YAML纯Python资源已包含，缺少可用解析器时要报明确边界。所有命令使用 `-X utf8`。

先读 [workflow.md](references/workflow.md) 和 [schemas.md](references/schemas.md)。有论文再读 [paper-and-experiments.md](references/paper-and-experiments.md)；每批函数按 [reading-protocol.md](references/reading-protocol.md) 执行。不把整份85KB实施规格每次加载。

## 分阶段执行

1. 自然语言整理成 `request.json`：项目路径、入口和场景、配置/args、论文、**位于项目外的新输出目录**、预算和runtime=false。完整示例与参数见 [使用说明](README.md)、[scripts/README.md](scripts/README.md)。相对 project/output/paper 路径基于request所在目录；入口/config路径基于project_root。
2. `PY -X utf8 SK/scripts/atlas.py inspect --request REQUEST` → `extract --request REQUEST` → `configs --run-dir R` → `paper --run-dir R`。没有论文继续代码流程。
3. 阅读structure的范围、入口闭包与未解析调用。先说明静态边、候选边和未知；**调用图不是模块树、张量流或反向图**。有论文按原文先写贡献/机制，再核对源码。
4. `batches --run-dir R --size 4`。只深读当前1个复杂函数或3–5个相关小函数，填写notes/todo提供的骨架，另存notes/batch_NNN.json；不能改prefilled、源码范围、kind、calls。shape缺证据就null+reason。每批 `check --run-dir R --file FILE`，只修当前失败项。
5. 各入口写notes/overview_*.json；论文写paper-map.json（direct/inferred/not_found/conflict，逐页短引文）；实验写experiment-settings.json（论文值/默认值/本次值/优先级/消费行），需要改动分析才写change-impacts.json。每个都check。未解析callable不能补成真实执行，论文冲突保留双方原文。
6. `assemble --run-dir R` → `validate --run-dir R` → `render --run-dir R`。Agent负责中文解释，脚本负责符号/行号/哈希/事实，不把骨架当完成理解。
7. 打开 `R/viewer/index.html`（file://直接运行），实际点击核对源码、步骤、论文映射和配置消费者。需要HTTP时 `serve --run-dir R --port 0`，只绑定127.0.0.1，打印实际地址，Ctrl+C停止。
8. 汇报路径、已解释/待解释、未解析调用、论文与证据状态、快照/新鲜度、学习顺序和未验证边界。后续复用同报告；源码变化 `validate --recheck-source`，过期后在新目录extract，再复用真正未变的说明。

上述PY/SK/R/REQUEST/FILE由Agent替换为当前实际路径；不是可原样输入的终端变量。script支持从任意cwd启动。

## 事实与安全边界

- 不导入/运行/修改目标项目，不训练，不执行request.args，不求环境变量或Hydra插值。不提供runtime capture命令。
- 每个结论分别标confirmed_source/inferred/unknown/conflict/not_applicable；observed_runtime在本静态工具中禁止。未知合理，确定结论缺证据、假引文、悬空symbol、越界行号失败。
- 多入口scenario_contracts分别保留。默认配置不是自动确认的最终值；“找到候选消费行”不等于运行时采用。
- 输出目录非空则拒绝extract；源快照与原项目重验分开。file://只看捕获快照，不能自行判断原项目最新。
- 调用解析是保守静态解析；动态注册表/传入callable/未确定类型保持未知。修改影响始终称候选，零调用者不代表安全。
- 没有真实项目/论文时只能使用明确标注的fixture；不能把19条ground truth或示例论文当真实研究验收。

## 验收与迁移

完整复制此目录，运行 `PY -X utf8 SK/scripts/verify_bundle.py` 校验资源文件集合/哈希。自有测试：`PY -X utf8 -m unittest discover -s SK/tests -v`；Windows浏览器脚本见tests/README.md。可直接打开 [教学示例](examples/demo/viewer/index.html) 和 [无论文示例](examples/demo-no-paper/viewer/index.html)。[HANDOFF.md](HANDOFF.md) 记录实际验收；[portability.md](references/portability.md) 说明平台/发现性边界。
