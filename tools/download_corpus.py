#!/usr/bin/env python3
"""Discover and download the latest selected AI/systems papers legally available online."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
PAPERS = ROOT / "papers"
MANIFEST = CORPUS / "manifest.jsonl"
FAILURE_FIELDS = (
    "domain", "venue", "year", "title", "authors", "track", "stable_id",
    "landing_url", "pdf_url", "status", "failure_reason", "attempts", "last_attempt",
)
USER_AGENT = "byd-transfer-paper-corpus/1.0 (research corpus; contact unavailable)"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def request_json(url: str, retries: int = 1) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == retries:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")


def request_text(url: str, retries: int = 1) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def source_score(item: dict, venue: dict) -> tuple[int, int]:
    display = normalized(item.get("display_name", ""))
    target = normalized(venue["name"])
    acronym = normalized(venue["venue"])
    exact = int(display == target or display == acronym)
    overlap = len(set(display.split()) & set(target.split()))
    return exact, overlap


def resolve_source(venue: dict) -> dict | None:
    if venue.get("issn"):
        url = "https://api.openalex.org/sources/issn:" + urllib.parse.quote(venue["issn"])
        try:
            return request_json(url)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    query = urllib.parse.quote(venue["name"])
    payload = request_json(f"https://api.openalex.org/sources?search={query}&per_page=10")
    candidates = payload.get("results", [])
    return max(candidates, key=lambda item: source_score(item, venue), default=None)


def abstract_text(index: dict | None) -> str:
    if not index:
        return ""
    words = {}
    for word, positions in index.items():
        for position in positions:
            words[position] = word
    return " ".join(words[position] for position in sorted(words))


def pdf_candidates(work: dict) -> list[str]:
    result = []
    for location in [work.get("best_oa_location"), work.get("primary_location"), *work.get("locations", [])]:
        if not location:
            continue
        for key in ("pdf_url", "landing_page_url"):
            value = location.get(key)
            if value and (key == "pdf_url" or value.lower().endswith(".pdf")) and value not in result:
                result.append(value)
    return result


def work_record(work: dict, venue: dict) -> dict:
    authors = "; ".join(a.get("author", {}).get("display_name", "") for a in work.get("authorships", []))
    ids = work.get("ids") or {}
    stable_id = ids.get("doi") or ids.get("openalex") or work.get("id", "")
    candidates = pdf_candidates(work)
    primary = work.get("primary_location") or {}
    return {
        "domain": venue["domain"], "venue": venue["venue"], "year": venue["year"],
        "kind": venue["kind"], "title": work.get("title") or "Untitled", "authors": authors,
        "track": "main" if venue["kind"] == "conference" else "journal",
        "stable_id": stable_id, "doi": ids.get("doi", ""), "openalex_id": ids.get("openalex", ""),
        "landing_url": primary.get("landing_page_url") or work.get("doi") or work.get("id", ""),
        "pdf_candidates": candidates, "pdf_url": candidates[0] if candidates else "",
        "abstract": abstract_text(work.get("abstract_inverted_index")), "status": "pending",
        "failure_reason": "", "attempts": 0, "last_attempt": "", "relative_path": "",
        "bytes": 0, "sha256": "", "source_id": venue.get("source_id", ""),
    }


def bib_value(entry: str, field: str) -> str:
    match = re.search(rf"(?ims)^\s*{re.escape(field)}\s*=\s*[{{\"](.*?)[}}\"]\s*,?\s*$", entry)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def discover_bib(venue: dict) -> tuple[list[dict], dict]:
    text = request_text(venue["bib_url"])
    entries = re.split(r"(?=@(?:InProceedings|article)\s*\{)", text, flags=re.I)
    rows = []
    for entry in entries:
        key = re.search(r"@\w+\s*\{\s*([^,]+)", entry, re.I)
        title = bib_value(entry, "title")
        if not key or not title:
            continue
        paper_key = key.group(1).strip()
        landing = bib_value(entry, "url")
        pdf = bib_value(entry, "pdf")
        authors = bib_value(entry, "author")
        if not authors and not pdf:
            continue
        rows.append({
            "domain": venue["domain"], "venue": venue["venue"], "year": venue["year"],
            "kind": venue["kind"], "title": title.replace("{", "").replace("}", ""),
            "authors": authors.replace(" and ", "; "), "track": "main",
            "stable_id": paper_key, "doi": "", "openalex_id": "", "landing_url": landing,
            "pdf_candidates": [pdf] if pdf else [], "pdf_url": pdf, "abstract": bib_value(entry, "abstract"),
            "status": "pending", "failure_reason": "", "attempts": 0, "last_attempt": "",
            "relative_path": "", "bytes": 0, "sha256": "", "source_id": venue["bib_url"],
        })
    info = {"venue": venue["venue"], "year": venue["year"], "source_id": venue["bib_url"],
            "source_name": "official PMLR BibTeX", "expected": len(rows), "discovered": len(rows), "error": ""}
    return rows, info


def official_record(venue: dict, title: str, landing: str, pdf: str, stable_id: str) -> dict:
    return {
        "domain": venue["domain"], "venue": venue["venue"], "year": venue["year"],
        "kind": venue["kind"], "title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(),
        "authors": "", "track": "main", "stable_id": stable_id, "doi": "", "openalex_id": "",
        "landing_url": landing, "pdf_candidates": [pdf] if pdf else [], "pdf_url": pdf,
        "abstract": "", "status": "pending", "failure_reason": "", "attempts": 0,
        "last_attempt": "", "relative_path": "", "bytes": 0, "sha256": "",
        "source_id": venue["index_url"],
    }


def discover_official_html(venue: dict) -> tuple[list[dict], dict]:
    base = venue["index_url"]
    kind = venue["html_type"]
    text = request_text(base)
    rows = []
    if kind == "proceedings":
        for href, title in re.findall(r'<a[^>]+title=["\']paper title["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
            landing = urllib.parse.urljoin(base, href)
            pdf = re.sub(r"-Abstract-[^.]+\.html$", "-Paper-Conference.pdf", landing).replace("/hash/", "/file/")
            rows.append(official_record(venue, title, landing, pdf, href))
    elif kind == "cvf":
        text = request_text(base + ("&" if "?" in base else "?") + "day=all")
        for href, title in re.findall(r'<a[^>]+href=["\']([^"\']+_paper\.html)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
            landing = urllib.parse.urljoin(base, href)
            pdf = landing.replace("/html/", "/papers/").replace("_paper.html", "_paper.pdf")
            rows.append(official_record(venue, title, landing, pdf, href))
    elif kind == "acl":
        prefix = venue["paper_prefix"]
        pattern = rf'<a[^>]+href=["\']?(/?{re.escape(prefix)}\.(\d+)/)["\']?[^>]*>(.*?)</a>'
        for href, number, title in re.findall(pattern, text, re.I | re.S):
            if number == "0":
                continue
            landing = urllib.parse.urljoin(base, href)
            pdf = f"https://aclanthology.org/{prefix}.{number}.pdf"
            rows.append(official_record(venue, title, landing, pdf, f"{prefix}.{number}"))
    elif kind == "usenix_full":
        match = re.search(r'href=["\']([^"\']+full[-_]proceedings\.pdf)["\']', text, re.I)
        if match:
            pdf = urllib.parse.urljoin(base, match.group(1))
            rows.append(official_record(venue, f"{venue['venue']} {venue['year']} Full Proceedings",
                                        base, pdf, f"{venue['venue']}-{venue['year']}-full-proceedings"))
        else:
            pattern = rf'<a[^>]+href=["\']([^"\']+/conference/{venue["venue"].lower()}\d+/presentation/[^"\']+)["\'][^>]*>(.*?)</a>'
            for href, title in re.findall(pattern, text, re.I | re.S):
                if "keynote" in href.lower():
                    continue
                landing = urllib.parse.urljoin(base, href)
                rows.append(official_record(venue, title, landing, "", href))
    elif kind == "jmlr":
        pattern = r"<dt>(.*?)</dt>.*?<a href='([^']+\.html)'>abs</a>.*?<a[^>]+href='([^']+\.pdf)'>pdf</a>"
        for title, landing_href, pdf_href in re.findall(pattern, text, re.I | re.S):
            landing = urllib.parse.urljoin(base, landing_href)
            pdf = urllib.parse.urljoin(base, pdf_href)
            rows.append(official_record(venue, title, landing, pdf, landing_href))
    unique = {row["stable_id"]: row for row in rows}
    rows = list(unique.values())
    info = {"venue": venue["venue"], "year": venue["year"], "source_id": base,
            "source_name": "official proceedings", "expected": len(rows),
            "discovered": len(rows), "error": "" if rows else "official_index_empty"}
    return rows, info


def discover_venue(venue: dict) -> tuple[list[dict], dict]:
    if venue.get("bib_url"):
        return discover_bib(venue)
    if venue.get("index_url"):
        return discover_official_html(venue)
    source = resolve_source(venue)
    if not source:
        return [], {"venue": venue["venue"], "year": venue["year"], "error": "source_not_found"}
    venue = dict(venue, source_id=source["id"].rsplit("/", 1)[-1], source_name=source.get("display_name", ""))
    filters = f"primary_location.source.id:{venue['source_id']},publication_year:{venue['year']}"
    selected = "id,doi,title,publication_year,authorships,ids,primary_location,best_oa_location,locations,abstract_inverted_index"
    cursor = "*"
    rows = []
    expected = None
    while cursor:
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
            "filter": filters, "cursor": cursor, "per_page": 100, "select": selected,
        })
        payload = request_json(url)
        expected = payload.get("meta", {}).get("count", expected)
        if expected is not None and expected > 10000:
            raise RuntimeError(f"unsafe result count {expected}; likely wrong source match")
        rows.extend(work_record(work, venue) for work in payload.get("results", []))
        cursor = payload.get("meta", {}).get("next_cursor")
        if not payload.get("results"):
            break
        time.sleep(0.12)
    info = {"venue": venue["venue"], "year": venue["year"], "source_id": venue["source_id"],
            "source_name": venue["source_name"], "expected": expected, "discovered": len(rows), "error": ""}
    return rows, info


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def interleave_by_venue(items: list[tuple[int, dict]]) -> list[tuple[int, dict]]:
    grouped = defaultdict(list)
    for item in items:
        grouped[item[1]["venue"]].append(item)
    queues = [deque(group) for group in grouped.values()]
    result = []
    while queues:
        remaining = []
        for queue in queues:
            result.append(queue.popleft())
            if queue:
                remaining.append(queue)
        queues = remaining
    return result


def slug(value: str, limit: int = 90) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return (value or "paper")[:limit].rstrip("_")


def build_pdf_path(root: Path, domain: str, venue: str, year: int, index: int, work: dict) -> Path:
    stable = work.get("stable_id") or work["title"]
    digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return root / domain / venue / str(year) / digest[:2] / f"{index:04d}_{slug(work['title'])}_{digest[:10]}.pdf"


def existing_pdf_path(root: Path, row: dict) -> Path | None:
    relative = row.get("relative_path")
    return root / Path(relative) if relative else None


def validate_pdf(path: Path) -> tuple[bool, str]:
    try:
        if path.stat().st_size < 1024 or path.read_bytes()[:5] != b"%PDF-":
            return False, "invalid_pdf"
        result = subprocess.run(
            ["pdfinfo", str(path)], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        return (True, "") if result.returncode == 0 else (False, "incomplete_pdf")
    except (OSError, subprocess.SubprocessError):
        return False, "incomplete_pdf"


def classify_http(error: urllib.error.HTTPError) -> str:
    if error.code == 429:
        return "rate_limited"
    if error.code in (401, 403):
        return "access_denied"
    return "http_error"


def download_one(args: tuple[int, dict]) -> tuple[int, dict]:
    index, row = args
    row = dict(row)
    recorded = existing_pdf_path(ROOT, row)
    target = recorded if recorded and recorded.exists() else build_pdf_path(
        PAPERS, row["domain"], row["venue"], row["year"], index, row
    )
    if target.exists():
        valid, reason = validate_pdf(target)
        if valid:
            data = target.read_bytes()
            row.update(status="downloaded", relative_path=str(target.relative_to(ROOT)).replace("\\", "/"),
                       bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            return index, row
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    candidates = row.get("pdf_candidates") or ([row["pdf_url"]] if row.get("pdf_url") else [])
    if not candidates:
        row.update(status="pdf_url_missing", failure_reason="no legal open PDF URL found", last_attempt=now())
        return index, row
    last_status = "http_error"
    last_reason = ""
    for url in candidates[:2]:
        for attempt in range(2):
            row["attempts"] += 1
            part = target.with_suffix(".pdf.part")
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf"})
                with urllib.request.urlopen(request, timeout=90) as response, part.open("wb") as handle:
                    while chunk := response.read(1024 * 1024):
                        handle.write(chunk)
                valid, reason = validate_pdf(part)
                if valid:
                    part.replace(target)
                    data = target.read_bytes()
                    row.update(status="downloaded", pdf_url=url,
                               relative_path=str(target.relative_to(ROOT)).replace("\\", "/"),
                               bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                               failure_reason="", last_attempt=now())
                    return index, row
                last_status, last_reason = reason, f"downloaded content failed validation from {url}"
            except urllib.error.HTTPError as error:
                last_status, last_reason = classify_http(error), f"HTTP {error.code}: {url}"
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last_status, last_reason = "http_error", f"{type(error).__name__}: {error}"
            finally:
                part.unlink(missing_ok=True)
            if attempt == 0:
                time.sleep(2)
    row.update(status=last_status, failure_reason=last_reason, last_attempt=now())
    return index, row


def markdown_escape(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def render_not_downloaded(rows: list[dict], totals: dict[str, int], discovery: list[dict] | None = None) -> str:
    failures = [row for row in rows if row.get("status") != "downloaded"]
    reasons = Counter(row.get("status", "other") for row in failures)
    out = ["# NOT_DOWNLOADED", "", f"> Generated: {now()}", "",
           f"Target records: {len(rows)}; downloaded: {len(rows)-len(failures)}; unavailable: {len(failures)}.", "",
           "## Venue totals", "", "| Venue | Target | Unavailable |", "|---|---:|---:|"]
    failed_counts = Counter(row["venue"] for row in failures)
    for venue in sorted(totals):
        out.append(f"| {venue} | {totals[venue]} | {failed_counts[venue]} |")
    out += ["", "## Failure statuses", "", "| Status | Count |", "|---|---:|"]
    for status, count in sorted(reasons.items()):
        out.append(f"| {status} | {count} |")
    gaps = [item for item in (discovery or []) if item.get("error") or not item.get("discovered")]
    if gaps:
        out += ["", "## Discovery gaps", "", "| Venue | Year | Source | Error |", "|---|---:|---|---|"]
        for item in sorted(gaps, key=lambda value: (value["venue"], value["year"])):
            out.append("| " + " | ".join(markdown_escape(value) for value in (
                item["venue"], item["year"], item.get("source_name") or item.get("source_id"),
                item.get("error") or "discovered=0",
            )) + " |")
    grouped = defaultdict(list)
    for row in failures:
        grouped[(row["domain"], row["venue"], row["year"])].append(row)
    current_domain = None
    for (domain, venue, year), venue_rows in sorted(grouped.items()):
        if domain != current_domain:
            out += ["", f"## {domain}"]
            current_domain = domain
        out += ["", f"### {venue} ({year})", "",
                "| # | Title | Authors | Track | Stable ID | Landing | PDF | Status | Reason | Attempts | Last attempt |",
                "|---:|---|---|---|---|---|---|---|---|---:|---|"]
        for position, row in enumerate(venue_rows, 1):
            landing = f"[page]({row['landing_url']})" if row.get("landing_url") else "-"
            pdf = f"[PDF]({row['pdf_url']})" if row.get("pdf_url") else "-"
            values = [position, row["title"], row.get("authors"), row.get("track"), row.get("stable_id"),
                      landing, pdf, row.get("status"), row.get("failure_reason"),
                      row.get("attempts", 0), row.get("last_attempt")]
            out.append("| " + " | ".join(markdown_escape(value) for value in values) + " |")
    return "\n".join(out) + "\n"

def generate_reports(rows: list[dict], discovery: list[dict]) -> None:
    totals = Counter(row["venue"] for row in rows)
    failures = [row for row in rows if row.get("status") != "downloaded"]
    downloaded = [row for row in rows if row.get("status") == "downloaded"]
    CORPUS.mkdir(exist_ok=True)
    fields = ["domain", "venue", "year", "title", "authors", "track", "stable_id", "doi",
              "landing_url", "pdf_url", "relative_path", "bytes", "sha256"]
    with (CORPUS / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(downloaded)
    with (CORPUS / "not_downloaded.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FAILURE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(failures)
    (CORPUS / "NOT_DOWNLOADED.md").write_text(
        render_not_downloaded(rows, totals, discovery), encoding="utf-8", newline="\n"
    )
    with (CORPUS / "checksums.sha256").open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(downloaded, key=lambda item: item["relative_path"]):
            handle.write(f"{row['sha256']}  {row['relative_path']}\n")
    statuses = Counter(row.get("status", "pending") for row in rows)
    summary = ["# Paper corpus download summary", "", f"> Generated: {now()}", "",
               f"- Target records: {len(rows)}", f"- Downloaded: {len(downloaded)}",
               f"- Unavailable: {len(failures)}", f"- Downloaded bytes: {sum(row.get('bytes', 0) for row in downloaded)}", "",
               "## Status", "", "| Status | Count |", "|---|---:|"]
    summary += [f"| {key} | {value} |" for key, value in sorted(statuses.items())]
    summary += ["", "## Discovery", "", "| Venue | Year | Source | Expected | Discovered | Error |",
                "|---|---:|---|---:|---:|---|"]
    for item in discovery:
        summary.append(f"| {item['venue']} | {item['year']} | {item.get('source_name', '')} | "
                       f"{item.get('expected', '')} | {item.get('discovered', 0)} | {item.get('error', '')} |")
    (CORPUS / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8", newline="\n")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--reports", action="store_true", help="rebuild CSV/Markdown reports from the current manifest")
    parser.add_argument("--venue", action="append", default=[])
    parser.add_argument("--year", type=int)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    phases = args.discover or args.download or args.check or args.reports
    run_discover, run_download, run_check = (args.discover, args.download, args.check) if phases else (True, True, True)
    venues = json.loads((CORPUS / "venues.json").read_text(encoding="utf-8"))
    if args.venue:
        requested = {value.upper() for value in args.venue}
        venues = [venue for venue in venues if venue["venue"].upper() in requested]
    if args.year:
        venues = [venue for venue in venues if venue["year"] == args.year]
    if args.dry_run:
        print(json.dumps({"venues": len(venues), "discover": run_discover, "download": run_download,
                          "check": run_check, "max_workers": args.max_workers}, ensure_ascii=False))
        return 0
    discovery_path = CORPUS / "discovery.json"
    rows = read_jsonl(MANIFEST)
    discovery = json.loads(discovery_path.read_text(encoding="utf-8")) if discovery_path.exists() else []
    if run_discover:
        selected = {venue["venue"] for venue in venues}
        rows = [row for row in rows if row.get("venue") not in selected]
        discovery = [item for item in discovery if item.get("venue") not in selected]
        for venue in venues:
            print(f"Discovering {venue['venue']} {venue['year']}...", flush=True)
            try:
                venue_rows, info = discover_venue(venue)
            except Exception as error:
                venue_rows, info = [], {"venue": venue["venue"], "year": venue["year"],
                                        "error": f"{type(error).__name__}: {error}"}
            rows.extend(venue_rows); discovery.append(info)
            write_jsonl(MANIFEST, rows)
            discovery_path.write_text(json.dumps(discovery, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        unique = {}
        for row in rows:
            unique[(row["venue"], row["stable_id"] or normalized(row["title"]))] = row
        rows = list(unique.values())
        write_jsonl(MANIFEST, rows)
        discovery_path.write_text(json.dumps(discovery, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    if args.reports:
        known = {item.get("venue") for item in discovery}
        for venue in venues:
            if venue["venue"] not in known:
                discovery.append({"venue": venue["venue"], "year": venue["year"], "error": "not_discovered"})
        generate_reports(rows, discovery)
        print("Corpus records:", len(rows), "downloaded:", sum(r.get("status") == "downloaded" for r in rows))
        return 0

    if run_download:
        eligible = interleave_by_venue([(index, row) for index, row in enumerate(rows, 1)
                    if row.get("status") != "downloaded" and (args.retry_failed or row.get("status") in ("pending", None))])
        with ThreadPoolExecutor(max_workers=max(1, min(args.max_workers, 48))) as executor:
            futures = [executor.submit(download_one, item) for item in eligible]
            for completed, future in enumerate(as_completed(futures), 1):
                index, row = future.result(); rows[index - 1] = row
                if completed % 25 == 0:
                    write_jsonl(MANIFEST, rows)
                    print(f"Processed {completed}/{len(eligible)}", flush=True)
        write_jsonl(MANIFEST, rows)
    if run_check:
        for index, row in enumerate(rows, 1):
            if row.get("status") != "downloaded":
                continue
            path = ROOT / row["relative_path"]
            valid, reason = validate_pdf(path) if path.exists() else (False, "incomplete_pdf")
            if not valid:
                rows[index - 1].update(status=reason, failure_reason="local PDF failed final validation")
        write_jsonl(MANIFEST, rows)
    generate_reports(rows, discovery)
    print(f"Corpus records: {len(rows)}; downloaded: {sum(r.get('status') == 'downloaded' for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())