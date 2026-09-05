from __future__ import annotations

from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
SITE = "https://fukuoka-ihinseiri-guide.com"
ADSENSE_RE = re.compile(
    r"\s*<script\s+async\s+src=[\"']https://pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js\?client=ca-pub-4944616437202027[\"']\s+crossorigin=[\"']anonymous[\"']></script>",
    re.I,
)
AD_WIDGET_RE = re.compile(
    r"\s*<script\s+src=[\"']https://fukuokaguide-afgvbgyb\.manus\.space/ad-widget\.js[\"']\s+defer></script>",
    re.I,
)

# 検索意図がほぼ同じで、後発・集約ページへ統合するもの。
DUPLICATE_REDIRECTS = {
    "/blog/area/article-20260706-kitakyushu-guide.html": "/blog/area/article-20260714-kitakyushu-ihinseiri-guide.html",
    "/blog/area/article-20260711-chikushino-onojo-kasuga.html": "/blog/area/article-20260722-chikushino-onojo-kasuga-guide.html",
    "/blog/cost/article-20260706-cost-saving-tips.html": "/blog/cost/article-20260707-cost-yasuku-suru.html",
    "/blog/cost/article-20260804-hiyou-yasuku-suru-houhou.html": "/blog/cost/article-20260707-cost-yasuku-suru.html",
    "/blog/kuyo/article-20260706-butsudan-shobun.html": "/blog/kuyo/article-20260805-butsudan-shobun-kuyo-tejun.html",
    "/blog/kuyo/article-20260708-butsudan-shobun-houhou.html": "/blog/kuyo/article-20260805-butsudan-shobun-kuyo-tejun.html",
    "/blog/kuyo/article-20260712-butsudan-shobun-houhou.html": "/blog/kuyo/article-20260805-butsudan-shobun-kuyo-tejun.html",
    "/blog/kuyo/article-20260718-butsudan-shobun-heigan.html": "/blog/kuyo/article-20260805-butsudan-shobun-kuyo-tejun.html",
}

# 法律・税務・感染症など、資格者監修なしで検索流入・広告対象にするにはリスクが高いページ。
# 削除はせず、内容を再監修できるまで noindex + 広告停止。
HIGH_RISK_HOLD = {
    "/blog/ihinseiri/article-20260719-souzoku-houki-ihinseiri.html",
    "/blog/cost/article-20260708-souzokuzei-koujo.html",
    "/blog/cost/article-20260711-souzoku-tetsuzuki-kigen.html",
    "/blog/cost/article-20260715-seikatsu-hogo-ihinseiri.html",
    "/blog/tokushu-seisou/article-20260715-kansenshou-shoudoku.html",
}

TEXT_REPLACEMENTS = {
    "完全ガイド": "ガイド",
    "徹底解説": "解説",
    "徹底比較": "比較",
    "まで網羅": "まで整理",
    "を網羅": "を整理",
    "悪徳業者を見抜く": "契約トラブルを避ける",
    "悪徳業者": "トラブルにつながる業者",
    "適正価格の判断基準": "見積もりを確認するポイント",
    "相場より3割節約できる具体的テクニック": "費用を抑えるための具体的な方法",
    "相場より3割節約": "費用を抑える",
    "失敗しない業者の選び方": "業者選びで確認したいポイント",
    "おすすめ業者": "業者",
}


def rel_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[:-10]
    return "/" + rel


def set_noindex(html: str) -> str:
    robots_rx = re.compile(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>', re.I)
    tag = '<meta name="robots" content="noindex, follow, max-image-preview:large">'
    if robots_rx.search(html):
        return robots_rx.sub(tag, html, count=1)
    return html.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n  ' + tag, 1)


def remove_ads(html: str) -> str:
    html = ADSENSE_RE.sub("", html)
    html = AD_WIDGET_RE.sub("", html)
    return html


def normalize_overclaim_language() -> list[str]:
    changed = []
    for path in sorted(ROOT.rglob("*.html")):
        old = path.read_text(encoding="utf-8")
        html = old
        for before, after in TEXT_REPLACEMENTS.items():
            html = html.replace(before, after)
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def fix_known_unsupported_claims() -> list[str]:
    changed = []
    path = ROOT / "blog/ihinseiri/article-20260706-jibun-vs-gyousha.html"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        html = re.sub(
            r'<p><a href="https://www\.mhlw\.go\.jp/"[^>]*>厚生労働省</a>の調査によると、遺品整理を経験した方の約60%が「自分（家族）で行った」と回答しており、残りの約40%が「業者に依頼した」または「一部を業者に依頼した」と回答しています。.*?</p>',
            '<p>自分で行うか業者に依頼するかは、部屋の広さ、荷物の量、退去期限、作業できる人数、体力、遠方からの移動負担などを踏まえて判断する必要があります。割合だけで一般化せず、ご自身の状況で安全に完了できるかを基準にしてください。</p>',
            old,
            flags=re.S,
        )
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def hold_high_risk_pages() -> list[str]:
    changed = []
    for url in sorted(HIGH_RISK_HOLD):
        path = ROOT / url.lstrip("/")
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        html = remove_ads(set_noindex(old))
        notice = (
            '<div class="content-review-notice" style="margin:20px 0;padding:16px;border:1px solid #ddd;border-radius:8px;">'
            '<strong>個別判断が必要な内容について</strong>'
            '<p style="margin:8px 0 0;">この記事は一般的な情報整理を目的としています。法律・税務・衛生上の判断は個別事情で異なるため、実行前に記事内の公的機関または資格を持つ専門家へ確認してください。</p>'
            '</div>'
        )
        if "content-review-notice" not in html:
            html = html.replace("<article", notice + "\n      <article", 1) if "<article" in html else html.replace("<main", notice + "\n  <main", 1)
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def update_redirects() -> None:
    path = ROOT / "_redirects"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = "# AdSense quality consolidation 2026-09-04"
    lines = [marker]
    for source, target in sorted(DUPLICATE_REDIRECTS.items()):
        lines.append(f"{source} {target} 301")
    block = "\n".join(lines) + "\n"
    if marker in text:
        text = re.sub(r"# AdSense quality consolidation 2026-09-04\n(?:/.*\n)*", block, text)
    else:
        text = text.rstrip() + "\n\n" + block
    path.write_text(text, encoding="utf-8")


def remove_urls_from_sitemap() -> list[str]:
    path = ROOT / "sitemap.xml"
    xml = path.read_text(encoding="utf-8")
    removed = []
    excluded = set(DUPLICATE_REDIRECTS) | set(HIGH_RISK_HOLD)
    for url in sorted(excluded):
        absolute = SITE + url
        pattern = re.compile(r"\s*<url>\s*<loc>" + re.escape(absolute) + r"</loc>.*?</url>", re.S)
        xml, count = pattern.subn("", xml)
        if count:
            removed.append(url)
    path.write_text(xml, encoding="utf-8")
    return removed


def remove_cards_from_index_pages() -> list[str]:
    changed = []
    excluded = set(DUPLICATE_REDIRECTS) | set(HIGH_RISK_HOLD)
    candidate_pages = [ROOT / "index.html", ROOT / "blog/index.html"] + list((ROOT / "blog").glob("*/index.html"))
    for path in candidate_pages:
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        html = old
        for url in excluded:
            # article-card のアンカーブロックを除去。テンプレート差異を許容。
            html = re.sub(
                r'\s*<a\s+href=["\']' + re.escape(url) + r'["\'][^>]*class=["\'][^"\']*article-card[^"\']*["\'][^>]*>.*?</a>',
                "",
                html,
                flags=re.S | re.I,
            )
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def update_search_data() -> bool:
    path = ROOT / "js/search-data.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    excluded = set(DUPLICATE_REDIRECTS) | set(HIGH_RISK_HOLD)
    if isinstance(data, list):
        new_data = [item for item in data if not (isinstance(item, dict) and item.get("url") in excluded)]
    elif isinstance(data, dict):
        new_data = data.copy()
        for key, value in list(new_data.items()):
            if isinstance(value, list):
                new_data[key] = [item for item in value if not (isinstance(item, dict) and item.get("url") in excluded)]
    else:
        return False
    if new_data != data:
        path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True
    return False


def write_decision_log(summary: dict) -> None:
    path = ROOT / "docs/ADSENSE_CONSOLIDATION_DECISIONS_20260904.md"
    lines = [
        "# AdSense コンテンツ統合判断（2026-09-04）",
        "",
        "## 301統合",
        "",
        "検索意図が重なるページを複数残すのではなく、代表ページに集約します。",
        "",
    ]
    for source, target in sorted(DUPLICATE_REDIRECTS.items()):
        lines.append(f"- `{source}` → `{target}`")
    lines += [
        "",
        "## 一時 noindex・広告停止",
        "",
        "資格者監修なしで断定すると誤解や不利益につながり得る法律・税務・感染症関連ページです。削除せず、内容の再確認が済むまで検索・広告対象から外します。",
        "",
    ]
    for url in sorted(HIGH_RISK_HOLD):
        lines.append(f"- `{url}`")
    lines += [
        "",
        "## 実施結果",
        "",
        f"- 誇張表現の正規化: {summary['language_pages']}ページ",
        f"- 根拠不明の既知統計を削除: {summary['claim_pages']}ページ",
        f"- 高リスク保留: {summary['hold_pages']}ページ",
        f"- sitemapから除外: {summary['sitemap_removed']} URL",
        f"- 一覧カードから除外: {summary['index_pages']}ページ",
        f"- 検索データ更新: {'実施' if summary['search_data'] else '変更なし'}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    language = normalize_overclaim_language()
    claims = fix_known_unsupported_claims()
    held = hold_high_risk_pages()
    update_redirects()
    removed = remove_urls_from_sitemap()
    index_pages = remove_cards_from_index_pages()
    search_changed = update_search_data()
    summary = {
        "language_pages": len(language),
        "claim_pages": len(claims),
        "hold_pages": len(held),
        "sitemap_removed": len(removed),
        "index_pages": len(index_pages),
        "search_data": search_changed,
    }
    write_decision_log(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
