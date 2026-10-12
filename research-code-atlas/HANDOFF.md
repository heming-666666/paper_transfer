# Research Code Atlas 当前交付状态

WORKSPACE_ROOT=原机D:/Code；BUILD_ROOT=SKILL_SRC=本文件所在目录（原机D:/Code/byd_transfer/research-code-atlas）；PY=runtime/windows/python.exe；REPORTS_ROOT=本目录reports；PROJECT_ROOT=每次request指定只读目录；RUN_DIR=报告目录。本机路径不是迁移后的依赖。

- [x] 阶段0：通读最终规格、检查环境与Git边界、写PRD；原规格/前一个Skill不改。
- [x] 阶段1：规格指定fixture、19条ground truth边，保留先失败证据。
- [x] 阶段2：AST/tokenize抽取29符号、30条边、7条未解析调用；19条预期边全部通过。
- [x] 阶段3：5批、19张手工深读函数卡片；不可变步骤/逐事实证据校验。
- [x] 阶段4：论文映射、配置消费、值不一致和未消费项；真实两页PDF/无论文/空白PDF/错误引文负例。
- [x] 阶段5：assemble/validate/render通过；原源码matched→变更后stale检查通过。
- [x] 阶段6：file://离线HTML，28项真实Chromium交互检查通过，无外部请求或浏览器错误；桌面/窄屏截图已核看。
- [x] 阶段7：官方quick_validate通过；CLI/refs/README/许可/原始规格齐备。
- [x] 阶段8：fixture完整端到端；独立新上下文Agent仅读Skill和fixture生成17 done、2 partial报告，装配/校验/渲染均0；未提供真实研究项目。
- [x] 阶段9：异目录解释器、CLI、file://浏览器通过；完整性与工作区收尾收据见checks；创建阶段未全局安装/commit/push。

已复用并实际复制Python3.11.9、PyYAML6.0.3、Cytoscape3.34.3和本地Dagre；包含pypdf6.20.0、Playwright及Windows Chromium headless shell。没有源包外运行资源链接，不需要在线下载、Node构建或其他Skill。

## 可复验交付

- `runtime/windows/python.exe -X utf8 -m unittest discover -s tests -v`：8项通过；日志 `checks/logs/core-final.log`。
- `runtime/windows/python.exe tests/ui_smoke.py --run-dir examples/demo --out 新目录`：28项通过；`checks/browser-layout-final/browser-validation.json`及desktop/narrow截图。
- `runtime/windows/python.exe scripts/verify_bundle.py`：核对package-manifest.json的交付文件集合、字节数、SHA-256；checks/reports及缓存为验证产物，不计入发布清单。
- 路径迁移：`checks/relocation.json`；localhost服务/路径穿越检查：`checks/serve.json`；独立试用：`checks/forward-pass/README.md`及command-index.json。
- 独立Agent的CUA没有浏览器surface，因此该Agent未点击页面；主线程包内真实Chromium完成28项交互验收，另实际打开该Agent的报告并验证搜索→函数→源码导航，收据见checks/delivery-static.json。动态callable的不确定性保留为partial/unknown。
- 原始6份需求文档完整保存在 `references/source-spec`，仅prompt_final.md作最终规范；源码/论文的UTF-8快照哈希与原文件原始字节哈希分开保存。

## 边界与恢复

Windows x64本机与异目录验证通过；其他平台/另一台机器/宿主自动发现未验证。Python静态深读，不导入或执行目标，不提供runtime capture；扫描论文不自动OCR。真实研究项目及论文未提供，fixture通过不能代表真实训练或模型复现通过。图库采用已验证本地cytoscape-dagre2.5.0/dagre0.8.5代替规格4.0.1，理由及许可见PRD/portability。

使用时只生成新报告目录；目标源码只读。迁移复制整个本目录，读取SKILL.md；不覆盖目标已有Skill或报告。恢复本次交付时仅撤销本任务新增目录，保留用户后续文件。旁边model-inspector、用户reports和30项既有Git删除不改动、不暂存。最终Capture→Check与Claude清单核验结果另见 `checks/workspace-closeout.json`。

## GitHub交付补充｜2026-10-12

用户随后授权提交到heming-666666/byd_transfer的新分支1012，使用现有SSH密钥。范围仅本Skill发布清单和清单文件；本机checks/reports/缓存、其他Skill及用户既有删除不纳入。两项大二进制使用Git LFS，完整clone物化后核验PACKAGE_OK；网页ZIP的LFS指针不是完整离线包。分支提交/远端SHA及LFS核验结果保存本机checks/git-delivery-1012.json，按真实推送结果填，不将创建阶段收据当推送证据。
