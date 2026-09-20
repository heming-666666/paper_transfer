#!/usr/bin/env python3
"""Select a reproducible 3,000-paper reading list from the local corpus and Semantic Scholar."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import time
import urllib.parse
import urllib.error
from collections import Counter
from pathlib import Path

from tools.download_corpus import MANIFEST, normalized, now, read_jsonl, request_json

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "selection"
SYSTEM_CACHE = OUTPUT / "system_candidates.jsonl"

AI_VENUE_WEIGHT = {
    "CoRL": 20, "RSS": 20, "ICRA": 18, "IROS": 16, "NeurIPS": 16,
    "ICML": 16, "ICLR": 16, "CVPR": 10, "ICCV": 10, "AAAI": 8,
    "IJCAI": 8, "AAMAS": 10, "HRI": 12, "CDC": 10, "ACL": 5, "EMNLP": 5,
}

SYSTEM_VENUES = {
    "MLSys": ("Conference on Machine Learning and Systems", 100),
    "OSDI": ("USENIX Symposium on Operating Systems Design and Implementation", 55),
    "SOSP": ("ACM Symposium on Operating Systems Principles", 40),
    "ASPLOS": ("Architectural Support for Programming Languages and Operating Systems", 55),
    "ISCA": ("International Symposium on Computer Architecture", 45),
    "HPCA": ("International Symposium on High-Performance Computer Architecture", 30),
    "MICRO": ("International Symposium on Microarchitecture", 30),
    "NSDI": ("USENIX Symposium on Networked Systems Design and Implementation", 30),
    "SIGCOMM": ("ACM SIGCOMM Conference", 20),
    "EuroSys": ("European Conference on Computer Systems", 30),
    "FAST": ("USENIX Conference on File and Storage Technologies", 15),
    "SC": ("International Conference for High Performance Computing Networking Storage and Analysis", 20),
    "PPoPP": ("ACM SIGPLAN Symposium on Principles and Practice of Parallel Programming", 20),
    "USENIX ATC": ("USENIX Annual Technical Conference", 10),
}

THEMES = {
    "Embodied/WBC": [
        r"\bembodied\b", r"whole[- ]body", r"\bwbc\b", r"humanoid", r"locomot", r"legged",
        r"biped", r"quadruped", r"dexter", r"robot(?:ic)? manipulation", r"motion control",
    ],
    "Teleoperation": [r"teleoperat", r"telepresence", r"shared autonomy", r"shared control", r"retarget"],
    "VLA": [r"vision[- ]language[- ]action", r"\bvla\b", r"robot foundation model", r"generalist robot"],
    "World Model": [r"world model", r"dynamics model", r"video prediction", r"model[- ]based control", r"latent dynamics"],
    "Agent RL": [r"reinforcement learning", r"\boffline rl\b", r"\bmarl\b", r"multi[- ]agent", r"policy optimization",
                 r"reward model", r"imitation learning", r"behavior cloning", r"autonomous agent", r"agentic"],
    "Robot Learning": [r"robot learning", r"robot policy", r"visuomotor", r"sim[- ]to[- ]real", r"robot demonstration",
                       r"grasp", r"manipulation policy", r"tactile"],
    "AI Infra": [r"llm inference", r"model serving", r"distributed training", r"deep learning system", r"machine learning system",
                 r"gpu", r"accelerator", r"tensor compiler", r"quantization", r"parallel training", r"checkpoint",
                 r"collective communication", r"mixture[- ]of[- ]experts", r"memory optimization", r"\bdnn\b",
                 r"neural network training", r"model parallel", r"ml serving", r"serving system", r"vector search", r"smartnic"],
    "Supporting Perception": [r"3d scene", r"3d reconstruction", r"visual navigation", r"vision[- ]language", r"multimodal",
                              r"video generation", r"scene understanding", r"object tracking", r"depth estimation"],
    "Systems": [r"distributed system", r"operating system", r"storage", r"file system", r"datacenter", r"data center",
                r"computer network", r"network(?:ing)? system", r"congestion control", r"scheduler", r"scheduling",
                r"compiler", r"distributed runtime", r"computer architecture", r"processor architecture",
                r"microarchitecture", r"cache", r"memory system", r"parallel computing", r"cloud", r"serverless"],
}


def text_of(row: dict) -> str:
    return f"{row.get('title', '')} {row.get('abstract', '')}".lower()


def classify_themes(row: dict) -> list[str]:
    text = text_of(row)
    return [name for name, patterns in THEMES.items() if any(re.search(pattern, text) for pattern in patterns)]


def paper_score(row: dict, domain: str) -> float:
    themes = classify_themes(row)
    if domain == "AI" and not themes:
        return -1
    score = 18 * len(themes)
    title = row.get("title", "").lower()
    score += 9 * sum(any(re.search(pattern, title) for pattern in patterns) for patterns in THEMES.values())
    if domain == "AI":
        score += AI_VENUE_WEIGHT.get(row.get("venue", ""), 4)
    else:
        score += 12 if "AI Infra" in themes else 5 if "Systems" in themes else 0
    score += min(10, math.log2(1 + int(row.get("cited_by_count") or 0)))
    score += max(0, int(row.get("year") or 0) - 2020) * 0.25
    return round(score, 3)


def dedupe_key(row: dict) -> str:
    doi = str(row.get("doi") or "").lower().replace("https://doi.org/", "")
    return f"doi:{doi}" if doi else f"title:{normalized(row.get('title', ''))}"


def is_main_paper(row: dict) -> bool:
    title = row.get("title", "").lower()
    return not re.search(r"\b(proceedings|workshop|tutorial|doctoral consortium|demo(?:nstration)? track)\b", title)


def choose_exact(rows: list[dict], count: int, domain: str) -> list[dict]:
    unique = {}
    for row in rows:
        key = dedupe_key(row)
        candidate = dict(row)
        candidate["themes"] = classify_themes(candidate)
        candidate["selection_score"] = paper_score(candidate, domain)
        if key not in unique or candidate["selection_score"] > unique[key]["selection_score"]:
            unique[key] = candidate
    ranked = sorted(unique.values(), key=lambda row: (-row["selection_score"], -int(row.get("cited_by_count") or 0),
                                                      row.get("venue", ""), row.get("title", "")))
    if len(ranked) < count:
        raise ValueError(f"only {len(ranked)} unique {domain} candidates for requested {count}")
    return ranked[:count]


def semantic_scholar_record(work: dict, venue: str) -> dict:
    authors = "; ".join(item.get("name", "") for item in work.get("authors", []))
    ids = work.get("externalIds") or {}
    pdf = work.get("openAccessPdf") or {}
    doi = ids.get("DOI", "")
    return {
        "domain": "SYSTEMS", "venue": venue, "year": work.get("year"), "kind": "conference",
        "title": work.get("title") or "Untitled", "authors": authors, "track": "main",
        "stable_id": f"doi:{doi}" if doi else work.get("paperId", ""), "doi": doi,
        "openalex_id": "", "landing_url": work.get("url", ""), "pdf_url": pdf.get("url") or "",
        "relative_path": "", "abstract": work.get("abstract") or "",
        "cited_by_count": work.get("citationCount", 0), "source": "Semantic Scholar",
    }


def fetch_system_candidates() -> list[dict]:
    rows = []
    fields = "title,abstract,authors,year,venue,externalIds,url,citationCount,openAccessPdf"
    query_text = "system | distributed | network | storage | architecture | parallel | compiler | memory | machine learning | inference | training"
    for acronym, (name, quota) in SYSTEM_VENUES.items():
        token = None
        venue_rows = []
        limit = max(200, quota * 5)
        while len(venue_rows) < limit:
            params = {"query": query_text, "venue": acronym, "year": "2021-2026", "fields": fields}
            if token:
                params["token"] = token
            url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + urllib.parse.urlencode(params)
            try:
                payload = request_json(url)
            except urllib.error.HTTPError as error:
                if error.code != 429:
                    raise
                completed = subprocess.run(
                    ["curl.exe", "-L", "--fail", "--silent", "--show-error", url],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
                )
                if completed.returncode:
                    raise RuntimeError(f"Semantic Scholar curl fallback failed: {completed.stderr.strip()}") from error
                payload = json.loads(completed.stdout)
            batch = payload.get("results", [])
            if not batch:
                batch = payload.get("data", [])
            venue_rows.extend(semantic_scholar_record(work, acronym) for work in batch)
            token = payload.get("token")
            if not token or not batch:
                break
            time.sleep(0.25)
        print(f"{acronym}: {len(venue_rows)} candidates", flush=True)
        rows.extend(venue_rows)
    OUTPUT.mkdir(exist_ok=True)
    with SYSTEM_CACHE.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return rows


def select_systems(rows: list[dict], count: int) -> list[dict]:
    by_venue = {venue: [] for venue in SYSTEM_VENUES}
    for row in rows:
        if not is_main_paper(row):
            continue
        if row.get("venue") in by_venue:
            by_venue[row["venue"]].append(row)
    selected, used = [], set()
    scale = count / sum(quota for _, quota in SYSTEM_VENUES.values())
    for venue, (_, quota) in SYSTEM_VENUES.items():
        target = round(quota * scale)
        choices = choose_exact(by_venue[venue], min(target, len(by_venue[venue])), "SYSTEMS")
        selected.extend(choices)
        used.update(dedupe_key(row) for row in choices)
    if len(selected) < count:
        remaining = [row for row in rows if dedupe_key(row) not in used]
        selected.extend(choose_exact(remaining, count - len(selected), "SYSTEMS"))
    return sorted(selected[:count], key=lambda row: (row["venue"], -row["selection_score"], row["title"]))


def write_outputs(ai: list[dict], systems: list[dict]) -> None:
    OUTPUT.mkdir(exist_ok=True)
    rows = []
    for domain_rows in (ai, systems):
        for row in domain_rows:
            item = dict(row)
            item["themes"] = "; ".join(item.get("themes", []))
            item["priority"] = "核心" if item["selection_score"] >= 65 else "重要" if item["selection_score"] >= 40 else "扩展"
            rows.append(item)
    fields = ["domain", "venue", "year", "title", "authors", "themes", "priority", "selection_score",
              "abstract", "doi", "openalex_id", "landing_url", "pdf_url", "relative_path", "stable_id", "source"]
    with (OUTPUT / "selected_papers.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    with (OUTPUT / "selected_papers.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    venue_counts = Counter((row["domain"], row["venue"]) for row in rows)
    theme_counts = Counter(theme.strip() for row in rows for theme in row["themes"].split(";") if theme.strip())
    lines = ["# 3000 篇论文阅读清单", "", f"> 生成时间：{now()}", "",
             f"- AI：{len(ai)} 篇", f"- 系统：{len(systems)} 篇", f"- 总计：{len(rows)} 篇", "",
             "## 按会议统计", "", "| 领域 | 会议 | 数量 |", "|---|---|---:|"]
    lines += [f"| {domain} | {venue} | {total} |" for (domain, venue), total in sorted(venue_counts.items())]
    lines += ["", "## 按主题统计", "", "| 主题 | 数量 |", "|---|---:|"]
    lines += [f"| {theme} | {total} |" for theme, total in theme_counts.most_common()]
    lines += ["", "## 文件", "", "- `selected_papers.csv`：便于 Excel 查看。",
              "- `selected_papers.jsonl`：保留结构化字段，供后续逐篇简析。",
              "- `system_candidates.jsonl`：系统会议候选元数据缓存。", ""]
    (OUTPUT / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-count", type=int, default=2500)
    parser.add_argument("--systems-count", type=int, default=500)
    parser.add_argument("--refresh-systems", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    local = read_jsonl(MANIFEST)
    ai_candidates = [row for row in local if row.get("domain") == "AI" and row.get("kind") == "conference"
                     and row.get("status") == "downloaded"]
    if args.dry_run:
        print(json.dumps({"ai_candidates": len(ai_candidates), "ai_target": args.ai_count,
                          "systems_target": args.systems_count, "system_cache": SYSTEM_CACHE.exists()}, ensure_ascii=False))
        return 0
    ai = choose_exact(ai_candidates, args.ai_count, "AI")
    if args.refresh_systems or not SYSTEM_CACHE.exists():
        system_candidates = fetch_system_candidates()
    else:
        system_candidates = read_jsonl(SYSTEM_CACHE)
    local_systems = [row for row in local if row.get("domain") == "SYSTEMS" and row.get("kind") == "conference"
                     and row.get("status") == "downloaded"]
    systems = select_systems(local_systems + system_candidates, args.systems_count)
    write_outputs(ai, systems)
    print(f"Selected AI={len(ai)} SYSTEMS={len(systems)} TOTAL={len(ai)+len(systems)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
