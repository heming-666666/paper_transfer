# 怎样创建并使用“论文与代码执行图谱” Skill

这里交付的是 **让本地 agent 创建 skill 的完整任务包**，不是已安装的 skill。包含：

- [prompt.md](prompt.md)：完整实施说明，直接交给本地 agent。
- [调研依据.md](调研依据.md)：候选比较、准确 GitHub 链接、现成 skill、维护与许可证快照、检索边界。

## 1. 推荐的实现方向

基于 [Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) 的结构解析和可视化面板，创建新入口 `research-code-atlas`。扩展函数数据契约、内部流程、论文创新与实验设置对照，而不是同时接入多个代码图谱平台。

上游已有 [understand](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand/SKILL.md)、[understand-explain](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand-explain/SKILL.md) 和 [understand-dashboard](https://github.com/Egonex-AI/Understand-Anything/blob/main/understand-anything-plugin/skills/understand-dashboard/SKILL.md)。它们依赖完整包；仅下载 SKILL.md 不等于安装了可用解析器和界面。

## 2. 先让本地 agent 创建

在工作区打开本地 agent，发送下面这一段。它先完成可逆的构建准备；新增软件/依赖与安装仍遵守您的现有授权：

```text
读取 D:/Code/research-code-atlas-skill/prompt.md，按它实际创建并验收 research-code-atlas skill。
先检查现有环境和准确目标，使用已有 skill-creator。
建议建设目录 D:/Code/tools/research-code-atlas，保留完整 Understand-Anything 包和许可。
不要覆盖 D:/Code/prompt.md 或已有同名文件，不要修改被分析项目，不要执行训练。
先完成不需要额外授权的部分；新增依赖/下载/安装需要确认时，给出具体包、版本、路径与影响。
分阶段保存 HANDOFF，每阶段提供实际检查结果，不能只输出方案或 SKILL.md。
```

如果您愿意一次性授权指定范围内的下载和依赖安装，可以在上述消息后自行加上这一段；这段文字会授予后续 agent 相应操作权限：

```text
允许下载 prompt 中固定版本的 Understand-Anything 到本任务建设目录，
并在 D 盘本任务专用环境/缓存中安装其锁文件所需依赖。
不要全局更改 Node/Python、系统权限或安全设置，不覆盖现有 skill，不下载模型/数据集。
skill 验收通过后，给出具体发现目录和待安装文件，按工作区规则完成获授权的安装与迁移检查。
```

只有当前机器缺少软件时，才需要安装 Node/Python/pnpm；agent 应先给出实际缺失项。不要预先手动安装 GitNexus、CodeGraphContext、Pyan3、Graphviz、Docker 和数据库整套工具。

## 3. 需要哪些 Skill

| Skill/能力 | 建议 |
| --- | --- |
| skill-creator | 用于创建与验证；Codex 通常已内置，先检查即可 |
| research-code-atlas | 本地 agent 根据 prompt 真正创建的最终入口 |
| Understand-Anything 完整包 | 主解析器与界面依赖；不必全局安装其所有 skill |
| paper-understanding-pack、PDF 工具 | 本机已有时按需读取论文；缺失时 prompt 已提供自包含流程，不强制装全部论文 skills |
| paper-lookup、agent-reach | 只在论文来源缺失或用户要求联网时使用 |
| codex-config-transfer | 本工作区实际 skill/配置维护后的 Capture → Check；分析项目时无需每次运行 |

准确来源与完整“何时用、哪里用”表在 prompt 第 2–3 节。个人论文 skill 没有经过核验的公开仓库地址，因此没有编造安装链接。

Codex 当前官方文档列出 repo/user 的 `.agents/skills` 路径，而这台机器的现有技能清单也使用 `.codex/skills` 来源。让 agent 根据实际宿主与 canonical 规则确认安装位置，并用新一轮实际调用验证发现性。[官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)

## 4. skill 创建并确认可调用后

提供真实项目路径、入口文件、论文和当前配置。例子中的路径需换成您的真实文件：

```text
使用 $research-code-atlas。
项目：D:/Research/MyProject
入口：train.py
场景：train
论文：D:/Papers/my-paper.pdf
配置：configs/train.yaml
启动参数线索：--config configs/train.yaml
重点：训练主循环、模型 forward、loss、论文创新模块和关键实验设置。
先做静态分析，不执行训练。
生成本地可视化界面；所有函数卡片、调用层级和内部步骤都能点击定位准确源码。
```

没有论文时可以先分析代码，界面应明确显示论文未提供；缺少运行环境也可以做静态分析。输入输出中无法确定的格式必须标未知或推断。

后续准备改动时：

```text
继续这个 research-code-atlas 分析结果。
我想修改特征融合模块。
请定位负责融合的函数，解释输入输出、内部步骤与论文对应，
展示它的调用者、下游消费者、loss/配置关联和候选修改影响。
先给源码位置与最小验证清单，暂不改源码。
```

也可给 train/eval/infer 多个入口，要求比较共享模块、模式与参数差异。需要实测 shape 或真实调用时，再提供已有环境、精确安全样例命令和输入，不默认启动完整训练。

每个入口应分别保留配置和输入输出格式。源码导航默认查看分析时的快照；原项目是否后来改动，需要让 agent 显式重新核验，不能只靠离线页面判断。

## 5. 打开界面后怎样学习

1. 先看入口阶段图，理解配置、数据、模型、loss、更新和评估的顺序。
2. 点击核心函数，读用途、输入输出、内部步骤与副作用。
3. 点击步骤或调用者/被调用者，核对源码与条件分支。
4. 追一个具体数据样本，观察容器字段和 tensor 维度怎样变化。
5. 打开论文创新面板，从公式/算法定位实现函数，再查看相关实验参数在哪里消费。
6. 使用修改影响面板，找可能需要同步的接口、配置、loss 和评估检查。

界面应提供实际 `http://127.0.0.1:<端口>` 地址及停止方法。这里的“本地离线可用”表示构建后不依赖外网；可能仍需要本地静态服务，不能默认双击 HTML 就能工作。

## 6. 判断本地 agent 是否真的做完

至少要求它交出：可发现的 skill、完整包位置、一个能点击源码的界面、函数/论文/实验结构化数据、实际验证记录，以及未覆盖的语言/动态调用/运行边界。

只出现一份 SKILL.md、一张图、一个 JSON、一个通过帮助命令的脚本，都不算全部完成。若只完成测试小项目，要明确真实研究项目尚未验证；若运行模式没有实现，不可展示假的调用轨迹。

本任务包已检查文字编码、结构、相对链接和需求覆盖；上游资料已经联网核验。尚未执行后续 skill 实现、安装、浏览器功能或真实研究项目验收。
