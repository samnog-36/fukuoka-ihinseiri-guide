"""Deterministic growth targeting: no additional model calls."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def strategy(root=ROOT):
    return json.loads((root/'config/seo_growth.json').read_text())

def target(path,root=ROOT):
    return next((r for r in strategy(root)['priority_pages'] if r['path']==path),None)

def context(root=ROOT):
    return json.dumps(strategy(root),ensure_ascii=False)

def signals(path,gsc,root=ROOT):
    t=target(path,root);bonus=18 if t else 0;reasons=[]
    if t:reasons.append('重点検索意図: '+t['query'])
    if gsc and gsc.get('impressions',0)>=30 and 4<=gsc.get('position',0)<=20:
        bonus+=45;reasons.append('実測表示あり・平均掲載順位4〜20位の改善候補')
    return {'bonus':bonus,'reasons':reasons,'target':t,'measurement':'available' if gsc else 'unavailable'}

def report(gsc_map,root=ROOT):
    rows=[]
    for t in strategy(root)['priority_pages']:
        path='/'+t['path'][:-5];g=gsc_map.get(path)
        rows.append({**t,'measurement':'available' if g else 'unavailable','clicks':g.get('clicks') if g else None,'impressions':g.get('impressions') if g else None,'average_position':g.get('position') if g else None})
    import os
    snapshot=root/os.getenv('CONTENT_OS_PRIVATE_DIR','.content-os-private')/'search_console_latest.json'
    measured=json.loads(snapshot.read_text()) if snapshot.exists() else {}
    periods={k:measured.get(k) for k in ('start_date','end_date','previous_start_date','previous_end_date','current_totals','previous_totals')}
    return {'periods':periods,'note':'GSC平均掲載順位は固定順位ではない。未取得はnull。記事数やAI審査点はSEO成果と区別。','targets':rows,'measured_pages':len(gsc_map)}
