# 工具说明

## `build_review.py`

根据 `selection/selected_papers.csv` 生成逐篇快速理解和会议级汇总 Markdown。对缺失索引摘要但有本地 PDF 的论文，读取 PDF 前三页尝试补抽摘要；无法补齐时明确标注为标题/主题推断。

| 参数 | 必需 | 格式/默认值 | 说明 |
|---|---|---|---|
| `--input` | 否 | 文件路径；默认 `selection/selected_papers.csv` | 3000 篇论文清单。 |
| `--output-dir` | 否 | 目录路径；默认 `selection/reports` | Markdown、缓存和清单输出目录。 |
| `--no-pdf-extract` | 否 | 开关 | 不读取本地 PDF，只使用索引摘要或标题/主题标签。 |

示例：

```powershell
python -m tools.build_review
```

脚本本身只生成分析 Markdown 和中间缓存；PDF 使用 `markdown-to-pdf` skill 的脚本转换，并使用 `pdf` skill 的渲染检查流程验证。

## `release_papers.ps1`

把 `papers/` 下的完整 PDF 语料按容量分成 tar 分卷并上传到 GitHub Release。PDF 不写入 Git 历史；分卷默认约 1500 MB，便于低于 GitHub Release 的单附件限制。脚本使用 Git Credential Manager 中已有的 GitHub 凭据和指定代理，重复运行会跳过已完成分卷。未完成下载的 `*.part` 文件不会上传。

| 参数 | 必需 | 格式/默认值 | 说明 |
|---|---|---|---|
| `-Repository` | 否 | `owner/name`；默认 `heming-666666/byd_transfer` | GitHub 仓库。 |
| `-ReleaseTag` | 否 | Git tag；默认 `papers-2026-09-22` | Release 和附件前缀；重复运行使用同一 Release。 |
| `-ArchiveDirectory` | 否 | Windows 路径；默认仓库同级 `byd_release_work` | tar 分卷、文件列表和完成标记的本地目录。 |
| `-VolumeSizeMB` | 否 | 整数 `500–1900`；默认 `1500` | 每个分卷的容量上限；单位 MB。 |
| `-Proxy` | 否 | URL；默认 `http://127.0.0.1:7897` | GitHub API 和附件上传使用的 HTTP 代理。 |
| `-CheckOnly` | 否 | 开关 | 只统计 PDF、容量和 `.part` 数量，不创建 Release、不写分卷、不上传。 |

示例：

```powershell
pwsh -NoProfile -File tools\release_papers.ps1 -CheckOnly
pwsh -NoProfile -File tools\release_papers.ps1 -ReleaseTag papers-2026-09-22 -ArchiveDirectory D:\Code\byd_release_work
```

成功后，将同一 Release 的所有 `papers-<tag>-NNN.tar` 下载到同一目录，从仓库根目录逐个运行 `tar -xf <asset>.tar` 即可还原 `papers/`。实际上传前应确认论文具有可重新分发的许可；脚本只验证文件和远端附件大小，不验证版权。
