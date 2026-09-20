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
