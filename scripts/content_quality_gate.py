from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/content_os.json").read_text(encoding="utf-8"))
TAG_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>", re.I | re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
CANONICAL_RE = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', re.I)
DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', re.I)
NOINDEX_RE = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', re.I)
URL_RE = re.compile(r'https?://[^"\'<>\s]+')
RISK_RE = re.compile(r"(?:必ず|絶対|100%|最も多い|業界No\.?1|専門家監修|弁護士監修)")
PLACEHOLDER_RE = re.compile(r"(?:TODO|TBD|仮URL|example\.com|未確認のまま公開)", re.I)

def text_only(html):
    return re.sub(r"\s+", " ", unescape(TAG_RE.sub(" ", html))).strip()

def redirected_paths():
    out=set()
    p=ROOT/"_redirects"
    if not p.exists(): return out
    for raw in p.read_text(encoding="utf-8").splitlines():
        parts=raw.strip().split()
        if len(parts)>=3 and parts[-1] in {"301","302","307","308"}:
            out.add(parts[0])
    return out

def audit_file(path, redirects):
    html=path.read_text(encoding="utf-8")
    rel=path.relative_to(ROOT).as_posix()
    indexable=("/"+rel not in redirects) and not NOINDEX_RE.search(html)
    errors=[]; warnings=[]
    mt=TITLE_RE.search(html); title=mt.group(1).strip() if mt else ""
    h1s=H1_RE.findall(html)
    mc=CANONICAL_RE.search(html); canonical=mc.group(1).strip() if mc else ""
    md=DESC_RE.search(html); desc=md.group(1).strip() if md else ""
    if indexable:
        if not title: errors.append("missing_title")
        if len(h1s)!=1: errors.append("h1_count="+str(len(h1s)))
        if not canonical: errors.append("missing_canonical")
        elif urlparse(canonical).netloc != urlparse(CONFIG["site_url"]).netloc: errors.append("canonical_wrong_host")
        if len(desc)<40: errors.append("description_too_short")
        if 'class="editorial-info"' not in html: errors.append("missing_editorial_info")
        if 'class="reference-links"' not in html: errors.append("missing_reference_links")
        if PLACEHOLDER_RE.search(html): errors.append("placeholder_content")
    visible=text_only(html)
    official_urls=[]
    for u in URL_RE.findall(html):
        host=urlparse(u).netloc
        if any(x in host for x in (".go.jp",".lg.jp","kokusen.go.jp","courts.go.jp","e-gov.go.jp","stat.go.jp")):
            official_urls.append(u)
    risk=len(RISK_RE.findall(visible))
    if indexable and risk: warnings.append("strong_claim_terms="+str(risk))
    return {"path":rel,"indexable":indexable,"title":re.sub(r"<[^>]+>","",title),"errors":errors,"warnings":warnings,"official_sources":len(set(official_urls))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--strict",action="store_true")
    ap.add_argument("--report",default="docs/growth/quality-gate.json")
    args=ap.parse_args()
    red=redirected_paths()
    records=[audit_file(p,red) for p in sorted(ROOT.glob(CONFIG["content_glob"]))]
    active=[r for r in records if r["indexable"]]
    counts=Counter(r["title"] for r in active if r["title"])
    for r in active:
        if r["title"] and counts[r["title"]]>1: r["errors"].append("duplicate_title")
    summary={"articles_total":len(records),"indexable":len(active),"errors":sum(len(r["errors"]) for r in records),"warnings":sum(len(r["warnings"]) for r in records),"error_pages":[r for r in records if r["errors"]],"warning_pages":[r for r in records if r["warnings"]]}
    out=ROOT/args.report; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k not in {"error_pages","warning_pages"}},ensure_ascii=False))
    for r in summary["error_pages"][:20]: print("ERROR",r["path"],",".join(r["errors"]))
    return 1 if args.strict and summary["errors"] else 0

if __name__=="__main__":
    sys.exit(main())
