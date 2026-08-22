from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from prepare_cafef_data import HEADERS, KEYWORD_RE, parse_article, parse_sitemap

ROOT = Path(__file__).parent
DEFAULT_ROOT = ROOT / "data" / "cafef_multiyear"
SITEMAP_PARTS = ["1-5", "6-10", "11-15", "16-20", "21-25", "26-31"]


def request_text(session: requests.Session, url: str, timeout: int = 45) -> str:
    response = session.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def build_manifest(session: requests.Session, year: int, month: int) -> tuple[pd.DataFrame, dict[str, str]]:
    rows: list[dict] = []
    errors: dict[str, str] = {}
    for part in SITEMAP_PARTS:
        sitemap = f"https://cafef.vn/sitemaps/sitemaps-{year}-{month:02d}-{part}.xml"
        try:
            xml = request_text(session, sitemap)
            for row in parse_sitemap(xml):
                row.update({"year": year, "month": month, "period": f"{year}-{month:02d}", "sitemap": sitemap})
                rows.append(row)
        except Exception as exc:
            errors[sitemap] = f"{type(exc).__name__}: {exc}"
    if not rows:
        return pd.DataFrame(columns=["year", "month", "period", "sitemap", "url", "lastmod", "title_hint", "candidate", "candidate_reason"]), errors
    manifest = pd.DataFrame(rows).drop_duplicates("url")
    manifest["title_hint"] = manifest.get("title_hint", "").fillna("").astype(str)
    manifest["url"] = manifest["url"].fillna("").astype(str)
    title_hit = manifest["title_hint"].str.lower().map(lambda x: bool(KEYWORD_RE.search(x)))
    url_hit = manifest["url"].str.lower().map(lambda x: bool(KEYWORD_RE.search(x)))
    manifest["candidate"] = title_hit | url_hit
    manifest["candidate_reason"] = ""
    manifest.loc[title_hit, "candidate_reason"] = "title_keyword"
    manifest.loc[(~title_hit) & url_hit, "candidate_reason"] = "url_keyword"
    return manifest, errors


def load_or_build_manifest(session: requests.Session, period_root: Path, year: int, month: int) -> tuple[pd.DataFrame, dict[str, str]]:
    manifest_path = period_root / "sitemap_manifest.csv"
    errors_path = period_root / "sitemap_errors.json"
    if manifest_path.exists():
        manifest = pd.read_csv(manifest_path).fillna("")
        errors = json.loads(errors_path.read_text(encoding="utf-8")) if errors_path.exists() else {}
        return manifest, errors
    manifest, errors = build_manifest(session, year, month)
    period_root.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(manifest_path, index=False)
    errors_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest, errors


def fetch_period(session: requests.Session, manifest: pd.DataFrame, period_root: Path, sleep_seconds: float, max_fetch: int, workers: int) -> pd.DataFrame:
    raw_dir = period_root / "raw_html"
    raw_dir.mkdir(parents=True, exist_ok=True)
    candidates = manifest[manifest["candidate"].astype(bool)].copy()
    if max_fetch > 0:
        candidates = candidates.head(max_fetch)
    out_path = period_root / "articles.csv"
    existing = pd.read_csv(out_path).fillna("") if out_path.exists() else pd.DataFrame()
    done = set(existing.get("url", pd.Series(dtype=str)).astype(str)) if not existing.empty else set()
    todo = [row for row in candidates.to_dict("records") if str(row.get("url", "")) not in done]
    rows = existing.to_dict("records") if not existing.empty else []

    def fetch_one(row: dict) -> dict:
        url = str(row.get("url", ""))
        try:
            time.sleep(sleep_seconds)
            html = request_text(requests.Session(), url)
            raw_path = raw_dir / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".html")
            raw_path.write_text(html, encoding="utf-8")
            parsed = parse_article(html, url, str(row.get("lastmod", "")))
            parsed["raw_path"] = str(raw_path.relative_to(ROOT))
            parsed["crawl_status"] = "ok"
            parsed["year"] = int(row.get("year", 0))
            parsed["month"] = int(row.get("month", 0))
            parsed["period"] = str(row.get("period", ""))
            return parsed
        except Exception as exc:
            return {
                "url": url,
                "sitemap_lastmod": row.get("lastmod", ""),
                "raw_path": "",
                "crawl_status": f"error:{type(exc).__name__}",
                "year": int(row.get("year", 0)),
                "month": int(row.get("month", 0)),
                "period": str(row.get("period", "")),
            }

    print(f"{period_root.name}: todo={len(todo)} workers={workers}", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(fetch_one, row) for row in todo]
        for idx, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if idx % 25 == 0 or idx == len(futures):
                pd.DataFrame(rows).drop_duplicates("url").to_csv(out_path, index=False)
                print(f"{period_root.name}: fetched={idx}/{len(todo)}", flush=True)
    result = pd.DataFrame(rows).drop_duplicates("url")
    result.to_csv(out_path, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare comparable one-month CafeF datasets for multiple years")
    parser.add_argument("--years", default="2019,2020,2021,2022")
    parser.add_argument("--month", type=int, default=10, help="Same month for each year; default is October")
    parser.add_argument("--out-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--fetch", action="store_true", help="Download and parse candidate article HTML")
    parser.add_argument("--max-fetch-per-period", type=int, default=0, help="0 means all candidates")
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument("--workers", type=int, default=3, help="Concurrent article fetch workers")
    args = parser.parse_args()
    years = [int(x.strip()) for x in args.years.split(",") if x.strip()]
    if not years or not 1 <= args.month <= 12:
        raise SystemExit("years and month must be valid")
    root = Path(args.out_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    summaries: list[dict] = []
    all_articles: list[pd.DataFrame] = []
    for year in years:
        period = f"{year}-{args.month:02d}"
        period_root = root / period
        manifest, errors = load_or_build_manifest(session, period_root, year, args.month)
        candidate_count = int(manifest["candidate"].astype(bool).sum()) if not manifest.empty else 0
        summary = {"period": period, "sitemap_rows": len(manifest), "candidate_urls": candidate_count, "sitemap_errors": len(errors)}
        if args.fetch:
            articles = fetch_period(session, manifest, period_root, args.sleep, args.max_fetch_per_period, args.workers)
            all_articles.append(articles)
            summary["article_rows"] = len(articles)
            summary["crawl_ok"] = int((articles.get("crawl_status", pd.Series(dtype=str)) == "ok").sum())
        print(summary, flush=True)
        summaries.append(summary)
    pd.DataFrame(summaries).to_csv(root / "multiyear_manifest_summary.csv", index=False)
    if all_articles:
        combined = pd.concat(all_articles, ignore_index=True).drop_duplicates("url")
        combined.to_csv(root / "articles.csv", index=False)
        print(f"saved={root / 'articles.csv'} rows={len(combined)}", flush=True)
    print(f"saved={root / 'multiyear_manifest_summary.csv'}", flush=True)


if __name__ == "__main__":
    main()
