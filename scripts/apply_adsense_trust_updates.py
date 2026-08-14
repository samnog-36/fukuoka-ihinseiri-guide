from __future__ import annotations

from pathlib import Path
import re


ROOT = Path("/home/ubuntu/fukuoka-guide-new")
TODAY = "2026-08-14"
CSS_VERSION = "20260814a"


SOURCES = {
    "ihinseiri": [
        ("環境省｜廃棄物・リサイクル対策", "https://www.env.go.jp/recycle/"),
        ("国民生活センター｜くらしの相談", "https://www.kokusen.go.jp/"),
        ("法務省｜民事局（相続・遺言に関する制度）", "https://www.moj.go.jp/MINJI/minji07.html"),
    ],
    "tokushu-seisou": [
        ("環境省｜廃棄物・リサイクル対策", "https://www.env.go.jp/recycle/"),
        ("国民生活センター｜くらしの相談", "https://www.kokusen.go.jp/"),
        ("福岡県｜公式サイト", "https://www.pref.fukuoka.lg.jp/"),
    ],
    "seizenseiri": [
        ("法務省｜民事局（相続・遺言に関する制度）", "https://www.moj.go.jp/MINJI/minji07.html"),
        ("国税庁｜相続税", "https://www.nta.go.jp/taxes/shiraberu/sozoku-tokushu/index.htm"),
        ("国民生活センター｜くらしの相談", "https://www.kokusen.go.jp/"),
    ],
    "kuyo": [
        ("環境省｜廃棄物・リサイクル対策", "https://www.env.go.jp/recycle/"),
        ("福岡県｜公式サイト", "https://www.pref.fukuoka.lg.jp/"),
        ("国民生活センター｜くらしの相談", "https://www.kokusen.go.jp/"),
    ],
    "cost": [
        ("国民生活センター｜くらしの相談", "https://www.kokusen.go.jp/"),
        ("環境省｜廃棄物・リサイクル対策", "https://www.env.go.jp/recycle/"),
        ("国税庁｜相続税", "https://www.nta.go.jp/taxes/shiraberu/sozoku-tokushu/index.htm"),
    ],
    "area": [
        ("福岡県｜公式サイト", "https://www.pref.fukuoka.lg.jp/"),
        ("環境省｜廃棄物・リサイクル対策", "https://www.env.go.jp/recycle/"),
        ("国民生活センター｜くらしの相談", "https://www.kokusen.go.jp/"),
    ],
}


def reference_links(category: str) -> str:
    items = "\n".join(
        f'          <li><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a></li>'
        for label, url in SOURCES[category]
    )
    return f'''\n        <section class="reference-links" aria-labelledby="official-info-title">
          <h2 id="official-info-title">制度・公式情報の確認先</h2>
          <p>制度や自治体の運用は変更されることがあります。手続きや処分を行う前に、対象地域の自治体・関係機関の最新案内をご確認ください。</p>
          <ul>
{items}
          </ul>
        </section>\n'''


EDITORIAL_INFO = '''
        <aside class="editorial-info" aria-label="この記事の編集情報">
          <p class="editorial-info-label">この記事の編集</p>
          <p class="editorial-info-name">福岡遺品整理ガイド編集部</p>
          <p>当サイトは、自治体・公的機関・法令・公式団体が公開する情報を確認し、生活者の判断に役立つよう記事を編集しています。個別の事情に応じた法的・税務・医療上の判断については、各分野の専門家または関係機関へご確認ください。</p>
          <p class="editorial-info-links"><a href="/about.html">編集方針・運営情報</a><span aria-hidden="true">｜</span><a href="/contact/">内容の訂正・お問い合わせ</a></p>
        </aside>
'''


ABOUT_PAGE = f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-S1QGZ4ETK0"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-S1QGZ4ETK0');
  </script>
  <meta charset="UTF-8">
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>編集方針・運営情報 | 福岡遺品整理ガイド</title>
  <meta name="description" content="福岡遺品整理ガイドの目的、記事の編集方針、情報確認の方法、広告表記、訂正依頼・お問い合わせ窓口についてご案内します。">
  <link rel="canonical" href="https://fukuoka-ihinseiri-guide.com/about.html">
  <link rel="alternate" hreflang="ja" href="https://fukuoka-ihinseiri-guide.com/about.html">
  <meta property="og:title" content="編集方針・運営情報 | 福岡遺品整理ガイド">
  <meta property="og:description" content="福岡遺品整理ガイドの目的、編集方針、情報確認の方法、広告表記について。">
  <meta property="og:site_name" content="福岡遺品整理ガイド">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://fukuoka-ihinseiri-guide.com/about.html">
  <meta property="og:image" content="https://fukuoka-ihinseiri-guide.com/images/ogp-default.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet"></noscript>
  <link rel="preload" href="/css/style.css?v={CSS_VERSION}" as="style">
  <link rel="stylesheet" href="/css/style.css?v={CSS_VERSION}">
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4944616437202027" crossorigin="anonymous"></script>
  <script>
    if ('scrollRestoration' in history) {{ history.scrollRestoration = 'manual'; }}
    window.scrollTo(0, 0);
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": "編集方針・運営情報 | 福岡遺品整理ガイド",
    "url": "https://fukuoka-ihinseiri-guide.com/about.html",
    "inLanguage": "ja",
    "isPartOf": {{"@type": "WebSite", "name": "福岡遺品整理ガイド", "url": "https://fukuoka-ihinseiri-guide.com/"}}
  }}
  </script>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="header-logo">福岡遺品整理ガイド</a>
      <nav class="header-nav" id="headerNav">
        <a href="/area/">地域別情報</a>
        <a href="/cost/">費用相場</a>
        <a href="/guide/">お役立ちガイド</a>
        <a href="/blog/">記事を検索</a>
        <a href="/for-business/">業者様向け</a>
        <a href="/contact/" class="header-cta">無料相談する</a>
      </nav>
      <button class="mobile-menu-btn" id="menuBtn" aria-label="メニュー" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </header>

  <main class="article-page site-info-page">
    <div class="article-container">
      <nav class="breadcrumb" aria-label="パンくずリスト"><a href="/">ホーム</a><span>›</span><span aria-current="page">編集方針・運営情報</span></nav>
      <h1>編集方針・運営情報</h1>
      <p class="site-info-lead">福岡遺品整理ガイドは、福岡県内で遺品整理・生前整理・特殊清掃・遺品供養に関する情報を探す方に向けた情報サイトです。ご家族が状況を整理し、次に確認すべきことを判断しやすくなるよう、記事を編集しています。</p>

      <section>
        <h2>サイトの目的</h2>
        <p>遺品整理や相続に関わる片付けは、急な出来事の中で判断を求められることがあります。当サイトでは、福岡県内の自治体情報、費用の考え方、事業者選びの視点、供養・手続きに関する基礎情報を、初めて調べる方にも分かりやすい形でお伝えします。</p>
      </section>

      <section>
        <h2>運営・編集体制</h2>
        <p>記事の企画・編集・更新は、<strong>福岡遺品整理ガイド編集部</strong>が行っています。これは当サイトの情報編集・運営窓口の名称です。掲載内容に関するご質問、誤記・更新が必要と思われる点は、<a href="/contact/">お問い合わせフォーム</a>からご連絡ください。</p>
      </section>

      <section>
        <h2>記事の編集方針</h2>
        <p>記事の作成・更新では、自治体、国の行政機関、法令、公式団体が公開する情報を優先して確認します。制度や自治体の運用は変更されることがあるため、特にごみの処分方法、持ち込みの条件、手続き、料金、相談窓口については、実行前に各記事に案内する公式情報および対象自治体の最新情報をご確認ください。</p>
        <p>情報の正確性に努めていますが、記事は一般的な情報提供を目的としています。個別の相続、法律、税務、契約、健康・衛生に関する判断を保証するものではありません。必要に応じて、弁護士、税理士、行政機関、医療・衛生の関係機関などへご相談ください。</p>
      </section>

      <section>
        <h2>記事の更新・訂正について</h2>
        <p>法令改正、自治体の制度変更、内容の明確化などが必要な場合には、記事を見直して更新します。各記事には公開日または更新日を表示します。事実と異なる可能性がある記載、リンク切れ、分かりにくい表現を見つけた場合は、確認のうえ必要に応じて訂正します。</p>
      </section>

      <section>
        <h2>広告・掲載情報について</h2>
        <p>当サイトでは、第三者配信の広告を掲載する場合があります。また、事業者の掲載情報や広告枠を設ける場合があります。広告またはPRに該当する掲載は、読者が判別できるよう表示に配慮します。広告掲載の有無にかかわらず、記事の内容は読者が情報を確認する際の参考となるよう編集します。</p>
      </section>

      <section>
        <h2>個人情報・お問い合わせ</h2>
        <p>お問い合わせでお預かりする情報の取り扱いは、<a href="/privacy-policy.html">プライバシーポリシー</a>をご確認ください。記事内容の訂正依頼、サイト運営に関するお問い合わせは、<a href="/contact/">お問い合わせフォーム</a>をご利用ください。</p>
      </section>

      <p class="site-info-updated">最終更新日：2026年8月14日</p>
    </div>
  </main>

  <footer class="footer">
    <div class="footer-inner">
      <div>
        <div class="footer-brand">福岡遺品整理ガイド</div>
        <p class="footer-desc">福岡県の遺品整理・特殊清掃・生前整理に特化した情報サイトです。</p>
      </div>
      <div class="footer-col"><h3>カテゴリ</h3><ul><li><a href="/guide/">遺品整理ガイド</a></li><li><a href="/guide/seizenseiri.html">生前整理</a></li><li><a href="/guide/tokushu-seisou.html">特殊清掃</a></li><li><a href="/guide/kuyo.html">遺品供養</a></li></ul></div>
      <div class="footer-col"><h3>お役立ち情報</h3><ul><li><a href="/cost/">費用相場</a></li><li><a href="/area/">地域別情報</a></li><li><a href="/blog/">ブログ記事一覧</a></li><li><a href="/for-business/">業者様向け</a></li></ul></div>
      <div class="footer-col"><h3>サイト情報</h3><ul><li><a href="/about.html">編集方針・運営情報</a></li><li><a href="/contact/">お問い合わせ</a></li><li><a href="/privacy-policy.html">プライバシーポリシー</a></li></ul></div>
    </div>
    <div class="footer-bottom">&copy; 2026 福岡遺品整理ガイド All Rights Reserved.</div>
  </footer>
  <script>
    document.getElementById('menuBtn').addEventListener('click', function() {{
      document.getElementById('headerNav').classList.toggle('active');
      this.setAttribute('aria-expanded', document.getElementById('headerNav').classList.contains('active') ? 'true' : 'false');
    }});
  </script>
  <script src="https://fukuokaguide-afgvbgyb.manus.space/ad-widget.js" defer></script>
</body>
</html>
'''


STANDARD_FOOTER = '''<footer class="footer">
    <div class="footer-inner">
      <div>
        <div class="footer-brand">福岡遺品整理ガイド</div>
        <p class="footer-desc">福岡県の遺品整理・特殊清掃・生前整理に特化した情報サイトです。</p>
      </div>
      <div class="footer-col">
        <h3>カテゴリ</h3>
        <ul>
          <li><a href="/guide/">遺品整理ガイド</a></li>
          <li><a href="/guide/seizenseiri.html">生前整理</a></li>
          <li><a href="/guide/tokushu-seisou.html">特殊清掃</a></li>
          <li><a href="/guide/kuyo.html">遺品供養</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h3>お役立ち情報</h3>
        <ul>
          <li><a href="/cost/">費用相場</a></li>
          <li><a href="/area/">地域別情報</a></li>
          <li><a href="/blog/">ブログ記事一覧</a></li>
          <li><a href="/for-business/">業者様向け</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h3>サイト情報</h3>
        <ul>
          <li><a href="/about.html">編集方針・運営情報</a></li>
          <li><a href="/contact/">お問い合わせ</a></li>
          <li><a href="/privacy-policy.html">プライバシーポリシー</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">&copy; 2026 福岡遺品整理ガイド All Rights Reserved.</div>
  </footer>'''


def update_css_version(content: str) -> str:
    return re.sub(r"/css/style\.css\?v=[^\"']+", f"/css/style.css?v={CSS_VERSION}", content)


def update_footer(content: str) -> str:
    footer_start = content.rfind("<footer")
    if footer_start == -1:
        return content
    footer = content[footer_start:]
    footer_end = footer.find("</footer>")
    if footer_end != -1 and 'class="footer"' not in footer[: footer_end + len("</footer>")]:
        return content[:footer_start] + STANDARD_FOOTER + footer[footer_end + len("</footer>"):]
    if 'href="/about.html"' in footer:
        return content
    target = '<li><a href="/privacy-policy.html">プライバシーポリシー</a></li>'
    if target in footer:
        updated_footer = footer.replace(target, '<li><a href="/about.html">編集方針・運営情報</a></li>\n          ' + target, 1)
        return content[:footer_start] + updated_footer
    return content


def update_article(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    original = content
    category = path.parent.name
    if category not in SOURCES:
        return False
    if 'class="editorial-info"' not in content:
        insert = EDITORIAL_INFO + reference_links(category)
        cta_match = re.search(r'\n(\s*)<div class="cta-section"', content)
        if cta_match:
            content = content[:cta_match.start()] + '\n' + insert + content[cta_match.start():]
        else:
            article_close = content.rfind('</article>')
            if article_close != -1:
                content = content[:article_close] + insert + content[article_close:]
            else:
                main_close = content.rfind('</main>')
                if main_close != -1:
                    content = content[:main_close] + insert + content[main_close:]
    content = update_footer(content)
    content = update_css_version(content)
    content = re.sub(
        r'("author"\s*:\s*(?:\[\s*)?\{[^{}]*"name"\s*:\s*")福岡遺品整理ガイド("[^{}]*\})',
        r'\1福岡遺品整理ガイド編集部\2',
        content,
    )
    if content != original:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main() -> None:
    about = ROOT / "about.html"
    about.write_text(ABOUT_PAGE, encoding="utf-8")
    changed_articles = 0
    for article in ROOT.glob("blog/*/article-*.html"):
        if update_article(article):
            changed_articles += 1

    changed_pages = 0
    for page in ROOT.rglob("*.html"):
        if page == about or "node_modules" in page.parts:
            continue
        content = page.read_text(encoding="utf-8")
        updated = update_css_version(update_footer(content))
        if updated != content:
            page.write_text(updated, encoding="utf-8")
            changed_pages += 1

    sitemap = ROOT / "sitemap.xml"
    sitemap_content = sitemap.read_text(encoding="utf-8")
    if "https://fukuoka-ihinseiri-guide.com/about.html" not in sitemap_content:
        addition = f'''\n  <!-- 編集方針・運営情報 -->
  <url>
    <loc>https://fukuoka-ihinseiri-guide.com/about.html</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
'''
        sitemap.write_text(sitemap_content.replace("</urlset>", addition + "</urlset>"), encoding="utf-8")

    print(f"Created: {about}")
    print(f"Articles updated: {changed_articles}")
    print(f"Other pages updated: {changed_pages}")


if __name__ == "__main__":
    main()
