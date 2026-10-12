# 给本地 Agent 的完整任务：创建 research-code-atlas Skill

版本与研究快照：2026-10-12（北京时间）。输出语言：中文。

> 本文件是实现规格，不是已发布工具的使用手册。下文 `atlas.mjs` 的子命令、`atlas.json` 的字段以及 `research-code-atlas` 都需要你真正实现。Understand-Anything 已有的文件和命令会另外标注，不能把本规格中的命令说成现成命令。
>
> 请读取全文建立任务清单，再分阶段执行。每阶段都落盘、验收、记录状态。不要只回复方案，不要只创建 SKILL.md，不要用漂亮截图替代功能验收。

## 0. 最终任务与已确定的方案

创建一个可复用 skill：`research-code-atlas`，中文显示名“论文与代码执行图谱”。用户给项目、入口文件及可选论文，它应生成本地可视化学习界面，帮助用户真正理解执行逻辑并定位改动位置。

**唯一推荐方向：基于 Understand-Anything 改造并封装 skill。** 复用其确定性结构提取与前端，增加本规格的数据与面板。不要同时接入多个图数据库；不要重写一个通用跨语言编译器；不要把整个上游 skill 的全仓多 agent 流程当作每次运行的必需步骤。

先把 Python 研究代码的完整流程做好；其他语言复用上游已支持的结构提取与源码浏览。跨语言、动态调用、运行数据的精度必须按实际证据分级，不能承诺所有项目都有完整且准确的调用图。

本次实现的默认边界：

- 分析与展示项目，不自动修改被分析项目。
- 静态分析是基础能力：不导入、不执行目标项目，不需要它的依赖安装成功。
- 论文与实验对照是有论文时的必需流程，不是最后附一句论文摘要。
- 真实调用/输入输出观测是可选增强；只有具体执行命令、环境、输入与副作用范围得到授权后才运行。
- 本地网页是必需交付。它可由 `127.0.0.1` 的静态服务打开，构建后不依赖外网；不强制双击 HTML 直接运行。
- 不需要新的商业 LLM API、向量数据库、Docker、云部署、编辑器插件或联网聊天服务。
- 语义解释由当前 agent 按固定小批次生成，结构、引用和验证由脚本完成。弱模型不能靠一段巨大上下文一次猜完整仓库。

成功标准：用户能从入口看到主要阶段，展开到具体函数，读清楚输入输出格式、条件分支与内部步骤，点到准确源码；在同一界面查看论文创新点如何落实、实验配置何处生效，以及改动某函数可能影响什么。

## 1. 先确认路径、环境与授权，不要猜机器状态

### 1.1 路径变量

把以下变量记入建设目录的 `HANDOFF.md`；路径根据实际环境解析，禁止把示例路径硬编码进可迁移 skill：

| 变量 | 含义 | 本机建议与限制 |
| --- | --- | --- |
| WORKSPACE_ROOT | 用户允许写入的工作区 | 本机为 `D:\Code`；换机需重新确认 |
| BUILD_ROOT | 本任务的完整开发包 | 建议 `WORKSPACE_ROOT/tools/research-code-atlas`；已存在时先检查，不能覆盖用户内容 |
| UPSTREAM_ROOT | Understand-Anything 完整源代码包 | 建议 `BUILD_ROOT/vendor/understand-anything`，保留完整 package 布局 |
| SKILL_SOURCE | 维护 skill 的唯一源目录 | 本工作区应遵守 canonical `Codex_transfer/skills` 规则；在沙箱试制后由授权维护流程纳入 |
| SKILL_INSTALL_ROOT | 宿主实际可发现的 skill 根目录 | 读取宿主配置/技能清单后决定，不能只照旧教程猜路径 |
| PROJECT_ROOT | 本次被分析项目根目录 | 每次调用由用户提供；不能指向 skill 工程本身代替真实项目 |
| RUN_DIR | 当前分析产物目录 | 默认放在工作区 `reports/research-code-atlas/<项目名>/<运行ID>`，不写目标源码 |
| PROJECT_PYTHON | 可选真实运行使用的 Python | 必须来自目标项目已有环境，静态分析不用它导入项目 |

本机已有另一份 `D:\Code\prompt.md`，属于 model-inspector 任务。不要覆盖、移动或改写它。

### 1.2 实际检查

1. 读取目标工作区的 AGENTS.md 或等效规则。按规则选择对应阶段技能，不把本 prompt 当作更高优先级指令。
2. 检查建设目标是否存在，确认最近 Git 根、remote、既有改动和敏感内容边界。仅修改本任务范围。
3. 检查 Node.js、pnpm、Python、rg 的实际路径和版本，以及现有浏览器/浏览器测试工具。
4. 检查当前已有 skill，优先复用，不重复安装同名 skill。
5. 建立 `docs/PRD.md`，写入本文件的目标、界面、输入、数据契约、风险和验收；这是产品实现，不省略需求收敛。
6. 为实际新增脚本维护同目录 README，列每个参数的格式、默认值、允许值、作用、退出码和真实验证命令。

本机可能出现 shell 的 Windows sandbox 启动故障。先保留原始错误并区分宿主进程问题、命令失败与目标工具失败；不要把工具没有启动解释成文件不存在。使用宿主允许的只读或受审核执行通道，不关闭沙箱、不改安全策略。

新增软件、依赖安装、第三方源码下载、全局 skill 安装、覆盖现有文件按用户与工作区授权处理。先完成不依赖这些动作的源码检查与具体安装清单；已有明确授权时继续，不重复询问。

## 2. 官方来源与应参考的现成 Skill

### 2.1 主项目：Understand-Anything

当前官方地址：[Egonex-AI/Understand-Anything](https://github.com/Egonex-AI/Understand-Anything)。旧的 `Lum1104/Understand-Anything` 会重定向；请使用当前地址。

本次调研核验提交：`f2d0164f72fe678805c34245a6df36acededfebd`。默认参考这一提交以便复现；若改用其他版本，先重新核验文件、API、许可证、锁文件和构建命令，把变更原因写入 HANDOFF。

按下列顺序读，不需要先读完整仓库：

| 来源 | 何时读 | 读取目的 |
| --- | --- | --- |
| [官方 README](https://github.com/Egonex-AI/Understand-Anything/blob/main/README.md) | 阶段 A | 了解布局、构建、当前数据目录与安装边界 |
| [understand/SKILL.md](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand/SKILL.md) | 阶段 A/B | 借鉴确定性提取与语义分析分开执行的方法 |
| [understand-explain/SKILL.md](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand-explain/SKILL.md) | 函数解释阶段 | 借鉴符号深读，必须重新核验实际源码 |
| [understand-dashboard/SKILL.md](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand-dashboard/SKILL.md) | 界面阶段 | 了解现有界面启动、源码接口与资源位置 |
| [understand-diff/SKILL.md](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand-diff/SKILL.md) | 修改影响阶段 | 借鉴变化与依赖关联，不能继承未经证实的安全保证 |
| [types.ts](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/packages/core/src/types.ts) | 写 adapter 前 | 确认 GraphNode/GraphEdge；不要猜字段或枚举 |
| [schema.ts](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/packages/core/src/schema.ts) | 写 adapter 前 | 确认上游验证可能剥离未知字段；研究数据用 sidecar 保存 |
| [extract-structure.mjs](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand/extract-structure.mjs) | 结构提取阶段 | 读取真实输入输出与错误信息 |
| [scan-project.mjs](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand/scan-project.mjs) | 文件枚举阶段 | 复用分类、忽略、计数；增加精确范围与路径守卫 |
| [CodeViewer.tsx](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/packages/dashboard/src/components/CodeViewer.tsx) | 源码导航阶段 | 当前组件用本地接口读取源码，需适配产物内的源码快照 |
| [NodeInfo.tsx](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/packages/dashboard/src/components/NodeInfo.tsx) | 函数卡片阶段 | 复用选中节点展示 |
| [GraphView.tsx](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/packages/dashboard/src/components/GraphView.tsx) | 图展示阶段 | 复用图交互，不重写布局引擎 |
| [store.ts](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/packages/dashboard/src/store.ts) | 导航阶段 | 复用已有选择、导航和状态 |

已确认上游真实命令：

```text
node <UPSTREAM_ROOT>/understand-anything-plugin/skills/understand/scan-project.mjs <PROJECT_ROOT> <scan-output.json>
node <UPSTREAM_ROOT>/understand-anything-plugin/skills/understand/extract-structure.mjs <extract-input.json> <extract-output.json>
```

第二个脚本的输入包含 `projectRoot`、`batchFiles` 和 `batchImportData`；`batchFiles` 的每项包括 `path`、`language`、`sizeLines`、`fileCategory`。输出有 `scriptCompleted`、`filesAnalyzed`、`filesSkipped`、`filesUnreadable`、`results`。继续读取固定版本中的细节，先真实试运行，不凭这里的概述猜完整 JSON。

完整保留旁置脚本与核心包，不能只复制一个 SKILL.md。不要自动运行上游全局安装器、commit hooks、自动清理、worktree 重定向或全仓多 agent 命令；本任务仅复用已核验、符合当前授权的部分。

### 2.2 其他参考：只借鉴，不设为基础依赖

- [GitNexus Exploring](https://github.com/abhigyanpatwari/GitNexus/blob/main/gitnexus/skills/gitnexus-exploring.md)：借鉴显式绑定仓库、核验索引新鲜度、先找流程再读符号。
- [GitNexus Impact Analysis](https://github.com/abhigyanpatwari/GitNexus/blob/main/gitnexus/skills/gitnexus-impact-analysis.md)：借鉴向上追调用者；不要把“存在直接调用者”写成“必然损坏”。
- [GitNexus LICENSE](https://github.com/abhigyanpatwari/GitNexus/blob/main/LICENSE)：实际为 PolyForm Noncommercial，不能假定 MIT 或随意复制代码。
- [CodeGraphContext Skill](https://github.com/CodeGraphContext/CodeGraphContext/blob/main/.cursor/skills/codegraphcontext/SKILL.md)：借鉴先索引、明确数据库与仓库作用域；无需同时装它。
- [Pyan3](https://github.com/Technologicat/pyan)：Python 静态关系的可选交叉检查。GPL-2.0；uses 不等于 calls，不复制其实现作为自写代码。
- [code2flow](https://github.com/scottrogowski/code2flow)：仅理解近似调用图的能力边界，不作默认后端。
- [Python AST](https://docs.python.org/3/library/ast.html)、[Python profile hooks](https://docs.python.org/3/library/sys.html#sys.setprofile)：补充 Python 数据契约与可选运行观察。

上游 MIT 代码复用要保留 LICENSE、版权与来源记录；不把第三方功能描述成原创。若按工作区规则下载第三方源码副本，先确认精确目标、固定 revision、LFS/submodule 需求和完整性，再按规则处理仅该副本的 Git 元数据，保留原 README 为不冲突的 README_UPSTREAM 名称并补中文来源说明。不能对已有用户仓库执行删除、重置或清理。

## 3. 需要哪些 Skill 与软件，什么时候使用

### 3.1 Skill 清单

| 类别 | 名称/来源 | 使用阶段与理由 | 是否必须新装 |
| --- | --- | --- | --- |
| 创建辅助 | `skill-creator`；[OpenAI 版本](https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md) | 创建入口、分层 references、验证 frontmatter | Codex 通常已内置；先发现，不重复覆盖系统 skill |
| 主项目依赖 | Understand-Anything 的完整包 | 解析器和 UI 的实现基础 | 获得源码与依赖授权后按固定版本构建；无需全局安装其所有 skills |
| 使用入口 | 本次要创建的 `research-code-atlas` | 之后每次分析项目都调用它 | 必须真正创建并验收；安装位置按宿主核验 |
| 论文精读 | 本机已有 `paper-understanding-pack` | 新单篇论文需要深读时，复用正文证据与创新点 | 本机已提供。外机无该 skill 时按本 prompt 的论文流程执行，不虚构公网安装地址 |
| PDF 读取 | 本机 `pdf:pdf` 或现有 PDF 工具 | 论文 PDF 抽取、页码核对与公式原页检查 | 先发现现有工具；无则列出具体依赖安装需求 |
| 论文发现 | 本机 `paper-lookup` | 用户只给标题、DOI、arXiv ID 或要求找论文时 | 按需；已给本地论文时无需重新检索 |
| 现有论文包 | `paper-distillation` | 仅明确要求五报告或继续既有五报告时 | 不与 paper-understanding-pack 重复运行 |
| 网页检索 | 本机 `agent-reach` | 用户给网络链接、要求搜索或缺失论文来源时 | 本机已有；遵守其实际范围与登录边界 |
| 工程证据 | 已有规划、debugging、TDD、verification、review skills | 对应工程阶段 | 适用且已安装时读对应文件；缺失时执行等效小流程，不强制安装整套 |
| 简化 | 已有 `ponytail` | 方案确定后及交付前检查重复实现 | 不削弱所列需求和验证 |
| 配置迁移 | 本机 `codex-config-transfer` | 实际维护/安装 skill 或配置后 | 本机规则要求串行 Capture → Check；普通分析运行不做配置快照 |

创建辅助的另一个官方参考：[Anthropic Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)。只选择与当前 agent 宿主相符的一份，不把两套作者工作流叠加为全部强制依赖。

本机个人论文 skills 的可用路径来自当前技能清单，例如 `C:/Users/Administrator/.codex/skills/paper-understanding-pack/SKILL.md`；canonical 维护目录按 `Codex_transfer` 规则确定。换机不存在时不能声称已安装，也不能猜一个 GitHub 地址。

### 3.2 软件清单与环境隔离

| 软件 | 用途 | 基础要求/默认判断 |
| --- | --- | --- |
| Node.js | 上游解析器、构建与 atlas CLI | 上游 skill 写明 Node.js ≥22；仍核验所固定版本 package 的 engines 与依赖支持 |
| pnpm | 完整包的 workspace 构建 | 本次根 packageManager 为 pnpm 10.6.2；跟随固定版本锁文件，不随手换 npm 全仓安装 |
| Python | Python AST 契约提取、可选运行追踪、PDF 辅助 | 分析工具建议 3.10+；目标语法较新时使用兼容解析器并记录版本 |
| rg | 按符号/配置关键词定位调用者与证据 | 已有则复用；不可执行时记录原始原因，再用窄范围替代搜索 |
| 浏览器 | 打开本地学习界面 | 现有 Chrome/Edge 即可 |
| 现有浏览器自动化工具 | 点击、导航、离线与布局验收 | 优先复用；没有时完成真人可重现检查并如实标为人工/未执行 |
| 已有 PDF 库 | 抽取正文与核对页面 | 优先宿主工具、PyMuPDF/pypdf 或 Poppler；不为纯文本论文安装 OCR |
| 项目已有深度学习环境 | 可选真实运行观测 | 只用该项目明确的环境，不在分析环境安装一套完整 CUDA/PyTorch |

新依赖与缓存放 D 盘或用户指定目录，遵守既有环境设计。只在获得授权后安装；不要污染目标项目环境。依赖版本、锁文件和实际构建结果写入验收，不用 README 声明代替安装成功。

## 4. 创建最小但完整的包

下面是建议结构，文件名可因上游约定调整；每个实际创建文件都必须有明确用途：

```text
BUILD_ROOT/
  README.md                       用户安装、调用、查看与恢复说明
  HANDOFF.md                      单个当前进度与未完成项
  docs/PRD.md                     已确定需求与验收
  vendor/understand-anything/      固定版本完整包，保留法律声明
  research-code-atlas/
    SKILL.md                      简明触发与执行入口
    references/workflow.md        项目、入口、深读、装配步骤
    references/data-contract.md   schema、证据枚举、引用约束
    references/paper-mapping.md   论文创新及实验对照
    references/runtime.md         仅可选运行模式时读取
    scripts/atlas.mjs             一个 CLI，调度已有能力
    scripts/python_contracts.py   Python AST 补充，不导入目标
    scripts/runtime_capture.py    仅获授权后观测目标，若实现该模式
    scripts/README.md             实际参数、输入输出、失败与验收
    assets/viewer/                基于上游面板的构建产物/必要扩展
    tests/                        必要端到端 fixture 与回归检查
```

不把整个上游工程复制进每个 analysis run。不维护两份独立前端。不新增只有一种实现的 adapter 框架或配置中心。允许模块化，但按照真实职责拆分，不按行数机械拆文件。

上游核心图谱保留为 `knowledge-graph.json`；研究新增信息保留为 `atlas.json` sidecar，通过经过核验的 `upstream_node_id → symbol_id` 对应表连接。不要随手给 GraphNode 增加字段，再被上游 Zod schema 悄悄剥离。

本地前端需要添加的面板可以集中在少数职责明确的组件：函数详情、论文对照、实验配置、修改影响。复用已有 graph、store、search、code viewer 与样式。

## 5. 用户输入契约

skill 支持自然语言输入；agent 先规范化成 `request.json` 再调用脚本。所有示例路径均需由用户实际路径替换。

```json
{
  "schema_version": "1.0",
  "project_root": "D:/Research/ExampleProject",
  "entries": [
    {"entry_id": "entry:train", "path": "train.py", "symbol": null,
     "scenario": "train", "configs": ["configs/base.yaml"], "overrides": [],
     "args": ["--config", "configs/base.yaml"]}
  ],
  "scenario": "train",
  "paper": {"path": "D:/Papers/example.pdf", "url": null},
  "configs": ["configs/base.yaml"],
  "overrides": [],
  "focus": "理解训练主循环、模型 forward 和损失；准备修改特征融合",
  "output_dir": "D:/Code/reports/research-code-atlas/example/run-001",
  "runtime": {"enabled": false}
}
```

字段规则：

- `project_root`：必填存在目录，解析绝对 realpath。
- `entries`：至少一个；每项有稳定唯一的 `entry_id`；path 必须是项目内存在的文件；symbol 可选，为具体全限定函数或模块入口；args 是字符串数组，**静态阶段仅作为配置线索，不执行**。
- `scenario`：`train|eval|infer|other`，默认 `other`；只用于解释与分组，不凭它决定实际代码路径。全局 scenario/configs/overrides 仅为默认值：入口省略时继承，显式提供时使用该入口的值；数组不隐式合并，空数组表示明确不继承。将各入口的有效请求分别落盘，保留默认来源与覆盖证据。
- `paper`：可选；path/url 至少一个真实值。有本地文件先用本地文件；没有论文时输出缺失状态并继续代码分析。
- `configs`：显式配置文件清单；先解析为项目内路径，用户另外提供的外部文件需单独列允许范围。
- `overrides`：命令行覆盖线索，例如 `model.hidden_dim=256`，保留原始写法；不要未经证据假定所有项目采用 Hydra。
- `focus`：可选改动/学习目标，不代表允许改源码。
- `output_dir`：可选；默认 RUN_DIR。不覆盖已有产物，更新时先核验 run 身份与原子写入。
- `runtime.enabled`：默认 false；true 仍要求完整运行清单和已有授权，不能只凭该值自动训练。

同时支持多个入口并分别标明 train/eval/infer；以单入口先完成闭环，随后验证多入口合并，不能让它们互相覆盖节点或场景。共享源码符号保持一个 symbol_id；输入输出约束、最终配置值、运行证据和论文路径映射按 entry_id 分开。单入口里不同调用点或分支仍可有不同契约，不能把第一次观察推广为该函数的通用格式。

输入不足时优先从 README、参数定义、配置文件获取事实；只问一个真正改变结果的问题。例如项目里有两篇论文但没有对应关系，先说明证据再询问使用哪篇。不要向用户索取可以从文件读取的函数列表。

## 6. 建立统一的证据模型

### 6.1 结论状态

| 状态值 | 中文显示 | 含义 |
| --- | --- | --- |
| `confirmed_source` | 源码确认 | 定义/表达式/调用点与解析规则支持该结论，不代表运行时一定执行 |
| `observed_runtime` | 本次运行观测 | 仅在记录的输入、配置、环境、模式与进程范围内观察到 |
| `inferred` | 推断 | 有理由但缺少充分证据，必须说明依据和反例/限制 |
| `unknown` | 未知 | 不知道；写明缺什么以及如何验证 |
| `conflict` | 证据冲突 | 论文、源码、默认配置或运行值不一致，分别保留 |
| `not_applicable` | 不适用 | 例如数据工具没有模型损失，明确解释原因 |

状态不能只是卡片上的一个总标签。函数目的、参数类型、shape、调用边、论文映射和配置值都要能独立标记证据。

### 6.2 引用定位

每条源码证据有 `file`、`start_line`、`end_line`、`file_sha256`；行号为从 1 开始、两端含端点。所有文件相对 PROJECT_ROOT 表示，规范化 `/`，UI 与 CLI 统一。

每条论文证据有 `paper_id`、`pdf_page`、`printed_page`（若可确认）、`section`、`equation`/`figure`/`table`（适用时）；PDF 页与印刷页分开。摘录保持简短，重要公式要核对原页，不把 OCR 的错字当原论文。

每条运行证据有 `run_id`、具体输入摘要、配置哈希、环境、命令参数、模式、时间、PID/线程信息和覆盖限制。不要导出密码、token、Cookie、环境变量全文、原始训练数据或模型权重。

证据记录建议结构：

```json
{
  "id": "ev:src:losses.py:12:17",
  "kind": "source",
  "file": "losses.py",
  "start_line": 12,
  "end_line": 17,
  "file_sha256": "实际计算的64位小写十六进制哈希",
  "note": "返回各项加权损失的和"
}
```

这只是字段示意，实际输出中的哈希不能用占位符。schema 约束实际哈希格式与来源文件行数。

## 7. 核心数据契约：函数、调用、流程与覆盖

使用 JSON Schema 或已有 Zod 定义并真正执行验证。`atlas.json` 的最低结构如下；不要把字符串模板当真实分析结果：

```text
schema_version
project {id, name, root_local, git_commit_or_null, worktree_dirty, analyzed_at}
request {entries, scenario, configs, focus}
coverage {indexed_files, analyzed_files, excluded, parse_failures,
          unresolved_calls, truncated, pending_explanations, limitations}
sources [{file, language, sha256, line_count, content_or_snapshot_ref}]
symbols [{id, upstream_node_id_or_null, file, qualname, kind,
          definition_range, signature, decorators, role, purpose,
          inputs, outputs, side_effects, exceptions, preconditions,
          steps, callers, callees, paper_refs, config_refs, evidence_refs,
          scenario_contracts, analysis_status}]
edges [{id, caller, callee_or_null, candidates, relation,
        callsite, expression, conditions, resolution, evidence_refs}]
flows [{id, entry_id, entry_symbol, scenario, stages, step_edges, limitations}]
paper {status, papers, contributions, mappings, conflicts}
experiments [{id, entry_id, setting, paper_value, repo_default, selected_value,
              precedence, consumed_by, evidence_refs, status}]
change_impacts [{target, entry_ids, goal, upstream, downstream, affected_contracts,
                 paper_constraints, config_consumers, suggested_checks, limitations}]
evidence [{id, kind, ...locator}]
```

### 7.1 稳定符号身份

- 符号 id 至少包含项目内路径、词法全限定名、符号种类；需要时加入重复定义序号。
- 不用“函数名”或“函数名+行号”作为唯一身份。多个文件、同名方法、嵌套函数会撞名，增删行也会导致无谓失效。
- 例如 `sym:models/encoder.py:Encoder.forward:function`；同一作用域重复定义要保留重定义顺序并标明实际绑定不确定性。
- 模块顶层使用 `sym:train.py:<module>:module`，`__main__` 保护块为控制区域，不凭空把它当真实函数。
- HTML hash/DOM id 使用编码后的稳定 id 或单独安全编码，不直接把路径拼成选择器。

### 7.2 每个项目内已分析函数的最低说明

| 项目 | 必须解释的内容 |
| --- | --- |
| 主要作用 | 一句话明确它在入口流程中的职责 |
| 使用目的 | 为什么需要它，解决哪一步的问题，谁消费结果 |
| 签名 | 参数顺序、位置/关键字限制、默认值、类型注解、返回注解、装饰器 |
| 输入 | 字段、类型、容器层级、shape/dtype/device、单位、值域、可空性、证据 |
| 输出 | 返回值/生成器产出/async 结果、容器层级、shape、语义、消费者 |
| 内部流程 | 按执行顺序说明关键步骤、条件、循环、异常及早退，各步指向源码 |
| 调用关系 | 当前函数调用谁、被谁调用、具体调用点、确定性与分支条件 |
| 副作用 | 原地修改、状态改变、文件、日志、优化器、随机数、网络/硬件操作 |
| 异常与前提 | 真实 assert/检查/raise 或已确认的环境前提；没有证据则未知 |
| 论文对应 | 有/无对应、定位、落实的创新或设置；不强行关联工具函数 |
| 改动影响 | 可能受影响的输入输出契约、调用者和实验假设 |

外部库函数可以作为边界节点显示签名/用途与官方定义链接；不声称已经深读其全部实现。每个被列为“已深读”的项目内函数都必须有上述卡片。待深读项留在 pending 清单；不能只解释入口和几个大函数却称全链路已完成。

### 7.3 输入输出格式不要靠猜

每个参数/返回字段用统一对象：

```json
{
  "name": "batch.observations",
  "container_path": ["batch", "observations"],
  "type": "Tensor",
  "shape": ["B", "T", "D_obs"],
  "dimensions": {"B": "batch size", "T": "时间窗口", "D_obs": "观测特征数"},
  "dtype": null,
  "device": null,
  "units": null,
  "default": null,
  "constraints": [],
  "status": "inferred",
  "evidence_refs": [],
  "reason": "示意：需用数据集返回定义、模型操作及选定配置继续验证"
}
```

这段是规范形状示意，不可原样填给任意模型。实际分析要为已确认值提供真实证据。无法确认的字段用 null + 原因；不要因参数叫 `images` 就写 `[B,3,224,224]`。

函数的 inputs/outputs 保存有证据的通用约束；`scenario_contracts` 保存 `{entry_id, callsite_or_null, conditions, inputs, outputs, config_refs, runtime_run_ids, evidence_refs}`。界面切换入口时切换相应契约，同时仍可查看共同签名和其他入口差异。不同配置得到不同 shape/返回分支时不能覆盖同一条通用记录。

证据优先查：类型注解与 schema → 数据构建/collate → assert/reshape/transpose → 实际消费者 → 明确配置 → 已授权运行观测。静态符号维度、项目默认数值和本次实测值分开展示。

`None` 返回、tuple/list/dict/dataclass、原地修改、generator 的 yield 与最终 return、协程返回、可变参数都要按实际语言语义说明；不要都写成普通同步 tensor 函数。

### 7.4 调用边与流程节点

边类型至少区分：`calls`、`constructs`、`imports`、`contains`、`inherits`、`dataflow`、`configured_by`、`implements_paper`。基础图与研究 sidecar 可分别建枚举，通过 adapter 转换；不能把上游所有 uses/depends_on 都渲染成调用。

调用 `resolution` 使用：`resolved_static|observed_runtime|candidate|unresolved|external`。静态可解析仅表示当前代码结构支持这一目标，不承诺所有运行中的绑定相同。

每条调用边保留调用表达式、调用点行号、条件与目标身份。不要把“在函数体里出现一个名字”当调用；注册回调与回调执行要分开。未知目标有 null/candidates，不偷换成同名函数。

内部流程 `steps` 至少包含：`id`、`order`、`title`、`action`、`why`、`input_refs`、`output_refs`、`source_range`、`conditions`、`next`。函数只有赋值/返回，也要准确说明这些语句的作用。

`return`、`raise`、`break`、`continue`、循环回边、分支合流要正确。调用图和内部控制流程用不同标签；调用关系没有天然执行时间顺序。真实轨迹只能来自运行数据。

## 8. 静态分析算法：先机械提取，再按证据解释

### 8.1 入口及范围

1. 检查入口文件和可选符号真实存在；`.sh/.bat` 入口先读其参数与实际下游程序，不默认执行。
2. 读项目 README、启动脚本、依赖声明、入口 imports、参数解析和显式配置。
3. 对完整项目先建立轻量符号/文件索引；深读从入口与其项目内调用闭包开始。
4. 同时追相关配置、数据构建、loss、训练/评估入口和论文关键模块。论文模块不在该入口路径时，单列“此入口未覆盖”，不要强行接一条调用边。
5. 图显示默认折叠深度可为 3，但不把显示深度当分析范围。达到分析预算时记录 truncated/pending，继续可恢复任务。
6. 从函数到所有调用者时，用全项目索引和精确 rg 搜索补查；不能在入口闭包里查不到就说它没有调用者。

默认排除 `.git`、环境、node_modules、构建与缓存、模型权重、数据集、日志、账号/秘密文件；必要的测试、配置和启动脚本应按问题读取，不能全部一律排除。

路径守卫：确认 realpath 在允许根内；处理 symlink/junction 越界、循环目录、大小写碰撞、不可解码文本和过大文件。排除/解析失败要写覆盖清单；被忽略文件仍可能是显式入口，应先验证授权再针对性纳入。

### 8.2 复用提取与 Python 补充

- 用上游 scan/extract 得到确定性结构，不让 LLM 重新写正则扫描所有函数。
- 用 Python `tokenize.open` 或等效编码机制读取源码，再用 `ast.parse` 补充签名、参数种类、return/yield、callsite、控制区域与注解。
- AST 遍历维护词法 scope 栈；访问嵌套定义不能把其函数体调用算在外层函数的直接调用里。
- 函数默认值、装饰器及 class body 在定义/导入阶段执行，不能都计入以后调用该函数的运行体。
- 导入别名、相对 import、`src/` 布局、包 `__init__`、同名模块与循环 import 要按项目布局处理；导入符号不等于调用符号。
- 直接 Name 调用、明确 import alias、明确 class/instance 绑定可给规则支持的静态目标。参数传入的 callable、重新赋值、猴子补丁、动态 import、注册表、`getattr`、多态等保留不确定性。
- 上游 call graph 与 AST/真实调用点不一致时，显示差异，不能悄悄覆盖成确定边。
- 不运行 `eval`、`exec` 或目标 import 来“聪明地解析”配置/注解。

其他语言沿用上游 parser；仅验证它真正支持的结构。没有可靠名称/类型绑定时只显示候选调用与源码定位，明确限制；不宣称 AST 语法解析自动等于语言服务器的完整引用解析。

### 8.3 PyTorch/训练项目

把“Python 函数调用”“模型模块包含”“tensor 数据流”“反向传播图”分开。不得把 `named_modules()` 的树当 forward 的执行顺序。

读实际模型 class 与构造绑定，解释 `model(x)` 如何通过 Module 的调用机制触发 forward；hooks、自定义 `__call__`、条件分支和框架包装不应被省略。静态边先标 framework/candidate，运行 hook 证据只能证明样例中的模块执行。

训练主线至少追：参数/配置 → seed/设备 → 数据集/collate → 模型 → 预处理 → forward → 每项 loss → 聚合 → backward → optimizer/梯度累积/clip → scheduler → checkpoint → eval/metric。只展示代码实际存在的环节。

说明 train/eval、no_grad、AMP、detach、冻结参数、分布式 worker、归一化统计、checkpoint 选择等影响语义的设置。自动求导的 backward 边不伪造为源码直接调用。

## 9. 给弱模型的函数深读协议

按“一个函数或 3–5 个紧密相关小函数”一个批次，不一次塞整个项目。每批给：符号签名、完整函数体、必要类字段、直接 callers/callees、相关配置和论文证据；遇到跨文件未知项再定向读取。

每批采用下列任务模板，保存在 `references/workflow.md`：

```text
只解释下列已提取的 symbol IDs，不创建新的不存在的函数。
阅读完整函数体和必要上下文；保持源码真实行号。
输出符合函数 schema 的 JSON，不能只输出 Markdown。
逐项填写 purpose、输入、输出、steps、side_effects、exceptions。
每个确定性结论附现有 evidence ID；未知值使用 null 和 reason。
调用目标只能引用已存在的 symbol ID 或 unresolved/candidate。
把当前无法确认而需要读取的文件/配置放在 needs_context。
禁止补造 tensor shape、loss 权重、论文对应或运行结果。
```

脚本验证每批 JSON、符号数量、引用和行范围。失败只修该批；连续两次相同失败先诊断，不反复全仓重跑。已经通过、输入哈希未变化的批次可复用。

入口目的与“核心函数”由代码和论文证据共同排序：入口控制、主要数据变换、模型 forward、loss、训练/评估逻辑、创新相关实现优先。工具函数也保留契约；排序不是随意删掉较小函数。

用一个具体样本解释关键数据流：原始数据 → collate → tensor → 编码/重排/融合 → prediction → loss 或后处理。标出容器路径与维度，不只画框。示意样本与实际运行样本明确区分。

## 10. 论文创新点与代码的双向对照

有论文时按以下顺序执行；没有论文时输出 missing 状态，代码部分照常完成：

1. 确认论文标题、版本、正文与附录，以及代码是否声明对应某个 release/branch。
2. 先看 abstract/introduction/contributions，整理作者明确主张，不根据仓库名称自行发明创新。
3. 读 method、公式、算法、模型架构与 training/inference 部分，生成概念/符号表。
4. 读 experiments、implementation details、appendix、ablation；找训练与评估关键设置。
5. 用论文术语、类名、配置名与公式变量在项目中定向检索；名字不一致时根据输入输出与计算语义追踪。
6. 读候选函数的完整实现及直接上下文，与公式/算法逐步对照；形状、归一化、符号、目标方向、mask、采样顺序都要核对。
7. 每条映射同时给论文定位与源码定位，标为 direct/inferred/not_found/conflict。
8. 对未落实、未在入口执行、只在测试存在、配置默认关闭、仅 inference 或 only train 的模块分别说明。

映射表至少包含：

| 字段 | 要求 |
| --- | --- |
| 创新点 | 论文原始主张的简明中文改写 |
| 相比什么改变 | 论文明确比较对象；证据不足则未知 |
| 核心机制 | 算法步骤、公式/模块，变量与维度含义 |
| 论文定位 | PDF 页/section/equation/figure/table |
| 代码定位 | 文件、符号、真实行范围与哈希 |
| 进入路径 | 从所选入口如何到达；未到达也要显示 |
| 关键配置 | 哪些开关/超参控制这一实现 |
| 输入输出变化 | 创新对数据格式或训练目标的影响 |
| 证据/差异 | 对应状态、支持理由、冲突与未找到部分 |
| 修改约束 | 想改这里需要保持哪些数学与实验假设 |

一个创新点可能对应多个函数；一个函数可能实现多个步骤。双方允许多对多，不强行一一映射。普通日志、下载和参数解析函数没有创新对应时如实说明。

论文公式与代码冲突时分别保留原始写法；检查路径导数、初始端点、采样/积分方向、损失 target 和实际更新式。不要自动把任意一方改成另一方，也不凭作者信誉选择。

视觉上至少提供“创新点 → 实现函数 → 所选入口路径”的可点击定位，以及“论文计算步骤 ↔ 代码内部步骤”的对照。不能只有论文摘要面板。

## 11. 实验关键设置：三方对照与实际消费者

对每个关键设置分开记录 **论文值、仓库默认值、所选场景最终值**；最终值无法静态确定时写未知，不拿默认值冒充。

按项目真实存在的项目核对：

- 数据集版本、划分、过滤、augmentation、归一化/统计来源、采样窗口、tokenizer、collate。
- 模型层数、维度、head、共享/冻结参数、预训练/checkpoint、精度与量化。
- 每项 loss 的数学定义、reduction、权重、mask、正负样本、detach、正则。
- batch size、有效 batch、学习率、优化器、scheduler、warmup、epoch/steps、梯度累计/裁剪。
- seed、重复实验数、设备/分布式、训练/评估模式、推理采样步骤、温度与随机性。
- checkpoint 选择、验证频次、评估数据/环境、成功判据、指标公式、聚合方式和 ablation 开关。

配置解析先确认项目机制：argparse、Hydra/OmegaConf、dataclass、YAML、JSON、TOML、环境变量或 Python config。查 include/defaults、继承、合并、插值、CLI override、环境 override 与运行中再次修改的真实顺序。

YAML 只用 safe loader；Python config 在静态模式用 AST 读可确定部分，不执行。自定义 resolver/动态配置可能不可解；列出缺少的环境/值。不打印秘密环境变量。

每个设置都追到消费它的代码行。例如仅查到 `lr: 1e-4` 不够，还要指向 optimizer 初始化或 scheduler；仅查到 loss_weight 也要指向真正乘法/聚合。CLI 参数解析出来却未使用，显示“定义但未确认消费”。

展示实验差异对执行逻辑和改动的影响，不能把“一次成功运行”写成“论文复现成功”。区分静态一致性、真实样例观测与论文规模/指标复现。

## 12. 可视化界面要求与准确源码跳转

### 12.1 最低可用布局

```text
顶部：项目/入口/场景 | 分析时间与源码快照 | 覆盖/未知/未完成状态
左侧：入口、文件、核心函数、搜索、学习步骤
中央：入口阶段图 / 调用关系图 / 函数内部流程 / 具体数据流
右侧：函数卡片（用途、I/O、步骤、调用者/被调用者、副作用、证据）
下方/页签：源码 | 论文创新对照 | 实验设置差异 | 修改影响 | 未知清单
```

一屏显示最关键的信息；长解释可折叠，但字段不能隐藏到用户无法找到的位置。默认中文，第一次使用专业术语解释其含义。

必需交互：

1. 点调用图节点，更新选中函数、详情、相关边与源码。
2. 搜索名字/路径/用途；同名函数显示全限定名和文件，选择准确对象。
3. callers/callees 每项可点击跳到对应函数；未知项点开调用位置与原因。
4. 展开/收起层级、调显示深度、过滤 edge 类型、查看上下游和递归环。
5. 点击内部步骤定位到步骤所在源码范围。
6. 点论文创新/实验设置定位代码与相关函数；能反向看到函数关联论文位置。
7. 用稳定 URL hash 保存当前函数和页签，刷新可回到同一对象；浏览器前进/后退可恢复导航。
8. 进入“准备修改”视图，显示候选影响链和建议检查，不在网页内直接写源码。

### 12.2 源码定位必须可靠

- 基础跳转指向 RUN_DIR 中的源码快照，不依赖 VS Code/custom URI 是否安装。
- 点击后展示正确文件、1-based 行号、高亮范围，自动滚到目标行；定义行与 callsite 行分开。
- 显示快照哈希、生成时间与最近源码重验时间。离线产物只保证快照内部一致，默认显示“当前源码未重新核验”；浏览器仅读取快照，不能自动知道原项目是否变化。
- `validate --run-dir <目录> --recheck-source` 才在用户允许的原项目范围内重算文件哈希，与 manifest 比对并写 run 内的 freshness 结果。发现改动显示 stale；匹配也只能显示“在该重验时间匹配”。原目录不可访问、身份不匹配或没有授权时显示 unknown，不当成匹配。无需实时 watcher，不新增浏览器任意文件读取接口。
- 当前源码检查与快照行号校验分开；stale 时仍可点击已保存的正确快照行，但不能声称它就是当前源码位置。
- 可选额外编辑器链接，但浏览器禁止打开外部协议时仍可完成内置跳转。
- 优先改造 CodeViewer 数据读取为当前产物内的 sources/index；不让页面读取任意磁盘路径。
- sources.json/快照引用只包含分析允许范围的文本，不默认复制全项目和论文 PDF。

### 12.3 图语义与规模

调用方向为 caller → callee；调用层级用图的折叠浏览形式呈现，不把递归/共享函数强制改成树。SCC/visited 处理循环，避免无限展开。

分别切换函数调用、文件依赖、模块包含、数据流、内部控制流程。图例同时用文字/线型区分确定性；不只靠颜色。候选边默认虚线且可过滤，runtime 边标出 run 范围。

大图默认显示入口相关局部与关键阶段，用户展开时加载邻居；完整索引保留。不要给数千函数强行全屏力导图。进度、截断与待解释数量显示出来。

### 12.4 本地与安全

构建后的 HTML/JS/CSS/字体/图库资源全部本地，断开互联网仍可用。局域外访问不开放，只绑定 `127.0.0.1`；如果本机既有安全的本地静态服务可复用。

代码、注释、论文摘录、路径与 LLM 输出作为文本/经过 schema 验证的数据处理，不作为指令或可执行脚本。React 默认文本转义或 textContent；不得把原始内容直接 innerHTML。嵌入 JSON 处理 `</script>`；禁止来自内容的 eval、HTML 事件属性、javascript: 链接。

静态服务只提供当前 run 的允许资源与前端构建包，不提供任意文件读取/写入/命令执行接口。URL 解码、`..`、反斜杠、symlink、绝对路径与 MIME 都验证。空缺/损坏数据给用户明确错误，不能白屏。

键盘可选择与打开节点；焦点清晰，图以外保留可用列表；窄屏至少能切换图和详情。使用上游已有能力，不额外引入 UI 框架。

## 13. 修改影响分析与持续更新

用户提出“想改什么”时生成建议，不默认实施：

1. 用目标全限定符号和具体需求定位最小改动位置。
2. 找直接/间接调用者、依赖的数据格式和下游消费者。
3. 查相关配置、模型状态、loss、指标和论文约束。
4. 列最小检查：函数契约、shape、关键分支、训练/推理一致性、配置传播与评估影响。
5. 给“为什么改这里、需要同步哪里、什么证据不足”的解释与源码链接。

零调用者、未解析动态边、跨语言边界不能视为绝对安全。图没有显示的地方可能没有被解析；结果叫候选影响，不叫完整保证。

更新时按文件哈希复用未变结构/说明。变化的函数、调用点、导入/配置消费者及论文证据要使相关说明失效并重新分析；不能只更新图线不更新函数卡片。

不得把 Git HEAD 当作未提交源码的唯一版本；同一 commit 下文件变化也要在重新核验时触发 stale。更新后的行号、源码哈希、图与解释必须对应同一快照。只有离线快照且未执行重验时，当前源码状态保持 unknown，不能沿用生成时 matched 状态冒充持续实时监测。

## 14. 可选真实运行观测

这是增强模式，不是静态学习界面上线的前置条件。基础功能通过后才实现；未实现时 CLI 与 skill 明确不支持，不能留一个返回假数据的命令。

执行前必须列清：目标环境绝对路径、cwd、精确 argv 数组、样例输入、checkpoint、预计副作用、超时、产物路径与运行范围。只在对应授权内执行；不默认跑完整训练、自动下载数据、驱动机器人或调用收费服务。

机制选择：

- Python `sys.setprofile` 等标准 hook 记录调用/返回关系；输入 metadata 可来自 frame 与签名，输出来自可获取的真实返回值。
- hooks 只记录有限容器层级、type、shape、dtype、device、单位线索；不调用用户对象的任意 repr，不序列化完整 tensor/数据，不把 tensor 搬到 CPU 计算大统计。
- PyTorch 已有环境中可用 forward pre/post hooks 记录模块 I/O；调用图与模块树分开输出。
- `sys.setprofile` 不提供所有异常/行事件，也不是所有线程、子进程或 async task 的完整覆盖。缺覆盖时写 limitation，必要时采用已有更合适工具，不伪造捕获。
- 不把 generator 的每次 resume/yield 误标为最终完成，也不把异常返回的 None 直接当函数正常返回 None；无法区分时标 unknown。
- 以 PID/thread/task（能取得时）分隔 call stack；超过事件数/深度/时间预算时标 truncated。

子进程运行必须尊重目标调用方式：script/module、sys.path、argv、cwd 与项目环境；不把 runpy 包装自动当等价于所有 CLI。捕获异常保留原始 traceback、退出码和部分轨迹，并正确停止自身 hooks。

单个受限运行只是这组条件下的观测，不证明未走分支不会执行，也不证明论文复现。运行失败不影响已通过的静态产物，但 UI 明确标出失败和缺少的值。

## 15. 需要实现的 CLI 与产物

使用一个 `scripts/atlas.mjs` 入口。下列接口是本任务要实现的规格；不允许文档出现未实现参数：

| 子命令 | 参数与默认 | 作用/真实产物 |
| --- | --- | --- |
| `inspect` | `--request <JSON文件>`，必填 | 校验路径、入口、环境与允许范围；输出 readiness 与缺失项，不执行目标 |
| `extract` | `--request <JSON文件>`，必填 | 复用上游结构提取与 AST 补充；输出 run 的 inventory、structure、证据与源码快照 |
| `assemble` | `--run-dir <目录>`，必填 | 合并结构与 agent 写出的函数/论文/配置说明为 atlas.json；校验，拒绝悬空引用 |
| `render` | `--run-dir <目录>`，必填 | 生成可用本地 viewer bundle 与数据文件，不自动发布 |
| `validate` | `--run-dir <目录>` 必填；`--recheck-source` 可选布尔开关，默认不重验原项目 | 默认检查产物内部一致性；显式开关在原项目允许范围比对哈希，输出独立 freshness 证据，不把未知当前状态当全链路通过 |
| `serve` | `--run-dir <目录>` 必填；`--port <整数>` 默认 0，由系统分配 | 仅在 127.0.0.1 提供该 run 的只读资源，打印实际 URL；明确停止方式 |
| `capture` | 可选实现；`--request <JSON文件>` 必填；`--timeout <秒>` 默认 60，正整数；具体运行清单在 request 内 | 获授权的目标样例观测；未实现则清晰报不支持，不创建伪轨迹 |

不同命令之间的批次语义工作由 skill 调度：extract 后读结构 → 分批写 function-notes.json → 论文/实验说明 → assemble → render → validate → 浏览器验收。CLI 不默认再开一个未配置的 LLM 服务来完成说明。

退出码：0=该命令接受的具体检查/步骤通过；1=运行故障；2=参数/路径/schema 错误；3=必要证据/验收未满足。部分分析可保留产物，但 validate 不能因 unknown 合理存在而一律失败；缺“已确认结论所需证据”、未完成必需功能或不一致引用才失败。CLI 成功不是全任务自动完成。

每次 run 建议保留：

```text
request.json                  规范化输入，无凭据
manifest.json                 输入/源码/配置/论文哈希、工具版本、覆盖与状态
freshness.json                最近源码重验时间、范围与 matched/stale/unknown；离线默认未重验
inventory.json                轻量文件与范围清单
structure.json                原始结构、调用点和未解析项
knowledge-graph.json          兼容上游 graph 的基础结构
function-notes.json           agent 按符号 ID 写的解释
paper-map.json                论文与代码映射；无论文也有 missing 状态
experiment-settings.json      论文/默认/最终配置与消费位置
atlas.json                    前端统一研究数据
sources.json 或 sources/      允许范围内的文本快照
viewer/index.html + assets/    本地可视化页面
report.md                     简明入口、学习路线与未验证边界
validation.json               静态、功能、浏览器、人工抽查的实际结果
runtime/                      仅实际执行时出现
```

可减少文件数量，但不能丢独立证据、复用边界与重试所需输入。所有持久文件显式 UTF-8；中文内容不能通过编码不明的 shell 标准输入传丢。

## 16. 分阶段执行计划：每阶段交付什么

### 阶段 A：预检、PRD、参考接口核验

确认环境、授权与源码目标；读第 2 节主项目 anchor；保存 upstream revision/许可/接口核验。完成 PRD 与 acceptance checklist。不要凭上游 README 宣称本机支持。

### 阶段 B：基础提取与数据契约

实现 request/schema、路径守卫、scan/extract adapter、Python AST 契约补充、覆盖清单与源码快照。先用小 fixture 验证直接调用、别名与未知项。未通过不做全仓语义深读。

### 阶段 C：函数深读与内部流程

完成分批协议与 JSON 合并；对 fixture 全部函数真正生成说明。确保源码行范围正确、输入输出未知可表达、内部控制流程不是模块调用图的重复。

### 阶段 D：论文与实验对照

先用明确标为“测试材料”的小论文 fixture 检查引用与跳转；再在用户真实研究项目有论文时核验内容。测试论文不能宣传成真实学术结论。实现三方配置、消费位置与冲突显示。

### 阶段 E：改造面板与源码导航

复用上游 viewer，实现 atlas sidecar 加载与所需面板，适配快照源码，构建后断网访问可用。确保当前 project/run 绑定正确，不沿用上一次数据。

### 阶段 F：修改影响、多入口与更新

验证 train/eval/infer 不覆盖，搜索所有调用者，显示可能影响与未知。用两个入口以不同配置调用同一共享函数，证明各自契约/最终设置均可查看且互不覆盖。改变文件后显式运行源码重验，stale 生效；重新分析使卡片与行号同步。

### 阶段 G：可选 runtime

只有静态完整路径通过后且当前任务要求/授权该功能时实现。验证真实事件、metadata、异常/超时与覆盖边界；如果此阶段缺环境，说明准确未验证边界，保留前面已通过产物。

### 阶段 H：真实项目验收、安装与配置收尾

用用户提供或用户明确选择的真实研究项目，从 PROJECT_ROOT + entry + paper 生成完整界面并抽查。不能拿 BUILD_ROOT 自己的脚本或一个 toy fixture 替代研究项目验收。

当前没有真实项目时，完成 fixture 的端到端交付，明确“真实研究项目适配未验证”；让 skill 后续运行具备完整流程，不编造论文准确率或项目支持结论。

实际安装/维护 skill 后，执行工作区要求的配置迁移和 Claude 差距记录。记录完成与未完成，给用户准确使用命令与 URL。

每阶段更新同一个 HANDOFF：通过项、失败原始证据、已建文件、授权边界和下一步命令。上下文不足先保存，不从头重新设计；下次从 manifest/HANDOFF 中的真实状态继续。

## 17. 验收：需要真实可运行的检查

### 17.1 固定 fixture

创建一个小的 Python 项目，包含：入口保护、相对/别名导入、两个同名函数、嵌套函数、class 方法、共享调用、条件分支、递归、一个无法确定目标的动态调用、一个返回 tuple/dict 的函数，以及默认值/装饰器执行位置。

对期望边与未知项写人工确认的 ground truth，检查脚本输出，不仅检查“有 JSON 文件”。不要为全部函数建立庞大测试框架；复用上游现有测试工具，小而有判别力。

需要至少证明：

1. 入口与参数真实存在，别名解析到正确目标。
2. 同名符号不合并，嵌套函数调用不计入错误作用域。
3. 动态调用保留 unresolved/candidate，不猜为确定边。
4. 递归/共享函数不会无限展开，calls 与 contains/imports 不混用。
5. 函数参数种类、默认值、tuple/dict 输出及副作用按源码说明。
6. 内部步骤的分支/早退与行范围正确，示例数据流的维度变化可核对。
7. 源码哈希与行号验证成立，所有 symbol/evidence/config/paper 引用存在。
8. 论文 fixture 的 direct/not_found/conflict 状态均可表达，不把未找到当已实现。
9. 配置默认与 CLI 覆盖不混淆，设置能定位消费行。
10. 无论文场景仍完整生成代码界面，明确论文 missing。
11. 两个入口有不同模式、配置和同一函数的不同 shape，切换 entry_id 能查看两份契约与最终设置，共享 symbol_id 不复制或覆盖。
12. 修改原源码但不执行重验，界面显示“当前未重验”；显式源码重验后显示 stale；快照跳转仍正确，重建后新图/说明/哈希/行号一致。

### 17.2 浏览器端到端

从实际 CLI inspect → extract → 分批解释 → assemble → render → validate → serve 跑通，再用现有浏览器工具：

- 点入口到核心函数，核对卡片和选中边。
- 点 caller/callee 与内部步骤，确认准确文件和高亮行。
- 选择两个同名函数，证明跳到不同源码。
- 点击论文映射、配置消费者与修改影响链，确认符号一致。
- 刷新带 hash 的 URL、前进后退，核对状态恢复。
- 断开外网请求仍能使用；没有 CDN、远端模型或字体依赖。
- 在代码/注释中放字面量 `</script><script>window.__unexpected=1</script>`，页面只展示文字，没有执行；路径遍历测试不能读到 run 外文件。
- 至少检查常见桌面与窄窗口布局，无被截断的重要按钮、遮挡源码或无法关闭的面板。
- 记录浏览器控制台异常、实际资源状态与操作结果。截图只是证据的一部分。

如浏览器工具不可用，不能写“自动浏览器验收通过”。给准确人工检查步骤、标未执行边界，保留可运行本地 URL。

### 17.3 真实研究项目

至少人工/独立审查抽查：入口、关键模型函数、一个 loss、一个数据处理、一个评估/输出函数；项目没有某类时说明不适用。核对每个调用点、每个确定 shape 的证据、主要创新与至少三个关键实验设置。

没有公开/用户授权的真实材料时，不为了验收随意下载大仓库、模型与数据集。需要的项目/论文缺失属于明确边界，不可用 toy 结果替代。

### 17.4 Runtime 若实现

只在已有环境中运行小 fixture；检查调用/返回事件来自真实函数、metadata 受限、错误与超时如实输出。若已有 PyTorch 环境，再用小模型验证实际 forward I/O 与共享模块两次调用。无环境则不安装大套依赖“凑验证”。

### 17.5 Skill 与脚本

- 使用当前 skill-creator 的实际 validator；本机 Windows 中文内容用 `PYTHONUTF8=1` 或 Python `-X utf8`，避免解码错误被误判为 skill 结构问题。
- 执行脚本真实入口、成功与重要失败分支，检查退出码和具体状态，`--help` 不算全链路通过。
- 文档参数、schema、实际实现一致；引用文件存在；没有未实现 TODO 冒充能力。
- 若 Git 可用，检查 task diff、`git diff --check` 与敏感内容；没有 Git 时说明静态文本检查范围。
- 验证通过只对已覆盖的版本、语言、场景与项目有效，不宣传全语言通用精确图。

## 18. Skill 入口需要怎样写

SKILL.md 入口简明，把第 5–17 节流程分到 references。不要把这一份建设 prompt 原样塞成巨大的常驻 skill。

建议 frontmatter：

```yaml
---
name: research-code-atlas
description: 根据项目路径、入口文件和可选论文，生成可点击源码的本地代码学习界面，解释函数输入输出、调用关系、内部流程，并对照论文创新、实验配置和修改影响。适用于深入理解研究代码；不默认修改项目或执行训练。
---
```

入口正文必须包含：

1. 什么时候用、所需输入与默认静态模式。
2. 解析当前 skill/package 根路径，验证上游完整包与构建产物。
3. 读取 workflow/data-contract；有论文读 paper-mapping；runtime 获授权时才读 runtime。
4. 规范化 request，执行 inspect/extract。
5. 按符号小批次写解释、论文/配置对照，运行 assemble/render/validate。
6. 打开/给出具体本地 viewer URL，做实际点击验收。
7. 回报覆盖、未知、源码快照时间、运行是否执行、下一学习/修改入口。

自动触发保持默认；显式调用为 `$research-code-atlas`。不要把整套上游 skills、MCP 和多个数据库写成必需条件。外机没有本机个人论文 skill 时，用 references 中自包含的论文流程继续。

## 19. 安装、迁移与当前工作区特殊规则

当前官方 Codex 文档列 `.agents/skills` 的 repo/user 发现位置；本机既有运行清单还提供 `.codex/skills` 来源。以实际宿主可发现性和工作区 canonical 规则为准，不能用“文件存在”证明安装生效。

参考：[OpenAI 当前 Skill 文档](https://learn.chatgpt.com/docs/build-skills)。安装时：

1. 先在 BUILD_ROOT 完成真正实现与验收。
2. 在工作区 canonical skill tree 维护唯一源版本，完整包保留在 BUILD_ROOT。
3. 获得安装授权后，在宿主实际发现根放一个完整新 skill 或明确依赖完整包的轻量适配器。大包路径写在本机配置，不硬编码旧机器盘符到可迁移指令。
4. 已有同名 skill 先比较来源、内容与版本；不能直接覆盖。只读说明与候选变更先准备好。
5. 不复制整个上游仓库到每个 skill 安装目录；不破坏跨目录 sidecar。若用 symlink/junction，要确认宿主支持与目标生命周期。
6. 安装后的结构、版本/哈希一致性与宿主实际发现性分别验收；新一轮/新会话实际调用确认，不用当前静态清单冒充刷新。

本工作区在实际 skill/配置维护后要求：读取 `codex-config-transfer` → 串行 Capture → 紧接 Check（退出码 0 且 CHECK_OK），不得并行快照或手改 manifest/payload；不要写 deprecated Agent_transfer。

还要按 AGENTS.md 对相关 Claude 模板做有边界比较，并维护 `ClaudeCode_transfer/配置待办.md` 的稳定项目条目；这只记录迁移差距，不自动安装 Claude、改权限或读取凭据。没有这些工作区设施的外机不擅自创建替代 bundle。

建设后仅在形成经过真实验证、非显然且跨任务的经验时按 record-ai-tips 评估记录。普通 prompt 文档、架构愿望与 fixture 通过不写成成功经验。

不自动 commit/push/publish。Git closeout 仅在当前既有授权内；所有用户内容保留，禁止为使状态干净而恢复、重置或删除。

## 20. 必须交给用户的最终结果

1. 可调用的 `research-code-atlas`，指出维护源、完整包、实际安装位置与当前发现性状态。
2. README：安装前提、参数、三种场景调用、界面操作、更新、停止与恢复。
3. 至少一个真正可点击的本地分析界面；说明是 fixture 还是真实研究项目。
4. 真实命令、退出码和 `validation.json`；区分数据、浏览器、真实项目、runtime 与论文级复现。
5. 主要源码精度/语言/动态调用/论文缺失等边界。
6. 工作区要求的配置 Capture/Check 与 Claude 差距记录证据，若实际触发。

禁止的“完成方式”：只给方案；只写 SKILL.md；用正则名匹配充当精确调用图；造 tensor shape；用 model tree 冒充执行路径；只给不可点击图片；靠编辑器 URI 冒充网页源码导航；无论文映射；不追参数消费者；命令没有实现；测试成功却未真生成界面；未验证安装却声称全局可调用。

## 21. 用户以后怎样调用：请放进最终 README

### 静态理解训练入口

```text
使用 $research-code-atlas。
项目：D:/Research/MyProject
入口：train.py
场景：train
论文：D:/Papers/my-paper.pdf
配置：configs/train.yaml
启动参数线索：--config configs/train.yaml
学习重点：训练主循环、模型 forward、loss 和评估指标。
模式：静态分析，不执行训练。
产物：本地可视化界面；函数卡片、调用层级、内部流程、I/O 格式、论文创新与实验对照都要可点击定位源码。
```

### 准备改代码

```text
继续这个 research-code-atlas 分析结果。
我想把模型的特征融合改成另一种方法。
先从入口链路定位负责融合的函数，解释输入输出与内部步骤，
再显示论文假设、相关 loss/配置、所有已找到的调用者和候选影响。
只给有证据的修改位置与最小验证清单，暂不改源码。
```

### 多入口对照

```text
使用 $research-code-atlas，对比同一项目的 train.py、evaluate.py、infer.py。
保留各自参数和配置，标明共享函数、模式差异、数据预处理/后处理差异，
以及论文训练和评估设置分别在哪些代码路径落实。
```

### 已授权的小样例真实观测

```text
在现有分析结果上增加一次真实运行观测。
环境、cwd、精确命令、样例输入和检查点如下：由我提供具体值。
只执行这条已确认的安全样例，超时 60 秒，不自动下载或训练。
显示本次实际调用和 I/O metadata，并保留静态未走分支及覆盖限制。
```

最后一个例子不是可直接执行的完整运行清单；agent 必须等用户提供真实值，不能自行填入随机 checkpoint 或猜环境。

现在按阶段 A 开始：读取规则、检查环境和准确目标，建立 PRD/验收/HANDOFF；在授权范围内持续推进到可运行且经过实际检查的 skill。
