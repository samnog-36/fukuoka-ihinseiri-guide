from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD="https://fukuokaguide-afgvbgyb.manus.space"
NEW="https://fukuoka-ihinseiri-guide.com"
changed=[]

for p in ROOT.rglob("*.html"):
    s=p.read_text(encoding="utf-8")
    n=s.replace(OLD+"/ad-widget.js","/ad-widget.js")
    if p.as_posix().endswith("/contact/index.html"):
        n=n.replace(OLD+"/api/trpc/inquiry.submit","/api/inquiry")
        n=n.replace("body: JSON.stringify({ json: data })","body: JSON.stringify(data)")
    if p.as_posix().endswith("/for-business/index.html"):
        n=n.replace(OLD+"/api/trpc/business.submit","/api/business")
        n=n.replace("body: JSON.stringify({ json: data })","body: JSON.stringify(data)")

    # Remove every remaining legacy Manus hostname from public HTML.
    # This also fixes stale OGP, JSON-LD, image URLs and old author/breadcrumb URLs.
    n=n.replace(OLD,NEW)

    if n!=s:
        p.write_text(n,encoding="utf-8")
        changed.append(p.relative_to(ROOT).as_posix())

audit=ROOT/"scripts/adsense_quality_audit.py"
if audit.exists():
    s=audit.read_text(encoding="utf-8")
    n=s.replace("fukuokaguide-afgvbgyb.manus.space/ad-widget.js","/ad-widget.js")
    if n!=s:
        audit.write_text(n,encoding="utf-8")
        changed.append("scripts/adsense_quality_audit.py")

runtime_refs=[]
for p in list(ROOT.rglob("*.html"))+[ROOT/"scripts/adsense_quality_audit.py"]:
    if p.exists() and OLD in p.read_text(encoding="utf-8"):
        runtime_refs.append(p.relative_to(ROOT).as_posix())

print("changed",len(changed))
for x in changed: print(x)
if runtime_refs:
    print("remaining runtime Manus refs:")
    for x in runtime_refs: print(x)
    raise SystemExit(1)
