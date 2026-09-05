from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ARTICLES = sorted(ROOT.glob("blog/*/article-*.html"))
NON_CONTENT_PAGES = [
    ROOT / "about.html",
    ROOT / "privacy-policy.html",
    ROOT / "contact/index.html",
    ROOT / "for-business/index.html",
]
ADSENSE_MARKER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"


def main() -> int:
    issues: list[str] = []
    if not ARTICLES:
        issues.append("記事が見つかりません")

    for article in ARTICLES:
        content = article.read_text(encoding="utf-8")
        relative = article.relative_to(ROOT)
        if 'href="/about.html"' not in content:
            issues.append(f"{relative}: 編集方針リンクがありません")
        if "福岡遺品整理ガイド編集部" not in content:
            issues.append(f"{relative}: 編集主体の表示がありません")
        if "弁護士監修レベル" in content:
            issues.append(f"{relative}: 実監修と誤認される『弁護士監修レベル』が残っています")

    about = ROOT / "about.html"
    if not about.exists():
        issues.append("about.htmlがありません")
    else:
        about_content = about.read_text(encoding="utf-8")
        for needle in (
            "編集方針・運営情報",
            "記事の作成・確認方法",
            "業者掲載・紹介の基準",
            'href="/contact/"',
            'href="/privacy-policy.html"',
        ):
            if needle not in about_content:
                issues.append(f"about.htmlに「{needle}」がありません")
        if ADSENSE_MARKER in about_content:
            issues.append("about.htmlでAdSenseを読み込んでいます")

    for page in NON_CONTENT_PAGES:
        if not page.exists():
            issues.append(f"{page.relative_to(ROOT)} がありません")
            continue
        content = page.read_text(encoding="utf-8")
        if ADSENSE_MARKER in content:
            issues.append(f"{page.relative_to(ROOT)}: 非コンテンツページでAdSenseを読み込んでいます")

    privacy = ROOT / "privacy-policy.html"
    if privacy.exists():
        content = privacy.read_text(encoding="utf-8")
        expected = '<link rel="alternate" hreflang="ja" href="https://fukuoka-ihinseiri-guide.com/privacy-policy.html">'
        if expected not in content:
            issues.append("privacy-policy.html: hreflangが自己URLを指していません")

    ads_txt = ROOT / "ads.txt"
    if not ads_txt.exists() or "pub-4944616437202027" not in ads_txt.read_text(encoding="utf-8"):
        issues.append("ads.txtがない、またはPublisher IDが一致しません")

    every_html = list(ROOT.rglob("*.html"))
    missing_footer_link: list[str] = []
    for page in every_html:
        page_content = page.read_text(encoding="utf-8")
        footer_start = page_content.rfind("<footer")
        if footer_start != -1 and 'href="/about.html"' not in page_content[footer_start:]:
            missing_footer_link.append(str(page.relative_to(ROOT)))
    if missing_footer_link:
        issues.append("編集方針リンクのないHTML: " + ", ".join(missing_footer_link))

    print(f"記事数: {len(ARTICLES)}")
    print(f"HTML数: {len(every_html)}")
    if issues:
        print("検証失敗:")
        print("\n".join(f"- {issue}" for issue in issues))
        return 1
    print("検証成功: AdSense再審査向けの信頼性・非コンテンツ広告・共通導線の基礎条件を満たしています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
