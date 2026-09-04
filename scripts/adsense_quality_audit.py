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

# 広告を主目的にしない情報・フォームページ。Googleの non-content inventory を避ける。
NON_CONTENT = {
    "about.html",
    "privacy-policy.html",
    "contact/index.html",
    "for-business/index.html",
}

# 実態を確認できない強い表現だけを、安全な説明へ置換する。
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
    ".go.jp",
    "city.",
    "pref.fukuoka",
    "www.city.",
    "courts.go.jp",
    "kokusen.go.jp",
    "nta.go.jp",
    "mhlw.go.jp",
    "moj.go.jp",
    "env.go.jp",
)

TAG_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>", re.I | re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def visible_text(html: str) -> str:
    text = TAG_RE.sub("", html)
    text = unescape(text)
    text = re.sub(r"\s+", "", text)
    return text


def shingles(text: str, n: int = 7) -> set[str]:
    if len(text) < n:
        return {text} if text else set()
    # ページ共通フッター等の影響を減らすため先頭～本文中心を利用
    sample = text[:18000]
    return {sample[i:i+n] for i in range(len(sample) - n + 1)}


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def title_of(html: str) -> str:
    m = TITLE_RE.search(html)
    return re.sub(r"\s+", " ", unescape(m.group(1))).strip() if m else ""


def remove_ads_from_non_content(path: Path, html: str) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel not in NON_CONTENT:
        return html
    html = re.sub(
        r"\s*<script\s+async\s+src=[\"']https://pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js\?client=ca-pub-4944616437202027[\"']\s+crossorigin=[\"']anonymous[\"']></script>",
        "",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"\s*<script\s+src=[\"']https://fukuokaguide-afgvbgyb\.manus\.space/ad-widget\.js[\"']\s+defer></script>",
        "",
        html,
        flags=re.I,
    )
    return html


def apply_safe_fixes() -> list[str]:
    changed: list[str] = []
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


def build_audit() -> dict:
    articles = sorted(ROOT.glob("blog/*/article-*.html"))
    html_pages = sorted(ROOT.rglob("*.html"))
    records: list[dict] = []
    by_category: dict[str, list[dict]] = defaultdict(list)

    for path in articles:
        html = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        category = path.parent.name
        text = visible_text(html)
        risk_counts = {name: len(rx.findall(html)) for name, rx in RISK_PATTERNS.items()}
        public_links = sum(html.count(hint) for hint in PUBLIC_SOURCE_HINTS)
        rec = {
            "path": rel,
            "category": category,
            "title": title_of(html),
            "visible_chars": len(text),
            "public_source_hints": public_links,
            "risk_counts": risk_counts,
            "has_editorial_info": 'class="editorial-info"' in html,
            "has_reference_links": 'class="reference-links"' in html,
            "has_adsense": ADSENSE in html,
            "is_noindex": bool(re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', html, re.I)),
            "shingles": shingles(text),
        }
        records.append(rec)
        by_category[category].append(rec)

    duplicate_candidates: list[dict] = []
    for category, group in by_category.items():
        for i, left in enumerate(group):
            for right in group[i + 1:]:
                score = similarity(left["shingles"], right["shingles"])
                # タイトルが似ている場合は本文類似度が低めでも候補に出す
                title_left = re.sub(r"[｜|【】\[\]（）()・\s0-9年月日版]", "", left["title"])
                title_right = re.sub(r"[｜|【】\[\]（）()・\s0-9年月日版]", "", right["title"])
                title_score = similarity(shingles(title_left, 3), shingles(title_right, 3))
                if score >= 0.22 or title_score >= 0.46:
                    duplicate_candidates.append({
                        "category": category,
                        "left": left["path"],
                        "right": right["path"],
                        "content_similarity": round(score, 3),
                        "title_similarity": round(title_score, 3),
                    })

    duplicate_candidates.sort(
        key=lambda x: (max(x["content_similarity"], x["title_similarity"]), x["content_similarity"]),
        reverse=True,
    )

    risk_files = []
    for rec in records:
        total = sum(rec["risk_counts"].values())
        if total:
            risk_files.append({
                "path": rec["path"],
                "title": rec["title"],
                "risk_total": total,
                "risk_counts": rec["risk_counts"],
                "public_source_hints": rec["public_source_hints"],
            })
    risk_files.sort(key=lambda x: (x["risk_total"], -x["public_source_hints"]), reverse=True)

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
        "articles": len(articles),
        "categories": dict(Counter(r["category"] for r in records)),
        "noindex_articles": sum(1 for r in records if r["is_noindex"]),
        "articles_without_public_source_hint": sum(1 for r in records if r["public_source_hints"] == 0),
        "articles_without_editorial_info": sum(1 for r in records if not r["has_editorial_info"]),
        "articles_without_reference_links": sum(1 for r in records if not r["has_reference_links"]),
        "non_content_ads_remaining": non_content_ads,
        "duplicate_candidates": duplicate_candidates[:80],
        "risk_files": risk_files[:100],
    }


def write_report(data: dict, changed: list[str]) -> None:
    serializable = json.loads(json.dumps(data, ensure_ascii=False))
    REPORT_JSON.write_text(json.dumps(serializable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# AdSense コンテンツ品質監査（2026-09-04）",
        "",
        "Google AdSense の『有用性の低いコンテンツ』再審査に向け、サイト全体を機械監査した結果です。",
        "",
        "## 全体",
        "",
        f"- HTMLページ数: **{data['html_pages']}**",
        f"- ブログ記事数: **{data['articles']}**",
        f"- noindex記事数: **{data['noindex_articles']}**",
        f"- 公的情報リンクのヒントが0件の記事: **{data['articles_without_public_source_hint']}**",
        f"- 編集情報ブロックがない記事: **{data['articles_without_editorial_info']}**",
        f"- 公式確認先ブロックがない記事: **{data['articles_without_reference_links']}**",
        f"- 非コンテンツページで広告読込が残るページ: **{len(data['non_content_ads_remaining'])}**",
        "",
        "### カテゴリ別記事数",
        "",
    ]
    for category, count in sorted(data["categories"].items()):
        lines.append(f"- {category}: {count}")

    lines += [
        "",
        "## この実行で安全に自動修正したページ",
        "",
    ]
    lines.extend([f"- `{p}`" for p in changed] or ["- なし"])

    lines += [
        "",
        "## 重複・検索意図競合の候補",
        "",
        "本文またはタイトルの類似度が高い順です。自動削除はせず、人手で統合/noindex/canonicalを決めます。",
        "",
        "| 本文類似 | タイトル類似 | ページA | ページB |",
        "|---:|---:|---|---|",
    ]
    for item in data["duplicate_candidates"][:50]:
        lines.append(
            f"| {item['content_similarity']:.3f} | {item['title_similarity']:.3f} | `{item['left']}` | `{item['right']}` |"
        )

    lines += [
        "",
        "## 根拠確認・表現見直しの優先候補",
        "",
        "割合・監修/専門家表示・強い断定などを含むページです。出典が本文の主張を直接支えているか確認します。",
        "",
        "| 指摘数 | 公的リンクヒント | ページ | タイトル |",
        "|---:|---:|---|---|",
    ]
    for item in data["risk_files"][:60]:
        title = item["title"].replace("|", "｜")
        lines.append(f"| {item['risk_total']} | {item['public_source_hints']} | `{item['path']}` | {title} |")

    lines += [
        "",
        "## 次の処置",
        "",
        "1. 類似度が高く検索意図も同じページは、情報量・一次情報・更新日の優れた1ページを残す。",
        "2. 残さないページは `noindex, follow` と残すページへの canonical を設定し、sitemap から外す。",
        "3. 法律・税務・医療/衛生など判断リスクの高い記事は、根拠を一次情報まで追えない場合は一旦 noindex とする。",
        "4. 根拠不明の割合・費用・期間・『おすすめ』『正確』『専門家』等の断定は、出典を直接確認できる場合だけ残す。",
        "5. 新規量産は停止し、既存記事の統合・独自情報追加を優先する。",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    changed = apply_safe_fixes()
    data = build_audit()
    write_report(data, changed)
    print(json.dumps({
        "changed_pages": len(changed),
        "articles": data["articles"],
        "duplicate_candidates": len(data["duplicate_candidates"]),
        "risk_files": len(data["risk_files"]),
        "report": str(REPORT_MD.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
