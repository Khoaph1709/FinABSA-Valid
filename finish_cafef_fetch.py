from __future__ import annotations

import argparse
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

from prepare_cafef_data import DATA, RAW, HEADERS, parse_article, request_text


def fetch_one(row: dict, sleep: float) -> dict:
    url = row["url"]
    time.sleep(sleep)
    try:
        html = request_text(requests.Session(), url)
        raw_path = RAW / (hashlib.sha1(url.encode()).hexdigest() + ".html")
        raw_path.write_text(html, encoding="utf-8")
        parsed = parse_article(html, url, row.get("lastmod", ""))
        parsed["raw_path"] = str(raw_path.relative_to(Path(__file__).parent))
        parsed["crawl_status"] = "ok"
        return parsed
    except Exception as exc:
        return {"url": url, "sitemap_lastmod": row.get("lastmod", ""), "raw_path": "", "crawl_status": f"error:{type(exc).__name__}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()
    manifest = pd.read_csv(DATA / "sitemap_manifest.csv").fillna("")
    candidates = manifest[manifest["candidate"]].copy()
    out_path = DATA / "articles.csv"
    existing = pd.read_csv(out_path).fillna("") if out_path.exists() else pd.DataFrame()
    done = set(existing.get("url", [])) if not existing.empty else set()
    todo = candidates[~candidates["url"].isin(done)].to_dict("records")
    rows = existing.to_dict("records") if not existing.empty else []
    print(f"existing={len(done)} todo={len(todo)} workers={args.workers}")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch_one, row, args.sleep) for row in todo]
        for idx, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if idx % 25 == 0 or idx == len(futures):
                pd.DataFrame(rows).drop_duplicates("url").to_csv(out_path, index=False)
                print(f"completed={idx}/{len(futures)}")
    result = pd.DataFrame(rows).drop_duplicates("url")
    result.to_csv(out_path, index=False)
    print(f"saved={out_path} rows={len(result)}")
    print(result.get("crawl_status", pd.Series(dtype=str)).value_counts().to_string())


if __name__ == "__main__":
    main()
