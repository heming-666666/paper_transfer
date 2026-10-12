# 给本地 Agent 的完整任务：创建 `research-code-atlas` Skill（最终合并版）

版本：2026-10-12（北京时间）。输出语言：中文。
来源：Claude 独立草案（`claude_prompt.md`）+ Codex 规格（`prompt.md`）合并。合并取舍见 `合并说明与使用指南.md`。

> 你（本地 agent）要**真正实现**一个 skill，不是写方案。本文件里的 `atlas.py` 子命令、JSON 字段、目录都需要你亲手实现，不是现成工具。
> 本文件很长。**第一步**：通读全文，把第 17 节的阶段 0–9 抄进 `HANDOFF.md` 作为任务清单；之后每次只做一个阶段，做完跑该阶段的验收命令，把命令、退出码、关键输出写进 HANDOFF，再进入下一阶段。

---

## 0. 写给执行者的硬规则（每个阶段开始前重读一遍）

1. **不编造。** 不知道就写 `null` + `reason`，状态标 `unknown`。尤其不准编 tensor shape、loss 权重、论文页码、论文引文、运行结果。
2. **不运行、不导入目标项目**（静态分析）。不执行训练。不修改被分析项目的任何文件。
3. **脚本负责事实，agent 负责解释。** 函数列表、行号、调用边、哈希都由脚本产生；你只往脚本生成的骨架里填解释，并用 `check` 命令校验。
4. **小批次。** 一次只深读 1 个函数或 3–5 个紧密相关的小函数，不把整个仓库塞进上下文。
5. **同一个错误连续失败 2 次就停**：把原始报错贴进 HANDOFF，分析原因（路径？编码？Python 版本？），不要盲目重试或改测试来“通过”。
6. **不覆盖已有文件**：`D:\Code\prompt.md`、`D:\Code\research-code-atlas-skill\` 里的所有文件、已有同名 skill，都只能读不能改。写文件前先检查目标是否存在。
7. **所有文件 UTF-8**。Python 读写文件一律写 `encoding="utf-8"`；在 Windows 终端运行 Python 时加 `-X utf8`。
8. **工作区规则优先**：先读 `D:\Code\AGENTS.md`（Codex）或 `D:\Code\CLAUDE.md`（Claude Code）。本文件不高于那些规则。
9. 每完成一个阶段才能说“该阶段完成”；只写了 SKILL.md、只有截图、只有 `--help` 能跑，都**不算完成**。

---

## 1. 最终目标与成功标准

用户给：项目根目录 + 入口文件（可多个：train/eval/infer）+ 可选论文 PDF + 可选配置/启动参数。
skill 产出一个**本地可视化学习界面**（HTML），用户可以：

| 用户需求 | 界面中对应功能 | 实现所在 |
| --- | --- | --- |
| 入口文件代码的主要作用 | 「总览」页：入口一句话作用 + 执行阶段（配置→数据→模型→loss→更新→评估） | agent 写 `overview.json` |
| 核心代码函数 | 左栏「核心函数」列表（带排序理由） | `overview.json` 的 `core_symbols` |
| 函数调用关系 | 「调用图」：caller → callee 有向图，线型区分确定/候选/未解析 | 脚本 `structure.json` 的 edges |
| 调用层级图 | 「调用层级」：从入口展开的可折叠树，递归/重复处标 ↻ | 前端由 edges 生成 |
| 每个函数的输入输出及格式 | 右侧「函数卡片」：参数/返回的类型、容器层级、shape、dtype、证据状态 | agent 写 `notes/*.json` |
| 函数使用目的 | 卡片「作用」「为什么需要」「谁使用结果」 | 同上 |
| 内部实现流程 | 「内部流程」：按执行顺序的步骤（分支/循环/早退），每步可点击到源码行 | 脚本给步骤骨架，agent 填说明 |
| 点击即可跳转函数 | 图节点、树节点、调用者/被调用者、步骤、论文映射、配置消费者，点击都跳到源码并高亮行 | 前端统一 `openSymbol()` |
| 可视化界面方便观察 | 离线 HTML，双击 `index.html` 就能打开（也可本地服务打开） | `assets/viewer` |
| 结合论文创新点 | 「论文对照」：创新点 → 实现函数 → 是否在所选入口路径上；论文步骤 ↔ 代码步骤 | agent 写 `paper-map.json`，脚本核对引文 |
| 结合实验关键设置 | 「实验设置」：论文值 / 仓库默认值 / 本次最终值 / 消费该值的代码行 | 脚本扫配置，agent 写 `experiment-settings.json` |
| 为了做改动 | 「修改影响」：选中函数的上游调用者、下游被调用者、相关配置/loss/论文约束、建议检查 | 前端 BFS + agent 写的针对性说明 |

**成功标准**：用户从入口看到主要阶段 → 点进具体函数 → 读懂输入输出、条件分支和内部步骤 → 点到准确源码行；同一界面能查论文创新怎么落地、实验配置在哪里生效、改某个函数可能影响什么。所有“不确定”都明确标出。

---

## 2. 技术路线（已确定，不要再换）

### 2.1 决定

**自建轻量实现，借鉴现成项目的设计，不把任何大项目当运行依赖。**

- 抽取：Python 标准库 `ast` + `tokenize`（Python ≥ 3.10），不导入目标代码，不需要目标依赖装好。
- 解释：agent 按批次填 JSON，脚本校验。
- 界面：原生 HTML/CSS/JS，**无需构建**；图库只用本地 vendored 的 Cytoscape.js + cytoscape-dagre（MIT）。数据以 `<script src="atlas-data.js">` 方式加载，因此**双击 index.html（file://）即可使用**，无需服务器；另提供 `serve` 子命令绑定 127.0.0.1 作为备选。
- 先把 Python 研究代码（含 PyTorch）做好；其他语言本期只在 inventory 中列出“未分析”，不承诺。

为什么不按 Codex 原方案“改造 Understand-Anything 的 React 面板”：它需要 pnpm workspace 构建、TypeScript、Zod schema 适配和 React 组件修改，本地模型能力不足时极易卡死；而且其 CodeViewer 依赖本地接口读源码、不能离线双击使用。Understand-Anything 仍作为**设计参考**和**可选的后续增强**（第 2.3 节）。

### 2.2 参考项目（只读，不安装；按“何时读”去读）

| 项目 | 链接 | 何时读 | 借鉴什么 |
| --- | --- | --- | --- |
| Claude Code 官方 skill 文档（含 codebase-visualizer 示例） | https://code.claude.com/docs/en/skills | 阶段 7 写 SKILL.md 前 | frontmatter、`${CLAUDE_SKILL_DIR}`、skill 目录位置、`/reload-skills` |
| Codex 官方 skill 文档 | https://developers.openai.com/codex/skills | 阶段 7（若宿主是 Codex） | `.agents/skills` 发现路径、`$skill` 调用 |
| Anthropic skill-creator | https://github.com/anthropics/skills/tree/main/skills/skill-creator | 阶段 7 | SKILL.md 写法、`scripts/quick_validate.py` 校验 |
| OpenAI skill-creator | https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md | 阶段 7（Codex 宿主） | 同上；只选与宿主一致的一份 |
| Understand-Anything | https://github.com/Egonex-AI/Understand-Anything | 阶段 2、6 之前各读 10 分钟 | 确定性抽取与语义解释分离；节点详情面板布局；guided tour |
| ├ understand/SKILL.md | https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand/SKILL.md | 阶段 2 | 先脚本扫描、再分批 LLM 解释的流程 |
| ├ understand-explain/SKILL.md | https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand-explain/SKILL.md | 阶段 3 | 符号深读的提问方式 |
| ├ understand-diff/SKILL.md | https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand-diff/SKILL.md | 阶段 6 修改影响 | 变化 → 依赖关联 |
| └ NodeInfo.tsx / CodeViewer.tsx | https://github.com/Egonex-AI/Understand-Anything/tree/main/understand-anything-plugin/packages/dashboard/src/components | 阶段 6 | 卡片字段排布、源码高亮交互 |
| showme-skill | https://github.com/jolynestarchaser/showme-skill | 阶段 6 | 一份 graph.json 派生一切；FACT/INFERENCE/UNKNOWN 用边框+符号区分（不只靠颜色）；URL fragment 保存状态；纯 JS 无依赖 |
| walkthrough | https://github.com/alexanderop/walkthrough | 阶段 6 | 图节点点击 → 详情面板；`references/html-patterns.md` 把 HTML 模板放进 references 的组织方式（注意它用 CDN，我们不用） |
| codebase-to-course | https://github.com/zarazhangrui/codebase-to-course | 阶段 6 | “代码 ↔ 白话”并排、术语提示 |
| paper-to-course | https://github.com/KaguraTart/paper-to-course | 阶段 4 论文 | 论文拆成 动机/方法/实验/消融 的阅读顺序、公式拆解 |
| claude-paper | https://github.com/alaliqing/claude-paper | 阶段 4 | PDF → 文本 → 学习材料的流程 |
| graphify | https://github.com/safishamsi/graphify | 阶段 2 | AST 确定性抽取 + 语义抽取两遍；“每条边都有解释” |
| GitNexus impact skill | https://github.com/abhigyanpatwari/GitNexus/blob/main/gitnexus/skills/gitnexus-impact-analysis.md | 阶段 6 修改影响 | 向上追调用者；“有调用者 ≠ 必然损坏”。**许可证是 PolyForm Noncommercial，不复制代码** |
| CodeGraphContext skill | https://github.com/CodeGraphContext/CodeGraphContext/blob/main/.cursor/skills/codegraphcontext/SKILL.md | 阶段 2 | 先索引、限定仓库作用域再查询 |
| Pyan3 | https://github.com/Technologicat/pyan | 阶段 2（可选交叉检查） | Python 静态关系；GPL-2.0，**不复制实现**；“uses ≠ calls” |
| code2flow | https://github.com/scottrogowski/code2flow | 只了解 | 近似调用图的能力边界 |
| Python ast 文档 | https://docs.python.org/3/library/ast.html | 阶段 2 | 节点类型、`lineno/end_lineno`、`get_source_segment`、`unparse` |
| Cytoscape.js | https://js.cytoscape.org/ | 阶段 6 | 元素/样式/事件 API |
| cytoscape.js-dagre | https://github.com/cytoscape/cytoscape.js-dagre | 阶段 6 | 分层布局 `rankDir: 'LR'` |

### 2.3 可选后续增强（本期不做，写进 README 的“以后可以做”）

- 导出兼容 Understand-Anything 的 `knowledge-graph.json`，用它的 dashboard 看多语言全仓图。
- 用 Pyan3 对 Python 调用边做交叉检查并在“未知清单”显示差异。
- 第 15 节的真实运行观测（runtime capture）。

---

## 3. 本机环境事实（2026-10-12 已核验；换机必须重新检查）

| 项目 | 事实 | 你要怎么做 |
| --- | --- | --- |
| 默认 `python` | 3.8.20（`D:\anaconda\envs\OCR`），**太旧** | 不要用 `python` 命令。用 `py -3.13`（`D:\study\python\python.exe`）或 `py -3.14` |
| PyYAML / PyMuPDF / pypdf | 3.13、3.14 都没装 | 见第 4.2 节：建专用 venv 安装 PyYAML（需授权）；PDF 用 `pdftotext` |
| `pdftotext` | 可用（Git Bash `/mingw64/bin/pdftotext`） | 论文抽文本首选它 |
| Node.js | v24.14.1 | 仅用于下载 vendored JS 和做数据文件语法冒烟测试 |
| ripgrep | 15.2.0 | 找调用者/配置消费者时用 `rg -n` |
| Playwright | 未安装 | 不要为验收临时安装；有浏览器自动化工具（如 Claude in Chrome、已有 Playwright MCP）就用，没有就按人工清单验收并如实标注 |
| Claude Code skill 目录 | 设置了 `CLAUDE_CONFIG_DIR=D:\APP\ClaudeCode\config` → 个人 skill 实际在 `D:\APP\ClaudeCode\config\skills\` | 安装到这里；`C:\Users\Administrator\.claude\skills\` 下的不会被当前 Claude Code 发现 |
| Codex skill 目录 | 本机已有 skill 在 `C:\Users\Administrator\.codex\skills\`；官方文档写的是 `~/.agents/skills` | 以实际能被发现为准；工作区规则要求维护源在 `D:\Code\Codex_transfer\skills`，改完做 Capture → Check |
| 已有可复用 skill | Codex：`paper-understanding-pack`、`paper-lookup`、`agent-reach`、`systematic-debugging`、`test-driven-development`、`verification-before-completion`、`writing-plans`、`codex-config-transfer`；Claude Code：内置 `skill-creator` | 见第 4.1 节何时用 |

### 3.1 路径变量（写进 HANDOFF.md 顶部）

| 变量 | 值 | 说明 |
| --- | --- | --- |
| WORKSPACE_ROOT | `D:\Code` | |
| BUILD_ROOT | `D:\Code\tools\research-code-atlas` | 开发目录。已存在就先列出内容，不覆盖 |
| SKILL_SRC | `BUILD_ROOT\research-code-atlas` | skill 源码（自包含，可整体复制安装） |
| VENV | `BUILD_ROOT\.venv` | 分析器专用 Python 环境（`py -3.13 -m venv`） |
| PY | `BUILD_ROOT\.venv\Scripts\python.exe`；venv 未建时用 `py -3.13` | 下文所有 `PY` 都指它 |
| REPORTS_ROOT | `D:\Code\reports\research-code-atlas` | 每次分析产物：`REPORTS_ROOT\<项目名>\<YYYYMMDD-HHMM>` |
| PROJECT_ROOT | 每次由用户提供 | 被分析项目，只读 |
| RUN_DIR | 某次分析的产物目录 | |

---

## 4. 需要哪些 Skill 和软件，何时用，在哪用

### 4.1 Skill 清单

| Skill | 来源 | 需要安装吗 | 什么时候用 | 在哪里用 |
| --- | --- | --- | --- | --- |
| skill-creator | Claude Code 内置（`anthropic-skills:skill-creator`）；Codex 内置 system skill。参考源码见 2.2 节 | 不用装，先确认存在 | 阶段 7 写 SKILL.md、校验 frontmatter | 建 skill 时 |
| **research-code-atlas** | 本任务要创建 | **必须由你创建并安装** | 以后每次分析项目 | 用户调用 |
| paper-understanding-pack | 本机 Codex skill（`C:\Users\Administrator\.codex\skills\paper-understanding-pack\SKILL.md`） | 已有；外机没有就按第 12 节自带流程 | 用户要求“论文先精读”或论文很长、创新点难定位时；Claude Code 下不可直接调用，可以**读它的 SKILL.md 当参考流程** | 阶段 4 / 运行时论文步骤 |
| paper-lookup | 本机 Codex skill | 已有 | 用户只给论文标题/arXiv ID/DOI 时找 PDF（下载需授权） | 运行时 |
| agent-reach | 本机 Codex skill | 已有 | 用户要求联网补充资料时 | 运行时，可选 |
| systematic-debugging / test-driven-development / verification-before-completion / writing-plans | 本机 Codex skill | 已有 | 写脚本时：先写 fixture 测试再实现；出错按调试流程；交付前做验证 | 阶段 1–8 |
| codex-config-transfer | 本机 Codex skill | 已有 | 把 skill 装进 Codex 后，按工作区规则串行 Capture → Check | 阶段 9 |
| Understand-Anything 等 | GitHub | **不安装** | 只读设计（2.2 节） | — |

**不需要安装**：GitNexus、CodeGraphContext、Pyan3、code2flow、Graphviz、Docker、任何数据库、任何向量库、任何商业 LLM API。

### 4.2 软件与依赖

| 依赖 | 用途 | 处理方式 | 需要授权吗 |
| --- | --- | --- | --- |
| Python 3.13（已有） | 全部脚本 | `py -3.13 -m venv D:\Code\tools\research-code-atlas\.venv` | 建 venv 属于本任务目录内的可逆操作 |
| PyYAML 6.x | 安全读取 YAML 配置（`yaml.safe_load`） | `VENV\Scripts\python.exe -m pip install "pyyaml>=6,<7"` | **需要**（安装依赖）。未授权时脚本走降级：只用正则按缩进记录 YAML 键（状态标 `inferred`） |
| cytoscape 3.34.3（MIT） | 调用图绘制 | 见阶段 6：`npm pack cytoscape@3.34.3` 解出 `dist/cytoscape.min.js` 放到 `assets/viewer/vendor/` | **需要**（下载第三方代码）。未授权时“调用图”页降级为只显示“调用层级树”（纯 HTML），其他功能照常 |
| cytoscape-dagre 4.0.1（MIT，已内置 dagre） | 分层布局 | `npm pack cytoscape-dagre@4.0.1` 取 `dist/cytoscape-dagre.js` | 同上 |
| pdftotext（已有） | 论文转文本 | 直接调用 | 不需要 |
| rg（已有） | 定向搜索 | 直接调用 | 不需要 |

vendored 文件旁边放 `assets/viewer/vendor/LICENSES.md`，写明包名、版本、MIT 许可证全文来源（取自 npm 包里的 LICENSE）。

### 4.3 授权边界

- **可以直接做**：在 `BUILD_ROOT` 内建目录/文件、建 venv、写脚本、跑 fixture、跑静态分析、在 `REPORTS_ROOT` 写产物。
- **先问用户（一次性列清单：包名、版本、路径、影响）**：pip/npm 下载安装、把 skill 复制到全局 skill 目录、覆盖任何已存在文件、运行目标项目、联网下载论文。
- **永远不做**：修改被分析项目；执行训练；全局改 Python/Node；改系统权限/安全设置；读取或导出密码、token、cookie；commit/push。

---

## 5. 目录结构（每个文件都要有用途）

```text
D:\Code\tools\research-code-atlas\          (BUILD_ROOT)
  HANDOFF.md                     当前进度、每阶段命令与结果、未完成项
  docs\PRD.md                    从第 1、7、17 节摘出的需求与验收
  .venv\                         分析器专用环境（不复制进 skill）
  research-code-atlas\           (SKILL_SRC，自包含，可整体复制)
    SKILL.md                     入口（第 16 节模板）
    local.example.json           {"python": "...", "reports_root": "..."} 示例
    references\
      workflow.md                运行时 10 步流程（第 10 节）
      schemas.md                 全部 JSON 契约（第 7 节）
      reading-protocol.md        函数深读批次模板（第 11 节）
      paper-and-experiments.md   论文对照 + 实验设置流程（第 12、13 节）
      runtime.md                 （仅当实现了第 15 节时才创建）
    scripts\
      atlas.py                   唯一 CLI 入口，分发子命令
      pyextract.py               AST 抽取：符号、调用点、步骤骨架、shape 线索
      resolve.py                 调用解析（import/别名/self/构造/候选）
      configs.py                 argparse / YAML / dataclass 配置抽取 + 消费者候选
      paper.py                   pdftotext 分页 + 引文核对
      checks.py                  各类 JSON 的校验（check 子命令）
      assemble.py                合并为 atlas.json
      render.py                  生成 viewer 目录与数据 JS
      README.md                  每个子命令的参数、默认值、输出、退出码、示例
    assets\viewer\
      index.html  app.js  style.css
      vendor\cytoscape.min.js  vendor\cytoscape-dagre.js  vendor\LICENSES.md
    tests\
      fixtures\mini_proj\        第 18 节小项目
      fixtures\mini_paper.md     测试用“论文”（明确标注为测试材料）
      ground_truth.json          人工确认的期望边/未解析项
      test_extract.py            用 unittest（标准库）对比 ground truth
```

不要建：多余的 adapter 框架、配置中心、第二套前端、每个 run 复制整份 skill。

---

## 6. 用户输入：request.json

skill 接受自然语言，agent 先整理成 `RUN_DIR\request.json` 再调脚本：

```json
{
  "schema_version": "1.0",
  "project_root": "D:/Research/ExampleProject",
  "entries": [
    {"entry_id": "entry:train", "path": "train.py", "symbol": null,
     "scenario": "train", "configs": ["configs/base.yaml"],
     "args": ["--config", "configs/base.yaml", "--lr", "3e-4"], "overrides": []}
  ],
  "paper": {"path": "D:/Papers/example.pdf", "url": null},
  "focus": "理解训练主循环、模型 forward 和损失；准备修改特征融合",
  "output_dir": "D:/Code/reports/research-code-atlas/ExampleProject/20261012-2030",
  "limits": {"max_depth": 8, "max_symbols": 300},
  "runtime": {"enabled": false}
}
```

字段规则：

- `project_root`：必须是存在的目录，脚本转成绝对真实路径。
- `entries`：至少 1 个；`entry_id` 唯一；`path` 相对 project_root 且文件存在；`symbol` 可选（如 `main` 或 `Trainer.fit`）；`scenario` ∈ `train|eval|infer|other`；`args`/`overrides` **只作为配置线索，绝不执行**。
- `paper`：可选；有本地文件优先；支持 `.pdf/.md/.txt`；都没有时论文状态为 `missing`，代码分析照常。
- `output_dir`：不存在则创建；已存在且非空 → 报错退出码 2（不覆盖）。
- `limits`：分析预算；超出记 `truncated`，不是错误。
- `runtime.enabled` 默认 false；为 true 也必须另有第 15 节的完整运行清单和用户授权。

输入不全时先从 README、启动脚本、argparse、配置文件里找；只在答案会改变结果时问用户**一个**问题（例如仓库里有两篇论文不知道对应哪篇）。不要问用户能从文件读到的东西。

---

## 7. 数据契约（写进 `references/schemas.md`）

### 7.1 证据状态（每个结论单独标，不是整张卡一个标签）

| 值 | 中文 | 含义 |
| --- | --- | --- |
| `confirmed_source` | 源码确认 | 源码中的定义/表达式/调用点直接支持；不代表运行时一定执行 |
| `observed_runtime` | 运行观测 | 仅在记录的那次运行条件下观察到 |
| `inferred` | 推断 | 有依据但不充分，必须写依据和限制 |
| `unknown` | 未知 | 写清楚缺什么、怎么验证 |
| `conflict` | 冲突 | 论文/源码/配置不一致，各方原文都保留 |
| `not_applicable` | 不适用 | 例如工具函数与论文无关 |

### 7.2 稳定符号 ID

- 格式：`sym:<相对路径用/>:<限定名>:<kind>`，kind ∈ `module|class|function|method|async_function`。
- 例：`sym:models/net.py:Net.forward:method`、`sym:models/net.py:Net.head.scale:function`（嵌套函数）、`sym:train.py:<module>:module`。
- 同一作用域重复定义：第二个加 `#2`。
- 不准用“函数名”或“函数名+行号”当 ID。
- 外部符号：`ext:torch.nn.functional.relu`。
- HTML 里放进 URL hash 时用 `encodeURIComponent`。

### 7.3 源码证据写法（agent 写的简写 → 脚本展开）

agent 只写字符串 `"models/net.py:10-12"`（1 起始，两端包含）。`check` 会：检查文件在快照中、行号不越界，并展开为：

```json
{"id": "ev:src:models/net.py:10-12", "kind": "source", "file": "models/net.py",
 "start_line": 10, "end_line": 12, "file_sha256": "<脚本真实计算>"}
```

论文证据写：`{"page": 4, "quote": "原文中连续的一小段（15–200字符）", "section": "3.2", "equation": "(5)", "figure": null, "table": null}`。`page` 是 **PDF 页码**（从 1 开始），印刷页码另写 `printed_page`（能确认才写）。`check` 会去 `paper/pages/page_004.txt` 里（去掉多余空白、连字符换行后）查找 quote，找不到就报错——这是防止编造引文的关键。

### 7.4 输入/输出字段对象（IO）

```json
{
  "name": "batch.obs",
  "container_path": ["batch", "obs"],
  "type": "Tensor",
  "shape": ["B", "T", "D_obs"],
  "dimensions": {"B": "batch size", "T": "时间窗口", "D_obs": "观测维度"},
  "dtype": null, "device": null, "units": null, "default": null,
  "constraints": [],
  "status": "inferred",
  "evidence": ["data/dataset.py:88-95", "models/enc.py:40-41"],
  "reason": "collate 中 torch.stack 得到 [B,T,D]；enc.py:40 的 view 使用 D_obs"
}
```

规则：不能因为参数叫 `images` 就写 `[B,3,224,224]`。查证顺序：类型注解/dataclass → 数据集 `__getitem__` 与 collate → `assert`/`reshape`/`view`/`permute` → 实际消费者 → 配置中的维度值。查不到：`shape: null` + `reason`。返回值要区分：普通 return / 多个 return 分支 / tuple / dict / generator（yield）/ async / 原地修改参数 / 返回 None。

### 7.5 内部步骤对象（step）

```json
{
  "id": "s3", "order": 3,
  "source_range": [42, 47],
  "kind": "if",
  "title": "按 epoch 奇偶选择损失",
  "action": "epoch 为偶数时计算 total_loss，否则调用 normalize",
  "why": "演示条件分支：两种目标交替训练",
  "inputs": ["epoch", "model"], "outputs": ["loss"],
  "conditions": "epoch % 2 == 0",
  "calls": ["sym:losses.py:total_loss:function"],
  "children": []
}
```

`source_range`、`kind`、`calls` **由脚本生成的骨架提供，agent 不得改**；agent 只填 `title/action/why/inputs/outputs`，可把多个相邻骨架步骤合并（合并后的范围 = 被合并步骤的并集，check 会校验）。

### 7.6 调用边（edge，脚本生成）

```json
{
  "id": "e:sym:train.py:main:function->sym:losses.py:total_loss:function@train.py:21",
  "caller": "sym:train.py:main:function",
  "callee": "sym:losses.py:total_loss:function",
  "candidates": [],
  "relation": "calls",
  "resolution": "resolved_static",
  "callsite": {"file": "train.py", "line": 21, "end_line": 21},
  "expression": "losses.total_loss(model, [1, 2])",
  "conditions": ["for epoch in range(args.epochs)", "if epoch % 2 == 0"],
  "note": ""
}
```

- `relation` ∈ `calls | constructs | module_call(nn.Module 调用→forward) | definition_time(装饰器/默认值在定义时执行)`；文件依赖 `imports` 与类继承 `inherits` 另放 `file_edges` / `class_edges`，**不画进调用图**。
- `resolution` ∈ `resolved_static | candidate | unresolved | external`。
- `callee` 为 null 时 `candidates` 列出候选（可为空），`note` 写原因（如“getattr 动态取属性”）。

### 7.7 函数说明（agent 填写，`notes/batch_XXX.json`）

`batches` 子命令会生成待填文件，每个符号一条，脚本已预填的字段不要改：

```json
{
  "symbol_id": "sym:losses.py:total_loss:function",
  "prefilled": {"signature": "...", "definition_range": [5, 12], "docstring": null,
                "callers": [...], "callees": [...], "returns": [...], "yields": [],
                "raises": [], "asserts": [], "shape_hints": [...], "step_skeleton": [...]},
  "role": "loss",
  "summary": "一句话：它在入口流程中负责什么",
  "purpose": "为什么需要它、解决哪一步的问题、谁消费它的结果",
  "inputs": [IO, ...],
  "outputs": [IO, ...],
  "side_effects": [{"text": "修改全局随机种子", "status": "confirmed_source", "evidence": ["utils/helpers.py:3-5"]}],
  "exceptions": [],
  "steps": [step, ...],
  "paper_refs": ["c1"],
  "config_refs": ["lr"],
  "scenario_contracts": [],
  "change_notes": "改这里要注意：返回 tuple(总损失, 分项 dict)，调用者解包两项",
  "needs_context": [],
  "analysis_status": "done"
}
```

- `role` ∈ `entry|config|data|model|loss|train_loop|optim|eval|io|util|other`。
- `analysis_status` ∈ `done|partial|pending`；`partial` 必须在 `needs_context` 写缺什么。
- `scenario_contracts`：多入口时同一函数在不同入口下输入输出不同，按 `{entry_id, callsite, conditions, inputs, outputs, evidence}` 分别记录，不覆盖通用的 inputs/outputs。

### 7.8 其他 agent 写的文件

- `overview.json`（每个入口一份，放在 `notes/overview_<entry名>.json`）：
  `{entry_id, summary, stages:[{order, title, description, symbols:[ids]}], core_symbols:[{id, reason}], learning_path:[ids], dataflow:[{order, symbol_id, line_ref, variable, container_path, shape, meaning, status, evidence}]}`
  `dataflow` 用一个具体样本走一遍：原始数据 → collate → tensor → 编码/融合 → 预测 → loss/后处理；示意样本与真实运行样本要标明。
- `paper-map.json`：第 12 节。
- `experiment-settings.json`：第 13 节。
- `change-impacts.json`（用户提了改动目标时）：`[{target, goal, entry_ids, why_here, upstream:[ids], downstream:[ids], affected_contracts, config_consumers, paper_constraints, suggested_checks, limitations}]`。

### 7.9 atlas.json 顶层（assemble 产出，前端只读它）

```text
schema_version, generated_at
project {name, root, git_commit_or_null, worktree_dirty_or_null}
request {...}
coverage {indexed_files, analyzed_files, excluded, parse_failures, unresolved_calls,
          truncated, pending_symbols, non_python_files, limitations}
sources [{file, sha256, line_count}]            (源码文本单独放 atlas-sources.js)
symbols [{id, file, qualname, kind, definition_range, signature, decorators,
          prefilled..., note(合并后的 agent 说明) | null, in_entries:[entry_id]}]
edges [...]  file_edges [...]  class_edges [...]
entries [{entry_id, path, scenario, root_symbol, closure:[ids], depth_of:{id:n}}]
overviews [...]  paper {...}  experiments [...]  change_impacts [...]
evidence {id: {...}}
freshness {snapshot_at, rechecked_at|null, status: "not_rechecked"|"matched"|"stale"|"unknown"}
```

---

## 8. 脚本实现说明

所有脚本只用标准库（PyYAML 可选）。开头检查版本：

```python
import sys
if sys.version_info < (3, 10):
    sys.stderr.write("需要 Python >= 3.10，当前 %s。Windows 请用 py -3.13\n" % sys.version.split()[0])
    sys.exit(2)
```

### 8.1 `atlas.py` 子命令（实现了才能写进文档）

| 子命令 | 参数 | 作用 / 产出 |
| --- | --- | --- |
| `inspect` | `--request <json>` | 校验路径、入口、论文、Python 版本、PyYAML/pdftotext 是否可用；打印 readiness，不写产物，不执行目标 |
| `extract` | `--request <json>` | 建 RUN_DIR；写 `request.json`、`inventory.json`、`structure.json`（符号/边/步骤骨架/shape 线索/入口闭包）、`sources/`（允许范围内的源码快照）、`manifest.json` |
| `configs` | `--run-dir <dir>` | 写 `config-index.json`：argparse 参数、YAML 键、dataclass 字段、每个键的候选消费行 |
| `paper` | `--run-dir <dir>` | 论文分页：`paper/pages/page_NNN.txt`、`paper/fulltext.txt`（带 `=== PDF第N页 ===` 标记）；无论文写 `paper/status.json` = missing |
| `batches` | `--run-dir <dir> [--size 4]` | 按入口闭包顺序（BFS 深度优先级）生成 `notes/todo/batch_NNN.json` 待填文件 |
| `check` | `--run-dir <dir> --file <json>` | 自动识别类型（notes/overview/paper-map/experiments/change-impacts）并校验；列出每个错误的 JSON 路径与原因 |
| `assemble` | `--run-dir <dir>` | 合并所有已通过 check 的文件 → `atlas.json`；悬空引用直接失败 |
| `validate` | `--run-dir <dir> [--recheck-source]` | 内部一致性检查，写 `validation.json`；带开关时重算原项目文件哈希写 `freshness.json` |
| `render` | `--run-dir <dir>` | 复制 `assets/viewer` → `RUN_DIR/viewer/`，写 `atlas-data.js`、`atlas-sources.js`；打印 `index.html` 绝对路径 |
| `serve` | `--run-dir <dir> [--port 0]` | 只在 127.0.0.1 提供 `RUN_DIR/viewer` 静态文件；打印实际 URL；Ctrl+C 停止 |

退出码：`0` 通过；`1` 程序故障（异常）；`2` 参数/路径/schema 错误；`3` 必要证据或验收不满足。合理存在的 `unknown` 不导致失败；缺证据的“确定”结论、悬空引用、行号越界才失败。

### 8.2 `pyextract.py`：AST 抽取（核心，务必按此实现）

**文件枚举**：从 project_root 递归，排除 `.git .venv venv env __pycache__ node_modules build dist .idea .vscode wandb outputs logs checkpoints data datasets *.pt *.pth *.ckpt *.safetensors *.bin` 及 >1MB 的文本文件；排除项写进 `inventory.json` 的 `excluded`（带原因）。用 `os.path.realpath` 确认每个文件仍在 project_root 内（防 symlink/junction 越界）。非 `.py` 文件只列入 `non_python_files`。

**读源码**：`tokenize.open(path)`（按 PEP 263 识别编码）；失败或 `SyntaxError` → 写入 `parse_failures`（文件、错误、行号），继续下一个文件。

**模块名**：相对路径去 `.py`，`/` 换 `.`，`__init__` 去掉；若存在 `src/` 布局，同时登记去掉 `src.` 前缀的别名。

**作用域遍历骨架**（补全细节，但不要改变这些语义）：

```python
import ast

class Collector(ast.NodeVisitor):
    def __init__(self, rel, src, modname):
        self.rel, self.src, self.mod = rel, src, modname
        self.scope = [("module", "<module>", f"sym:{rel}:<module>:module")]
        self.conds = []                 # 当前语句所处的 if/for/while/try/with 条件文字
        self.symbols, self.calls, self.imports, self.attr_assigns = [], [], [], []

    def seg(self, node):
        return ast.get_source_segment(self.src, node) or ast.unparse(node)

    def cur(self):
        return self.scope[-1][2]

    def qual(self, name):
        parts = [s[1] for s in self.scope[1:]] + [name]
        return ".".join(parts)

    def _def(self, node, kind):
        # 1) 装饰器与默认值在“定义时”由外层作用域执行 -> 记为外层的 definition_time
        for d in node.decorator_list:
            self._visit_definition_time(d)
        if not isinstance(node, ast.ClassDef):
            for d in node.args.defaults + [x for x in node.args.kw_defaults if x is not None]:
                self._visit_definition_time(d)
        in_class = self.scope[-1][0] == "class"
        if kind == "function" and in_class:
            kind = "method"
        sid = f"sym:{self.rel}:{self.qual(node.name)}:{kind}"
        sid = self._dedupe(sid)
        self.symbols.append({"id": sid, "file": self.rel, "qualname": self.qual(node.name),
                             "kind": kind, "definition_range": [node.lineno, node.end_lineno],
                             "body_start": node.body[0].lineno,
                             "decorators": [self.seg(d) for d in node.decorator_list],
                             "docstring": ast.get_docstring(node),
                             "parent": self.cur()})
        # 2) 函数体属于新作用域；嵌套函数的调用不算外层函数的调用
        self.scope.append(("class" if isinstance(node, ast.ClassDef) else "function", node.name, sid))
        saved, self.conds = self.conds, []
        for stmt in node.body:
            self.visit(stmt)
        self.conds = saved
        self.scope.pop()

    def visit_FunctionDef(self, n): self._def(n, "function")
    def visit_AsyncFunctionDef(self, n): self._def(n, "async_function")
    def visit_ClassDef(self, n): self._def(n, "class")

    def visit_If(self, n):
        self.visit(n.test)
        t = self.seg(n.test)
        self.conds.append(f"if {t}")
        for s in n.body: self.visit(s)
        self.conds.pop()
        if n.orelse:
            self.conds.append(f"else (not {t})")
            for s in n.orelse: self.visit(s)
            self.conds.pop()
    # visit_For / visit_While / visit_Try / visit_With 同理：先访问 iter/test/items，
    # 再压入 "for x in ..." / "while ..." / "try" / "except E" / "with ..." 条件后访问 body

    def visit_Call(self, n):
        self.calls.append({"caller": self.cur(), "func": describe(n.func),
                           "expression": self.seg(n), "line": n.lineno, "end_line": n.end_lineno,
                           "conditions": list(self.conds), "definition_time": self._deftime})
        self.generic_visit(n)

    _deftime = False

    def _visit_definition_time(self, node):
        # 注意：@deco 在 AST 里是 Name，不是 Call；但装饰器在定义时会被调用一次，
        # 所以对非 Call 的装饰器也要补记一条“定义时调用”。默认值表达式则正常访问其中的 Call。
        if not isinstance(node, ast.Call) and node in self._decorators_now:
            self.calls.append({"caller": self.cur(), "func": describe(node),
                               "expression": "@" + self.seg(node), "line": node.lineno,
                               "end_line": node.end_lineno, "conditions": list(self.conds),
                               "definition_time": True})
        old, self._deftime = self._deftime, True
        self.visit(node)
        self._deftime = old
    # _decorators_now：在 _def 开头设为 set(node.decorator_list)，处理完装饰器后清空。
    # _dedupe(sid)：同一 sid 已存在时返回 sid + "#2"、"#3"……
```

`describe(func)` 返回：`Name` → `{"kind":"name","name":"foo"}`；属性链 `a.b.c` → `{"kind":"attr","base":["a","b"],"attr":"c"}`；其他（下标、调用结果再调用等）→ `{"kind":"dynamic","text": 源码}`。

还要在同一遍中收集：
- `import`/`from ... import ... as ...`（含相对导入层级 `level`）→ `imports`。
- 类方法里的 `self.X = Name(...)` / `self.X = mod.Name(...)` → `attr_assigns`（用于推断 `self.X` 的类型）。
- 模块顶层 `if __name__ == "__main__":` → 记一个 `control_region`（不是函数），其中的调用 caller 仍是 `<module>`，条件为 `if __name__ == "__main__"`。
- 每个函数：参数（posonly/普通/`*args`/kwonly/`**kwargs`、默认值文字、注解 `ast.unparse`）、返回注解、所有 `return` 的行号与表达式、`yield`、`raise`、`assert` 文字。
- **shape 线索**：函数体内匹配 `.view( .reshape( .permute( .transpose( .unsqueeze( .squeeze( .flatten( torch.cat( torch.stack( rearrange( einsum( .shape .size(` 的行，记 `{line, text}`，供 agent 判断 shape。
- **步骤骨架**：对函数体的顶层语句逐条生成 `{id, order, kind, source_range:[lineno,end_lineno], first_line_text, calls:[该语句内的调用表达式], children}`；`if/for/while/try/with` 的子体递归生成 children（最多 3 层）；连续的、不含调用的简单赋值合并为一步。

### 8.3 `resolve.py`：调用解析规则（按顺序判断，命中即停）

对每个调用记录，在其 caller 所在模块里：

1. `name` 调用（顺序模仿 Python 的“局部 → 外层 → 模块 → 内置”查找）：
   a. 名字是当前函数或外层函数作用域里定义的嵌套函数 → 该符号，`resolved_static`。
   b. 名字是当前函数的参数或局部变量（例如 `model(batch)`、`fn()`）→ `unresolved`，note=“调用参数/局部变量中的可调用对象，静态无法确定”。例外：同一函数内 `x = 项目内类(...)` 直接赋值后调用 `x(...)` → 见规则 3。
   c. 名字是本模块顶层函数/类 → 函数则 `calls`，类则 `constructs` 指向 `Class.__init__`（没有 `__init__` 就指向类本身），`resolved_static`。
   d. 名字来自 `from X import Y as name`：X 是项目内模块 → 在 X 中找 Y（若 Y 又是 X 再导入的名字，最多追 3 层）→ `resolved_static`；若 `X.Y` 本身是项目内子模块（如 `from utils import helpers`），则 name 是**模块别名**，按规则 2a 处理其属性调用；X 是外部包 → `external`，callee=`ext:X.Y`。
   e. 是 Python 内置函数（`print len range sum ...`）→ 默认不建边，只计数到 `coverage.builtin_calls`。
   f. 其他 → `unresolved`。
2. `attr` 调用 `base.attr()`：
   a. base 是 import 的模块别名（`import losses`、`from utils import helpers`、`import a.b as c`）→ 在该模块找 attr，规则同 1b/1c。
   b. base == `["self"]` 且在类方法内 → 先在本类找 attr，再按项目内基类名逐级找；本类找到 `resolved_static`，基类找到 `candidate`（note=“可能被子类覆盖”）。
   c. base == `["self", X]`，且 `attr_assigns` 记录 `self.X = SomeClass(...)` 且 SomeClass 在项目内 → 在 SomeClass 找 attr → `candidate`，note=“由 __init__ 中 self.X = SomeClass(...) 推断”。
   d. 其他 base：项目内同名方法数量 1–5 个且 attr 不在常见通用名单（`append get items keys values update to cuda cpu item numpy detach format join split strip`）→ `candidate`，`candidates` 列全部，`callee` = null；否则 `unresolved`。
   e. base 来自外部包（`torch.xxx`、`np.xxx`、`F.relu`）→ `external`。
3. **PyTorch 模块调用**：`self.X(...)`（X 由 1.2c 推断为项目内类）或 `name(...)` 中 name 是项目内类的实例变量（仅限同函数内 `name = Class(...)` 直接赋值）→ 若该类定义了 `forward` 且没有自定义 `__call__`，建 `relation="module_call"`、`resolution="candidate"` 指向 `Class.forward`，note=“nn.Module.__call__ 会调用 forward（还会触发 hooks）”；若定义了 `__call__` 则指向 `__call__`。
4. `dynamic` → `unresolved`。`getattr(...)`、`importlib.import_module`、注册表 `REGISTRY[name](...)` 一律 `unresolved`，不猜。
5. 装饰器/默认值里的调用 → `relation="definition_time"`，caller 为外层作用域（模块或类）。

**入口闭包**：从入口的 root symbol（指定 `symbol` 则用它，否则 `<module>`）出发，沿 `calls/constructs/module_call` 且 resolution ∈ {resolved_static, candidate} 的边 BFS；记录每个符号的最小深度 `depth_of`；超过 `max_depth` 或 `max_symbols` 时停止并在 `coverage.truncated` 写明。callers 列表用**全项目**边计算，不只入口闭包（否则会漏调用者）。

**PyTorch 训练项目要额外注意**（写进 workflow.md 让 agent 解释时遵守）：函数调用图 ≠ 模块包含树（`named_modules()`）≠ tensor 数据流 ≠ 反向传播图；`loss.backward()` 不画成调用了 forward；`model.train()/eval()`、`torch.no_grad()`、AMP、`detach`、冻结参数、DDP 都要在相关步骤里说明。

### 8.4 `configs.py`：配置抽取

- argparse：找 `add_argument(...)` 调用，记录 flag、`dest`（没写就由 flag 推导，`-` 换 `_`）、`default`、`type`、`choices`、`help`、行号。
- YAML（有 PyYAML 时 `yaml.safe_load`，**禁止** `yaml.load`）：展开成 `a.b.c → value`，用文本搜索补近似行号。没有 PyYAML：按缩进正则读 `key: value`，状态标 `inferred`。
- JSON/TOML：`json` / `tomllib`。
- dataclass / `class Config:` 的类属性：AST 读取字面量默认值；表达式无法求值就存源码文字。
- Hydra/OmegaConf：只识别 `defaults:` 列表和 `${...}` 插值并原样记录，**不求值**，不假设项目一定用 Hydra。
- 不执行任何 Python 配置文件；不读取环境变量的值。
- 消费者候选：对每个键的末段名 `k`，在项目 `.py` 中 `rg -n` 搜 `args.k`、`cfg.k`、`config.k`、`["k"]`、`['k']`、`.get("k"`，记录 `{file, line, text, symbol(所在函数)}`。只有定义、没找到消费处 → 标记“定义但未确认消费”。

### 8.5 `paper.py`

- PDF：`pdftotext -layout -enc UTF-8 <pdf> <out.txt>`，按换页符 `\f` 切分为每页文本（页码从 1 开始）。某页文本少于 50 字符 → 在 `paper/status.json` 记“可能是扫描页，需人工看原页”，**不要装 OCR**。
- `.md/.txt`：按 `=== PDF第N页 ===` 或 `<!-- page N -->` 标记切页；没有标记就整篇算第 1 页并在 status 里说明。
- 提供函数 `find_quote(page_text, quote)`：两边都做“合并空白、去掉行尾连字符换行、统一引号”后做子串匹配。

### 8.6 `checks.py`（check 子命令）

至少检查：
- JSON 能解析、必填字段齐全、枚举值合法。
- 所有 `symbol_id` 存在于 `structure.json`；所有源码证据文件存在、行号在 `[1, line_count]` 内。
- notes 的 `steps[].source_range` 在函数 `definition_range` 内，且等于骨架步骤或其并集。
- notes 中 status 为 `confirmed_source` 的 IO/副作用必须有至少一条 evidence。
- `analysis_status=="done"` 时 `summary/purpose/steps` 非空，inputs/outputs 字段存在（可以是空列表 + 说明“无参数/返回 None”）。
- 论文证据的 page 存在且 quote 能在该页找到。
- 实验设置的 `consumed_by` 行号存在。
- 报错格式：`[ERROR] notes/todo/batch_003.json $.items[1].steps[2].source_range: [40, 60] 超出函数范围 [42, 55]`，方便弱模型逐条修。

### 8.7 `render.py`

- 复制 `assets/viewer/*` 到 `RUN_DIR/viewer/`。
- 写 `atlas-data.js`：`window.ATLAS_DATA = <json>;`。json 用 `json.dumps(obj, ensure_ascii=False)`，然后把 `<` 替换为 `\u003c`、`\u2028`/`\u2029` 替换为转义形式。
- 写 `atlas-sources.js`：`window.ATLAS_SOURCES = {"相对路径": "源码全文", ...};`（同样转义），只包含 inventory 中被分析的 `.py` 和用到的配置文件；不复制 PDF、权重、数据。
- 冒烟测试（validate 也会做）：`node -e "global.window={};require('./atlas-data.js');require('./atlas-sources.js');console.log(Object.keys(window.ATLAS_DATA).length)"`。

### 8.8 `serve`

用 `http.server` 的 `SimpleHTTPRequestHandler`（`directory=RUN_DIR/viewer`），绑定 `127.0.0.1`。拒绝含 `..`、反斜杠、绝对路径的请求。只读，不提供任何写入或命令接口。

---

## 9. 可视化界面（`assets/viewer`）

### 9.1 布局

```text
┌ 顶栏：项目名 | 入口切换(entry_id) | 场景 | 快照时间 | 新鲜度(未重验/匹配/已过期) | 覆盖率: 已解释 n/m, 未解析调用 k ┐
├ 左栏 ──────────────┬ 中区（页签）────────────────────────┬ 右栏：函数卡片 ─────────┤
│ 搜索框             │ [总览] [调用图] [调用层级] [内部流程] │ 名称/全限定名/文件:行     │
│ 入口阶段           │                                     │ 一句话作用 / 使用目的      │
│ 核心函数（排序）    │                                     │ 签名                     │
│ 学习路线           │                                     │ 输入表 / 输出表(含shape)  │
│ 文件树             │                                     │ 副作用 / 异常             │
│                    │                                     │ 调用者 ↑ / 被调用者 ↓(可点)│
│                    │                                     │ 论文对应 / 配置引用        │
├────────────────────┴─────────────────────────────────────┴──────────────────────────┤
│ 底部页签：[源码] [论文对照] [实验设置] [修改影响] [未知清单]                             │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

中文界面；专业术语第一次出现加 `title` 悬停解释。窄窗口时左右栏可折叠。

### 9.2 必须实现的交互

1. 点击调用图节点 / 层级树节点 / 列表项 → 选中函数：右栏更新、图中高亮相邻边、底部切到源码并高亮定义范围。
2. 搜索名字/路径/作用；同名函数显示全限定名+文件，选中的是准确的那个。
3. 卡片中调用者/被调用者每项可点；未解析的项点开显示调用表达式、行号与原因。
4. 调用图：按深度显示（默认 3，滑块 1–8）；过滤边类型与 resolution；双击节点展开其邻居；`candidate` 虚线、`unresolved` 点线 + 指向“? 未解析”占位节点；图例同时用文字和线型，不只靠颜色。
5. 调用层级树：从入口 root 递归 `<details>` 展开；已展开过的符号再出现时显示 “↻ 见上方” 不再展开（防递归死循环）；每行显示调用条件（如 `if epoch % 2 == 0`）和调用行号，点击行号跳到调用点。
6. 内部流程：按 `steps` 竖向展示，`if/for/while/try` 的 children 缩进显示，分支标“是/否”；点击步骤 → 源码高亮该步行范围。
7. 论文对照：创新点卡片 → 实现函数（可点）→ 是否在当前入口闭包（是/否/仅其他入口）；“论文步骤 ↔ 代码步骤”两列对照；反向：函数卡片显示它对应的论文位置（页码 + 引文）。
8. 实验设置表：设置名 | 论文值(页码) | 仓库默认值(文件:行) | 本次最终值 | 优先级说明 | 消费位置(可点) | 状态；不一致行醒目标记。
9. 修改影响：以当前选中函数为目标，BFS 显示上游调用者（深度可调）、下游被调用者、相关配置、论文约束、`change-impacts.json` 中的说明；顶部固定提示“候选影响，动态调用/未解析边可能遗漏”。
10. 未知清单：未解析调用、pending 函数、unknown 字段、conflict、解析失败文件、截断信息。
11. URL hash 记录状态，例如 `#sym=<encodeURIComponent(id)>&tab=code&line=21&entry=entry:train`；刷新可恢复；浏览器前进/后退可用。
12. 键盘：Tab 可聚焦列表项，Enter 打开。

### 9.3 关键代码骨架（`app.js`，补全即可）

```javascript
const D = window.ATLAS_DATA, SRC = window.ATLAS_SOURCES;
if (!D) { document.body.textContent = '未找到 atlas-data.js，请先运行 render'; throw new Error('no data'); }
const SYM = new Map(D.symbols.map(s => [s.id, s]));
const OUT = new Map(), IN = new Map();
for (const e of D.edges) {
  if (!OUT.has(e.caller)) OUT.set(e.caller, []); OUT.get(e.caller).push(e);
  if (e.callee) { if (!IN.has(e.callee)) IN.set(e.callee, []); IN.get(e.callee).push(e); }
}

// 安全创建元素：永远用 textContent，绝不把数据拼进 innerHTML
function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'onclick') n.addEventListener('click', v);
    else if (k === 'class') n.className = v;
    else n.setAttribute(k, String(v));
  }
  for (const k of kids) n.append(k instanceof Node ? k : document.createTextNode(String(k ?? '')));
  return n;
}

function go(params) {                       // 所有跳转统一走这里
  const p = new URLSearchParams(location.hash.slice(1));
  for (const [k, v] of Object.entries(params)) v == null ? p.delete(k) : p.set(k, v);
  location.hash = p.toString();
}
window.addEventListener('hashchange', route);
function route() {
  const p = new URLSearchParams(location.hash.slice(1));
  const sym = p.get('sym'), line = Number(p.get('line')) || null;
  if (sym && SYM.has(sym)) { renderCard(SYM.get(sym)); highlightInGraph(sym); }
  if (p.get('tab')) showTab(p.get('tab'));
  if (sym && SYM.has(sym)) showSource(SYM.get(sym).file, line ? [line, line] : SYM.get(sym).definition_range);
}

function showSource(file, [start, end]) {   // 行号 1 起始、两端包含
  const box = document.getElementById('source'); box.replaceChildren();
  const text = SRC[file]; if (text == null) { box.append(el('p', {}, `快照中没有 ${file}`)); return; }
  const lines = text.split('\n');
  box.append(el('div', {class: 'src-head'}, `${file}  第 ${start}-${end} 行  (快照，${D.freshness.status})`));
  const tbl = el('table', {class: 'src'});
  lines.forEach((t, i) => {
    const n = i + 1;
    const tr = el('tr', {id: `L${n}`, class: n >= start && n <= end ? 'hl' : ''},
                  el('td', {class: 'ln'}, n), el('td', {class: 'code'}, t));
    tbl.append(tr);
  });
  box.append(tbl);
  document.getElementById(`L${start}`)?.scrollIntoView({block: 'center'});
}

function renderTree(rootId, container) {    // 调用层级树
  const seen = new Set();
  (function walk(id, parent, depth) {
    const s = SYM.get(id); const d = el('details', depth < 2 ? {open: ''} : {});
    d.append(el('summary', {}, el('a', {href: '#', onclick: ev => { ev.preventDefault(); go({sym: id, tab: 'code', line: null}); }}, s ? s.qualname : id)));
    parent.append(d);
    if (seen.has(id)) { d.append(el('div', {class: 'muted'}, '↻ 已在上方展开')); return; }
    seen.add(id);
    for (const e of (OUT.get(id) || [])) {
      const row = el('div', {class: `edge ${e.resolution}`},
        el('a', {href: '#', onclick: ev => { ev.preventDefault(); go({sym: e.caller, line: e.callsite.line, tab: 'code'}); }}, `L${e.callsite.line}`),
        ' ', e.conditions.length ? `[${e.conditions.join(' / ')}] ` : '');
      d.append(row);
      if (e.callee && SYM.has(e.callee)) walk(e.callee, d, depth + 1);
      else row.append(el('span', {class: 'unresolved'}, `? ${e.expression}（${e.note || e.resolution}）`));
    }
  })(rootId, container, 0);
}
```

调用图（有 vendored 库时）：

```javascript
const cy = cytoscape({
  container: document.getElementById('graph'),
  elements: buildElements(currentEntry, depthLimit),   // 只放入口闭包中 depth<=depthLimit 的节点
  layout: {name: 'dagre', rankDir: 'LR', nodeSep: 20, rankSep: 60},
  style: [
    {selector: 'node', style: {label: 'data(label)', 'font-size': 10, shape: 'round-rectangle'}},
    {selector: 'edge', style: {'curve-style': 'bezier', 'target-arrow-shape': 'triangle', width: 1.5}},
    {selector: 'edge[resolution = "candidate"]', style: {'line-style': 'dashed'}},
    {selector: 'edge[resolution = "unresolved"]', style: {'line-style': 'dotted'}},
    {selector: '.hl', style: {'border-width': 3, 'line-color': '#d33', 'target-arrow-color': '#d33'}}
  ]
});
cy.on('tap', 'node', ev => go({sym: ev.target.id(), tab: 'code', line: null}));
```

若 `typeof cytoscape === 'undefined'`（未授权下载库），调用图页显示“图库未安装，请使用调用层级页”，其余功能正常。

### 9.4 安全（必须）

- 源码、注释、论文摘录、agent 写的文字一律 `textContent` 渲染；禁止 `innerHTML`、`eval`、`new Function`、`on*` 属性字符串、`javascript:` 链接。
- 所有资源本地，无 CDN、无远程字体、无联网请求。
- 可选“在 VS Code 打开”链接 `vscode://file/<绝对路径>:<行>`，作为额外按钮；页面内跳转不能依赖它。

---

## 10. 运行时工作流（写进 `references/workflow.md`，skill 每次被调用时执行）

以下 `PY` 为第 3.1 节的 Python，`SK` 为 skill 目录（Claude Code 用 `${CLAUDE_SKILL_DIR}`；Codex 用 SKILL.md 所在目录）。

1. **整理输入**：根据用户的话写 `request.json`（第 6 节）；缺入口就看 README/启动脚本猜候选并问用户一次。
2. **预检**：`PY -X utf8 SK/scripts/atlas.py inspect --request request.json`；非 0 就按提示修正，不要继续。
3. **抽取**：`... extract --request request.json`；然后 `... configs --run-dir R`、`... paper --run-dir R`。
4. **读结构**：读 `structure.json` 的 coverage、入口闭包大小、未解析调用数；向用户简要报告规模。闭包 >300 个函数时，先只深读深度 ≤4 的和论文相关的，其余标 pending。
5. **论文先行（有论文时）**：按第 12 节读论文，先产出 `paper-map.json` 的 contributions 与 experiment 部分（代码映射可留空），`check` 通过。这样深读函数时就知道哪些函数是创新相关的。
6. **生成批次**：`... batches --run-dir R --size 4`。
7. **逐批深读**（第 11 节模板）：读 `notes/todo/batch_NNN.json` → 打开对应源码 → 填写 → 另存为 `notes/batch_NNN.json` → `check`。不通过只改这一批。所有 batch 完成或达到预算后进入下一步。
8. **总览、论文映射、实验设置**：写 `overview_<entry>.json`；补全 `paper-map.json` 的代码映射；写 `experiment-settings.json`；用户提了改动目标就写 `change-impacts.json`。每个都要 `check` 通过。
9. **装配与渲染**：`assemble` → `validate` → `render`。
10. **交付**：打开 `RUN_DIR/viewer/index.html`（或 `serve` 后给出 `http://127.0.0.1:<端口>`）；有浏览器工具就实际点击：入口 → 核心函数 → 调用者 → 步骤 → 论文映射 → 实验消费者，确认跳到正确行。向用户汇报：产物路径、已解释/待解释数量、未解析调用数、论文状态、快照时间、未执行运行观测、建议的学习顺序。

---

## 11. 函数深读批次模板（写进 `references/reading-protocol.md`）

每个 batch 给自己下面这段指令，然后照做：

```text
你只解释本批 notes/todo/batch_NNN.json 中列出的 symbol_id，不新增不存在的函数。
1. 打开每个函数的完整源码（definition_range），以及 prefilled 中 callers/callees 的签名。
2. 需要时再读：所属类的 __init__、直接调用者的调用行、相关配置键、论文对应段落。只定向读，不通读仓库。
3. 逐项填写：role、summary（一句话）、purpose（为什么需要、谁用结果）、inputs、outputs、
   side_effects、exceptions、steps、paper_refs、config_refs、change_notes。
4. steps：基于 step_skeleton，保留 source_range/kind/calls 不变，只填 title/action/why/inputs/outputs；
   可以合并相邻步骤，不能拆出骨架没有的行范围。
5. 每个 status=confirmed_source 的结论都写 evidence（"文件:起-止"）。
6. shape 只能来自 shape_hints、注解、collate、assert、配置；否则 shape=null 并写 reason。
7. 调用目标只能引用 prefilled.callees 里已有的 ID 或写“未解析”。
8. 看不懂、缺上下文的写进 needs_context，analysis_status=partial，不要猜。
9. 输出必须是合法 JSON（不要 Markdown、不要注释、不要尾逗号）。
写完运行 check；按报错的 JSON 路径逐条修改，直到退出码 0。
```

核心函数排序（写 `core_symbols` 时用）：入口控制 > 数据构建/collate > 模型 forward > loss > 训练/评估循环 > 论文创新相关实现 > 工具函数。排序只决定展示顺序，工具函数也要有卡片。

---

## 12. 论文创新点 ↔ 代码对照（写进 `references/paper-and-experiments.md`）

没有论文：`paper.status = "missing"`，界面显示“未提供论文”，代码部分照常完成。

有论文时按顺序：

1. 读 `paper/fulltext.txt` 的标题、摘要、引言末尾的 contributions 列表 → 记录作者**明确声称**的创新点（不要根据仓库名自己发明）。
2. 读方法章节、公式、算法框、模型结构图说明 → 每个创新点写“核心机制”：步骤、公式、变量含义与维度。
3. 读实验、实现细节、附录、消融 → 列关键实验设置（第 13 节）。
4. 用论文术语、模块名、公式变量名、超参名在项目中 `rg -n -i` 定向搜索；名字对不上时根据输入输出与计算过程追踪。
5. 读候选函数完整实现，与公式/算法逐步对照：shape、归一化、符号方向、mask、采样顺序、loss 目标。
6. 每条映射标 `direct | inferred | not_found | conflict`，并给论文定位和代码定位。
7. 分别说明：已实现但不在当前入口路径上、只在测试中存在、配置默认关闭、只在训练/只在推理使用的模块。

`paper-map.json`：

```json
{
  "status": "available",
  "paper": {"title": "...", "source": "D:/Papers/x.pdf", "pages": 14},
  "contributions": [
    {"id": "c1",
     "claim": "论文原始主张的中文简述",
     "compared_to": "相对哪个基线/旧方法改变了什么；论文没说就 null",
     "mechanism": "算法步骤/公式，变量与维度含义",
     "paper_evidence": [{"page": 4, "quote": "...", "section": "3.2", "equation": "(5)"}],
     "code_mappings": [
       {"symbol_id": "sym:models/fusion.py:CrossFusion.forward:method",
        "evidence": ["models/fusion.py:30-52"],
        "status": "direct",
        "step_alignment": [{"paper_step": "式(5) 计算注意力权重", "code_step": "s2", "note": ""}],
        "on_entry_path": null}
     ],
     "key_configs": ["fusion.num_heads"],
     "io_change": "创新对数据格式或训练目标的影响",
     "modification_constraints": "要保持的数学/实验假设",
     "conflicts": []}
  ]
}
```

`on_entry_path` 由 assemble 根据入口闭包自动填写，agent 写 null。一个创新可对应多个函数，一个函数可对应多个创新。公式与代码冲突时两边原文都保留，标 `conflict`，不擅自判断谁对。界面必须提供“创新点 → 实现函数 → 入口路径”的可点击定位，以及“论文步骤 ↔ 代码步骤”的对照，不能只有一段论文摘要。

---

## 13. 实验关键设置：三方对照 + 实际消费者

对每个关键设置分别记录**论文值、仓库默认值、本次场景最终值**；最终值静态无法确定就写 unknown，不能拿默认值冒充。

按项目实际情况核对（没有的写不适用）：数据集版本/划分/增强/归一化统计/窗口长度/tokenizer；模型层数/维度/head/冻结/预训练权重/精度；每项 loss 的定义/reduction/权重/mask；batch size/有效 batch/学习率/优化器/scheduler/warmup/epoch 或 steps/梯度累积/裁剪；seed/重复次数/设备/分布式；推理采样步数/温度；checkpoint 选择、验证频率、评估指标公式与聚合方式、消融开关。

优先级：先确认项目的配置机制（argparse / YAML / Hydra / dataclass / 环境变量），再写出真实覆盖顺序，例如“YAML 默认 < 命令行 --lr < 代码中第 88 行再次修改”。

`experiment-settings.json`：

```json
[
  {"id": "lr", "entry_id": "entry:train", "setting": "学习率",
   "paper_value": {"value": "3e-4", "evidence": [{"page": 9, "quote": "learning rate of 3e-4"}]},
   "repo_default": {"value": "1e-3", "evidence": ["train.py:12-12"]},
   "selected_value": {"value": "3e-4", "source": "request.entries[0].args --lr", "status": "confirmed_source"},
   "precedence": "argparse 默认 1e-3，被命令行 --lr 3e-4 覆盖",
   "consumed_by": [{"evidence": "train.py:30-30", "symbol_id": "sym:train.py:main:function", "how": "传入 Adam(lr=args.lr)"}],
   "status": "match",
   "impact": "影响收敛速度；改模型宽度时可能需要重新调"}
]
```

`status` ∈ `match | mismatch | unknown | paper_only | code_only | defined_not_consumed`。每个设置都必须追到消费它的代码行（例如 `lr` 要指到 optimizer 构造处）。不能把“一次运行成功”写成“论文复现成功”。

---

## 14. 修改影响与更新

用户说“我想改 X”时（只给建议，不改源码）：

1. 用全限定符号定位最小改动位置，解释为什么是这里。
2. 列直接/间接调用者（全项目边）和下游消费者，以及依赖的输入输出契约。
3. 列相关配置、模型状态、loss、指标、论文约束。
4. 给最小检查清单：函数契约、shape、关键分支、训练/推理一致性、配置传播、评估影响。
5. 写进 `change-impacts.json`，重新 assemble/render，在界面“修改影响”页可见。

“零调用者”“未解析动态边”不代表安全，结果一律称“候选影响”。

更新：源码变了就重新 `extract`；`batches` 对比旧 run 的文件哈希，未变化函数的 notes 可复制复用，变化函数重新深读。`validate --recheck-source` 比对原项目当前哈希：一致 → `matched`（只代表“在重验时刻一致”），不一致 → `stale`，原项目不可访问 → `unknown`。离线打开且未重验时显示“未重验”。

---

## 15. 可选：真实运行观测（本期默认不做）

只有在静态版本全部验收通过、且用户明确要求并提供了**环境绝对路径、cwd、精确命令数组、样例输入、checkpoint、超时、允许的副作用**之后才实现。实现时：

- 用 `sys.setprofile` 记录项目内函数的 call/return；只记录参数和返回值的 type / shape / dtype / device（最多 2 层容器），不调用对象的 `repr`，不保存 tensor 内容。
- PyTorch 可加 forward pre/post hook 记录模块 I/O，单独输出，不和调用图混在一起。
- 超时、事件数上限、异常 traceback、退出码都要记录；generator 的 yield 不当作 return。
- 结果状态标 `observed_runtime`，并写清楚这是哪次运行、哪组输入下的观测；不能证明未走分支不会执行。

没实现就不要在 CLI 和文档中出现 `capture` 命令。

---

## 16. SKILL.md 模板（阶段 7 照此写，按实际实现调整）

```markdown
---
name: research-code-atlas
description: 论文与代码执行图谱。给定项目路径、入口文件（可多个）和可选论文/配置，静态分析 Python 研究代码，生成可离线打开、可点击跳转源码的 HTML 学习界面：入口主要作用、核心函数、调用关系图与调用层级树、每个函数的输入输出格式、使用目的、内部执行步骤，并对照论文创新点、实验关键设置和修改影响。用于“帮我理解这个项目/入口/训练流程”“结合论文看代码”“我想改某个模块先看影响”。不修改项目、不执行训练。
---

# 论文与代码执行图谱

## 何时使用
用户想深入理解一个研究代码项目的执行逻辑（常见：train.py / eval.py / infer.py），尤其要结合论文创新点和实验设置，或准备修改代码前看影响。

## 需要的输入
项目根目录（必需）、入口文件（必需，可多个并标 train/eval/infer）、论文 PDF/MD（可选）、配置文件与启动参数（可选，只作线索）、学习/修改重点（可选）。

## 准备
1. skill 目录：Claude Code 为 `${CLAUDE_SKILL_DIR}`；其他宿主为本文件所在目录。下文记为 SK。
2. Python：读取 `SK/local.json` 的 `python`；没有则依次尝试 `py -3.13`、`python3`、`python`，必须 >= 3.10。命令统一加 `-X utf8`。
3. 读 `SK/references/workflow.md` 和 `SK/references/schemas.md`。有论文时再读 `SK/references/paper-and-experiments.md`；深读函数时读 `SK/references/reading-protocol.md`。

## 流程（详见 workflow.md）
1. 写 request.json → `PY -X utf8 SK/scripts/atlas.py inspect --request request.json`
2. `extract` → `configs` → `paper`
3. 有论文：先写 paper-map.json 的创新点与实验设置并 check
4. `batches` → 逐批填写 notes → 每批 `check`
5. 写 overview / 补全 paper-map 代码映射 / experiment-settings /（如有）change-impacts，并 check
6. `assemble` → `validate` → `render`，打开 `RUN_DIR/viewer/index.html`
7. 汇报：产物路径、已解释/待解释数、未解析调用、论文状态、快照时间、学习顺序

## 规则
- 只做静态分析；不导入、不运行目标项目；不改目标文件。
- 不编造 shape、引文、页码、配置值；不确定写 unknown + 原因。
- 每次只深读一个小批次；check 不通过只修当前批。
- 运行观测需要用户提供完整运行清单和授权（若已实现，见 runtime.md）。
```

frontmatter 只用 `name` 与 `description` 两个字段（两个宿主都兼容）；description 写清何时用、何时不用。

---

## 17. 分阶段执行计划（逐项打勾，写进 HANDOFF）

每阶段格式：**做什么 → 用什么 → 产出 → 验收命令 → 通过标准**。

### 阶段 0：预检与 PRD
- 做：读工作区规则；检查 BUILD_ROOT 是否存在（存在则列内容、不覆盖）；记录 `py -3.13 --version`、`node --version`、`rg --version`、`pdftotext -v`；确认 skill-creator 可用；写 HANDOFF.md（路径变量 + 阶段清单）和 docs/PRD.md。
- 授权：把需要授权的事一次列给用户（建 venv 并装 PyYAML；npm pack 两个 JS 库；最后复制 skill 到全局目录）。未获授权的项走降级方案，不停工。
- 通过：HANDOFF 与 PRD 存在；环境版本已记录。

### 阶段 1：fixture 与 ground truth（先写测试）
- 做：按第 18 节原样创建 `tests/fixtures/mini_proj/`、`mini_paper.md`、`ground_truth.json`；写 `tests/test_extract.py`（unittest），此时运行应失败（脚本还没写）。
- 验收：`PY -X utf8 -m unittest discover -s SKILL_SRC/tests -v` → 失败原因是“找不到 pyextract/atlas”，不是语法错误。

### 阶段 2：抽取与调用解析
- 做：实现 `atlas.py`（inspect/extract）、`pyextract.py`、`resolve.py`。
- 验收：
  - `PY -X utf8 SKILL_SRC/scripts/atlas.py extract --request <fixture 的 request.json>` 退出码 0；
  - `unittest` 全部通过（第 18.3 节的每条期望边/未解析项/作用域规则）；
  - 用一个含 `SyntaxError` 的临时文件验证 parse_failures 记录且不崩溃。
- 通过前**不准**进入阶段 3。

### 阶段 3：批次与校验
- 做：实现 `batches`、`check`（notes 部分）。亲自为 fixture 的全部函数写 notes（这一步也是在练习深读协议）。故意制造 3 个错误（行号越界、不存在的 symbol、confirmed 无证据）确认 check 能报出准确 JSON 路径。
- 通过：fixture 全部 notes check 退出码 0；3 个故意错误都被拦截（退出码 2 或 3）。

### 阶段 4：论文与配置
- 做：实现 `paper`、`configs`、check 的 paper-map/experiments 部分。用 `mini_paper.md` 写 paper-map（必须包含 direct、not_found、conflict 三种状态各一条）和 experiment-settings（包含 match、mismatch、defined_not_consumed）。故意写一条页内不存在的 quote，确认被拦截。若本机有任意真实 PDF 可用，额外测试 pdftotext 分页（只读）。
- 通过：check 全部通过；假引文被拦截；`--unused_flag` 被标为 defined_not_consumed。

### 阶段 5：装配与验证
- 做：实现 `assemble`、`validate`（含 `--recheck-source`）。
- 通过：`atlas.json` 生成；validate 退出码 0；修改 fixture 中一个文件的一行后 `validate --recheck-source` 显示 stale（测完恢复该行，并说明这是 fixture 自己的文件）。

### 阶段 6：可视化界面
- 做：（获授权后）`npm pack cytoscape@3.34.3 cytoscape-dagre@4.0.1` 到临时目录，解压取 `dist/cytoscape.min.js`、`dist/cytoscape-dagre.js` 放入 `assets/viewer/vendor/`，写 LICENSES.md；实现 index.html/app.js/style.css 与 `render`、`serve`。
- 验收：
  - `render` 后 node 冒烟测试通过；
  - 双击 / 用浏览器打开 `viewer/index.html`，逐条完成第 19.2 节浏览器清单；
  - 安全测试：fixture 注释里的 `</script><script>window.__x=1</script>` 只显示为文字，`window.__x` 为 undefined；
  - 断网（或检查 DevTools Network 无外部请求）仍可用。
- 有浏览器自动化工具就用它截图+记录控制台；没有就写“人工检查”并列出你执行的每一步与结果，不得写“自动验收通过”。

### 阶段 7：SKILL.md 与 references
- 做：按第 16 节写 SKILL.md；把第 7、10、11、12、13 节整理进 references（不要把本 prompt 原样塞进去）；写 `scripts/README.md`（每个子命令的参数、默认值、产出、退出码、示例）；写 `local.example.json`。用 skill-creator 的校验（Anthropic 版 `quick_validate.py` 或宿主自带校验）检查 frontmatter。
- 通过：校验通过；README 中每个命令都实际跑过一次。

### 阶段 8：端到端（模拟真实使用）
- 做：在一个**新的会话**里，只说“使用 research-code-atlas 分析 `<fixture 路径>`，入口 train.py 和 eval.py，论文 mini_paper.md”，看 agent 能否只靠 SKILL.md 完成全流程。
- 再选一个**真实研究项目**（用户指定，或询问用户；不得自行下载大仓库/模型/数据）跑一次。抽查：入口、一个模型 forward、一个 loss、一个数据处理、一个评估函数的卡片与源码跳转；至少 3 个实验设置的消费行；主要创新点映射。没有真实项目就明确写“真实项目未验证”。

### 阶段 9：安装与配置收尾
- Claude Code：复制 `SKILL_SRC` 到 `D:\APP\ClaudeCode\config\skills\research-code-atlas\`（先检查同名目录；存在就比较，不覆盖），新建 `local.json` 写本机 python 与 reports_root；在新会话中 `/reload-skills` 或重启后，确认 `/research-code-atlas` 可见。
- Codex：按 `D:\Code\AGENTS.md`：维护源放 `D:\Code\Codex_transfer\skills\research-code-atlas`，安装到实际被发现的目录（本机现有为 `C:\Users\Administrator\.codex\skills\`）；然后按 `codex-config-transfer` 串行 Capture → 紧接 Check（退出码 0 且 CHECK_OK）；在 `ClaudeCode_transfer\配置待办.md` 更新对应条目。新会话中用 `$research-code-atlas` 验证发现性。
- 不 commit/push。

---

## 18. Fixture（原样创建）

### 18.1 文件

`tests/fixtures/mini_proj/train.py`

```python
import argparse
from models.net import Net as Model
from utils import helpers
from utils.helpers import seed_all
import losses


def build(cfg):
    return Model(cfg["dim"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--unused_flag", default=0)
    args = p.parse_args()
    seed_all(0)
    model = build({"dim": 4})
    print("lr", args.lr)
    for epoch in range(args.epochs):
        if epoch % 2 == 0:
            loss, parts = losses.total_loss(model, [1.0, 2.0])
        else:
            loss = helpers.normalize([3.0, 4.0])
    fn = getattr(helpers, "dyn_" + "x")
    fn()
    return helpers.fact(3)


if __name__ == "__main__":
    main()
```

`tests/fixtures/mini_proj/eval.py`

```python
from models.net import Net
import losses


def evaluate():
    net = Net(8)
    out = net.forward([1.0, 2.0, 3.0])
    total, parts = losses.total_loss(net, out)
    return {"total": total, "n": len(out)}


if __name__ == "__main__":
    evaluate()
```

`tests/fixtures/mini_proj/models/__init__.py`：空文件。

`tests/fixtures/mini_proj/models/net.py`

```python
from .blocks import Block


class Net:
    def __init__(self, dim):
        self.block = Block(dim)
        self.dim = dim

    def forward(self, x):
        h = self.block.run(x)
        return self.head(h)

    def head(self, h):
        def scale(v):
            return v * 2

        return [scale(v) for v in h]

    def __call__(self, x):
        return self.forward(x)
```

`tests/fixtures/mini_proj/models/blocks.py`

```python
from utils.helpers import normalize


class Block:
    def __init__(self, dim):
        self.dim = dim

    def run(self, x):
        # 安全测试：</script><script>window.__x=1</script>
        return normalize(x)
```

`tests/fixtures/mini_proj/utils/__init__.py`：空文件。

`tests/fixtures/mini_proj/utils/helpers.py`

```python
import random

_STATE = {"seed": None}


def seed_all(seed):
    random.seed(seed)
    _STATE["seed"] = seed


def normalize(x):
    s = sum(x)
    if s == 0:
        return x
    return [v / s for v in x]


def compute_default():
    return 1


def deco(f):
    return f


@deco
def decorated(x=compute_default()):
    return x


def fact(n):
    if n <= 1:
        return 1
    return n * fact(n - 1)


def dyn_x():
    return "dynamic"
```

`tests/fixtures/mini_proj/losses.py`

```python
def normalize(v):
    return [abs(t) for t in v]


def total_loss(model, batch):
    out = model(batch)
    parts = {"mse": sum(out), "reg": len(normalize(out))}
    return sum(parts.values()), parts
```

`tests/fixtures/mini_paper.md`（测试材料，非真实论文）

```markdown
<!-- 测试材料：不是真实论文，仅用于验证引用与跳转 -->
=== PDF第1页 ===
Mini Paper. Contributions: (1) a scaled head that rescales block features; (2) a normalized block; (3) a contrastive memory bank.
=== PDF第2页 ===
Method. The block normalizes the input so that it sums to one. The head multiplies each feature by 3.
=== PDF第3页 ===
Experiments. We train for 2 epochs with a learning rate of 3e-4 and batch size 64.
```

（设计意图：贡献(2) → `Block.run`/`normalize` 为 direct；贡献(1) 论文说乘 3、代码乘 2 → conflict；贡献(3) 代码中没有 → not_found；学习率 3e-4 vs 默认 1e-3 → mismatch；epochs 2 → match；`--unused_flag` → defined_not_consumed；batch size 64 → paper_only。）

`tests/fixtures/request_fixture.json`：两个入口 `entry:train`（train.py，scenario train）与 `entry:eval`（eval.py，scenario eval），paper 指向 `mini_paper.md`，output_dir 指向 BUILD_ROOT 下的临时 run 目录。

### 18.2 用途

覆盖：入口保护块、相对导入、import 别名、模块别名调用、两个同名函数、嵌套函数、类方法、self 属性类型推断、构造调用、`__call__`、共享函数（两个入口都调 total_loss）、条件分支、循环、递归、动态调用、参数传入的 callable、返回 tuple/dict、副作用（全局状态）、装饰器/默认值的定义时执行、安全注入字符串。

### 18.3 ground truth（写成 `ground_truth.json`，test_extract.py 逐条断言）

必须存在的边（caller → callee，relation，resolution）：

| # | caller | callee | relation | resolution | 额外断言 |
| --- | --- | --- | --- | --- | --- |
| 1 | `sym:train.py:<module>:module` | `sym:train.py:main:function` | calls | resolved_static | conditions 含 `__name__ == "__main__"` |
| 2 | `sym:train.py:main:function` | `sym:train.py:build:function` | calls | resolved_static | |
| 3 | `sym:train.py:build:function` | `sym:models/net.py:Net.__init__:method` | constructs | resolved_static | 通过别名 `Model` 解析 |
| 4 | `sym:train.py:main:function` | `sym:utils/helpers.py:seed_all:function` | calls | resolved_static | from-import |
| 5 | `sym:train.py:main:function` | `sym:losses.py:total_loss:function` | calls | resolved_static | conditions 同时含 for 循环与 `if epoch % 2 == 0` |
| 6 | `sym:train.py:main:function` | `sym:utils/helpers.py:normalize:function` | calls | resolved_static | 走 else 分支；**不是** losses.normalize |
| 7 | `sym:train.py:main:function` | `sym:utils/helpers.py:fact:function` | calls | resolved_static | 模块别名 |
| 8 | `sym:utils/helpers.py:fact:function` | `sym:utils/helpers.py:fact:function` | calls | resolved_static | 递归；层级树显示 ↻ |
| 9 | `sym:models/net.py:Net.forward:method` | `sym:models/net.py:Net.head:method` | calls | resolved_static | self 方法 |
| 10 | `sym:models/net.py:Net.forward:method` | `sym:models/blocks.py:Block.run:method` | calls | candidate | 由 `self.block = Block(dim)` 推断 |
| 11 | `sym:models/net.py:Net.__init__:method` | `sym:models/blocks.py:Block.__init__:method` | constructs | resolved_static | 相对导入 |
| 12 | `sym:models/net.py:Net.head:method` | `sym:models/net.py:Net.head.scale:function` | calls | resolved_static | 嵌套函数 |
| 13 | `sym:models/net.py:Net.__call__:method` | `sym:models/net.py:Net.forward:method` | calls | resolved_static | |
| 14 | `sym:models/blocks.py:Block.run:method` | `sym:utils/helpers.py:normalize:function` | calls | resolved_static | **不是** losses.normalize |
| 15 | `sym:losses.py:total_loss:function` | `sym:losses.py:normalize:function` | calls | resolved_static | 同名函数各归各的 |
| 16 | `sym:eval.py:evaluate:function` | `sym:models/net.py:Net.__init__:method` | constructs | resolved_static | |
| 17 | `sym:eval.py:evaluate:function` | `sym:losses.py:total_loss:function` | calls | resolved_static | 共享函数，第二个入口 |
| 18 | `sym:utils/helpers.py:<module>:module` | `sym:utils/helpers.py:compute_default:function` | definition_time | resolved_static | 默认值在定义时执行 |
| 19 | `sym:utils/helpers.py:<module>:module` | `sym:utils/helpers.py:deco:function` | definition_time | resolved_static | 装饰器 |

必须**不存在**的边：
- 任何指向内置函数（`sum`、`len`、`print`、`range`、`getattr`）的边（默认不建边，只计数）；
- `Net.head` 的直接 callees 只有 `Net.head.scale`（嵌套函数体内的内容不算 head 的直接调用）；
- `utils/helpers.py:decorated` → `compute_default`（定义时执行不属于 decorated 的函数体）；
- `Block.run` → `losses.normalize`。

必须是 `unresolved` 的调用：
- `train.py:main` 中的 `getattr(helpers, "dyn_" + "x")` 产生的 `fn()`，note 提到参数/局部变量或动态；
- `losses.py:total_loss` 中的 `model(batch)`（参数传入的可调用对象）。

`eval.py:evaluate` 中 `net.forward(...)`：`net = Net(8)` 在同一函数中直接赋值 → 允许 `candidate` 指向 `Net.forward`；断言其 resolution 不是 `resolved_static` 也不是缺失。

其他断言：
- 符号 `sym:models/net.py:Net.head.scale:function` 存在，parent 是 `Net.head`；
- `losses.normalize` 和 `utils/helpers.normalize` 是两个不同 ID；
- `seed_all` 的步骤骨架有 2 步，行号正确；`normalize` 的骨架中 `if s == 0` 是 kind=if、含 children；
- `total_loss` 的 returns 记录 1 条，表达式为 `sum(parts.values()), parts`；
- config-index 中 `--unused_flag` 无消费者，`--lr` 的消费者包含 `train.py` 中 `args.lr` 那一行；
- 入口 `entry:train` 闭包包含 main、build、Net.__init__、Block.__init__、seed_all、total_loss、losses.normalize、helpers.normalize、fact；`entry:eval` 闭包包含 evaluate、Net.__init__、Block.__init__、total_loss、losses.normalize、Net.forward（candidate）、Block.run、helpers.normalize、Net.head、scale；`entry:train` 闭包**不包含** Net.forward（因为 `model(batch)` 未解析——这正是要在“未知清单”里提示用户的地方）。

---

## 19. 验收清单

### 19.1 数据（脚本自动）
1. fixture 的 ground truth 全部通过。
2. 所有 symbol/evidence/config/paper 引用都存在；源码哈希与行号一致。
3. 论文 direct/not_found/conflict 三种状态都能表达；假引文被拦截。
4. 配置默认值与 CLI 覆盖分开显示；每个设置能定位到消费行；未消费参数被标出。
5. 无论文时（把 paper 置空再跑一次）界面完整、论文页显示“未提供”。
6. 两个入口共享的 total_loss 只有一个 symbol_id，`scenario_contracts` 分别记录两入口下的输入（train：`[1.0, 2.0]` 字面列表；eval：`net.forward` 的输出），切换入口能看到两份契约。
7. 修改源码后不重验 → “未重验”；`--recheck-source` → stale；重新 extract 后行号与说明同步。

### 19.2 浏览器（逐条执行并记录结果）
- 从入口点到核心函数，卡片内容与源码高亮一致。
- 点 caller/callee 与内部步骤，跳到正确文件和行。
- 分别选中 `losses.normalize` 与 `helpers.normalize`，跳到不同文件。
- 层级树中 `fact` 递归显示 ↻ 而不是无限展开。
- 点论文映射、配置消费者、修改影响链中的项，跳转正确。
- 刷新带 hash 的 URL 状态恢复；前进/后退可用。
- 无外部网络请求；`window.__x` 为 undefined。
- 桌面宽屏与窄窗口都没有被遮挡、无法关闭的面板；控制台无报错。

### 19.3 真实项目（阶段 8）
入口、模型 forward、一个 loss、一个数据处理、一个评估函数的卡片逐个人工抽查（调用点、shape 证据、步骤行号）；主要创新点映射与至少 3 个实验设置核对原文页。项目没有某类时写不适用。

---

## 20. 交付给用户的内容

1. 可调用的 `research-code-atlas`：维护源路径、安装路径、新会话中发现性的验证结果。
2. `scripts/README.md` 与 skill 内的使用说明：安装前提、三种调用方式（单入口、多入口、准备修改）、界面操作、更新与重验、停止 serve。
3. 至少一个能点击的本地界面：注明是 fixture 还是真实项目。
4. 实际命令、退出码、`validation.json`；分开说明数据验收、浏览器验收（自动/人工）、真实项目验收、runtime（未实现）。
5. 限制：只深度支持 Python；动态调用/注册表/参数传入 callable 无法静态确定；shape 多为推断；论文映射依赖文本质量。

**以下都不算完成**：只给方案；只写 SKILL.md；用正则名字匹配冒充调用图；编造 tensor shape 或论文引文；把模块树当执行路径；只有图片不能点击；靠 vscode:// 链接冒充页内跳转；没有论文映射；没追配置消费者；文档写了没实现的命令；测试通过却没生成界面；没验证安装就说“已全局可用”。

---

## 21. 用户以后怎样调用（放进最终 README）

**静态理解训练入口**
```text
使用 research-code-atlas（Claude Code 可直接输入 /research-code-atlas；Codex 用 $research-code-atlas）。
项目：D:/Research/MyProject
入口：train.py（场景 train）
论文：D:/Papers/my-paper.pdf
配置：configs/train.yaml；启动参数线索：--config configs/train.yaml --lr 3e-4
重点：训练主循环、模型 forward、loss、论文创新模块、关键实验设置。
只做静态分析，不执行训练。生成本地可视化界面。
```

**多入口对照**
```text
使用 research-code-atlas，对比同一项目的 train.py(train)、evaluate.py(eval)、infer.py(infer)。
保留各自参数和配置，标出共享函数、模式差异、预处理/后处理差异，
以及论文训练与评估设置分别在哪些代码路径落实。
```

**准备改代码**
```text
继续上次 research-code-atlas 的分析结果（RUN_DIR：<路径>）。
我想把特征融合换成另一种方法。定位负责融合的函数，解释输入输出、内部步骤与论文对应，
列出所有已找到的调用者、下游消费者、相关 loss/配置和候选影响，给最小验证清单。暂不改源码。
```

**源码改过之后**
```text
用 research-code-atlas 对 <RUN_DIR> 做 validate --recheck-source；
如果是 stale，重新 extract，复用未变化函数的说明，只重读变化的函数，然后重新 render。
```

---

现在从**阶段 0**开始：读规则 → 检查环境与 BUILD_ROOT → 写 HANDOFF 与 PRD → 一次性列出需要授权的事项 → 在授权范围内连续推进，直到阶段 9，每阶段都有实际验收证据。
