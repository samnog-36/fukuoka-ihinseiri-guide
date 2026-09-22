from __future__ import annotations
import json, os, sys
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRIVATE_DIR=ROOT/os.getenv("CONTENT_OS_PRIVATE_DIR",".content-os-private")
OUT=PRIVATE_DIR/"search_console_latest.json"

def main():
    raw=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON","").strip()
    site=os.getenv("SEARCH_CONSOLE_SITE_URL","https://fukuoka-ihinseiri-guide.com/").strip()
    if not raw:
        print("GOOGLE_SERVICE_ACCOUNT_JSON is not configured; skipping Search Console pull.")
        return 0
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as exc:
        print("Google API dependencies unavailable:",exc,file=sys.stderr); return 2
    try:
        info=json.loads(raw)
        creds=service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        svc=build("searchconsole","v1",credentials=creds,cache_discovery=False)
        end=date.today()-timedelta(days=2); start=end-timedelta(days=27)
        body={
            "startDate":start.isoformat(),
            "endDate":end.isoformat(),
            "dimensions":["page","query"],
            "rowLimit":25000,
            "dataState":"final"
        }
        rows=svc.searchanalytics().query(siteUrl=site,body=body).execute().get("rows",[])
    except Exception as exc:
        print("Search Console pull failed:",exc,file=sys.stderr); return 3
    normalized=[]
    for r in rows:
        keys=r.get("keys",["",""])
        normalized.append({
            "page":keys[0] if len(keys)>0 else "",
            "query":keys[1] if len(keys)>1 else "",
            "clicks":r.get("clicks",0),
            "impressions":r.get("impressions",0),
            "ctr":r.get("ctr",0),
            "position":r.get("position",0)
        })
    roll={}
    for r in normalized:
        cur=roll.setdefault(r["page"],{"clicks":0.0,"impressions":0.0,"weighted_position":0.0,"queries":[]})
        cur["clicks"]+=r["clicks"]; cur["impressions"]+=r["impressions"]; cur["weighted_position"]+=r["position"]*r["impressions"]
        if len(cur["queries"])<20:
            cur["queries"].append({k:r[k] for k in ("query","clicks","impressions","ctr","position")})
    pages=[]
    for p,v in roll.items():
        imp=v["impressions"]
        pages.append({
            "page":p,
            "clicks":round(v["clicks"],2),
            "impressions":round(imp,2),
            "ctr":round(v["clicks"]/imp,4) if imp else 0,
            "position":round(v["weighted_position"]/imp,2) if imp else 0,
            "queries":sorted(v["queries"],key=lambda x:x["impressions"],reverse=True)
        })
    pages.sort(key=lambda x:x["impressions"],reverse=True)
    payload={"site":site,"start_date":start.isoformat(),"end_date":end.isoformat(),"pages":pages}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Wrote private Search Console snapshot. pages=",len(pages)); return 0

if __name__=="__main__":
    raise SystemExit(main())
