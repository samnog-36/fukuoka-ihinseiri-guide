"""One publication inventory and mandatory article presentation contract.

No AI is used to generate navigation or repair HTML. Missing real images fail closed.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bs4.formatter import HTMLFormatter
from PIL import Image
from sync_home_latest import latest_articles, render_card

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://fukuoka-ihinseiri-guide.com'
TOC_SELECTOR = '.toc, .table-of-contents, .article-toc, #toc, [data-publication-toc]'


class StableAttributes(HTMLFormatter):
    def attributes(self, tag):
        priority = {'name': 0, 'property': 0, 'rel': 0, 'href': 1, 'content': 1}
        return sorted(tag.attrs.items(), key=lambda item: (priority.get(item[0], 2), item[0]))


def serialize(soup):
    return re.sub(r'>\s+<', '>\n<', soup.decode(formatter=StableAttributes()))


def image_path(url, root=ROOT):
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != urlparse(SITE).netloc:
        raise ValueError('Article images must be hosted on this site: ' + url)
    path = root / parsed.path.lstrip('/')
    if not path.resolve().is_relative_to(root.resolve()) or 'default' in path.name.lower() or not path.is_file():
        raise ValueError('Missing or placeholder article image: ' + url)
    with Image.open(path) as img:
        if img.width < 600 or img.height < 300:
            raise ValueError('Article image is too small: ' + url)
    return path


def image_approved(path, root=ROOT):
    registry = root / 'data/hero-image-approvals.json'
    if not registry.exists(): return False
    rows = json.loads(registry.read_text())
    record = rows.get(path.relative_to(root).as_posix(), {})
    return record.get('text_free') is True and record.get('sha256') == hashlib.sha256(path.read_bytes()).hexdigest()


def save_image_approval(path, method, root=ROOT):
    registry = root / 'data/hero-image-approvals.json'
    rows = json.loads(registry.read_text()) if registry.exists() else {}
    rows[path.relative_to(root).as_posix()] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'review': method, 'text_free': True}
    registry.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')


def article_headings(article):
    return [h for h in article.find_all('h2') if not h.find_parent(attrs={'data-publication-toc': True})]


def normalize_article(path, root=ROOT):
    original = path.read_text()
    soup = BeautifulSoup(original, 'html.parser')
    article = soup.find('article')
    if article is None or not article.find('h1'):
        raise ValueError('Article/H1 is missing: ' + str(path))
    # Find the actual article-specific image; never substitute the site logo.
    hero = article.find('img')
    src = hero.get('src', '') if hero else ''
    try:
        image_path(src, root)
    except ValueError:
        og = soup.find('meta', property='og:image')
        src = og.get('content', '') if og else ''
        image_path(src, root)
    src = urlparse(src).path
    # Standardize the hero container, with no prose or text layered over it.
    if hero:
        old_figure = hero.find_parent('figure')
        if old_figure:
            old_figure.decompose()
        else:
            hero.decompose()
    figure = soup.new_tag('figure', attrs={'class': 'article-hero-image', 'data-publication-hero': 'true'})
    with Image.open(root / src.lstrip('/')) as img:
        width, height = img.size
    figure.append(soup.new_tag('img', src=src, alt=article.h1.get_text(' ', strip=True) + 'のイメージ',
                              width=str(width), height=str(height), loading='eager', decoding='async'))
    header = article.h1.find_parent('header')
    (header if header and header in article.descendants else article.h1).insert_after(figure)
    for toc in list(article.select(TOC_SELECTOR)):
        if toc.parent:
            # Some legacy pages open <div class=toc> but close </nav>, so the
            # browser/parser puts the rest of the article inside that wrapper.
            # Remove navigation only; never discard the enclosed article body.
            title = toc.find(['h2', 'h3', 'p'])
            if title and title.get_text(strip=True) == '目次': title.decompose()
            links = toc.find(['ul', 'ol'])
            if links and all(a.get('href', '').startswith('#') for a in links.find_all('a')):
                links.decompose()
            if toc.find(['h2', 'p', 'table', 'section']): toc.unwrap()
            else: toc.decompose()
    headings = article_headings(article)
    if not headings:
        raise ValueError('No article sections: ' + str(path))
    ids = {tag.get('id') for tag in soup.find_all(id=True)}
    nav = soup.new_tag('nav', attrs={'class': 'toc', 'data-publication-toc': 'true', 'aria-label': '目次'})
    label = soup.new_tag('p', attrs={'class': 'toc-title'}); label.string = '目次'; nav.append(label)
    ol = soup.new_tag('ol'); nav.append(ol)
    for i, heading in enumerate(headings, 1):
        anchor = heading.get('id')
        if not anchor:
            anchor = f'article-section-{i}'
            while anchor in ids:
                anchor += '-section'
            heading['id'] = anchor; ids.add(anchor)
        li = soup.new_tag('li'); a = soup.new_tag('a', href='#' + anchor)
        a.string = heading.get_text(' ', strip=True); li.append(a); ol.append(li)
    figure.insert_after(nav)
    for prop in ('og:image', 'twitter:image'):
        tag = soup.find('meta', attrs={'property': prop}) or soup.find('meta', attrs={'name': prop})
        if tag:
            tag['content'] = SITE + src
    for script in soup.find_all('script', type='application/ld+json'):
        data = json.loads(script.string or script.get_text())
        def visit(obj):
            if isinstance(obj, list):
                for v in obj: visit(v)
            elif isinstance(obj, dict):
                if obj.get('@type') in ('Article', 'BlogPosting', 'NewsArticle'):
                    obj['image'] = SITE + src
                for v in obj.values(): visit(v)
        visit(data)
        script.string = json.dumps(data, ensure_ascii=False, indent=2)
    result = serialize(soup)
    if result != original:
        path.write_text(result)


def replace_grid(path, cards, home=False):
    html = path.read_text()
    if home:
        start, end = '<!-- HOME_LATEST_START -->', '<!-- HOME_LATEST_END -->'
        if html.count(start) != 1 or html.count(end) != 1:
            raise ValueError('Homepage markers are invalid')
        html = html[:html.index(start)+len(start)] + '\n' + cards + '\n' + html[html.index(end):]
    else:
        soup = BeautifulSoup(html, 'html.parser')
        grid = soup.select_one('.article-grid')
        if grid is None: raise ValueError('Missing article grid: ' + str(path))
        grid.clear()
        fragment = BeautifulSoup(cards, 'html.parser')
        for node in list(fragment.contents): grid.append(node)
        html = serialize(soup)
    path.write_text(html)


def synchronize(root=ROOT):
    articles = latest_articles(root, limit=None)
    if not articles: raise ValueError('No public articles')
    for a in articles: normalize_article(root / a['path'], root)
    articles = latest_articles(root, limit=None)
    render = lambda rows: '\n'.join(render_card(a) for a in rows)
    replace_grid(root / 'index.html', render(articles[:8]), home=True)
    replace_grid(root / 'blog/index.html', render(articles))
    for category in sorted({a['category'] for a in articles}):
        replace_grid(root / f'blog/{category}/index.html', render([a for a in articles if a['category'] == category]))
    by_url = {'/' + a['path'][:-5]: a for a in articles}
    for hub in ('area/index.html', 'cost/index.html', 'guide/index.html'):
        path = root / hub
        if not path.exists(): continue
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        for card in soup.select('a.article-card'):
            row = by_url.get(card.get('href', '').removesuffix('.html'))
            if row:
                card.replace_with(BeautifulSoup(render_card(row), 'html.parser').find('a'))
        path.write_text(serialize(soup))
    from regional_navigation import sync as sync_regions
    sync_regions(root)
    # Bust legacy year-long immutable URLs; subsequent requests revalidate.
    for path in root.rglob('*.html'):
        original = path.read_text()
        updated = re.sub(r'(/css/style\.css)(?:\?[^"\s<>]*)?', r'\1?v=20261021-integrity', original)
        updated = re.sub(r'(/js/search\.js)(?:\?[^"\s<>]*)?', r'\1?v=20261021-integrity', updated)
        if updated != original: path.write_text(updated)
    records = []
    for a in articles:
        article = BeautifulSoup((root / a['path']).read_text(), 'html.parser').find('article')
        records.append({'url': '/' + a['path'][:-5], 'title': a['title'], 'desc': a['description'],
                        'category': a['category'], 'categorySlug': a['category'], 'date': a['date'].date().isoformat(),
                        'thumbnail': urlparse(a['image']).path, 'text': article.get_text(' ', strip=True)})
    (root / 'js/search-data.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(f'Synchronized {len(articles)} public articles, homepage, all/category lists and search')


def validate(root=ROOT):
    errors = []
    articles = latest_articles(root, limit=None)
    urls = ['/' + a['path'][:-5] for a in articles]
    def cards(path, expected):
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        found = [a.get('href') for a in soup.select('.article-grid a.article-card')]
        if found != expected: errors.append(f'{path.relative_to(root)}: article set/order mismatch')
        by_url = {'/' + a['path'][:-5]: a for a in articles}
        for card in soup.select('.article-grid a.article-card'):
            a = by_url.get(card.get('href')); img = card.find('img')
            if a and (not img or urlparse(img.get('src', '')).path != urlparse(a['image']).path):
                errors.append(f'{path.relative_to(root)}: thumbnail mismatch: {card.get("href")}')
    cards(root / 'index.html', urls[:8]); cards(root / 'blog/index.html', urls)
    for c in {a['category'] for a in articles}:
        cards(root / f'blog/{c}/index.html', ['/' + a['path'][:-5] for a in articles if a['category'] == c])
    if (root/'data/municipalities.json').exists():
        from regional_navigation import render_regions
        area_soup=BeautifulSoup((root/'area/index.html').read_text(),'html.parser')
        directory=area_soup.select_one('[data-region-directory]')
        if directory is not None:
            expected_region=BeautifulSoup(render_regions(root),'html.parser')
            if directory.get_text(' ',strip=True)!=expected_region.get_text(' ',strip=True) or [a.get('href') for a in directory.find_all('a')]!=[a.get('href') for a in expected_region.find_all('a')]:
                errors.append('Regional directory differs from published inventory')
    search = json.loads((root / 'js/search-data.json').read_text())
    if [r['url'] for r in search] != urls: errors.append('Search article set/order mismatch')
    for a in articles:
        soup = BeautifulSoup((root / a['path']).read_text(), 'html.parser'); article = soup.find('article')
        if article is None: errors.append(a['path'] + ': article missing'); continue
        hero = article.select_one('figure[data-publication-hero]')
        if not hero or not hero.find('img') or hero.get_text(strip=True):
            errors.append(a['path'] + ': missing hero or text mixed into hero'); continue
        img = hero.find('img')
        try:
            asset = image_path(img.get('src', ''), root)
            if not image_approved(asset, root): errors.append(a['path'] + ': hero lacks text-free image review for these exact bytes')
        except ValueError as e: errors.append(a['path'] + ': ' + str(e))
        if urlparse(a['image']).path != img.get('src'): errors.append(a['path'] + ': hero/OG mismatch')
        toc = article.select_one('nav[data-publication-toc]')
        headings = article_headings(article)
        expected = ['#' + h.get('id', '') for h in headings]
        if not toc or [x.get('href') for x in toc.find_all('a')] != expected or '#' in expected:
            errors.append(a['path'] + ': TOC missing or section links differ')
        ids = [x.get('id') for x in soup.find_all(id=True)]
        if len(ids) != len(set(ids)): errors.append(a['path'] + ': duplicate section IDs')
    if errors: raise ValueError('\n'.join(errors))
    print(f'Publication contract PASS: {len(articles)} articles; lists, hero images and TOCs consistent')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    if not args.check: synchronize()
    validate()
