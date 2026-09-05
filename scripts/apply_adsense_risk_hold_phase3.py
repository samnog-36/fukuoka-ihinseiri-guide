from __future__ import annotations

from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
SITE = "https://fukuoka-ihinseiri-guide.com"
ADSENSE_RE = re.compile(
    r"\s*<script\s+async\s+src=[\"']https://pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js\?client=ca-pub-4944616437202027[\"']\s+crossorigin=[\"']anonymous[\"']></script>", re.I,
)
AD_WIDGET_RE = re.compile(
    r"\s*<script\s+src=[\"']https://fukuokaguide-afgvbgyb\.manus\.space/ad-widget\.js[\"']\s+defer></script>", re.I,
)

REDIRECTS = {
    "/blog/ihinseiri/article-20260707-chintai-taijo.html": "/blog/ihinseiri/article-20260803-chintai-ihinseiri.html",
}

# Keep these pages accessible for existing links, but remove them from Search and ad inventory
# until their technical/legal claims receive article-specific review.
HIGH_RISK_HOLD = {
    "/blog/tokushu-seisou/article-20260708-pet-tokushu-seisou.html",
    "/blog/tokushu-seisou/article-20260711-kasai-fukkyuu-seisou.html",
    "/blog/tokushu-seisou/article-20260712-suigai-shinsui-fukkyuu.html",
    "/blog/tokushu-seisou/article-20260713-ozone-dasshuu-shikumi.html",
    "/blog/tokushu-seisou/article-20260714-pet-tatougai-houkai.html",
    "/blog/tokushu-seisou/article-20260804-nioi-taisaku-kanzen.html",
    "/blog/tokushu-seisou/article-20260806-gaichuu-kujyo-ujimushi-hae.html",
    "/blog/ihinseiri/article-20260803-chintai-ihinseiri.html",
    "/blog/ihinseiri/article-20260805-kichouhin-genkin-toriatsukai.html",
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
    marker = "# AdSense risk hold phase 3 2026-09-04"
    block = marker + "\n" + "\n".join(f"{src} {dst} 301" for src, dst in sorted(REDIRECTS.items())) + "\n"
    if marker in text:
        text = re.sub(r"# AdSense risk hold phase 3 2026-09-04\n(?:/.*\n)*", block, text)
    else:
        text = text.rstrip() + "\n\n" + block
    path.write_text(text, encoding="utf-8")


def hold_pages() -> list[str]:
    changed = []
    notice = (
        '<div class="content-review-notice" style="margin:20px 0;padding:16px;border:1px solid #ddd;border-radius:8px;">'
        '<strong>この記事は内容を再確認中です</strong>'
        '<p style="margin:8px 0 0;">技術・衛生・契約・相続など個別条件で判断が変わる内容を含むため、検索・広告対象から一時的に外しています。実際の対応は公的機関、管理会社、または該当分野の資格・専門知識を持つ事業者へ確認してください。</p>'
        '</div>'
    )
    for url in sorted(HIGH_RISK_HOLD):
        path = ROOT / url.lstrip("/")
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        html = remove_ads(set_noindex(old))
        if "content-review-notice" not in html:
            if "<article" in html:
                html = html.replace("<article", notice + "\n      <article", 1)
            elif "<main" in html:
                html = html.replace("<main", notice + "\n  <main", 1)
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def excluded() -> set[str]:
    return set(REDIRECTS) | set(HIGH_RISK_HOLD)


def clean_sitemap() -> int:
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    removed = 0
    for url in excluded():
        rx = re.compile(r"\s*<url>\s*<loc>" + re.escape(SITE + url) + r"</loc>.*?</url>", re.S)
        text, n = rx.subn("", text)
        removed += n
    path.write_text(text, encoding="utf-8")
    return removed


def clean_listings() -> int:
    pages = [ROOT / "index.html", ROOT / "blog/index.html"] + list((ROOT / "blog").glob("*/index.html")) + list((ROOT / "guide").glob("*.html"))
    changed = 0
    for path in pages:
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        html = old
        for url in excluded():
            html = re.sub(
                r'\s*<a\s+href=["\']' + re.escape(url) + r'["\'][^>]*class=["\'][^"\']*article-card[^"\']*["\'][^>]*>.*?</a>',
                "", html, flags=re.S | re.I,
            )
        if html != old:
            path.write_text(html, encoding="utf-8")
            changed += 1
    return changed


def clean_search_data() -> bool:
    path = ROOT / "js/search-data.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    blocked = excluded()

    def clean(value):
        if isinstance(value, list):
            return [clean(x) for x in value if not (isinstance(x, dict) and x.get("url") in blocked)]
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        return value

    new = clean(data)
    if new != data:
        path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True
    return False


def clean_feed() -> int:
    path = ROOT / "feed.xml"
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    removed = 0
    for url in excluded():
        rx = re.compile(r"\s*<item>.*?<link>" + re.escape(SITE + url) + r"</link>.*?</item>", re.S)
        text, n = rx.subn("", text)
        removed += n
    path.write_text(text, encoding="utf-8")
    return removed


def clean_llms() -> int:
    path = ROOT / "llms.txt"
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    blocked_absolute = {SITE + url for url in HIGH_RISK_HOLD}
    redirect_map = {SITE + src: SITE + dst for src, dst in REDIRECTS.items()}
    out = []
    changed = 0
    seen = set()
    for line in lines:
        if any(url in line for url in blocked_absolute):
            changed += 1
            continue
        for src, dst in redirect_map.items():
            if src in line:
                line = line.replace(src, dst)
                changed += 1
        if line in seen and line.strip().startswith("-"):
            continue
        seen.add(line)
        out.append(line)
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return changed


def write_log(summary: dict) -> None:
    path = ROOT / "docs/ADSENSE_RISK_HOLD_PHASE3_20260904.md"
    lines = ["# AdSense リスク保留 Phase 3（2026-09-04）", "", "## 追加301統合", ""]
    lines += [f"- `{s}` → `{t}`" for s, t in sorted(REDIRECTS.items())]
    lines += ["", "## 一時 noindex・広告停止", ""]
    lines += [f"- `{u}`" for u in sorted(HIGH_RISK_HOLD)]
    lines += ["", "## 理由", "",
              "技術・衛生・契約・相続など、AI生成の一般論だけでは読者が誤判断する可能性がある記事を、記事単位の根拠確認が済むまで検索・広告対象から外しました。ページ自体は削除せず、既存リンクから閲覧できます。", "",
              "## 実施結果", "",
              f"- 保留ページ更新: {summary['held']}ページ",
              f"- sitemap除外: {summary['sitemap']}件",
              f"- 一覧更新: {summary['listings']}ページ",
              f"- 検索データ更新: {'実施' if summary['search'] else '変更なし'}",
              f"- feed除外: {summary['feed']}件",
              f"- llms.txt更新: {summary['llms']}件", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    apply_redirects()
    held = hold_pages()
    summary = {
        "held": len(held),
        "sitemap": clean_sitemap(),
        "listings": clean_listings(),
        "search": clean_search_data(),
        "feed": clean_feed(),
        "llms": clean_llms(),
    }
    write_log(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
