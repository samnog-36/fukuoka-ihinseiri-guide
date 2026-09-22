from __future__ import annotations
import argparse, json, os, re, sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/"config/content_os.json").read_text(encoding="utf-8"))
SOURCES=json.loads((ROOT/"data/source_registry.json").read_text(encoding="utf-8"))
PRIVATE_DIR=ROOT/os.getenv("CONTENT_OS_PRIVATE_DIR",".content-os-private")
TAG_RE=re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",re.I|re.S)
TITLE_RE=re.compile(r"<title>(.*?)</title>",re.I|re.S)
NOINDEX_RE=re.compile(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex',re.I)
ARTICLE_RE=re.compile(r'(<article\s+class=["\']article-content["\'][^>]*>.*?</article>)',re.I|re.S)
URL_RE=re.compile(r'https?://[^"\'<>\s]+')

def visible(html):
    return re.sub(r"\s+"," ",unescape(TAG_RE.sub(" ",html))).strip()

def redirects():
    p=ROOT/"_redirects"; out=set()
    if not p.exists(): return out
    for line in p.read_text(encoding="utf-8").splitlines():
        parts=line.strip().split()
        if len(parts)>=3 and parts[-1] in {"301","302","307","308"}: out.add(parts[0])
    return out

def article_records():
    red=redirects(); rows=[]
    for p in sorted(ROOT.glob(CONFIG["content_glob"])):
        html=p.read_text(encoding="utf-8"); rel=p.relative_to(ROOT).as_posix()
        if "/"+rel in red or NOINDEX_RE.search(html): continue
        mt=TITLE_RE.search(html); title=unescape(mt.group(1)).strip() if mt else rel
        text=visible(html); urls=set(URL_RE.findall(html))
        official=sum(1 for u in urls if any(d in urlparse(u).netloc for d in CONFIG["preferred_source_domains"]))
        quality=100
        if len(text.replace(" ",""))<3000: quality-=15
        if 'class="editorial-info"' not in html: quality-=20
        if 'class="reference-links"' not in html: quality-=15
        if official==0: quality-=12
        if re.search(r"(?:必ず|絶対|100%|最も多い|専門家監修)",text): quality-=8
        if len(re.findall(r"\d[\d,]*(?:%|％|円|万円|件|人|世帯)",text))>=5 and official<2: quality-=10
        rows.append({"path":rel,"title":title,"quality":max(0,quality),"chars":len(text),"official_sources":official})
    return rows

def load_gsc():
    p=PRIVATE_DIR/"search_console_latest.json"
    if not p.exists(): return {}
    try: data=json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}
    out={}; base=CONFIG["site_url"].rstrip("/")
    for row in data.get("pages",[]):
        url=row.get("page","")
        if url.startswith(base): out[url[len(base):].lstrip("/")]=row
    return out

def candidate_score(rec,gsc):
    score=(100-rec["quality"])*2
    if gsc:
        imp=float(gsc.get("impressions",0)); pos=float(gsc.get("position",0)); ctr=float(gsc.get("ctr",0))
        if imp>=CONFIG["min_impressions_for_gsc_priority"]: score+=min(60,imp**0.5)
        if CONFIG["position_opportunity_min"]<=pos<=CONFIG["position_opportunity_max"]: score+=35
        if imp>=100 and ctr<0.03: score+=15
    return round(score,2)

def duplicate_hints(rows):
    out=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            ratio=SequenceMatcher(None,a["title"],b["title"]).ratio()
            if ratio>=0.62: out.append({"a":a["path"],"b":b["path"],"title_similarity":round(ratio,3)})
    return sorted(out,key=lambda x:x["title_similarity"],reverse=True)[:30]

def make_report(rows,gsc_map):
    ranked=[]
    for r in rows:
        x=dict(r); x["gsc"]=gsc_map.get(r["path"]); x["priority_score"]=candidate_score(r,x["gsc"]); ranked.append(x)
    ranked.sort(key=lambda x:x["priority_score"],reverse=True)
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"site":CONFIG["site_url"],"top_improvement_candidates":ranked[:25],"duplicate_title_hints":duplicate_hints(rows)}

def improve(candidate):
    key=os.getenv("OPENAI_API_KEY","").strip()
    if not key: raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI
    path=ROOT/candidate["path"]; html=path.read_text(encoding="utf-8"); match=ARTICLE_RE.search(html)
    if not match: raise RuntimeError("article-content not found: "+candidate["path"])
    article=match.group(1)
    source_names=", ".join(s["name"] for s in SOURCES["sources"])
    prompt=f"""
あなたは福岡県の遺品整理情報サイトの調査編集者です。
検索エンジンを欺くのではなく、読者に役立つ一次情報・地域固有情報・判断材料を増やしてください。

対象: {candidate["path"]}
現在のタイトル: {candidate["title"]}
品質スコア: {candidate["quality"]}
Search Console: {json.dumps(candidate.get("gsc") or {},ensure_ascii=False)}
優先一次情報: {source_names}

必須条件:
- web検索を使い、制度・統計・自治体ルール・法律・料金に関する事実を再確認する。
- 国、福岡県、対象自治体、国民生活センター等の一次情報を優先する。
- 出典で確認できない数字・割合・相場・「最も多い」等の断定は削除または条件付き表現にする。
- 地名差し替え型の一般論ではなく、その地域固有の制度、処分方法、相談先、判断手順を増やす。
- 架空の体験談、口コミ、業者、資格、監修者、実績は作らない。
- HTMLの既存class、関連記事、編集情報、公式確認先、CTAをできる限り保持する。
- 重要な事実には本文近くで出典リンクを置く。
- headは変更しない。article要素だけ改善する。
- 広告目的の水増し文章は追加しない。

現在のarticle HTML:
---BEGIN ARTICLE---
{article}
---END ARTICLE---

返答はJSONだけ:
{{
  "article_html": "<article class=\\"article-content\\">...</article>",
  "change_summary": ["変更点"],
  "primary_sources": [{{"name":"機関名","url":"https://..."}}]
}}
"""
    client=OpenAI(api_key=key)
    model=os.getenv("OPENAI_MODEL","gpt-5.6-terra")
    resp=client.responses.create(model=model,tools=[{"type":"web_search"}],input=prompt)
    raw=resp.output_text.strip()
    fence=chr(96)*3
    if raw.startswith(fence):
        raw=re.sub("^"+re.escape(fence)+r"(?:json)?\s*|\s*"+re.escape(fence)+"$","",raw,flags=re.S)
    data=json.loads(raw); article_html=data.get("article_html","")
    if not article_html.startswith("<article") or "</article>" not in article_html: raise RuntimeError("AI response missing complete article")
    for marker in ('class="editorial-info"','class="reference-links"'):
        if marker not in article_html: raise RuntimeError("AI response lost required marker: "+marker)
    src=[s.get("url","") for s in data.get("primary_sources",[]) if isinstance(s,dict)]
    if not src: raise RuntimeError("AI response has no source list")
    preferred=False
    for u in src:
        if u.startswith("http") and any(d in urlparse(u).netloc for d in CONFIG["preferred_source_domains"]): preferred=True
    if not preferred: raise RuntimeError("AI response has no preferred primary source")
    path.write_text(html[:match.start(1)]+article_html+html[match.end(1):],encoding="utf-8")
    data["path"]=candidate["path"]; return data

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["audit","improve","discover"],default="audit"); args=ap.parse_args()
    PRIVATE_DIR.mkdir(parents=True,exist_ok=True)
    rows=article_records(); gsc=load_gsc(); rep=make_report(rows,gsc)
    (PRIVATE_DIR/"content-os-latest.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Content Growth OS レポート","",f"生成: {rep['generated_at']}","","## 改善優先候補","","|score|quality|記事|impressions|position|","|---:|---:|---|---:|---:|"]
    for r in rep["top_improvement_candidates"][:15]:
        g=r.get("gsc") or {}; lines.append(f"|{r['priority_score']}|{r['quality']}|{r['path']}|{g.get('impressions','-')}|{g.get('position','-')}|")
    lines+=["","## 重複タイトル候補",""]
    for d in rep["duplicate_title_hints"][:15]: lines.append(f"- {d['a']} ↔ {d['b']} ({d['title_similarity']})")
    (PRIVATE_DIR/"content-os-latest.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    if args.mode!="improve":
        print("Analysis complete; no article modified."); return 0
    if not rep["top_improvement_candidates"]: print("No candidates."); return 0
    c=rep["top_improvement_candidates"][0]
    if c["priority_score"]<=0: print("No positive-priority candidate."); return 0
    result=improve(c)
    (PRIVATE_DIR/"last-ai-change.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Improved",c["path"]); return 0

if __name__=="__main__":
    sys.exit(main())
