"""Build region navigation from published articles, never from placeholder pages."""
import json
from html import escape
from pathlib import Path
from bs4 import BeautifulSoup
from sync_home_latest import latest_articles
ROOT=Path(__file__).resolve().parents[1]
PREFS={'fukuoka':'福岡県','saga':'佐賀県','nagasaki':'長崎県','kumamoto':'熊本県','oita':'大分県','miyazaki':'宮崎県','kagoshima':'鹿児島県'}
CITIES={'saga':['佐賀市','唐津市','鳥栖市'],'nagasaki':['長崎市','佐世保市','諫早市'],'kumamoto':['熊本市','八代市','天草市'],'oita':['大分市','別府市','佐伯市'],'miyazaki':['宮崎市','都城市','延岡市'],'kagoshima':['鹿児島市','霧島市','鹿屋市']}

def regional_rows(root=ROOT):
    cities=dict(CITIES)
    cities['fukuoka']=[x['name'] for x in json.loads((root/'data/municipalities.json').read_text())['municipalities']]
    groups={k:[] for k in PREFS}
    for a in latest_articles(root,limit=None):
        if a['category']!='area':continue
        for key,pref in PREFS.items():
            matched=[c for c in cities[key] if c in a['title']]
            if matched or pref in a['title']:groups[key].append((a,matched))
    return groups

def render_regions(root=ROOT):
    groups=regional_rows(root); parts=['<nav aria-label="県から探す"><p>地域を選ぶ：'+' / '.join(f'<a href="#{k}-heading">{p}</a>' for k,p in PREFS.items())+'</p></nav>']
    for key,pref in PREFS.items():
        parts.append(f'<section class="area-group" aria-labelledby="{key}-heading"><h2 id="{key}-heading">{pref}</h2>')
        if groups[key]:
            parts.append('<ul>')
            for a,cities in groups[key]:
                label='・'.join(cities) or pref
                parts.append(f'<li><a href="/{a["path"][:-5]}"><strong>{escape(label)}</strong>：{escape(a["title"])}</a></li>')
            parts.append('</ul>')
        else:
            parts.append('<p>この県の自治体別ガイドは現在掲載していません。先に確認したい条件は、<a href="/guide/preparation-checklist">遺品整理の準備チェック</a>をご利用ください。</p>')
        parts.append('</section>')
    return '\n'.join(parts)

def sync(root=ROOT):
    # The test fixture for the article contract has no region inventory.
    if not (root/'data/municipalities.json').exists():return
    for filename in ('area/index.html','index.html'):
        p=root/filename;s=BeautifulSoup(p.read_text(),'html.parser')
        target=s.select_one('[data-region-directory]')
        if target:target.clear();target.append(BeautifulSoup(render_regions(root),'html.parser'))
        if filename=='index.html':
            groups=regional_rows(root)
            for link in s.select('a.area-tag'):
                label=link.get_text(strip=True); parent=link.find_parent(class_='area-group');heading=parent.find('h3').get_text() if parent and parent.find('h3') else ''
                candidates=[a for a,_ in groups['fukuoka'] if label in a['title']]
                if not candidates and '北九州市' in heading:candidates=[a for a,_ in groups['fukuoka'] if '北九州市' in a['title']]
                if candidates:link['href']='/'+candidates[0]['path'][:-5]
                else:link['href']='/area/#fukuoka-heading'
        from publication_contract import serialize
        p.write_text(serialize(s))
