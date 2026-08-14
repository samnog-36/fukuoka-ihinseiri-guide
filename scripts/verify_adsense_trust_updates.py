from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/ubuntu/fukuoka-guide-new")
ARTICLES = sorted(ROOT.glob("blog/*/article-*.html"))


def main() -> int:
    issues: list[str] = []
    if len(ARTICLES) == 0:
        issues.append("記事が見つかりません")

    for article in ARTICLES:
        content = article.read_text(encoding="utf-8")
        relative = article.relative_to(ROOT)
        for needle, label in (
            ('class="editorial-info"', "編集情報"),
            ('class="reference-links"', "公式確認先"),
        ):
            if content.count(needle) != 1:
                issues.append(f"{relative}: {label}の件数が{content.count(needle)}件です")
        if 'href="/about.html"' not in content:
            issues.append(f"{relative}: 編集方針リンクがありません")
        if '福岡遺品整理ガイド編集部' not in content:
            issues.append(f"{relative}: 編集部名がありません")
        if content.find('class="editorial-info"') > content.rfind("</main>"):
            issues.append(f"{relative}: 編集情報がmain要素の外です")
        if content.find('class="reference-links"') > content.rfind("</main>"):
            issues.append(f"{relative}: 公式確認先がmain要素の外です")

    about = ROOT / "about.html"
    if not about.exists():
        issues.append("about.htmlがありません")
    else:
        about_content = about.read_text(encoding="utf-8")
        for needle in (
            "編集方針・運営情報",
            'href="/contact/"',
            'href="/privacy-policy.html"',
            "ca-pub-4944616437202027",
        ):
            if needle not in about_content:
                issues.append(f"about.htmlに「{needle}」がありません")

    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    if sitemap.count("https://fukuoka-ihinseiri-guide.com/about.html") != 1:
        issues.append("sitemap.xmlのabout.html URLが1件ではありません")

    every_html = list(ROOT.rglob("*.html"))
    missing_footer_link = [str(p.relative_to(ROOT)) for p in every_html if 'href="/about.html"' not in p.read_text(encoding="utf-8")]
    if missing_footer_link:
        issues.append("編集方針リンクのないHTML: " + ", ".join(missing_footer_link))

    print(f"記事数: {len(ARTICLES)}")
    print(f"HTML数: {len(every_html)}")
    if issues:
        print("検証失敗:")
        print("\n".join(f"- {issue}" for issue in issues))
        return 1
    print("検証成功: 編集方針ページ、全記事の編集情報・公式確認先、共通導線、サイトマップは整合しています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
