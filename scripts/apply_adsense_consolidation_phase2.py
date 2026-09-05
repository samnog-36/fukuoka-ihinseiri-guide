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

# Phase 2: additional clusters whose search intent substantially overlaps.
REDIRECTS = {
    "/blog/area/article-20260707-higashi-ku-guide.html": "/blog/area/article-20260805-fukuokashi-hakata-higashi-chuo.html",
    "/blog/area/article-20260708-hakata-ku-guide.html": "/blog/area/article-20260805-fukuokashi-hakata-higashi-chuo.html",
    "/blog/area/article-20260706-minami-ku.html": "/blog/area/article-20260719-minami-jonan-ku-guide.html",
    "/blog/area/article-20260706-kurume.html": "/blog/area/article-20260713-kurume-ogori-tosu.html",
    "/blog/cost/article-20260712-ihinseiri-hiyo-yasuku.html": "/blog/cost/article-20260707-cost-yasuku-suru.html",
    "/blog/cost/article-20260706-mitsumori-hikaku.html": "/blog/cost/article-20260803-mitsumorisho-mikata.html",
    "/blog/ihinseiri/article-20260706-mitsumori-point.html": "/blog/cost/article-20260803-mitsumorisho-mikata.html",
    "/blog/ihinseiri/article-20260718-mitsumori-hikaku-checklist.html": "/blog/cost/article-20260803-mitsumorisho-mikata.html",
    "/blog/kuyo/article-20260706-otakiage-hikaku.html": "/blog/kuyo/article-20260809-otakiage-ryoukin-hikaku.html",
    "/blog/kuyo/article-20260707-shashin-kuyo.html": "/blog/kuyo/article-20260806-shashin-tegami-omoide-kuyo.html",
    "/blog/seizenseiri/article-20260706-ending-note.html": "/blog/seizenseiri/article-20260805-ending-note-kakikata-guide.html",
    "/blog/seizenseiri/article-20260709-ending-note-kakikata.html": "/blog/seizenseiri/article-20260805-ending-note-kakikata-guide.html",
    "/blog/tokushu-seisou/article-20260709-kodokushi-hakken-taiou.html": "/blog/tokushu-seisou/article-20260718-kodokushi-hakken-taiou.html",
}

# Legal responsibility around who must pay can materially affect users; keep available by direct URL
# but remove from Search/ads until professionally reviewed.
HIGH_RISK_HOLD = {
    "/blog/tokushu-seisou/article-20260805-kodokushi-hiyou-dare-ga-harau.html",
}

HUB_EXACT_REPLACEMENTS = {
    "guide/index.html": {
        "遺品整理お役立ちガイド｜福岡の専門家が教える完全マニュアル": "遺品整理お役立ちガイド｜福岡で確認したい手続き・費用・業者選び",
        "福岡県の遺品整理に関するお役立ち情報を整理。業者の選び方、特殊清掃、生前整理、遺品供養まで専門家が分かりやすく解説。": "福岡県の遺品整理に関するお役立ち情報を整理。業者選び、特殊清掃、生前整理、遺品供養について、公的な確認先とあわせて分かりやすく案内します。",
    },
    "guide/tokushu-seisou.html": {
        "特殊清掃 福岡｜費用相場・業者の選び方・孤独死現場の対応を専門家が解説【2026年最新】": "特殊清掃 福岡｜費用の考え方・作業の流れ・業者選びの確認ポイント",
        "福岡県の特殊清掃を解説。孤独死・ゴミ屋敷・事故現場の費用相場（1K：8万円〜）、作業の流れ、信頼できる業者の選び方5つの基準、保険適用の条件まで。福岡の専門家が実例を交えて紹介。": "福岡県の特殊清掃について、費用が変わる要因、作業の流れ、事業者選びで確認したい項目、公的な相談先を整理します。料金は汚染範囲や搬出条件などで大きく変わるため、現地確認後の見積もりで比較してください。",
        "福岡県の特殊清掃を解説。孤独死・ゴミ屋敷・事故現場の費用相場、作業の流れ、信頼できる業者の選び方、保険適用の条件まで専門家が紹介。": "福岡県の特殊清掃について、費用が変わる要因、作業の流れ、事業者選びで確認したい項目、公的な相談先を整理します。",
    },
    "guide/seizenseiri.html": {
        "生前整理の始め方｜やることリスト・費用相場・プロが教える進め方【福岡版】": "生前整理の始め方｜やることリスト・費用の考え方・進め方【福岡版】",
        "生前整理を始めたい方必見。50代・60代から始める具体的な手順、やることリスト、費用相場（1K：3万円〜）、エンディングノートの書き方をプロが解説。福岡県内の無料相談窓口も紹介。": "生前整理を始めたい方へ。50代・60代から進める手順、やることリスト、費用が変わる要因、エンディングノートの考え方、福岡県内の公的な相談先を整理します。",
        "生前整理を始めたい方必見。50代・60代から始める具体的な手順、やることリスト、費用相場、エンディングノートの書き方をプロが解説。福岡県内の無料相談窓口も紹介。": "生前整理を始めたい方へ。50代・60代から進める手順、やることリスト、費用が変わる要因、エンディングノートの考え方、福岡県内の公的な相談先を整理します。",
        "A. 福岡での生前整理サービスの費用相場は、1K・1DKで3万〜8万円、2LDKで8万〜20万円、3LDK以上で15万〜40万円です。物量や作業内容により変動します。": "A. 料金は間取りだけでなく、物量、搬出条件、処分品、作業人数、買取の有無、追加作業などで大きく変わります。間取りだけで一律に判断せず、作業範囲と追加料金条件をそろえた複数社の現地見積もりで比較してください。",
    },
    "guide/kuyo.html": {
        "福岡県での遺品供養の方法を完全解説。お焚き上げの費用比較、仏壇・神棚の処分方法、捨てられない遺品の供養先を紹介。": "福岡県で遺品供養を考える際の確認事項を整理。お焚き上げ、仏壇・神棚の扱い、思い出の品の供養について、方法と費用が変わる要因を案内します。",
    },
}

GLOBAL_TRUST_REPLACEMENTS = {
    "専門家が分かりやすく解説": "公的情報を確認しながら分かりやすく解説",
    "専門家が解説": "公的情報をもとに解説",
    "専門家が紹介": "公的情報をもとに紹介",
    "福岡の専門家が実例を交えて紹介": "公的情報と一般的な確認ポイントをもとに紹介",
    "プロが解説": "確認ポイントを解説",
    "プロが教える": "確認したい",
}


def set_noindex(html: str) -> str:
    rx = re.compile(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>', re.I)
    tag = '<meta name="robots" content="noindex, follow, max-image-preview:large">'
    if rx.search(html):
        return rx.sub(tag, html, count=1)
    return html.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n  ' + tag, 1)


def remove_ads(html: str) -> str:
    return AD_WIDGET_RE.sub("", ADSENSE_RE.sub("", html))


def apply_redirects() -> None:
    path = ROOT / "_redirects"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = "# AdSense quality consolidation phase 2 2026-09-04"
    block = [marker] + [f"{src} {dst} 301" for src, dst in sorted(REDIRECTS.items())]
    new_block = "\n".join(block) + "\n"
    if marker in text:
        text = re.sub(r"# AdSense quality consolidation phase 2 2026-09-04\n(?:/.*\n)*", new_block, text)
    else:
        text = text.rstrip() + "\n\n" + new_block
    path.write_text(text, encoding="utf-8")


def hold_high_risk() -> list[str]:
    changed: list[str] = []
    notice = (
        '<div class="content-review-notice" style="margin:20px 0;padding:16px;border:1px solid #ddd;border-radius:8px;">'
        '<strong>個別判断が必要な内容について</strong>'
        '<p style="margin:8px 0 0;">費用負担や契約上の責任は、契約内容・相続状況・保証関係などで結論が変わります。この記事は一般情報として残していますが、実際の判断は契約書を確認し、必要に応じて弁護士・司法書士・管理会社などへ確認してください。</p>'
        '</div>'
    )
    for url in sorted(HIGH_RISK_HOLD):
        path = ROOT / url.lstrip("/")
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        html = remove_ads(set_noindex(old))
        if "content-review-notice" not in html:
            html = html.replace("<article", notice + "\n      <article", 1) if "<article" in html else html.replace("<main", notice + "\n  <main", 1)
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def fix_hubs() -> list[str]:
    changed: list[str] = []
    for rel, replacements in HUB_EXACT_REPLACEMENTS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        html = old
        for before, after in replacements.items():
            html = html.replace(before, after)
        # Hub pages are evergreen navigation/reference pages rather than authored expert articles.
        html = html.replace('"@type": "Article"', '"@type": "WebPage"', 1)
        html = re.sub(r'^\s*"datePublished":\s*"[^"]+",\s*$', '', html, flags=re.M)
        html = re.sub(r'^\s*"dateModified":\s*"[^"]+",\s*$', '', html, flags=re.M)
        for before, after in GLOBAL_TRUST_REPLACEMENTS.items():
            html = html.replace(before, after)
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed.append(rel)

    # Clean residual expert wording across all pages without touching legitimate terms such as 専門業者.
    for path in sorted(ROOT.rglob("*.html")):
        old = path.read_text(encoding="utf-8")
        html = old
        for before, after in GLOBAL_TRUST_REPLACEMENTS.items():
            html = html.replace(before, after)
        if html != old:
            path.write_text(html, encoding="utf-8")
            rel = path.relative_to(ROOT).as_posix()
            if rel not in changed:
                changed.append(rel)
    return changed


def excluded_urls() -> set[str]:
    return set(REDIRECTS) | set(HIGH_RISK_HOLD)


def remove_sitemap_entries() -> int:
    path = ROOT / "sitemap.xml"
    xml = path.read_text(encoding="utf-8")
    removed = 0
    for url in sorted(excluded_urls()):
        absolute = SITE + url
        rx = re.compile(r"\s*<url>\s*<loc>" + re.escape(absolute) + r"</loc>.*?</url>", re.S)
        xml, count = rx.subn("", xml)
        removed += count
    path.write_text(xml, encoding="utf-8")
    return removed


def remove_cards() -> int:
    count_pages = 0
    pages = [ROOT / "index.html", ROOT / "blog/index.html"] + list((ROOT / "blog").glob("*/index.html")) + list((ROOT / "guide").glob("*.html"))
    for path in pages:
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        html = old
        for url in excluded_urls():
            html = re.sub(
                r'\s*<a\s+href=["\']' + re.escape(url) + r'["\'][^>]*class=["\'][^"\']*article-card[^"\']*["\'][^>]*>.*?</a>',
                "",
                html,
                flags=re.S | re.I,
            )
        if html != old:
            path.write_text(html, encoding="utf-8")
            count_pages += 1
    return count_pages


def update_search_data() -> bool:
    path = ROOT / "js/search-data.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    excluded = excluded_urls()

    def clean(value):
        if isinstance(value, list):
            return [clean(v) for v in value if not (isinstance(v, dict) and v.get("url") in excluded)]
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        return value

    new_data = clean(data)
    if new_data != data:
        path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True
    return False


def clean_feed() -> int:
    path = ROOT / "feed.xml"
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    removed = 0
    for url in excluded_urls():
        absolute = SITE + url
        rx = re.compile(r"\s*<item>.*?<link>" + re.escape(absolute) + r"</link>.*?</item>", re.S)
        text, count = rx.subn("", text)
        removed += count
    path.write_text(text, encoding="utf-8")
    return removed


def clean_llms() -> int:
    path = ROOT / "llms.txt"
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    changed = 0
    for source, target in REDIRECTS.items():
        old = SITE + source
        new = SITE + target
        if old in text:
            text = text.replace(old, new)
            changed += 1
    # Remove exact duplicate lines created by target replacement.
    seen = set()
    out = []
    for line in text.splitlines():
        if line in seen and line.strip().startswith("-"):
            continue
        seen.add(line)
        out.append(line)
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return changed


def write_log(summary: dict) -> None:
    path = ROOT / "docs/ADSENSE_CONSOLIDATION_PHASE2_20260904.md"
    lines = [
        "# AdSense コンテンツ統合 Phase 2（2026-09-04）",
        "",
        "## 追加の301統合",
        "",
    ]
    lines += [f"- `{s}` → `{t}`" for s, t in sorted(REDIRECTS.items())]
    lines += [
        "",
        "## 追加の一時 noindex・広告停止",
        "",
    ]
    lines += [f"- `{u}`" for u in sorted(HIGH_RISK_HOLD)]
    lines += [
        "",
        "## ハブページの信頼性修正",
        "",
        "- 実態を確認できない『専門家』『プロが解説』表現を削除・中立化",
        "- 根拠のない固定料金を、料金が変わる要因と複数見積もりの案内へ変更",
        "- ガイド一覧/ハブの構造化データを Article から WebPage へ整理し、根拠不明の公開日を削除",
        "",
        "## 実施結果",
        "",
        f"- ハブ/信頼性表現修正: {summary['hub_pages']}ページ",
        f"- 高リスク保留: {summary['held_pages']}ページ",
        f"- sitemap除外: {summary['sitemap_removed']}件",
        f"- 一覧カード更新: {summary['card_pages']}ページ",
        f"- 検索データ更新: {'実施' if summary['search_data'] else '変更なし'}",
        f"- feed除外: {summary['feed_removed']}件",
        f"- llms.txt URL更新: {summary['llms_changed']}件",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    apply_redirects()
    held = hold_high_risk()
    hubs = fix_hubs()
    summary = {
        "hub_pages": len(hubs),
        "held_pages": len(held),
        "sitemap_removed": remove_sitemap_entries(),
        "card_pages": remove_cards(),
        "search_data": update_search_data(),
        "feed_removed": clean_feed(),
        "llms_changed": clean_llms(),
    }
    write_log(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
