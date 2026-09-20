# byd_transfer

精选 AI、具身智能、机器人与系统论文语料库。Venue 选择见
[`AI_SYSTEM_TOP_VENUES.md`](AI_SYSTEM_TOP_VENUES.md)，下载结果见
[`corpus/summary.md`](corpus/summary.md)，未下载论文见
[`corpus/NOT_DOWNLOADED.md`](corpus/NOT_DOWNLOADED.md)。

## 论文下载器

运行环境：Python 3.11+、`pdfinfo`，并需要访问论文官方站点和 OpenAlex。
脚本只下载公开可访问的合法 PDF，不绕过订阅或登录。

| 参数 | 必需 | 格式/默认值 | 说明 |
|---|---|---|---|
| `--discover` | 否 | 开关；默认与其他阶段一起运行 | 发现配置 venue 的目标年度论文并重建 manifest。 |
| `--download` | 否 | 开关；默认与其他阶段一起运行 | 下载 manifest 中待处理的开放 PDF。 |
| `--check` | 否 | 开关；默认与其他阶段一起运行 | 用 `pdfinfo` 复核本地 PDF 并生成报告。 |
| `--venue` | 否 | 可重复简称，如 `--venue CoRL` | 只处理指定 venue。 |
| `--year` | 否 | 四位年份 | 只处理配置中该目标年份的 venue。 |
| `--retry-failed` | 否 | 开关 | 重试 manifest 中此前失败的论文。 |
| `--max-workers` | 否 | 整数，默认 `4`，上限 `48` | PDF 下载并发数；这是单个协调进程的线程数。 |
| `--limit` | 否 | 非负整数 | 本次最多处理多少条待下载记录；按 venue 优先级并在 AI/系统领域间交替取一个 venue。 |
| `--reports` | 否 | 开关 | 只根据现有 manifest 重建 CSV、Markdown、校验和报告，不重新发现或下载。 |
| `--dry-run` | 否 | 开关 | 仅打印计划，不联网、不写输出。 |

```powershell
python tools/download_corpus.py --dry-run
python tools/download_corpus.py --discover --venue CoRL
python tools/download_corpus.py --download --check --venue CoRL --max-workers 4
python tools/download_corpus.py --retry-failed --download --check
```

PDF 保存到 `papers/<领域>/<venue>/<年份>/<哈希分片>/`，该目录只用于本地阅读并被
Git 忽略。仓库提交逐篇元数据、SHA-256、汇总和未下载原因，从而可以复现下载且不会
重新分发受版权限制的论文。

## 实际验证

```powershell
python -m unittest tests.test_download_corpus -v
python tools/download_corpus.py --dry-run
python tools/download_corpus.py --discover --venue CoRL
python tools/download_corpus.py --download --check --venue CoRL
```

## 生成 3000 篇阅读清单

从已下载的最新一届 AI 会议论文中选出 2500 篇，并从 Semantic Scholar 补充
2021–2026 年权威系统会议元数据后选出 500 篇：

```powershell
python -m tools.select_papers --dry-run
python -m tools.select_papers --refresh-systems
```

| 参数 | 必需 | 格式/默认值 | 说明 |
|---|---|---|---|
| `--ai-count` | 否 | 非负整数；默认 `2500` | AI 论文数量。 |
| `--systems-count` | 否 | 非负整数；默认 `500` | 系统论文数量。 |
| `--refresh-systems` | 否 | 开关 | 重新从 Semantic Scholar 获取系统会议候选元数据。 |
| `--dry-run` | 否 | 开关 | 只显示本地候选数量和目标，不联网、不写文件。 |

结果保存在 `selection/selected_papers.csv` 和
`selection/selected_papers.jsonl`；`selection/README.md` 汇总会议与主题数量。
系统论文补充阶段只获取公开元数据，不批量下载 PDF。

### 分批下载

`--limit` 按 AI 一个 venue、系统一个 venue 的顺序交替推进，并使用 venue 优先级处理待下载记录。示例：

```powershell
python tools/download_corpus.py --retry-failed --download --limit 1000 --max-workers 48
python tools/download_corpus.py --reports
```
