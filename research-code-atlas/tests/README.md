# 验收

`python -X utf8 -m unittest discover -s tests -v`：标准库测试，19条指定调用ground truth、禁止/未知关系、步骤ID命名空间、全流程、证据负例、配置/多入口、源hash/新鲜度、SyntaxError/不执行源、预算、无论文及真实PDF文字分页。临时fixture副本在checks内，finally清理；不改原用户项目。

`build_demo.py --run-dir DIR`（参数必需，现有自有fixture报告目录；--help可选）为本任务已深读的19函数写卡片和教学论文对照。只用于已知fixture，不是自动解释任意项目的工具。没有额外参数；正常0，异常非零。Agent在真实项目必须按reading-protocol小批人工理解。

`ui_smoke.py --run-dir DIR --out CHECK_DIR`：两参数必需、目录路径、无默认；--help可选。Windows用包内Playwright/Chromium headless，直接file://，阻断非本地网络，实际点击源/步骤/调用/论文/实验/影响、切入口、hash历史、窄屏、注入安全。写browser-validation.json与desktop/narrow截图；成功0、失败3。浏览器资源已含，不下载。

上面python在Windows应为runtime/windows/python.exe，所有路径可绝对或cwd相对；UI仅在Windows验收。core在其他Python平台设计可用，不宣称已验收。结果见HANDOFF和checks，fixture证据不代替真实项目/论文验收。
