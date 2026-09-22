from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from html import escape, unescape
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/content_os.json").read_text(encoding="utf-8"))
SOURCES = json.loads((ROOT / "data/source_registry.json").read_text(encoding="utf-8"))
PRIVATE_DIR = ROOT / os.getenv("CONTENT_OS_PRIVATE_DIR", ".content-os-private")
ACTIVITY_LOG = ROOT / "data/ai-activity-log.json"

TAG_RE = re.compile(r"<script\\b.*?</script>|<style\\b.*?</style>|<[^>]+>", re.I | re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1\\b[^>]*>(.*?)</h1>", re.I | re.S)
NOINDEX_RE = re.compile(r'<meta[^>]+name=["\\']robots["\\'][^>]+content=["\\'][^"\\']*noindex', re.I)
ARTICLE_RE = re.compile(r'(<article\\s+class=["\\']article-content["\\'][^>]*>.*?</article>)', re.I | re.S)
URL_RE = re.compile(r'https?://[^"\\'<>\\s]+')
DESC_RE = re.compile(r'<meta[^>]+name=["\\']description["\\'][^>]*>', re.I)
CANONICAL_RE = re.compile(r'<link[^>]+rel=["\\']canonical["\\'][^>]+href=["\\']([^"\\']+)', re.I)
JSONLD_RE = re.compile(r'(<script[^>]+type=["\\']application/ld\\+json["\\'][^>]*>)(.*?)(</script>)', re.I | re.S)
IMG_RE = re.compile(r'<img\\b[^>]*>', re.I)
SRC_RE = re.compile(r'\\bsrc=["\\']([^"\\']+)["\\']', re.I)
ALT_RE = re.compile(r'\\balt=["\\']([^"\\']*)["\\']', re.I)


def visible(html: str) -> str:
    return re.sub(r"\\s+", " ", unescape(TAG_RE.sub(" ", html))).strip()


def redirects() -> set[str]:
    p = ROOT / "_redirects"
    out: set[str] = set()
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[-1] in {"301", "302", "307", "308"}:
            out.add(parts[0])
    return out


def article_records() -> list[dict]:
    red = redirects()
    rows = []
    for p in sorted(ROOT.glob(CONFIG["content_glob"])):
        html = p.read_text(encoding="utf-8")
        rel = p.relative_to(ROOT).as_posix()
        if "/" + rel in red or NOINDEX_RE.search(html):
            continue
        mt = TITLE_RE.search(html)
        title = unescape(mt.group(1)).strip() if mt else rel
        text = visible(html)
        urls = set(URL_RE.findall(html))
        official = sum(
            1 for u in urls
            if any(d in urlparse(u).netloc for d in CONFIG["preferred_source_domains"])
        )
        quality = 100
        if len(text.replace(" ", "")) < 3000:
            quality -= 15
        if 'class="editorial-info"' not in html:
            quality -= 20
        if 'class="reference-links"' not in html:
            quality -= 15
        if official == 0:
            quality -= 12
        if re.search(r"(?:必ず|絶対|100%|最も多い|専門家監修|弁護士監修)", text):
            quality -= 8
        if len(re.findall(r"\\d[\\d,]*(?:%|％|円|万円|件|人|世帯)", text)) >= 5 and official < 2:
            quality -= 10
        rows.append({
            "path": rel,
            "title": title,
            "quality": max(0, quality),
            "chars": len(text),
            "official_sources": official,
        })
    return rows


def load_gsc() -> dict:
    p = PRIVATE_DIR / "search_console_latest.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    base = CONFIG["site_url"].rstrip("/")
    for row in data.get("pages", []):
        url = row.get("page", "")
        if url.startswith(base):
            out[url[len(base):].lstrip("/")] = row
    return out


def candidate_score(rec: dict, gsc: dict | None) -> float:
    score = (100 - rec["quality"]) * 2
    if gsc:
        imp = float(gsc.get("impressions", 0))
        pos = float(gsc.get("position", 0))
        ctr = float(gsc.get("ctr", 0))
        if imp >= CONFIG["min_impressions_for_gsc_priority"]:
            score += min(60, imp ** 0.5)
        if CONFIG["position_opportunity_min"] <= pos <= CONFIG["position_opportunity_max"]:
            score += 35
        if imp >= 100 and ctr < 0.03:
            score += 15
    return round(score, 2)


def duplicate_hints(rows: list[dict]) -> list[dict]:
    out = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            ratio = SequenceMatcher(None, a["title"], b["title"]).ratio()
            if ratio >= 0.62:
                out.append({"a": a["path"], "b": b["path"], "title_similarity": round(ratio, 3)})
    return sorted(out, key=lambda x: x["title_similarity"], reverse=True)[:30]


def make_report(rows: list[dict], gsc_map: dict) -> dict:
    ranked = []
    for r in rows:
        x = dict(r)
        x["gsc"] = gsc_map.get(r["path"])
        x["priority_score"] = candidate_score(r, x["gsc"])
        ranked.append(x)
    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site": CONFIG["site_url"],
        "top_improvement_candidates": ranked[:25],
        "duplicate_title_hints": duplicate_hints(rows),
    }


def strip_json_fence(raw: str) -> str:
    raw = raw.strip()
    fence = chr(96) * 3
    if raw.startswith(fence):
        raw = re.sub("^" + re.escape(fence) + r"(?:json)?\\s*|\\s*" + re.escape(fence) + "$", "", raw, flags=re.S)
    return raw.strip()


def replace_title(html: str, title: str) -> str:
    safe = escape(title, quote=False)
    if TITLE_RE.search(html):
        return TITLE_RE.sub(f"<title>{safe}</title>", html, count=1)
    return html.replace("</head>", f"  <title>{safe}</title>\\n</head>", 1)


def replace_meta(html: str, *, name: str | None = None, prop: str | None = None, content: str) -> str:
    if not (name or prop):
        return html
    key = "name" if name else "property"
    value = name or prop or ""
    pattern = re.compile(
        rf'<meta\\b(?=[^>]*\\b{key}=["\\']{re.escape(value)}["\\'])[^>]*>',
        re.I,
    )
    tag = f'<meta {key}="{escape(value, quote=True)}" content="{escape(content, quote=True)}">'
    if pattern.search(html):
        return pattern.sub(tag, html, count=1)
    return html.replace("</head>", f"  {tag}\\n</head>", 1)


def canonical_url_for(path: str) -> str:
    return CONFIG["site_url"].rstrip("/") + "/" + path


def sync_structured_data(html: str, title: str, description: str, image_url: str | None) -> str:
    modified = datetime.now(ZoneInfo(CONFIG["timezone"])).date().isoformat()

    def walk(obj):
        if isinstance(obj, dict):
            typ = obj.get("@type")
            types = typ if isinstance(typ, list) else [typ]
            if any(t in {"Article", "BlogPosting", "NewsArticle"} for t in types):
                obj["headline"] = title
                obj["description"] = description
                obj["dateModified"] = modified
                if image_url:
                    obj["image"] = image_url
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    def repl(match: re.Match) -> str:
        raw = match.group(2).strip()
        try:
            data = json.loads(raw)
        except Exception:
            return match.group(0)
        walk(data)
        return match.group(1) + "\\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\\n" + match.group(3)

    return JSONLD_RE.sub(repl, html)


def update_first_image(article_html: str, src: str, alt: str) -> str:
    m = IMG_RE.search(article_html)
    if not m:
        return article_html
    tag = m.group(0)
    if SRC_RE.search(tag):
        tag = SRC_RE.sub(f'src="{escape(src, quote=True)}"', tag, count=1)
    else:
        tag = tag[:-1] + f' src="{escape(src, quote=True)}">'
    if ALT_RE.search(tag):
        tag = ALT_RE.sub(f'alt="{escape(alt, quote=True)}"', tag, count=1)
    else:
        tag = tag[:-1] + f' alt="{escape(alt, quote=True)}">'
    return article_html[:m.start()] + tag + article_html[m.end():]


def update_sitemap(path: str) -> None:
    p = ROOT / "sitemap.xml"
    if not p.exists():
        return
    url = canonical_url_for(path)
    today = datetime.now(ZoneInfo(CONFIG["timezone"])).date().isoformat()
    xml = p.read_text(encoding="utf-8")
    block_re = re.compile(
        rf"(<url>\\s*<loc>{re.escape(url)}</loc>.*?<lastmod>)([^<]+)(</lastmod>.*?</url>)",
        re.S,
    )
    if block_re.search(xml):
        xml = block_re.sub(rf"\\g<1>{today}\\g<3>", xml, count=1)
        p.write_text(xml, encoding="utf-8")


def update_search_data(path: str, title: str, description: str) -> None:
    p = ROOT / "js/search-data.json"
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    target = "/" + path
    changed = False

    def walk(v):
        nonlocal changed
        if isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            if v.get("url") == target:
                if v.get("title") != title:
                    v["title"] = title
                    changed = True
                for k in ("desc", "description"):
                    if k in v and v.get(k) != description:
                        v[k] = description
                        changed = True
            for x in v.values():
                walk(x)

    walk(data)
    if changed:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


def inventory_for_internal_links(rows: list[dict], current_path: str) -> list[dict]:
    return [
        {"path": "/" + r["path"], "title": r["title"]}
        for r in rows
        if r["path"] != current_path
    ][:120]


def call_editor(candidate: dict, rows: list[dict]) -> dict:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI

    path = ROOT / candidate["path"]
    html = path.read_text(encoding="utf-8")
    article_match = ARTICLE_RE.search(html)
    if not article_match:
        raise RuntimeError("article-content not found: " + candidate["path"])

    current_title = unescape(TITLE_RE.search(html).group(1)).strip() if TITLE_RE.search(html) else candidate["title"]
    desc_match = re.search(r'<meta[^>]+name=["\\']description["\\'][^>]+content=["\\']([^"\\']*)', html, re.I)
    current_desc = unescape(desc_match.group(1)).strip() if desc_match else ""
    canonical_match = CANONICAL_RE.search(html)
    current_canonical = canonical_match.group(1).strip() if canonical_match else canonical_url_for(candidate["path"])
    source_names = ", ".join(s["name"] for s in SOURCES["sources"])

    prompt = f"""
あなたは「福岡遺品整理ガイド」の自律サイト運営AIです。
目的は検索エンジンを欺くことではなく、読者価値・一次情報の正確性・検索意図への適合・サイト全体の品質を継続的に高めることです。

対象ページ: {candidate["path"]}
Search Console信号: {json.dumps(candidate.get("gsc") or {}, ensure_ascii=False)}
現在の品質スコア: {candidate["quality"]}
現在のtitle: {current_title}
現在のdescription: {current_desc}
canonical: {current_canonical}
優先一次情報: {source_names}

あなたは本文だけでなくページSEO全体を判断できます。
必要なら title、meta description、OGP文言、H1、見出し構成、本文、FAQ、内部リンク、画像alt、アイキャッチ画像を更新してください。
ただし canonicalのURLパスは変えないでください。URL変更・301統合が必要と判断した場合は今回は実行せず change_summary に提案として記録してください。

必須:
- web検索を使い、法律・制度・自治体ルール・料金・統計・相談窓口などの事実を一次情報で確認する。
- 国、福岡県、市町村、e-Gov、国民生活センター等を優先する。
- 根拠を確認できない数字、料金、割合、順位、実績、口コミ、体験談、専門家、業者情報を作らない。
- 重要な事実には本文近くに直接確認できる出典リンクを置く。
- 「地名だけを変えた一般論」を増やさず、福岡固有の判断材料を優先する。
- 既存のCTA、広告枠、編集情報、公式情報セクション、主要classは維持する。
- 広告目的の水増し文章を作らない。
- Search Consoleで伸びているページを不用意に全面改変しない。必要な部分だけ改善してよい。
- title/metaを変えない方が良ければ現状維持を選べる。
- 内部リンクは下記サイト内在庫から本当に関連するものだけ選ぶ。
- 画像は、既存画像が内容に合っているなら keep。読者理解やCTRに明確な改善が見込める時だけ generate。
- 画像に文字を焼き込まない。誤解を招くBefore/Afterや架空の人物・事業者・証拠写真風表現は避ける。

サイト内リンク候補:
{json.dumps(inventory_for_internal_links(rows, candidate["path"]), ensure_ascii=False)}

現在のarticle HTML:
---BEGIN ARTICLE---
{article_match.group(1)}
---END ARTICLE---

返答はJSONだけ:
{{
  "seo": {{
    "title": "titleタグ文字列",
    "description": "meta description",
    "og_title": "OG title",
    "og_description": "OG description"
  }},
  "article_html": "<article class=\\\"article-content\\\">...</article>",
  "change_summary": ["変更点"],
  "primary_sources": [{{"name":"機関名","url":"https://..."}}],
  "internal_links": ["/blog/..."],
  "image": {{
    "action": "keep または generate",
    "prompt": "generate時のみ、写真・イラスト生成指示。文字なし",
    "alt": "画像alt"
  }},
  "decision_reason": "なぜこの変更量にしたか"
}}
"""
    client = OpenAI(api_key=key)
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    resp = client.responses.create(
        model=model,
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    data = json.loads(strip_json_fence(resp.output_text))
    data["_original_html"] = html
    return data


def validate_editor_output(candidate: dict, data: dict) -> None:
    article_html = data.get("article_html", "")
    if not article_html.startswith("<article") or "</article>" not in article_html:
        raise RuntimeError("AI response missing complete article")
    for marker in ('class="editorial-info"', 'class="reference-links"'):
        if marker not in article_html:
            raise RuntimeError("AI response lost required marker: " + marker)
    seo = data.get("seo") or {}
    if not str(seo.get("title", "")).strip():
        raise RuntimeError("AI response missing SEO title")
    if len(str(seo.get("description", "")).strip()) < 40:
        raise RuntimeError("AI response description too short")
    src = [s.get("url", "") for s in data.get("primary_sources", []) if isinstance(s, dict)]
    if not src:
        raise RuntimeError("AI response has no source list")
    if not any(
        u.startswith("http") and any(d in urlparse(u).netloc for d in CONFIG["preferred_source_domains"])
        for u in src
    ):
        raise RuntimeError("AI response has no preferred primary source")
    canonical_match = CANONICAL_RE.search(data["_original_html"])
    if CONFIG.get("protect_canonical_path") and canonical_match:
        expected = canonical_url_for(candidate["path"])
        if canonical_match.group(1).rstrip("/") != expected.rstrip("/"):
            raise RuntimeError("existing canonical path is unexpected; refusing autonomous edit")


def build_proposed_html(candidate: dict, data: dict) -> str:
    original = data["_original_html"]
    article_match = ARTICLE_RE.search(original)
    if not article_match:
        raise RuntimeError("article-content not found while applying")
    seo = data["seo"]
    title = str(seo["title"]).strip()
    description = str(seo["description"]).strip()
    out = original[:article_match.start(1)] + data["article_html"] + original[article_match.end(1):]
    out = replace_title(out, title)
    out = replace_meta(out, name="description", content=description)
    out = replace_meta(out, prop="og:title", content=str(seo.get("og_title") or title))
    out = replace_meta(out, prop="og:description", content=str(seo.get("og_description") or description))
    out = replace_meta(out, prop="og:url", content=canonical_url_for(candidate["path"]))
    out = replace_meta(out, name="twitter:card", content="summary_large_image")
    return out


def call_reviewer(candidate: dict, original: str, proposed: str, editor: dict) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    reviewer_model = os.getenv("OPENAI_REVIEW_MODEL", "gpt-5.6-sol")
    prompt = f"""
あなたは公開前の独立レビュアーです。編集AIとは別人格として厳格に判定してください。
対象: {candidate["path"]}

目的:
- 読者価値と検索意図への適合
- 事実の正確性
- SEO title/meta/H1/内部リンクの妥当性
- AdSense品質
- 福岡固有情報の有用性
- HTML構造を壊していないこと

必ずweb検索で重要な法律・制度・自治体情報を再確認してください。
次のいずれかがあれば reject:
- 出典で確認できない数字や断定
- 架空の口コミ、業者、実績、専門家、体験談
- 検索順位操作だけを目的にした不自然な文章
- title/metaと本文内容の不一致
- canonical変更を必要とするのに無理に同一URLで別意図へ変更
- 重要な一次情報の誤読
- CTAや広告の過剰化
- 元ページより明らかに有用性が下がる

編集AIの申告:
{json.dumps({k:v for k,v in editor.items() if not k.startswith("_")}, ensure_ascii=False)}

変更前:
---OLD---
{original}
---END OLD---

変更後:
---NEW---
{proposed}
---END NEW---

JSONのみ:
{{
  "approve": true,
  "score": 0,
  "issues": ["問題点"],
  "strengths": ["良い点"],
  "seo_assessment": "評価",
  "factual_assessment": "評価"
}}
"""
    resp = client.responses.create(
        model=reviewer_model,
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    return json.loads(strip_json_fence(resp.output_text))


def generate_image_if_needed(candidate: dict, data: dict, html: str) -> tuple[str, str | None]:
    image = data.get("image") or {}
    if image.get("action") != "generate" or not CONFIG.get("allow_image_generation"):
        return html, None
    prompt = str(image.get("prompt", "")).strip()
    alt = str(image.get("alt", "")).strip()
    if not prompt or not alt:
        return html, None

    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
    result = client.images.generate(
        model=image_model,
        prompt=(
            "福岡の遺品整理情報サイトの記事用アイキャッチ。"
            "広告バナーではなく、落ち着いた実用メディアの写真・ビジュアル。"
            "画像内に文字、ロゴ、透かし、会社名を入れない。"
            "架空の証拠写真や誤認を招く表現を避ける。"
            + prompt
        ),
        size="1536x1024",
        quality="medium",
        output_format="webp",
    )
    raw = base64.b64decode(result.data[0].b64_json)
    stem = Path(candidate["path"]).stem.replace("article-", "")
    filename = f"ai-{stem}-{datetime.now(ZoneInfo(CONFIG['timezone'])).strftime('%Y%m%d')}.webp"
    dest = ROOT / "images" / "blog" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)

    article_match = ARTICLE_RE.search(html)
    if not article_match:
        return html, None
    updated_article = update_first_image(article_match.group(1), f"/images/blog/{filename}", alt)
    html = html[:article_match.start(1)] + updated_article + html[article_match.end(1):]
    html = replace_meta(html, prop="og:image", content=CONFIG["site_url"].rstrip("/") + f"/images/blog/{filename}")
    return html, f"images/blog/{filename}"


def append_activity(candidate: dict, data: dict, review: dict, image_path: str | None) -> None:
    log = []
    if ACTIVITY_LOG.exists():
        try:
            log = json.loads(ACTIVITY_LOG.read_text(encoding="utf-8"))
        except Exception:
            log = []
    if not isinstance(log, list):
        log = []
    seo = data.get("seo") or {}
    old_title_match = TITLE_RE.search(data.get("_original_html", ""))
    old_title = unescape(old_title_match.group(1)).strip() if old_title_match else candidate["title"]
    item = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "path": candidate["path"],
        "title_before": old_title,
        "title_after": seo.get("title"),
        "changes": data.get("change_summary", []),
        "sources": data.get("primary_sources", []),
        "internal_links": data.get("internal_links", []),
        "image_generated": bool(image_path),
        "image_path": image_path,
        "review_score": review.get("score"),
        "review_strengths": review.get("strengths", []),
        "status": "validated_for_auto_publish",
    }
    log.insert(0, item)
    ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    ACTIVITY_LOG.write_text(json.dumps(log[:180], ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


def improve(candidate: dict, rows: list[dict]) -> dict:
    data = call_editor(candidate, rows)
    validate_editor_output(candidate, data)
    proposed = build_proposed_html(candidate, data)
    review = call_reviewer(candidate, data["_original_html"], proposed, data)
    min_score = int(CONFIG.get("minimum_reviewer_score", 88))
    if not review.get("approve") or int(review.get("score", 0)) < min_score:
        result = {
            "path": candidate["path"],
            "published": False,
            "review": review,
            "change_summary": data.get("change_summary", []),
        }
        (PRIVATE_DIR / "last-ai-change.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("Reviewer rejected change", candidate["path"], review.get("score"))
        return result

    proposed, image_path = generate_image_if_needed(candidate, data, proposed)
    seo = data["seo"]
    image_url = None
    if image_path:
        image_url = CONFIG["site_url"].rstrip("/") + "/" + image_path
    proposed = sync_structured_data(proposed, seo["title"], seo["description"], image_url)

    path = ROOT / candidate["path"]
    path.write_text(proposed, encoding="utf-8")
    update_sitemap(candidate["path"])
    update_search_data(candidate["path"], seo["title"], seo["description"])
    append_activity(candidate, data, review, image_path)

    result = {
        "path": candidate["path"],
        "published": True,
        "review": review,
        "change_summary": data.get("change_summary", []),
        "primary_sources": data.get("primary_sources", []),
        "image_path": image_path,
        "seo": seo,
    }
    (PRIVATE_DIR / "last-ai-change.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Validated full-page improvement", candidate["path"], "score=", review.get("score"))
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["audit", "improve", "discover"], default="audit")
    args = ap.parse_args()

    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    rows = article_records()
    gsc = load_gsc()
    rep = make_report(rows, gsc)
    (PRIVATE_DIR / "content-os-latest.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.mode != "improve":
        print("Analysis complete; no article modified.")
        return 0

    if not rep["top_improvement_candidates"]:
        print("No candidates.")
        return 0

    candidate = rep["top_improvement_candidates"][0]
    if candidate["priority_score"] <= 0:
        print("No positive-priority candidate.")
        return 0

    improve(candidate, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
