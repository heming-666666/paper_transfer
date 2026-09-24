# byd_transfer Best Paper 记录

截至 2026-09-24，按仓库 `corpus/venues.json` 中的会议配置整理 **27 个会议、96 条获奖论文记录**，包括论文标题、作者和官方奖项来源；能与仓库论文目录匹配的记录另附官方论文页。

- [AI 与机器人会议](best_papers/AI/README.md)：15 个会议，69 条记录
- [系统会议](best_papers/SYSTEMS/README.md)：12 个会议，27 条记录

## 收录口径

- 仅纳入 venues.json 中 `kind: conference` 的 27 个会议；8 个期刊条目不纳入。
- 收录官方 Best Paper、Best Student Paper、最佳论文分轨奖，以及直接授予论文的专项奖（如 Social Impact Award）。主奖缺失时，按官方名称记录 Outstanding Paper 或 Distinguished Paper。
- finalists、runner-up、honorable mention、Test of Time、People’s Choice 和非论文类奖项不计为获奖论文。
- 3 条会议状态说明保留在分类清单中（ICRA 2026、IROS 2025、HPCA 2026）；没有可核实的最终获奖名单时，不把候选论文算作获奖。
- CDC 2025 的 Best Student Paper 已按 IEEE CSS 官方历史页更新。

仓库的 `papers/` PDF 文件由 `.gitignore` 排除，本次发布包含可追溯的 Markdown 记录和外部官方论文链接，不打包 PDF。
