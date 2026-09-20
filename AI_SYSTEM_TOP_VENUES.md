# AI、具身智能与系统方向核心论文 Venue 清单

> 面向背景：强化学习（RL）、AI Infra、具身智能、全身控制（WBC）、遥操作（Teleoperation）、视觉-语言-动作模型（VLA）和世界模型（WM）。
> 检索日期：2026-09-19。评级以 CCF 2026 第七版和 CORE 2023 为主；`—` 表示该体系未收录或未给出有效等级，不代表 venue 水平低。
> 本表用于确定后续论文下载源，不用于评价单篇论文质量。

## 如何使用

- **P0｜必跟踪**：与你当前研究主线直接重合，建议逐年完整下载或至少下载标题、摘要和引用数据。
- **P1｜重点扩展**：提供关键上游方法、控制理论、交互范式或底层系统能力，建议按主题关键词筛选下载。
- 同一优先级内，先看 **CCF A + CORE A\***，再看其他 A/B 组合；“领域例外”因与你的方向高度相关而保留。
- CCF 仅认可会议的 Full/Regular Paper；Workshop、Demo、Short Paper 等应在后续下载时单独标记。

## 核心会议（34）

### P0｜必跟踪（17）

| 简称 | 全称 | 重点标签 | CCF 2026 | CORE 2023 | 为什么值得跟踪 | 官方 / 论文入口 |
|---|---|---|---:|---:|---|---|
| NeurIPS（原 NIPS） | Conference on Neural Information Processing Systems | RL、WM、VLA、基础模型 | A | A* | 强化学习、生成式世界模型和多模态基础模型的首要来源之一。 | [官网](https://neurips.cc/) · [论文](https://proceedings.neurips.cc/) |
| ICML | International Conference on Machine Learning | RL、IL、WM、表示学习 | A | A* | 机器学习方法与理论主阵地，离线/在线 RL、模仿学习和机器人学习论文密集。 | [官网](https://icml.cc/) · [论文](https://proceedings.mlr.press/) |
| ICLR | International Conference on Learning Representations | VLA、WM、RL、表征学习 | — | A* | OpenReview 讨论公开，适合追踪 VLA、生成模型和可扩展学习的新方向。 | [官网/论文](https://openreview.net/group?id=ICLR.cc) |
| CoRL | Conference on Robot Learning | 具身智能、机器人学习、VLA、IL | — | Unranked | 与你的研究交集最高；覆盖策略学习、机器人数据、泛化与 sim-to-real；作为领域例外保留。 | [官网](https://www.corl.org/) · [论文](https://proceedings.mlr.press/) |
| RSS | Robotics: Science and Systems | 机器人学习、规划、控制、感知 | — | TBR（历史 A*） | 机器人领域高密度精选会议，兼顾学习、控制与真实机器人系统。 | [官网](https://roboticsconference.org/) · [论文](https://www.roboticsproceedings.org/) |
| ICRA | IEEE International Conference on Robotics and Automation | 具身智能、WBC、遥操作、控制 | B | A* | 机器人覆盖最全面，WBC、操作、遥操作和硬件系统论文数量大。 | [官网](https://www.ieee-ras.org/conferences-workshops/fully-sponsored/icra) · [论文](https://ieeexplore.ieee.org/xpl/conhome/1000639/all-proceedings) |
| IROS | IEEE/RSJ International Conference on Intelligent Robots and Systems | 具身智能、WBC、操作、遥操作 | C | A | 与 ICRA 互补，真实机器人、运动控制与人机协作内容丰富；作为领域例外保留。 | [官网](https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros) · [论文](https://ieeexplore.ieee.org/xpl/conhome/1000393/all-proceedings) |
| CVPR | IEEE/CVF Conference on Computer Vision and Pattern Recognition | 视觉、3D、VLM、具身感知 | A | A* | VLA 的视觉编码、3D 场景理解、视频生成与机器人感知的重要上游。 | [官网](https://cvpr.thecvf.com/) · [论文](https://openaccess.thecvf.com/menu) |
| ICCV | IEEE International Conference on Computer Vision | 视觉、视频、3D、VLM | A | A* | 与 CVPR 隔年互补，常见具身感知、视频世界模型和多模态方法。 | [官网](https://iccv.thecvf.com/) · [论文](https://openaccess.thecvf.com/menu) |
| ACL | Annual Meeting of the Association for Computational Linguistics | LLM、VLM、指令理解、Agent | A | A* | VLA 中语言对齐、规划、指令跟随和多模态推理的重要来源。 | [官网](https://www.aclweb.org/portal/) · [论文](https://aclanthology.org/venues/acl/) |
| MLSys | Conference on Machine Learning and Systems | AI Infra、训练/推理系统、编译 | — | — | AI Infra 的核心专项会议，覆盖训练、推理、调度、编译和模型服务；作为领域例外保留。 | [官网](https://mlsys.org/) · [论文](https://proceedings.mlsys.org/) |
| OSDI | USENIX Symposium on Operating Systems Design and Implementation | OS、分布式训练、存储、推理服务 | A | A* | 大规模 AI 系统、资源管理、数据系统与可靠服务的顶级系统会议。 | [官网/论文](https://www.usenix.org/conferences/byname/179) |
| SOSP | ACM Symposium on Operating Systems Principles | OS、分布式系统、AI 系统 | A | A* | 系统领域旗舰会议，适合追踪训练平台、资源隔离和分布式基础设施。 | [官网](https://sigops.org/s/conferences/sosp/) · [论文](https://dl.acm.org/conference/sosp/proceedings) |
| ASPLOS | ACM International Conference on Architectural Support for Programming Languages and Operating Systems | AI 系统、软硬协同、加速器 | A | A* | 连接体系结构、编译器和系统，特别适合 AI 推理与机器人计算栈。 | [官网](https://www.asplos-conference.org/) · [论文](https://dl.acm.org/conference/asplos/proceedings) |
| ISCA | ACM/IEEE International Symposium on Computer Architecture | AI 芯片、体系结构、推理加速 | A | A* | 计算机体系结构旗舰会议，覆盖 GPU/加速器、内存和高效推理。 | [官网](https://www.sigarch.org/isca/) · [论文](https://dl.acm.org/conference/isca/proceedings) |
| HPCA | IEEE International Symposium on High-Performance Computer Architecture | AI 加速、内存、系统优化 | A | A* | 高性能体系结构顶会，适合关注训练/推理效率与端侧机器人计算。 | [官网](https://www.hpca-conf.org/) · [论文](https://ieeexplore.ieee.org/xpl/conhome/1000368/all-proceedings) |
| MICRO | IEEE/ACM International Symposium on Microarchitecture | 微体系结构、AI 加速器、软硬协同 | A | A* | 聚焦处理器与加速器微体系结构，是 AI Infra 硬件方向的重要来源。 | [官网](https://www.microarch.org/micro/) · [论文](https://dl.acm.org/conference/micro/proceedings) |

### P1｜重点扩展（17）

| 简称 | 全称 | 重点标签 | CCF 2026 | CORE 2023 | 为什么值得跟踪 | 官方 / 论文入口 |
|---|---|---|---:|---:|---|---|
| AAAI | AAAI Conference on Artificial Intelligence | RL、规划、多智能体、通用 AI | A | A* | 覆盖面广，可补充 RL、规划和具身智能的综合型研究。 | [官网](https://aaai.org/conference/aaai/) · [论文](https://ojs.aaai.org/index.php/AAAI) |
| IJCAI | International Joint Conference on Artificial Intelligence | RL、规划、Agent、多模态 | A | A* | 综合 AI 顶会，适合追踪决策、规划和多智能体方法。 | [官网](https://www.ijcai.org/) · [论文](https://www.ijcai.org/proceedings/) |
| ECCV | European Conference on Computer Vision | 视觉、3D、视频、VLM | B | A* | 补充 CVPR/ICCV 的具身视觉、3D 表征和视频建模工作。 | [官网](https://eccv.ecva.net/) · [论文](https://www.ecva.net/papers.php) |
| EMNLP | Conference on Empirical Methods in Natural Language Processing | LLM、指令、Agent、多模态 | B | A* | 偏实证 NLP，适合补充 VLA 指令理解、Agent 与数据构造。 | [官网](https://www.emnlp.org/) · [论文](https://aclanthology.org/venues/emnlp/) |
| AAMAS | International Conference on Autonomous Agents and Multiagent Systems | 多智能体 RL、协作、博弈 | B | A* | 多机器人协作、MARL 和自主 Agent 的核心专项会议。 | [官网](https://www.ifaamas.org/) · [论文](https://dl.acm.org/conference/aamas/proceedings) |
| UAI | Conference on Uncertainty in Artificial Intelligence | 概率模型、因果、决策 | B | A | 为世界模型、不确定性估计和基于模型的决策提供理论工具。 | [官网](https://www.auai.org/) · [论文](https://proceedings.mlr.press/) |
| HRI | ACM/IEEE International Conference on Human-Robot Interaction | 遥操作、共享控制、人机协作 | B | A | 与遥操作、共享自治、用户研究和机器人交互直接相关。 | [官网](https://humanrobotinteraction.org/) · [论文](https://dl.acm.org/conference/hri/proceedings) |
| CHI | ACM Conference on Human Factors in Computing Systems | 交互、遥操作界面、用户研究 | A | A* | 适合研究遥操作界面、反馈设计、可用性和 human-in-the-loop 数据采集。 | [官网](https://chi.acm.org/) · [论文](https://dl.acm.org/conference/chi/proceedings) |
| CDC | IEEE Conference on Decision and Control | 控制理论、最优控制、WBC | — | A | WBC、稳定性、MPC 和学习控制的理论上游；作为领域例外保留。 | [官网](https://ieeecss.org/conferences/ieee-conference-decision-and-control) · [论文](https://ieeexplore.ieee.org/xpl/conhome/1000188/all-proceedings) |
| NSDI | USENIX Symposium on Networked Systems Design and Implementation | 分布式系统、网络、云 Infra | A | A* | 面向大规模训练/推理集群的网络、通信与分布式系统基础。 | [官网/论文](https://www.usenix.org/conferences/byname/178) |
| SIGCOMM | ACM Special Interest Group on Data Communication Conference | 数据中心网络、通信、集群 | A | A* | 关注训练集群通信、拥塞控制和高性能网络。 | [官网](https://conferences.sigcomm.org/sigcomm/) · [论文](https://dl.acm.org/conference/sigcomm/proceedings) |
| EuroSys | European Conference on Computer Systems | OS、分布式系统、云平台 | A | A | 系统研究覆盖均衡，常见资源管理、边缘系统和 ML 系统论文。 | [官网](https://www.eurosys.org/) · [论文](https://dl.acm.org/conference/eurosys/proceedings) |
| USENIX ATC | USENIX Annual Technical Conference | 通用系统、云、存储、Infra | A | A | 系统工程味较强，可补充 OSDI/SOSP 的实用型基础设施工作。 | [官网/论文](https://www.usenix.org/conferences/byname/131) |
| FAST | USENIX Conference on File and Storage Technologies | 数据管线、存储、检查点 | A | A | 与大模型数据加载、训练检查点和高吞吐存储直接相关。 | [官网/论文](https://www.usenix.org/conferences/byname/173) |
| SC | International Conference for High Performance Computing, Networking, Storage and Analysis | HPC、分布式训练、GPU 集群 | A | A | 超算与大规模训练基础设施的重要会议，覆盖网络、存储和加速计算。 | [官网](https://supercomputing.org/) · [论文](https://dl.acm.org/conference/sc/proceedings) |
| PPoPP | ACM SIGPLAN Symposium on Principles and Practice of Parallel Programming | 并行编程、编译、GPU | A | A* | 适合追踪训练/推理算子、并行运行时和编程系统。 | [官网](https://ppopp.org/) · [论文](https://dl.acm.org/conference/ppopp/proceedings) |
| DAC | Design Automation Conference | AI 芯片、EDA、硬件设计 | A | A | 面向专用加速器和设计自动化；当研究延伸到机器人端侧硬件时优先关注。 | [官网](https://www.dac.com/) · [论文](https://dl.acm.org/conference/dac/proceedings) |

## 核心期刊（14）

期刊分区会随年份和学科口径变化，且 JCR 完整分区通常需要订阅。本表不把无法公开复核的“一区”作为硬排序依据，而以 CCF 2026 和领域相关性为主。

### P0｜必跟踪（8）

| 简称 | 全称 | 重点标签 | CCF 2026 | 为什么值得跟踪 | 官方 / 论文入口 |
|---|---|---|---:|---|---|
| JMLR | Journal of Machine Learning Research | RL、ML、理论与方法 | A | 开放获取，适合系统阅读机器学习与强化学习的完整长文。 | [官网/论文](https://www.jmlr.org/) |
| TPAMI | IEEE Transactions on Pattern Analysis and Machine Intelligence | 视觉、VLM、表征学习 | A | 视觉与模式识别顶刊，常见比会议版本更完整的具身感知工作。 | [官网/论文](https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=34) |
| IJCV | International Journal of Computer Vision | 视觉、3D、视频、机器人感知 | A | 适合跟踪 3D 视觉、视频理解与机器人视觉的完整研究。 | [官网/论文](https://link.springer.com/journal/11263) |
| TNNLS | IEEE Transactions on Neural Networks and Learning Systems | 深度学习、RL、控制学习 | B | 覆盖神经网络、强化学习和学习控制，偏完整方法与理论分析。 | [官网/论文](https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=5962385) |
| TRO | IEEE Transactions on Robotics | 机器人、WBC、操作、遥操作 | B | 机器人领域核心期刊，特别适合跟踪系统完整、实验充分的工作。 | [官网/论文](https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=8860) |
| IJRR | The International Journal of Robotics Research | 机器人学习、控制、规划 | — | 机器人领域公认核心长文来源；作为领域例外保留。 | [官网/论文](https://journals.sagepub.com/home/ijr) |
| RA-L | IEEE Robotics and Automation Letters | 机器人、控制、具身系统 | — | 发文快、覆盖广，常与 ICRA/IROS 联动；适合持续追踪新机器人系统。 | [官网/论文](https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=7083369) |
| Science Robotics | Science Robotics | 具身智能、机器人硬件、真实系统 | — | 高选择性跨学科机器人期刊，强调真实系统能力与科学影响；作为领域例外保留。 | [官网/论文](https://www.science.org/journal/scirobotics) |

### P1｜重点扩展（6）

| 简称 | 全称 | 重点标签 | CCF 2026 | 为什么值得跟踪 | 官方 / 论文入口 |
|---|---|---|---:|---|---|
| AIJ | Artificial Intelligence | 通用 AI、规划、推理、Agent | A | 综合 AI 顶刊，补足会议论文较少展开的推理与规划内容。 | [官网/论文](https://www.sciencedirect.com/journal/artificial-intelligence) |
| Automatica | Automatica | 控制理论、MPC、学习控制 | — | WBC、稳定性与最优控制的重要理论来源；作为领域例外保留。 | [官网/论文](https://www.sciencedirect.com/journal/automatica) |
| TOCS | ACM Transactions on Computer Systems | OS、分布式系统、Infra | A | 系统顶刊，适合阅读比会议版更完整的设计、证明和评测。 | [官网/论文](https://dl.acm.org/journal/tocs) |
| TC | IEEE Transactions on Computers | 体系结构、加速器、计算系统 | A | 覆盖处理器、存储和 AI 加速系统，连接 Infra 与硬件。 | [官网/论文](https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=12) |
| TPDS | IEEE Transactions on Parallel and Distributed Systems | 分布式训练、并行系统、调度 | A | 适合跟踪大规模训练、并行运行时和分布式资源管理。 | [官网/论文](https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=71) |
| TON | IEEE/ACM Transactions on Networking | 网络、数据中心、集群通信 | A | 为大规模训练集群的网络与通信优化提供系统基础。 | [官网/论文](https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=90) |

## 推荐的论文下载顺序

1. **VLA / 世界模型 / 机器人学习**：CoRL → RSS → NeurIPS → ICML → ICLR → ICRA。
2. **强化学习 / 模仿学习**：NeurIPS → ICML → ICLR → CoRL → AAAI → AAMAS → UAI。
3. **WBC / 运动控制 / sim-to-real**：ICRA → IROS → RSS → TRO → IJRR → CDC → Automatica。
4. **遥操作 / 数据采集 / 人机协作**：ICRA → HRI → IROS → CHI → RA-L → TRO。
5. **VLA 的视觉与语言上游**：CVPR → ICCV/ECCV → ACL → EMNLP → TPAMI/IJCV。
6. **AI Infra / 训练与推理系统**：MLSys → OSDI/SOSP → ASPLOS → NSDI/SIGCOMM → ISCA/HPCA/MICRO → FAST/SC/PPoPP。

后续下载时建议为每篇论文保存统一元数据：`title`、`authors`、`year`、`venue`、`track`、`DOI/arXiv/OpenReview ID`、`official_url`、`pdf_url`、`code_url`、`tags`。优先从官方 proceedings 获取正式版本，再用 DBLP、OpenAlex 或 Semantic Scholar 补齐 DOI 和引用关系，用 arXiv/OpenReview 补充开放 PDF；按 DOI、规范化标题和作者年份组合去重。

## 评级与检索来源

- [CCF 推荐国际学术会议和期刊目录（第七版，2026）](https://www.ccf.org.cn/Academic_Evaluation/By_category/)
- [CCF 人工智能分类](https://www.ccf.org.cn/Academic_Evaluation/AI/)
- [CCF 计算机网络分类](https://www.ccf.org.cn/Academic_Evaluation/CN/)
- [CORE 2023 Conference Rankings](https://portal.core.edu.au/conf-ranks/?source=CORE2023)
- 各行所列会议、期刊官方网站与正式论文集入口

## 维护说明

- CCF、CORE 和期刊分区更新时，应保留评级年份，避免把不同版本混为同一结论。
- RSS 在 CORE 2023 显示为 `TBR`，历史版本曾为 A*；表中如实保留该状态。
- CoRL 在 CORE 2023 显示为 `Unranked`；因其与机器人学习、VLA 和具身智能高度相关，以“领域例外”保留。
- 新兴 venue 不因暂未评级而自动降级，也不据社区口碑伪造等级；仅以“领域例外”形式保留。
- 下载会议论文时区分主会 Full/Regular Paper、Workshop、Demo 和 Findings，避免统计口径混杂。
