#!/usr/bin/env python3
"""Build a traceable, compact Markdown report for the selected paper set."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover - the environment used for the report has fitz
    fitz = None

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "selection"
DEFAULT_INPUT = SELECTION / "selected_papers.csv"
DEFAULT_OUTPUT = SELECTION / "reports"

THEME_GUIDANCE = {
    "Embodied/WBC": "具身任务中的感知、动作生成、全身协调或运动控制",
    "Teleoperation": "人类示范、远程操作、共享自治或动作重定向",
    "VLA": "视觉、语言条件与机器人动作策略之间的对齐",
    "World Model": "环境动力学、视频预测、潜变量状态或模型式决策",
    "Agent RL": "强化学习、模仿学习、规划、奖励或多智能体决策",
    "Robot Learning": "机器人数据、策略学习、操作、触觉或 sim-to-real",
    "AI Infra": "训练、推理、服务、编译、调度、通信或 AI 加速",
    "Supporting Perception": "3D、视频、多模态视觉或具身感知支撑能力",
    "Systems": "操作系统、分布式系统、网络、存储、架构或并行运行时",
}


def clean_text(value: object) -> str:
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def join_pdf_linebreaks(text: str) -> str:
    return re.sub(r"(?<=[A-Za-z])-\s+(?=[a-z])", "", text)


def markdown_text(value: object) -> str:
    """Keep paper-provided text literal so LaTeX-like titles cannot break PDF conversion."""
    value = clean_text(value).replace("\\", "").replace("$", "")
    return value.replace("_", r"\_").replace("`", r"\`")


def abstract_sentences(text: str, limit: int = 2) -> str:
    text = markdown_text(text)
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    result = " ".join(parts[:limit]).strip()
    return result[:1000].rstrip() + ("..." if len(result) > 1000 else "")


def slug_heading(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", value).strip("-") or "report"


def pdf_abstract(path: Path) -> str:
    if fitz is None or not path.exists():
        return ""
    try:
        with fitz.open(path) as document:
            text = "\n".join(page.get_text("text") for page in document[:3])
    except (OSError, RuntimeError):
        return ""
    text = join_pdf_linebreaks(clean_text(text))
    match = re.search(
        r"\babstract\b\s*[:.]?\s*(.*?)(?=\b(?:keywords?|index terms|introduction)\b)",
        text,
        flags=re.IGNORECASE,
    )
    if match and len(match.group(1).strip()) >= 80:
        return match.group(1).strip()
    return text[:1200].strip()


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def enrich_rows(rows: list[dict], extract_pdf: bool = True) -> tuple[list[dict], Counter]:
    evidence = Counter()
    for row in rows:
        row["title"] = clean_text(row.get("title"))
        row["authors"] = clean_text(row.get("authors"))
        row["themes"] = clean_text(row.get("themes"))
        abstract = clean_text(row.get("abstract"))
        if abstract:
            row["analysis_abstract"] = abstract
            row["evidence_level"] = "索引摘要"
        elif extract_pdf and row.get("relative_path"):
            path = ROOT / row["relative_path"]
            abstract = pdf_abstract(path)
            if abstract:
                row["analysis_abstract"] = abstract
                row["evidence_level"] = "本地 PDF 前页"
            else:
                row["analysis_abstract"] = ""
                row["evidence_level"] = "标题/主题推断"
        else:
            row["analysis_abstract"] = ""
            row["evidence_level"] = "标题/主题推断"
        evidence[row["evidence_level"]] += 1
    return rows, evidence


def paper_note(row: dict, abstract: str, evidence: str) -> str:
    themes = [item.strip() for item in row.get("themes", "").split(";") if item.strip()]
    theme_text = "、".join(themes) or "未标注主题"
    if abstract:
        understanding = abstract_sentences(abstract)
    else:
        understanding = (
            f"摘要未随索引或本地 PDF 前页提供；根据标题与主题标签，本文关注"
            f"{markdown_text(theme_text)}相关问题。以下判断仅用于快速阅读排序，不能替代全文核对。"
        )
    focus = markdown_text("；".join(THEME_GUIDANCE.get(theme, theme) for theme in themes[:3]))
    return (
        f"**论文**：{markdown_text(row.get('title', '未命名论文'))}\n\n"
        f"**快速理解**：{understanding}\n\n"
        f"**关注点**：{focus or '需打开全文确认研究问题、方法和实验边界'}。\n\n"
        f"**证据层级**：{evidence}。"
    )


def theme_counts(rows: list[dict]) -> Counter:
    return Counter(theme.strip() for row in rows for theme in row.get("themes", "").split(";") if theme.strip())


def conference_summary(rows: list[dict]) -> str:
    themes = theme_counts(rows)
    top = sorted(rows, key=lambda row: (-float(row.get("selection_score") or 0), row["title"]))[:5]
    theme_line = "、".join(f"{name}（{count}）" for name, count in themes.most_common()) or "无主题标签"
    lines = [
        f"本会议纳入 **{len(rows)}** 篇。自动主题统计为：{theme_line}。",
        "这些统计用于组织阅读顺序，不能单独证明论文结论或实验优越性。",
        "",
        "**优先阅读候选**：",
    ]
    lines.extend(f"- {markdown_text(row['title'])}（优先级分数 {row.get('selection_score', '')}）" for row in top)
    return "\n".join(lines)


def report_markdown(rows: list[dict], evidence: Counter) -> str:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("domain", "UNKNOWN"), row.get("venue", "UNKNOWN"))].append(row)
    total_themes = theme_counts(rows)
    lines = [
        "# 3000篇 AI、具身智能与系统论文快速分析汇总",
        "",
        "> 本报告基于已锁定的 3000 篇论文清单生成。逐篇内容是快速理解入口，不能替代全文精读。",
        "",
        "## 1. 阅读范围与证据边界",
        "",
        f"- 论文总数：{len(rows)} 篇。",
        f"- AI：{sum(row.get('domain') == 'AI' for row in rows)} 篇；系统：{sum(row.get('domain') == 'SYSTEMS' for row in rows)} 篇。",
        f"- 证据层级：索引摘要 {evidence['索引摘要']} 篇，本地 PDF 前页 {evidence['本地 PDF 前页']} 篇，标题/主题推断 {evidence['标题/主题推断']} 篇。",
        "- 摘要抽取保留一至两句，方法、指标、数据集和局限性需要在后续全文阶段复核。",
        "- 主题来自清单筛选器的可复核标签；一篇论文可以属于多个主题。",
        "",
        "## 2. 全局主题分布",
        "",
        "| 主题 | 论文数 | 主题含义 |",
        "|---|---:|---|",
    ]
    lines.extend(f"| {theme} | {count} | {THEME_GUIDANCE.get(theme, '')} |" for theme, count in total_themes.most_common())
    lines += ["", "## 3. 按会议分析", ""]
    for (domain, venue), venue_rows in sorted(grouped.items()):
        lines += [f"### {domain} · {venue}", "", conference_summary(venue_rows), ""]
        for row in sorted(venue_rows, key=lambda item: (-float(item.get("selection_score") or 0), item["title"])):
            authors = row.get("authors") or "作者信息未提供"
            link = row.get("landing_url") or row.get("pdf_url") or ""
            source = f"[来源]({link})" if link else "来源链接未提供"
            lines += [
                f"#### {markdown_text(row['title'])}",
                "",
                f"- 作者：{markdown_text(authors)}",
                f"- 年份：{row.get('year', '')}；主题：{row.get('themes') or '未标注主题'}；优先级：{row.get('priority', '')}",
                f"- {source}",
                "",
                paper_note(row, row.get("analysis_abstract", ""), row.get("evidence_level", "标题/主题推断")),
                "",
            ]
    lines += [
        "## 4. 后续精读顺序",
        "",
        "1. 先读同时命中 VLA、World Model、Embodied/WBC、Teleoperation 的具身论文。",
        "2. 再读 Agent RL、Robot Learning 与 Supporting Perception 的高优先级论文。",
        "3. 最后按 AI Infra、Systems、分布式训练、推理服务、架构和存储路线阅读系统论文。",
        "",
        "## 5. 使用说明",
        "",
        "本报告中的“快速理解”主要来自摘要或本地 PDF 前页；没有摘要的记录明确标出推断边界。后续若需要论文级复现、公式核对、代码分析或实验结果比较，应以原始 PDF、官方代码和固定版本为证据。",
        "",
    ]
    return "\n".join(lines)


def write_cache(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-pdf-extract", action="store_true")
    args = parser.parse_args()
    rows, evidence = enrich_rows(load_rows(args.input), extract_pdf=not args.no_pdf_extract)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    markdown = report_markdown(rows, evidence)
    (args.output_dir / "analysis_3000_papers.md").write_text(markdown, encoding="utf-8", newline="\n")
    write_cache(rows, args.output_dir / "analysis_cache.jsonl")
    (args.output_dir / "analysis_manifest.json").write_text(
        json.dumps({"papers": len(rows), "evidence": evidence, "input": str(args.input)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"Wrote {len(rows)} paper notes to {args.output_dir / 'analysis_3000_papers.md'}")
    print("Evidence:", json.dumps(evidence, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
