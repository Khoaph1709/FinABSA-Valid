from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "cafef_oct2022"
RAW = DATA / "raw_html"
DATA.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

SITEMAPS = [
    f"https://cafef.vn/sitemaps/sitemaps-2022-10-{part}.xml"
    for part in ["1-5", "6-10", "11-15", "16-20", "21-25", "26-31"]
]

# Broad enough to capture company, market and macro-finance articles while
# excluding most lifestyle/social articles from the one-month corpus.
KEYWORDS = [
    "cổ phiếu", "chứng khoán", "vn-index", "vnindex", "vn30", "hà nội index",
    "hose", "hnx", "upcom", "trái phiếu", "ngân hàng", "lãi suất", "lợi nhuận",
    "doanh thu", "cổ đông", "doanh nghiệp", "thị trường", "tài chính", "đầu tư",
    "bán ròng", "mua ròng", "margin", "chứng quyền", "phái sinh", "chốt quyền",
    "cổ tức", "bctc", "báo cáo tài chính", "ipo", "flc", "sàn chứng khoán",
    "room tín dụng", "thanh khoản", "tỷ giá", "lạm phát", "fed", "trái phiếu",
]
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS), re.I)
TICKER_RE = re.compile(r"(?<![A-Za-z])([A-Z]{2,5})(?![A-Za-z])")

HEADERS = {
    "User-Agent": "NLP-course-research/1.0 (academic dataset preparation; contact via repository owner)",
    "Accept-Language": "vi,en;q=0.8",
}


def request_text(session: requests.Session, url: str, timeout: int = 30) -> str:
    response = session.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def parse_sitemap(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    rows = []
    for node in root:
        values = {child.tag.rsplit("}", 1)[-1]: (child.text or "").strip() for child in node}
        loc = values.get("loc", "")
        if not loc.startswith("https://cafef.vn/") or not loc.endswith(".chn"):
            continue
        title_hint = ""
        for child in node.iter():
            if child.tag.rsplit("}", 1)[-1] == "title":
                title_hint = (child.text or "").strip()
                break
        rows.append({"url": loc, "lastmod": values.get("lastmod", ""), "title_hint": title_hint})
    return rows


def meta_content(soup: BeautifulSoup, selector: str, attr: str = "content") -> str:
    tag = soup.select_one(selector)
    return (tag.get(attr) or "").strip() if tag else ""


def parse_article(html: str, url: str, sitemap_lastmod: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = meta_content(soup, 'meta[property="og:title"]') or (soup.title.get_text(" ", strip=True) if soup.title else "")
    description = meta_content(soup, 'meta[property="og:description"]')
    published = meta_content(soup, 'meta[property="article:published_time"]')
    modified = meta_content(soup, 'meta[property="article:modified_time"]')
    ld_published = ""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(script.get_text())
            items = obj if isinstance(obj, list) else [obj]
            for item in items:
                if isinstance(item, dict):
                    ld_published = ld_published or str(item.get("datePublished", ""))
                    published = published or str(item.get("datePublished", ""))
                    modified = modified or str(item.get("dateModified", ""))
        except Exception:
            continue
    sapo_tag = soup.select_one('[data-role="sapo"]') or soup.select_one(".sapo")
    body_tag = soup.select_one('[data-role="content"]') or soup.select_one(".contentdetail")
    sapo = sapo_tag.get_text(" ", strip=True) if sapo_tag else description
    body = body_tag.get_text(" ", strip=True) if body_tag else ""
    author_tag = soup.select_one('[data-role="author"]') or soup.select_one(".author")
    author = author_tag.get_text(" ", strip=True) if author_tag else ""
    text = " ".join(x for x in [title, sapo, body] if x).strip()
    tickers = sorted(set(TICKER_RE.findall(title + " " + sapo)))
    return {
        "url": url,
        "title": title,
        "summary": sapo,
        "body": body,
        "author": author,
        "published_at": published or ld_published or sitemap_lastmod,
        "updated_at": modified,
        "sitemap_lastmod": sitemap_lastmod,
        "title_tickers_upper": json.dumps(tickers, ensure_ascii=False),
        "source_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "body_chars": len(body),
        "parse_status": "ok" if title and body else "partial",
    }


def build_manifest(session: requests.Session) -> pd.DataFrame:
    rows = []
    for sitemap in SITEMAPS:
        xml = request_text(session, sitemap)
        for row in parse_sitemap(xml):
            row["sitemap"] = sitemap
            rows.append(row)
    manifest = pd.DataFrame(rows).drop_duplicates("url")
    manifest["title_hint"] = manifest.get("title_hint", "").fillna("")
    # Use both sitemap image titles and URL slugs. The title field is usually
    # more informative; the URL fallback catches articles without image title.
    title_hit = manifest["title_hint"].str.lower().map(lambda x: bool(KEYWORD_RE.search(x)))
    url_hit = manifest["url"].str.lower().map(lambda x: bool(KEYWORD_RE.search(x)))
    manifest["candidate"] = title_hit | url_hit
    manifest["candidate_reason"] = title_hit.map(lambda x: "title_keyword" if x else "")
    manifest.loc[(~title_hit) & url_hit, "candidate_reason"] = "url_keyword"
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="Fetch candidate article HTML")
    parser.add_argument("--max-fetch", type=int, default=0, help="0 means all URL candidates")
    parser.add_argument("--sleep", type=float, default=0.35)
    args = parser.parse_args()

    session = requests.Session()
    manifest_path = DATA / "sitemap_manifest.csv"
    if manifest_path.exists():
        manifest = pd.read_csv(manifest_path)
    else:
        manifest = build_manifest(session)
        manifest.to_csv(manifest_path, index=False)

    candidates = manifest[manifest["candidate"]].copy()
    print(f"manifest_rows={len(manifest)} candidates={len(candidates)}")

    if not args.fetch:
        print(candidates[["url", "lastmod", "candidate_reason"]].head(20).to_string(index=False))
        return

    if args.max_fetch > 0:
        candidates = candidates.head(args.max_fetch)
    out_path = DATA / "articles.csv"
    existing = pd.read_csv(out_path) if out_path.exists() else pd.DataFrame()
    done = set(existing.get("url", [])) if not existing.empty else set()
    rows = existing.to_dict("records") if not existing.empty else []

    for idx, row in enumerate(candidates.to_dict("records"), start=1):
        if row["url"] in done:
            continue
        try:
            html = request_text(session, row["url"])
            raw_path = RAW / (hashlib.sha1(row["url"].encode()).hexdigest() + ".html")
            raw_path.write_text(html, encoding="utf-8")
            parsed = parse_article(html, row["url"], row.get("lastmod", ""))
            parsed["raw_path"] = str(raw_path.relative_to(ROOT))
            parsed["crawl_status"] = "ok"
        except Exception as exc:
            parsed = {
                "url": row["url"], "sitemap_lastmod": row.get("lastmod", ""),
                "raw_path": "", "crawl_status": f"error:{type(exc).__name__}",
            }
        rows.append(parsed)
        done.add(row["url"])
        if idx % 25 == 0:
            pd.DataFrame(rows).drop_duplicates("url").to_csv(out_path, index=False)
            print(f"fetched={idx}/{len(candidates)}")
        time.sleep(args.sleep)

    result = pd.DataFrame(rows).drop_duplicates("url")
    result.to_csv(out_path, index=False)
    print(f"saved={out_path} rows={len(result)}")
    print(result.get("crawl_status", pd.Series(dtype=str)).value_counts().to_string())


if __name__ == "__main__":
    main()
