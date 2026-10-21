"""Render the eight most recently published/updated public articles at publish time."""
import json
import re
from datetime import datetime, timezone
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class Metadata(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.meta = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('name') or attrs.get('property')] = attrs.get('content', '')


def latest_articles(root=ROOT, limit=8):
    redirects = {line.split()[0] for line in (root / '_redirects').read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')}
    categories = json.loads((root / 'config/content_os.json').read_text())['new_article_categories']
    articles = []
    for path in root.glob('blog/*/article-*.html'):
        rel = path.relative_to(root).as_posix()
        html = path.read_text()
        meta = Metadata(html).meta
        if '/' + rel in redirects or 'noindex' in meta.get('robots', '').lower():
            continue
        dates = re.findall(r'"date(?:Published|Modified)"\s*:\s*"([^" ]+)"', html)
        parsed = []
        for date in dates:
            try:
                dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                parsed.append(dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt)
            except ValueError:
                pass
        if not parsed:
            continue
        date = max(parsed)
        title = re.search(r'<h1\b[^>]*>(.*?)</h1>', html, re.S | re.I)
        title = unescape(re.sub('<[^>]+>', '', title.group(1))).strip() if title else meta.get('og:title', '')
        articles.append(dict(path=rel, date=date, title=title, category=path.parent.name,
                             label=categories[path.parent.name], image=meta.get('og:image', ''),
                             description=meta.get('description', '')))
    return sorted(articles, key=lambda a: (a['date'], a['path']), reverse=True)[:limit]


def render_card(a):
    e = lambda value: escape(str(value), quote=True)
    image_url = urlparse(a["image"]).path if a["image"].startswith("https://fukuoka-ihinseiri-guide.com/") else a["image"]
    image = f'<div class="article-card-img"><img src="{e(image_url)}" alt="{e(a["title"])}" loading="lazy" width="800" height="533"></div>' if a['image'] else ''
    date = a['date'].strftime('%Y年%-m月%-d日')
    return f'''<a href="/{e(a['path'][:-5])}" class="article-card" data-category="{e(a['category'])}">
      {image}
      <div class="article-card-body"><span class="article-card-tag">{e(a['label'])}</span>
      <h3>{e(a['title'])}</h3><p>{e(a['description'])}</p>
      <span class="article-card-date">{date} 更新</span></div>
    </a>'''


def sync(root=ROOT):
    from publication_contract import synchronize
    synchronize(root)


if __name__ == '__main__':
    sync()
