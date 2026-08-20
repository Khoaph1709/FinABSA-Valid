from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "cafef_oct2022"

# Acronyms that frequently appear in financial headlines but are not listed
# company tickers. They remain in the article text but are not targets.
NON_TICKER = {
    "VN", "VNI", "VNINDEX", "VN30", "HNX", "HOSE", "UPCOM", "NHNN", "BCTC",
    "CEO", "CFO", "CTCK", "ETF", "IPO", "FED", "GDP", "USD", "EUR", "JPY",
    "MV", "TV", "AI", "KPI", "CEO", "CPI", "GNP", "NPL", "HOA", "META", "PV", "RA", "TRONG", "CHO", "GIA", "ESOP", "TSMC",
    "FII", "PPE", "ROE", "ROA", "PBR", "EPS", "P/E", "FY", "Q1", "Q2", "Q3", "Q4",
}
TICKER_RE = re.compile(r"(?<![A-Za-zÀ-ỹ0-9])([A-Z]{2,5})(?![A-Za-zÀ-ỹ0-9])")
MAPPING_RE = re.compile(r"(?:mã|ticker|cổ phiếu)\s*[:：]?\s*([A-Z]{2,5})\b", re.I)


def load_aliases(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["surface", "ticker", "canonical"])
    df = pd.read_csv(path).fillna("")
    for col in ["surface", "ticker", "canonical"]:
        if col not in df:
            df[col] = ""
    return df[["surface", "ticker", "canonical"]]


def find_targets(text: str, aliases: pd.DataFrame) -> list[dict]:
    found: list[dict] = []
    alias_surfaces = {str(x).strip().lower() for x in aliases["surface"].tolist() if str(x).strip()}
    for _, row in aliases.iterrows():
        surface = str(row["surface"]).strip()
        if surface and surface.lower() in text.lower():
            start = text.lower().find(surface.lower())
            found.append({
                "surface": text[start:start + len(surface)],
                "ticker": str(row["ticker"]).strip().upper(),
                "canonical": str(row["canonical"]).strip(),
                "method": "alias",
                "confidence": 0.98,
            })

    for match in TICKER_RE.finditer(text):
        ticker = match.group(1).upper()
        if ticker.lower() in alias_surfaces or ticker in NON_TICKER:
            continue
        found.append({
            "surface": match.group(1),
            "ticker": ticker,
            "canonical": "",
            "method": "explicit_uppercase_ticker",
            "confidence": 0.90,
        })

    for match in MAPPING_RE.finditer(text):
        ticker = match.group(1).upper()
        if ticker.lower() not in alias_surfaces and ticker not in NON_TICKER:
            found.append({
                "surface": ticker,
                "ticker": ticker,
                "canonical": "",
                "method": "ticker_context_rule",
                "confidence": 0.95,
            })

    unique = {}
    for item in found:
        key = (item["surface"].lower(), item["ticker"])
        if key not in unique or item["confidence"] > unique[key]["confidence"]:
            unique[key] = item
    return list(unique.values())


def mask_title(title: str, target: str, other_targets: list[str]) -> str:
    masked = title.replace(target, "Target", 1)
    for other in other_targets:
        if other != target:
            masked = masked.replace(other, "Other", 1)
    return masked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--articles", default=str(DATA / "articles.csv"))
    parser.add_argument("--aliases", default=str(ROOT / "data" / "entity_aliases.csv"))
    parser.add_argument("--out", default=str(DATA / "model_inputs.csv"))
    parser.add_argument("--out-strict", default=str(DATA / "model_inputs_strict.csv"))
    args = parser.parse_args()

    articles = pd.read_csv(args.articles).fillna("")
    aliases = load_aliases(Path(args.aliases))
    rows = []
    for _, article in articles.iterrows():
        title = str(article.get("title", "")).strip()
        if not title:
            continue
        targets = find_targets(title, aliases)
        if not targets:
            continue
        surfaces = [x["surface"] for x in targets]
        article_id = hashlib.sha1(str(article.get("url", "")).encode()).hexdigest()[:16]
        for idx, target in enumerate(targets):
            row_id = f"{article_id}_{idx:02d}"
            rows.append({
                "sample_id": row_id,
                "article_id": article_id,
                "url": article.get("url", ""),
                "published_at": article.get("published_at", ""),
                "updated_at": article.get("updated_at", ""),
                "category": article.get("category", ""),
                "raw_title": title,
                "summary": article.get("summary", ""),
                "body": article.get("body", ""),
                "target_surface": target["surface"],
                "ticker": target["ticker"],
                "canonical_entity": target["canonical"],
                "entity_method": target["method"],
                "entity_confidence": target["confidence"],
                "entity_review_status": "auto_high_confidence" if target["confidence"] >= 0.95 else "manual_review",
                "sentence": mask_title(title, target["surface"], surfaces),
                "input_text": mask_title(title, target["surface"], surfaces),
                "model_contract": "FinABSA_target_masked_headline_v1",
                "target_index": idx,
            })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.drop_duplicates(["url", "target_surface", "ticker"])
        out.to_csv(args.out, index=False)
        strict = out[out["entity_confidence"] >= 0.95].copy()
        strict.to_csv(args.out_strict, index=False)
    else:
        empty_cols = ["sample_id", "raw_title", "target_surface", "ticker", "input_text"]
        pd.DataFrame(columns=empty_cols).to_csv(args.out, index=False)
        pd.DataFrame(columns=empty_cols).to_csv(args.out_strict, index=False)
    print(f"articles={len(articles)} model_rows={len(out)} strict_rows={len(out[out['entity_confidence'] >= 0.95]) if not out.empty else 0}")
    print(out["entity_review_status"].value_counts().to_string() if not out.empty else "no rows")


if __name__ == "__main__":
    main()
