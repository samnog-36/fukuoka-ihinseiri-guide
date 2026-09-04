from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from html import unescape
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "docs/ADSENSE_CONTENT_AUDIT_20260904.md"
REPORT_JSON = ROOT / "docs/ADSENSE_CONTENT_AUDIT_20260904.json"
ADSENSE = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
AD_WIDGET = "fukuokaguide-afgvbgyb.manus.space/ad-widget.js"

NON_CONTENT = {
    "about.html",
    "privacy-policy.html",
    "contact/index.html",
    "for-business/index.html",
}

SAFE_REPLACEMENTS = {
    "弁護士監修レベルで解説": "公的情報をもとに注意点を解説",
    "弁護士監修レベル": "公的情報をもとに確認",
    "専門家が徹底解説": "公的情報を確認しながら解説",
    "優良業者のみ掲載": "掲載基準を公開",
    "信頼できる業者だけをご紹介": "業者情報の確認項目を公開",
    "許認可の確認・口コミ調査を経た福岡県内の優良業者のみを掲載しています。": "事業者情報を掲載する際の確認項目や広告・PRの扱いは、編集方針・運営情報で公開しています。",
    "間取り別・作業内容別の正確な相場情報で、適正価格を事前に把握できます。": "間取り別・作業内容別の料金目安を、見積もりを比較するときの参考情報として整理しています。",
    "信頼できる業者情報と、正確な費用相場をお届けします。": "事業者選びの確認ポイントと、料金の参考目安を整理しています。",
    "福岡県全域対応": "福岡県の情報を掲載",
    "福岡県内の信頼できる業者をご紹介します。": "福岡県内の事業者を選ぶ際の確認ポイントをご案内します。",
    "信頼できる業者をご紹介することも可能です。": "事業者選びの確認ポイントをご案内します。",
}

RISK_PATTERNS = {
    "監修・専門家表示": re.compile(r"(?:弁護士|税理士|司法書士|専門家).{0,12}(?:監修|解説|レベル)"),
    "絶対・必ず等の断定": re.compile(r"(?:絶対|必ず|確実|完全に|100%|間違いなく)"),
    "出典確認が必要な割合": re.compile(r"(?:約|およそ)?\d{1,3}(?:\.\d+)?[%％]"),
    "調査によると": re.compile(r"(?:調査|統計|データ)によると"),
    "正確・適正の断定": re.compile(r"(?:正確な|適正価格|適正な価格)"),
    "おすすめ断定": re.compile(r"おすすめ(?:業者|の業者|ランキング)"),
}

PUBLIC_SOURCE_HINTS = (
    ".go.jp", "city.", "pref.fukuoka", "www.city.", "courts.go.jp",
    "kokusen.go.jp", "nta.go.jp", "mhlw.go.jp", "moj.go.jp", "env.go.jp",
)

TAG_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>", re.I | re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def visible_text(html: str) -> str:
    return re.sub(r"\s+", "", unescape(TAG_RE.sub("", html)))


def shingles(text: str, n: int = 7) -> set[str]:
    sample = text[:18000]
    if len(sample) < n:
        return {sample} if sample else set()
    return {sample[i:i+n] for i in range(len(sample) - n + 1)}


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def title_of(html: str) -> str:
    match = TITLE_RE.search(html)
    return re.sub(r"\s+", " ", unescape(match.group(1))).strip() if match else ""


def redirect_sources() -> set[str]:
    path = ROOT / "_redirects"
    if not path.exists():
        return set()
    sources = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 3 and parts[-1] in {"301", "302", "307", "308"} and parts[0].startswith("/"):
            sources.add(parts[0])
    return sources


def remove_ads_from_non_content(path: Path, html: str) -> str:
    if path.relative_to(ROOT).as_posix() not in NON_CONTENT:
        return html
    html = re.sub(
        r"\s*<script\s+async\s+src=[\"']https://pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js\?client=ca-pub-4944616437202027[\"']\s+crossorigin=[\"']anonymous[\"']></script>",
        "", html, flags=re.I,
    )
    return re.sub(
        r"\s*<script\s+src=[\"']https://fukuokaguide-afgvbgyb\.manus\.space/ad-widget\.js[\"']\s+defer></script>",
        "", html, flags=re.I,
    )


def apply_safe_fixes() -> list[str]:
    changed = []
    for path in sorted(ROOT.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        html = original
        for old, new in SAFE_REPLACEMENTS.items():
            html = html.replace(old, new)
        html = remove_ads_from_non_content(path, html)
        if html != original:
            path.write_text(html, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def build_record(path: Path, redirected: set[str]) -> dict:
    html = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT).as_posix()
    url_path = "/" + rel
    text = visible_text(html)
    noindex = bool(re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', html, re.I))
    return {
        "path": rel,
        "category": path.parent.name,
        "title": title_of(html),
        "visible_chars": len(text),
        "public_source_hints": sum(html.count(hint) for hint in PUBLIC_SOURCE_HINTS),
        "risk_counts": {name: len(rx.findall(html)) for name, rx in RISK_PATTERNS.items()},
        "has_editorial_info": 'class="editorial-info"' in html,
        "has_reference_links": 'class="reference-links"' in html,
        "has_adsense": ADSENSE in html,
        "is_noindex": noindex,
        "is_redirect_source": url_path in redirected,
        "shingles": shingles(text),
    }


def build_audit() -> dict:
    articles = sorted(ROOT.glob("blog/*/article-*.html"))
    html_pages = sorted(ROOT.rglob("*.html"))
    redirects = redirect_sources()
    records = [build_record(path, redirects) for path in articles]
    active = [r for r in records if not r["is_redirect_source"] and not r["is_noindex"]]

    by_category = defaultdict(list)
    for rec in active:
        by_category[rec["category"]].append(rec)

    duplicate_candidates = []
    for category, group in by_category.items():
        for i, left in enumerate(group):
            for right in group[i + 1:]:
                content_score = similarity(left["shingles"], right["shingles"])
                left_title = re.sub(r"[｜|【】\[\]（）()・\s0-9年月日版]", "", left["title"])
                right_title = re.sub(r"[｜|【】\[\]（）()・\s0-9年月日版]", "", right["title"])
                title_score = similarity(shingles(left_title, 3), shingles(right_title, 3))
                if content_score >= 0.22 or title_score >= 0.46:
                    duplicate_candidates.append({
                        "category": category,
                        "left": left["path"], "right": right["path"],
                        "content_similarity": round(content_score, 3),
                        "title_similarity": round(title_score, 3),
                    })
    duplicate_candidates.sort(
        key=lambda item: (max(item["content_similarity"], item["title_similarity"]), item["content_similarity"]),
        reverse=True,
    )

    risk_files = []
    for rec in active:
        total = sum(rec["risk_counts"].values())
        if total:
            risk_files.append({
                "path": rec["path"], "title": rec["title"], "risk_total": total,
                "risk_counts": rec["risk_counts"], "public_source_hints": rec["public_source_hints"],
            })
    risk_files.sort(key=lambda item: (item["risk_total"], -item["public_source_hints"]), reverse=True)

    non_content_ads = []
    for rel in sorted(NON_CONTENT):
        path = ROOT / rel
        if path.exists():
            html = path.read_text(encoding="utf-8")
            if ADSENSE in html or AD_WIDGET in html:
                non_content_ads.append(rel)

    return {
        "generated": str(date.today()),
        "html_pages": len(html_pages),
        "article_files": len(records),
        "redirected_article_sources": sum(1 for r in records if r["is_redirect_source"]),
        "noindex_articles": sum(1 for r in records if r["is_noindex"] and not r["is_redirect_source"]),
        "active_indexable_articles": len(active),
        "active_categories": dict(Counter(r["category"] for r in active)),
        "active_without_public_source_hint": sum(1 for r in active if r["public_source_hints"] == 0),
        "active_without_editorial_info": sum(1 for r in active if not r["has_editorial_info"]),
        "active_without_reference_links": sum(1 for r in active if not r["has_reference_links"]),
        "non_content_ads_remaining": non_content_ads,
        "duplicate_candidates": duplicate_candidates[:80],
        "risk_files": risk_files[:100],
    }


def write_report(data: dict, changed: list[str]) -> None:
    REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# AdSense コンテンツ品質監査（2026-09-04）", "",
        "再審査で実際に検索・広告対象となる『有効な記事在庫』を中心に監査した結果です。301統合元とnoindex保留記事は、重複・危険表現ランキングから除外しています。", "",
        "## 有効在庫", "",
        f"- HTMLファイル総数: **{data['html_pages']}**",
        f"- ブログ記事ファイル総数: **{data['article_files']}**",
        f"- 301統合元の記事: **{data['redirected_article_sources']}**",
        f"- noindex保留記事: **{data['noindex_articles']}**",
        f"- 現在のindexable記事: **{data['active_indexable_articles']}**",
        f"- 公的情報リンクヒント0の有効記事: **{data['active_without_public_source_hint']}**",
        f"- 編集情報なしの有効記事: **{data['active_without_editorial_info']}**",
        f"- 公式確認先なしの有効記事: **{data['active_without_reference_links']}**",
        f"- 非コンテンツページで広告読込が残るページ: **{len(data['non_content_ads_remaining'])}**", "",
        "### 有効記事のカテゴリ別件数", "",
    ]
    for category, count in sorted(data["active_categories"].items()):
        lines.append(f"- {category}: {count}")
    lines += ["", "## この実行で安全に自動修正したページ", ""]
    lines += [f"- `{p}`" for p in changed] or ["- なし"]

    lines += ["", "## まだ残る重複・検索意図競合候補", "",
              "301統合元とnoindex記事を除外したうえで、本文またはタイトルが近いものです。", "",
              "| 本文類似 | タイトル類似 | ページA | ページB |", "|---:|---:|---|---|"]
    for item in data["duplicate_candidates"][:50]:
        lines.append(f"| {item['content_similarity']:.3f} | {item['title_similarity']:.3f} | `{item['left']}` | `{item['right']}` |")

    lines += ["", "## まだ残る根拠確認・表現見直しの優先候補", "",
              "有効記事だけを対象に、割合・強い断定・専門性表示などを検出したものです。", "",
              "| 指摘数 | 公的リンクヒント | ページ | タイトル |", "|---:|---:|---|---|"]
    for item in data["risk_files"][:60]:
        title = item["title"].replace("|", "｜")
        lines.append(f"| {item['risk_total']} | {item['public_source_hints']} | `{item['path']}` | {title} |")

    lines += ["", "## 方針", "",
              "1. 301統合元は検索在庫として数えず、代表ページへ評価を集約する。",
              "2. 法律・税務・感染症など個別判断リスクが高い記事は、再確認が済むまでnoindex・広告停止を維持する。",
              "3. 有効記事の残存候補だけを順次精査し、一般論の言い換えではなく福岡の一次情報・独自比較を増やす。",
              "4. 新規記事の量産は停止し、既存記事の統合・更新を優先する。", ""]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    changed = apply_safe_fixes()
    data = build_audit()
    write_report(data, changed)
    print(json.dumps({
        "active_indexable_articles": data["active_indexable_articles"],
        "redirected_article_sources": data["redirected_article_sources"],
        "noindex_articles": data["noindex_articles"],
        "remaining_duplicate_candidates": len(data["duplicate_candidates"]),
        "remaining_risk_files": len(data["risk_files"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
