# （Claude 独立草案）给本地 Agent：创建 research-code-atlas Skill

> 本文件是 Claude 在**未参考 Codex 版本**前独立形成的草案，保留作对照。真正交给本地 agent 执行的是合并后的 `prompt_final.md`。
> 调研与核验日期：2026-10-12。

## 0. 一句话目标

做一个 skill：用户给「项目路径 + 入口文件 + 论文（可选）+ 配置（可选）」，skill 生成一个**本地离线 HTML 学习界面**，能看到：入口主要作用、核心函数、调用关系图与调用层级树、每个函数的输入输出格式、使用目的、内部执行步骤，任何函数/步骤/调用点**点击即跳到源码对应行**，并且把**论文创新点**与**实验关键设置**对照到具体代码。

## 1. 路线选择（草案结论）

调研过的现成方案（全部实际打开核验）：

| 项目 | 链接 | 能借鉴什么 | 为什么不直接当底座 |
| --- | --- | --- | --- |
| Understand-Anything | https://github.com/Egonex-AI/Understand-Anything | 知识图谱 JSON、节点点击看源码与解释、guided tour | TypeScript + React + pnpm workspace，改面板要懂前端构建；弱模型极易卡在构建与 schema |
| walkthrough | https://github.com/alexanderop/walkthrough | Mermaid 节点可点击 → 详情面板；`references/html-patterns.md` 拆分方式 | 依赖 CDN（React/Tailwind/Mermaid/Shiki），离线不可用；只有 5–12 个概念，粒度不到函数 |
| showme-skill | https://github.com/jolynestarchaser/showme-skill | 一份 graph.json 派生一切；FACT/INFERENCE/UNKNOWN 标注；纯 JS+SVG 无依赖；URL fragment 保存状态 | 面向仓库/diff 的概念图，没有函数级 I/O 与论文对照 |
| codebase-to-course | https://github.com/zarazhangrui/codebase-to-course | “代码 ↔ 白话”并排、单文件离线 HTML、术语提示 | 课程式线性阅读，不是可导航调用图 |
| paper-to-course | https://github.com/KaguraTart/paper-to-course | 论文六模块（动机/方法/实验/消融…）、公式拆解 | 只读论文，不连代码 |
| claude-paper | https://github.com/alaliqing/claude-paper | PDF → 文本/图/公式 → 学习材料 | 只读论文 |
| graphify | https://github.com/safishamsi/graphify | 确定性 AST 抽取 + 语义抽取两阶段；graph.html 输出 | 通用知识图，不做函数契约和实验对照 |
| Claude Code 官方 skill 示例 codebase-visualizer | https://code.claude.com/docs/en/skills | `${CLAUDE_SKILL_DIR}/scripts/xxx.py` 打包脚本生成 HTML 的标准写法 | 只是目录树示例 |

**草案结论：自建轻量实现。** Python 标准库 `ast` 做确定性抽取（不导入、不运行目标项目）；agent 只负责按小批次“填空”写解释；一个无需构建的原生 JS 页面 + 本地 vendored 的 Cytoscape.js 画图。理由：弱模型能完成、离线可用、出错好定位。上面的项目只读设计，不安装。

## 2. 本机事实（已核验）

- 默认 `python` 是 3.8.20（anaconda OCR 环境），**不能用**；用 `py -3.13`（D:\study\python）或 `py -3.14`。
- Node v24.14.1，ripgrep 15.2.0，`pdftotext` 可用（Git Bash 的 mingw64）。
- 3.13/3.14 中没有 PyYAML、PyMuPDF、pypdf。
- Claude Code 设置了 `CLAUDE_CONFIG_DIR=D:\APP\ClaudeCode\config`，所以个人 skill 目录是 `D:\APP\ClaudeCode\config\skills\`，**不是** `C:\Users\Administrator\.claude\skills\`。
- Codex 本机 skill 在 `C:\Users\Administrator\.codex\skills\`；工作区规则要求 canonical 源为 `D:\Code\Codex_transfer\skills`，改完后 Capture → Check。

## 3. 架构

```
skill 目录 research-code-atlas/
  SKILL.md                 入口：何时用、7 步流程、命令
  references/workflow.md   运行时详细步骤
  references/schemas.md    所有 JSON 契约
  references/reading-protocol.md  函数深读 / 论文 / 实验 模板
  scripts/atlas.py         唯一 CLI：inspect/extract/batches/check/paper/configs/assemble/validate/render/serve
  scripts/pyextract.py     AST 抽取 + 调用解析
  scripts/render.py        生成 viewer 数据
  assets/viewer/           index.html app.js style.css vendor/cytoscape*.js
  tests/fixtures/mini_proj 小项目 + ground_truth.json
```

运行产物（不写进被分析项目）：`structure.json`（脚本）→ `notes/*.json`（agent 填）→ `atlas.json`（脚本合并校验）→ `viewer/`（双击 index.html 可开）。

## 4. 关键设计

1. **稳定符号 ID**：`sym:<相对路径>:<限定名>:<kind>`，同名不同文件绝不合并。
2. **调用解析分级**：`resolved_static`（直接名、import 别名、self 方法、构造）/`candidate`（self.x = Class() 推出的属性类型、nn.Module 的 `__call__→forward`、同名方法≤5个）/`unresolved`（getattr、注册表、参数传入的 callable）/`external`（torch 等）。
3. **脚本先给骨架，agent 只填空**：抽取时自动生成每个函数的“步骤骨架”（顶层语句 → 行号范围），以及 shape 线索（view/reshape/permute/assert shape）。agent 填 title/why/输入输出，不允许改行号范围以外的事实。
4. **证据写法极简**：agent 只写 `"models/net.py:10-12"`；脚本校验文件与行号并算 sha256。论文证据写 `{page, quote}`，脚本检查 quote 真在该页文本里——防编造。
5. **证据状态**：confirmed_source / inferred / unknown / conflict / not_applicable / observed_runtime。
6. **论文**：`pdftotext` 按页切分 → 贡献 → 方法步骤 → 实验设置；每条创新映射到 symbol + 行号 + 是否在所选入口路径上。
7. **实验设置三方对照**：论文值 / 仓库默认值 / 本次场景最终值 + 消费该值的代码行。
8. **界面**：左侧（入口/核心函数/搜索）、中间（调用图 / 调用层级树 / 函数内部步骤）、右侧函数卡片、底部页签（源码、论文、实验、修改影响、未知清单）；URL hash 保存状态；所有内容 textContent 渲染。
9. **修改影响**：前端 BFS 上游调用者 / 下游被调用者 + 相关配置与论文约束；标“候选影响”，不承诺完整。

## 5. 分阶段

0 预检 → 1 fixture 与 ground truth → 2 AST 抽取与解析（对 ground truth 测试）→ 3 批次与 check → 4 论文与配置 → 5 assemble/validate → 6 viewer → 7 SKILL.md 与安装 → 8 真实项目验收。每阶段在 HANDOFF.md 记录命令、退出码、产物。

## 6. 草案的不足（合并时需要补）

- 证据模型、多入口契约、源码新鲜度、安全测试、退出码细则不够细。
- 没写工作区授权、Capture → Check、Claude 迁移记录。
- 可选 runtime 观测只提了一句。

这些在合并版中由 Codex 版本补齐。
