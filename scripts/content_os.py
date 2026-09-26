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
RUN_LOG = ROOT / "data/ai-run-log.json"

TAG_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>", re.I | re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
NOINDEX_RE = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', re.I)
ARTICLE_RE = re.compile(r'(<article\b[^>]*>.*?</article>)', re.I | re.S)
URL_RE = re.compile(r'https?://[^"\'<>\s]+')
DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]*>', re.I)
CANONICAL_RE = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', re.I)
JSONLD_RE = re.compile(r'(<script[^>]+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)', re.I | re.S)
IMG_RE = re.compile(r'<img\b[^>]*>', re.I)
SRC_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.I)
ALT_RE = re.compile(r'\balt=["\']([^"\']*)["\']', re.I)


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(TAG_RE.sub(" ", html))).strip()


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
        if len(re.findall(r"\d[\d,]*(?:%|％|円|万円|件|人|世帯)", text)) >= 5 and official < 2:
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



def category_slug_from_path(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 3 and parts[0] == "blog":
        return parts[1]
    return "other"


def extract_area_tags() -> list[str]:
    p = ROOT / "area/index.html"
    if not p.exists():
        return []
    html = p.read_text(encoding="utf-8")
    tags = re.findall(r'<span[^>]+class=["\']area-tag["\'][^>]*>(.*?)</span>', html, re.I | re.S)
    return sorted({visible(x) for x in tags if visible(x)})


def clean_article_title(title: str) -> str:
    return re.sub(r"\s*[｜|]\s*福岡遺品整理ガイド.*$", "", title).strip()



def extract_area_hub_mapping() -> dict[str, list[str]]:
    p = ROOT / "area/index.html"
    if not p.exists():
        return {}
    html = p.read_text(encoding="utf-8")
    start = html.find("const areaArticles = {")
    if start < 0:
        return {}
    end = html.find("};", start)
    if end < 0:
        return {}
    block = html[start:end + 2]

    mapping: dict[str, list[str]] = {}
    for area in extract_area_tags():
        m = re.search(
            rf'"{re.escape(area)}"\s*:\s*\[(.*?)\]\s*(?:,|\n\s*\}})',
            block,
            re.S,
        )
        if not m:
            mapping[area] = []
            continue
        urls = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', m.group(1))
        mapping[area] = list(dict.fromkeys(urls))
    return mapping


def build_site_coverage(rows: list[dict]) -> dict:
    by_category: dict[str, list[dict]] = {}
    for row in rows:
        slug = category_slug_from_path(row["path"])
        by_category.setdefault(slug, []).append(row)

    area_tags = extract_area_tags()
    area_rows = by_category.get("area", [])
    hub_mapping = extract_area_hub_mapping()
    row_by_url: dict[str, dict] = {}
    for r in area_rows:
        row_by_url[public_path_for(r["path"])] = r
        row_by_url["/" + r["path"].lstrip("/")] = r

    area_coverage = []
    for area in area_tags:
        matches_by_path: dict[str, dict] = {}

        # Primary source of truth: the actual /area/ navigation mapping.
        for url in hub_mapping.get(area, []):
            # /area/ uses /blog/area/ as a generic fallback when no
            # dedicated regional article is mapped. Do not count that
            # fallback as an actual covered article.
            if "/blog/area/article-" not in url:
                continue
            normalized = public_path_for(url)
            row = row_by_url.get(url) or row_by_url.get(normalized)
            if row:
                matches_by_path[row["path"]] = {
                    "path": row["path"],
                    "title": clean_article_title(row["title"]),
                    "source": "area_hub_mapping",
                }
            else:
                matches_by_path[url] = {
                    "path": url,
                    "title": url,
                    "source": "area_hub_mapping",
                }

        # Secondary evidence: article title explicitly names the area.
        for r in area_rows:
            if area in clean_article_title(r["title"]):
                matches_by_path[r["path"]] = {
                    "path": r["path"],
                    "title": clean_article_title(r["title"]),
                    "source": matches_by_path.get(r["path"], {}).get("source", "title"),
                }

        matches = list(matches_by_path.values())
        area_coverage.append({
            "area": area,
            "article_count": len(matches),
            "articles": matches[:8],
            "status": "covered" if matches else "gap",
        })

    kyushu = {}
    pref_terms = CONFIG.get("kyushu_prefecture_terms", {})
    for pref in CONFIG.get("kyushu_prefectures", []):
        terms = pref_terms.get(pref, [pref])
        matches = []
        for r in rows:
            title = clean_article_title(r["title"])
            if any(term in title for term in terms):
                matches.append({
                    "path": r["path"],
                    "title": title,
                    "category": category_slug_from_path(r["path"]),
                    "matched_terms": [term for term in terms if term in title][:5],
                })
        kyushu[pref] = {
            "article_count": len(matches),
            "articles": matches[:12],
            "status": "covered" if matches else "gap",
        }

    dupes = duplicate_hints(rows)
    hub_paths = [
        "area/index.html",
        "cost/index.html",
        "guide/index.html",
        "guide/how-to-choose.html",
        "guide/seizenseiri.html",
        "guide/tokushu-seisou.html",
        "guide/kuyo.html",
        "blog/index.html",
    ] + [f"blog/{slug}/index.html" for slug in CONFIG.get("new_article_categories", {})]
    hubs = [p for p in hub_paths if (ROOT / p).exists()]
    area_duplicates = [
        {
            "area": x["area"],
            "article_count": x["article_count"],
            "articles": x["articles"],
        }
        for x in area_coverage if x["article_count"] >= 2
    ]
    area_duplicates.sort(key=lambda x: x["article_count"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hubs": hubs,
        "category_counts": {
            slug: len(items) for slug, items in sorted(by_category.items())
        },
        "category_titles": {
            slug: [{"path": r["path"], "title": r["title"]} for r in items]
            for slug, items in sorted(by_category.items())
        },
        "fukuoka_area_tags": area_tags,
        "fukuoka_area_coverage": area_coverage,
        "fukuoka_area_gaps": [x["area"] for x in area_coverage if x["status"] == "gap"],
        "fukuoka_area_duplicates": area_duplicates[:20],
        "kyushu_prefecture_coverage": kyushu,
        "duplicate_title_hints": dupes[:20],
        "strategy_rules": [
            "既存のarea/・guide/・cost/・各blogカテゴリを親ハブとして扱う",
            "地域別は未カバー地域を優先し、同一地域の重複記事は原則増やさない",
            "同じ検索意図が既存にあれば新規記事ではなく統合・改善を優先する",
            "新規記事は全記事一覧・カテゴリ一覧・サイト内検索・サイトマップへ必ず接続する",
            "福岡の主要地域カバレッジを厚くした上で、九州7県へ段階的に広げる",
            "九州展開は地名差替えではなく制度差・広域比較・遠方実家整理など独自価値を優先する",
        ],
    }


def make_report(rows: list[dict], gsc_map: dict) -> dict:
    ranked = []
    for r in rows:
        x = dict(r)
        x["gsc"] = gsc_map.get(r["path"])
        x["priority_score"] = candidate_score(r, x["gsc"])
        ranked.append(x)
    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    coverage = build_site_coverage(rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site": CONFIG["site_url"],
        "top_improvement_candidates": ranked[:25],
        "duplicate_title_hints": duplicate_hints(rows),
        "coverage": coverage,
    }


def strip_json_fence(raw: str) -> str:
    raw = raw.strip()
    fence = chr(96) * 3
    if raw.startswith(fence):
        raw = re.sub("^" + re.escape(fence) + r"(?:json)?\s*|\s*" + re.escape(fence) + "$", "", raw, flags=re.S)
    return raw.strip()


def replace_title(html: str, title: str) -> str:
    safe = escape(title, quote=False)
    if TITLE_RE.search(html):
        return TITLE_RE.sub(f"<title>{safe}</title>", html, count=1)
    return html.replace("</head>", f"  <title>{safe}</title>\n</head>", 1)


def replace_meta(html: str, *, name: str | None = None, prop: str | None = None, content: str) -> str:
    if not (name or prop):
        return html
    key = "name" if name else "property"
    value = name or prop or ""
    pattern = re.compile(
        rf'<meta\b(?=[^>]*\b{key}=["\']{re.escape(value)}["\'])[^>]*>',
        re.I,
    )
    tag = f'<meta {key}="{escape(value, quote=True)}" content="{escape(content, quote=True)}">'
    if pattern.search(html):
        return pattern.sub(tag, html, count=1)
    return html.replace("</head>", f"  {tag}\n</head>", 1)


def public_path_for(path: str) -> str:
    p = "/" + path.lstrip("/")
    if p.endswith("/index.html"):
        p = p[:-10] or "/"
    elif p.endswith(".html"):
        p = p[:-5]
    return p


def file_url_for(path: str) -> str:
    return CONFIG["site_url"].rstrip("/") + "/" + path.lstrip("/")


def canonical_url_for(path: str) -> str:
    return CONFIG["site_url"].rstrip("/") + public_path_for(path)


def normalized_url_path(url: str) -> str:
    try:
        p = urlparse(url).path or "/"
    except Exception:
        p = str(url)
    if p.endswith("/index.html"):
        p = p[:-10] or "/"
    elif p.endswith(".html"):
        p = p[:-5]
    return p.rstrip("/") or "/"


def replace_canonical(html: str, url: str) -> str:
    tag = f'<link rel="canonical" href="{escape(url, quote=True)}">'
    pattern = re.compile(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>', re.I)
    if pattern.search(html):
        return pattern.sub(tag, html, count=1)
    return html.replace("</head>", f"  {tag}\n</head>", 1)


def sanitize_article_html(article_html: str) -> str:
    # JSON-LD/head metadata are controlled by the system, never by free-form article output.
    article_html = re.sub(r"<script\b.*?</script>", "", article_html, flags=re.I | re.S)
    article_html = re.sub(r'href=["\']/about["\']', 'href="/about.html"', article_html, flags=re.I)
    return article_html


def sync_structured_data(html: str, title: str, description: str, image_url: str | None) -> str:
    modified = datetime.now(ZoneInfo(CONFIG["timezone"])).date().isoformat()
    canonical_match = CANONICAL_RE.search(html)
    canonical = canonical_match.group(1).strip() if canonical_match else ""
    h1_match = H1_RE.search(html)
    headline = visible(h1_match.group(1)) if h1_match else re.sub(r"\s*[｜|]\s*福岡遺品整理ガイド.*$", "", title).strip()

    def walk(obj):
        if isinstance(obj, dict):
            typ = obj.get("@type")
            types = typ if isinstance(typ, list) else [typ]
            if any(t in {"Article", "BlogPosting", "NewsArticle"} for t in types):
                obj["headline"] = headline
                obj["description"] = description
                obj["dateModified"] = modified
                if canonical:
                    obj["mainEntityOfPage"] = canonical
                    if "@id" in obj and isinstance(obj.get("@id"), str):
                        obj["@id"] = canonical + "#article"
                if image_url:
                    obj["image"] = image_url
            if "BreadcrumbList" in types and isinstance(obj.get("itemListElement"), list):
                items = obj["itemListElement"]
                if items:
                    last = items[-1]
                    if isinstance(last, dict):
                        last["name"] = headline
                        if "item" in last and canonical:
                            last["item"] = canonical
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
        return match.group(1) + "\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n" + match.group(3)

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
    canonical = canonical_url_for(path)
    legacy = file_url_for(path)
    today = datetime.now(ZoneInfo(CONFIG["timezone"])).date().isoformat()
    xml = p.read_text(encoding="utf-8")

    # Match either the old .html URL or the clean final URL.
    for url in (legacy, canonical):
        block_re = re.compile(
            rf"(<url>\s*<loc>){re.escape(url)}(</loc>.*?<lastmod>)([^<]+)(</lastmod>.*?</url>)",
            re.S,
        )
        if block_re.search(xml):
            xml = block_re.sub(
                lambda m: m.group(1) + canonical + m.group(2) + today + m.group(4),
                xml,
                count=1,
            )
            p.write_text(xml, encoding="utf-8")
            return


def update_search_data(path: str, title: str, description: str) -> None:
    p = ROOT / "js/search-data.json"
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    target = public_path_for(path)
    legacy_target = "/" + path.lstrip("/")
    changed = False

    def walk(v):
        nonlocal changed
        if isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            if v.get("url") in {target, legacy_target}:
                if v.get("url") != target:
                    v["url"] = target
                    changed = True
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
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inventory_for_internal_links(rows: list[dict], current_path: str) -> list[dict]:
    return [
        {"path": public_path_for(r["path"]), "title": r["title"]}
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
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', html, re.I)
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

あなたは本文とSEO文言を判断します。ただし実装上、あなたが直接変更するのはarticle_htmlとSEO文言です。
必要なら title、meta description、OGP文言、H1、見出し構成、本文、FAQ、内部リンク、画像alt、アイキャッチ画像を更新してください。
ただし canonicalのURLパスは変えないでください。URL変更・301統合が必要と判断した場合は今回は実行せず change_summary に提案として記録してください。

必須:
- web検索を使い、法律・制度・自治体ルール・料金・統計・相談窓口などの事実を一次情報で確認する。
- 国、福岡県、市町村、e-Gov、国民生活センター等を優先する。
- 根拠を確認できない数字、料金、割合、順位、実績、口コミ、体験談、専門家、業者情報を作らない。
- 重要な事実には本文近くに直接確認できる出典リンクを置く。
- 「地名だけを変えた一般論」を増やさず、福岡固有の判断材料を優先する。
- 既存のCTA、広告枠、編集情報、公式情報セクション、主要classは維持する。\n- article要素の開始タグとclassは既存ページから変更しない。
- 広告目的の水増し文章を作らない。
- Search Consoleで伸びているページを不用意に全面改変しない。必要な部分だけ改善してよい。
- title/metaを変えない方が良ければ現状維持を選べる。
- 内部リンクは下記サイト内在庫から本当に関連するものだけ選ぶ。
- 画像は、既存画像が内容に合っているなら keep。読者理解やCTRに明確な改善が見込める時だけ generate。
- 画像に文字を焼き込まない。誤解を招くBefore/Afterや架空の人物・事業者・証拠写真風表現は避ける。
- article_html内にscriptタグやJSON-LDを入れない。canonical、OG/Twitter URL・構造化データ・headメタはシステム側で最終URLへ同期する。
- ヘッダーやフッター等article外を変更したとchange_summaryやdecision_reasonで申告しない。article外はシステム管理領域。
- 内部リンクは可能な限りリダイレクト元の.htmlではなく、最終到達する拡張子なしURLを使う。

現在のサイト構造・地域カバレッジ:
{json.dumps(build_site_coverage(rows), ensure_ascii=False)}

既存構造を守る判断:
- このページが属するカテゴリ/地域クラスターの役割を理解してから編集する
- 既存の親ハブ・兄弟記事との内部リンクを必要に応じて強化する
- 地域別記事では、地域固有情報を増やし、別地域の一般論コピーにしない
- 重複している地域・検索意図は、新規ページ追加ではなく既存ページの役割整理を優先する

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
  "article_html": "現在のarticle開始タグ（classを含む）を維持した完全な<article>...</article>",
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
    client = OpenAI(api_key=key, timeout=240.0, max_retries=2)
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    resp = client.responses.create(
        model=model,
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    data = json.loads(strip_json_fence(resp.output_text))
    data["article_html"] = sanitize_article_html(str(data.get("article_html", "")))
    data["_original_html"] = html
    return data


def validate_editor_output(candidate: dict, data: dict) -> None:
    article_html = data.get("article_html", "")
    if not article_html.startswith("<article") or "</article>" not in article_html:
        raise RuntimeError("AI response missing complete article")
    if re.search(r"<script\b", article_html, re.I):
        raise RuntimeError("AI response must not place script or JSON-LD inside article_html")
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
        if normalized_url_path(canonical_match.group(1)) != normalized_url_path(expected):
            raise RuntimeError("existing canonical points to a different content path; refusing autonomous edit")



MANAGED_SCHEMA_TYPES = {"Article", "BlogPosting", "NewsArticle", "BreadcrumbList"}


def _schema_types(obj: dict) -> set[str]:
    typ = obj.get("@type")
    if isinstance(typ, list):
        return {str(x) for x in typ}
    if typ is None:
        return set()
    return {str(typ)}


def _find_first_article_schema(obj):
    if isinstance(obj, dict):
        if _schema_types(obj) & {"Article", "BlogPosting", "NewsArticle"}:
            return obj
        if isinstance(obj.get("@graph"), list):
            for child in obj["@graph"]:
                found = _find_first_article_schema(child)
                if found:
                    return found
        for key, value in obj.items():
            if key == "@graph":
                continue
            found = _find_first_article_schema(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_first_article_schema(value)
            if found:
                return found
    return None


def extract_existing_schema_meta(html: str) -> dict:
    out = {"datePublished": None, "image": None}
    for match in JSONLD_RE.finditer(html):
        try:
            data = json.loads(match.group(2).strip())
        except Exception:
            continue
        article = _find_first_article_schema(data)
        if not article:
            continue
        if not out["datePublished"] and article.get("datePublished"):
            out["datePublished"] = article.get("datePublished")
        if not out["image"] and article.get("image"):
            image = article.get("image")
            if isinstance(image, list) and image:
                image = image[0]
            if isinstance(image, dict):
                image = image.get("url")
            if isinstance(image, str):
                out["image"] = image
    return out


def _prune_managed_schema(obj):
    if isinstance(obj, dict):
        if _schema_types(obj) & MANAGED_SCHEMA_TYPES:
            return None

        if isinstance(obj.get("@graph"), list):
            graph = []
            for child in obj["@graph"]:
                kept = _prune_managed_schema(child)
                if kept is not None:
                    graph.append(kept)
            obj = dict(obj)
            if graph:
                obj["@graph"] = graph
            else:
                obj.pop("@graph", None)

        # Preserve unrelated schemas such as FAQPage, but recursively clean
        # any managed Article/Breadcrumb nodes nested within them.
        cleaned = {}
        for key, value in obj.items():
            if key == "@graph":
                cleaned[key] = value
                continue
            kept = _prune_managed_schema(value)
            if kept is not None:
                cleaned[key] = kept
        if set(cleaned.keys()) <= {"@context"}:
            return None
        return cleaned

    if isinstance(obj, list):
        values = []
        for value in obj:
            kept = _prune_managed_schema(value)
            if kept is not None:
                values.append(kept)
        return values or None

    return obj


def remove_managed_schema(html: str) -> str:
    def repl(match: re.Match) -> str:
        try:
            data = json.loads(match.group(2).strip())
        except Exception:
            return match.group(0)
        kept = _prune_managed_schema(data)
        if kept is None:
            return ""
        return (
            match.group(1)
            + "\n"
            + json.dumps(kept, ensure_ascii=False, indent=2)
            + "\n"
            + match.group(3)
        )

    return JSONLD_RE.sub(repl, html)


def _absolute_image_url(src: str | None) -> str | None:
    if not src:
        return None
    src = str(src).strip()
    if not src:
        return None
    if src.startswith("http://") or src.startswith("https://"):
        return src
    if src.startswith("/"):
        return CONFIG["site_url"].rstrip("/") + src
    return CONFIG["site_url"].rstrip("/") + "/" + src.lstrip("/")


def article_image_url(html: str, fallback: str | None = None) -> str:
    og = re.search(
        r'<meta\b(?=[^>]*property=["\']og:image["\'])[^>]*content=["\']([^"\']+)',
        html,
        re.I,
    )
    if og:
        return _absolute_image_url(og.group(1)) or CONFIG["site_url"].rstrip("/") + "/images/ogp-default.png"

    article_match = ARTICLE_RE.search(html)
    if article_match:
        img = SRC_RE.search(article_match.group(1))
        if img:
            return _absolute_image_url(img.group(1)) or CONFIG["site_url"].rstrip("/") + "/images/ogp-default.png"

    return _absolute_image_url(fallback) or CONFIG["site_url"].rstrip("/") + "/images/ogp-default.png"


def category_info_for_path(path: str) -> tuple[str, str]:
    slug = category_slug_from_path(path)
    label = CONFIG.get("new_article_categories", {}).get(slug, "ブログ")
    url = f"/blog/{slug}/" if slug in CONFIG.get("new_article_categories", {}) else "/blog/"
    return label, url


def normalize_managed_metadata(
    html: str,
    *,
    path: str,
    title: str,
    description: str,
    image_url: str | None = None,
) -> str:
    canonical = canonical_url_for(path)
    h1_match = H1_RE.search(html)
    headline = visible(h1_match.group(1)) if h1_match else clean_article_title(title)
    existing = extract_existing_schema_meta(html)

    published = existing.get("datePublished")
    if not published:
        date_match = re.search(
            r'<time\b[^>]*datetime=["\']([^"\']+)["\']',
            html,
            re.I,
        )
        published = date_match.group(1) if date_match else None
    if not published:
        published = datetime.now(ZoneInfo(CONFIG["timezone"])).date().isoformat()

    now_jst = datetime.now(ZoneInfo(CONFIG["timezone"])).replace(microsecond=0).isoformat()
    final_image = image_url or article_image_url(html, existing.get("image"))

    html = replace_title(html, title)
    html = replace_meta(html, name="description", content=description)
    html = replace_meta(html, prop="og:title", content=title)
    html = replace_meta(html, prop="og:description", content=description)
    html = replace_meta(html, prop="og:url", content=canonical)
    html = replace_meta(html, prop="og:image", content=final_image)
    html = replace_meta(html, name="twitter:card", content="summary_large_image")
    html = replace_meta(html, name="twitter:title", content=title)
    html = replace_meta(html, name="twitter:description", content=description)
    html = replace_meta(html, name="twitter:image", content=final_image)
    html = replace_canonical(html, canonical)

    html = remove_managed_schema(html)

    category_label, category_url = category_info_for_path(path)
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": canonical + "#article",
                "headline": headline,
                "description": description,
                "image": final_image,
                "datePublished": published,
                "dateModified": now_jst,
                "author": {
                    "@type": "Organization",
                    "name": "福岡遺品整理ガイド編集部",
                    "url": CONFIG["site_url"].rstrip("/") + "/about",
                },
                "mainEntityOfPage": canonical,
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "ホーム",
                        "item": CONFIG["site_url"].rstrip("/") + "/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "ブログ",
                        "item": CONFIG["site_url"].rstrip("/") + "/blog/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": category_label,
                        "item": CONFIG["site_url"].rstrip("/") + category_url,
                    },
                    {
                        "@type": "ListItem",
                        "position": 4,
                        "name": headline,
                        "item": canonical,
                    },
                ],
            },
        ],
    }
    tag = (
        '<script type="application/ld+json">\n'
        + json.dumps(graph, ensure_ascii=False, indent=2)
        + '\n</script>'
    )
    html = html.replace("</head>", "  " + tag + "\n</head>", 1)
    return html


def build_proposed_html(candidate: dict, data: dict) -> str:
    original = data["_original_html"]
    article_match = ARTICLE_RE.search(original)
    if not article_match:
        raise RuntimeError("article-content not found while applying")

    seo = data["seo"]
    title = str(seo["title"]).strip()
    description = str(seo["description"]).strip()
    article_html = sanitize_article_html(str(data["article_html"]))

    out = original[:article_match.start(1)] + article_html + original[article_match.end(1):]
    out = normalize_managed_metadata(
        out,
        path=candidate["path"],
        title=title,
        description=description,
    )
    return out


def call_reviewer(candidate: dict, original: str, proposed: str, editor: dict) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=240.0, max_retries=2)
    reviewer_model = os.getenv("OPENAI_REVIEW_MODEL", "gpt-5.6-sol")
    prompt = f"""
あなたは公開前の独立レビュアーです。編集AIとは別人格として厳格に判定してください。
対象: {candidate["path"]}

目的:
- 読者価値と検索意図への適合
- 事実の正確性
- SEO title/meta/H1/内部リンクの妥当性
- AdSense品質
- 福岡を核に、必要に応じた九州地域情報の有用性
- HTML構造を壊していないこと

必ずweb検索で重要な法律・制度・自治体情報を再確認してください。
なおcanonical、OG/Twitterメタ、Article/Breadcrumb構造化データはEditorではなくシステムが最終HTMLで正規化します。Editorの申告ではなく、提示されたNEW HTMLそのものを判定してください。
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
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=240.0, max_retries=2)
    image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
    try:
        result = client.images.generate(
            model=image_model,
            prompt=(
                "福岡を核に九州の遺品整理情報サイトで使う記事アイキャッチ。"
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
    except Exception as exc:
        print("Image generation skipped:", exc)
        return html, None
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




GENERIC_QUERY_TERMS = {
    "遺品整理", "遺品", "福岡", "福岡県", "方法", "やり方", "費用", "相場", "料金",
    "注意点", "手順", "ガイド", "おすすめ", "比較", "処分", "手続き", "対応",
    "見つかった", "どうする", "故人", "親", "親が亡くなった", "亡くなった",
    "実家", "家財", "整理", "2026", "2026年", "2026年版"
}


def topic_query_terms(topic: dict) -> list[str]:
    out = []
    for raw in topic.get("target_queries", []) or []:
        for term in re.split(r"[\s　/／・,，]+", str(raw)):
            term = term.strip()
            if len(term) >= 2 and term not in GENERIC_QUERY_TERMS:
                out.append(term)
    return sorted(set(out), key=len, reverse=True)


def core_topic_terms(topic: dict) -> list[str]:
    explicit = [
        str(x).strip()
        for x in (topic.get("core_topic_terms") or [])
        if len(str(x).strip()) >= 2 and str(x).strip() not in GENERIC_QUERY_TERMS
    ]
    if explicit:
        return sorted(set(explicit), key=len, reverse=True)

    # Infer terms that repeatedly appear across target queries.
    counts: dict[str, int] = {}
    queries = [str(x) for x in (topic.get("target_queries") or []) if str(x).strip()]
    for q in queries:
        seen = set()
        for term in re.split(r"[\s　/／・,，]+", q):
            term = term.strip()
            if len(term) < 3 or term in GENERIC_QUERY_TERMS:
                continue
            if term not in seen:
                counts[term] = counts.get(term, 0) + 1
                seen.add(term)

    threshold = max(2, (len(queries) + 1) // 2) if queries else 2
    inferred = [term for term, count in counts.items() if count >= threshold]

    # Strong legal / administrative subject phrases in the title are also anchors.
    title = str(topic.get("title") or "")
    known_subjects = [
        "相続放棄", "単純承認", "限定承認", "行政代執行", "家電リサイクル",
        "孤独死", "特殊清掃", "デジタル遺品", "形見分け", "お焚き上げ",
        "原状回復", "空き家", "成年後見", "相続税", "遺言書",
    ]
    inferred.extend(x for x in known_subjects if x in title)
    return sorted(set(inferred), key=len, reverse=True)


def find_existing_intent_match(topic: dict, rows: list[dict]) -> dict | None:
    terms = topic_query_terms(topic)
    anchors = core_topic_terms(topic)

    # If the research has a clear core subject, an existing page must share
    # that subject before it can be considered the same search intent.
    candidate_rows = rows
    if anchors:
        anchored = [
            row for row in rows
            if any(anchor in clean_article_title(row["title"]) for anchor in anchors)
        ]
        if not anchored:
            return None
        candidate_rows = anchored

    best = None
    best_score = 0.0
    for row in candidate_rows:
        title = clean_article_title(row["title"])
        matched = [t for t in terms if t in title]
        anchor_matches = [a for a in anchors if a in title]
        ratio = SequenceMatcher(None, str(topic.get("title", "")), title).ratio()

        score = ratio * 5
        score += sum(min(8, len(t)) for t in matched)
        score += sum(12 for _ in anchor_matches)

        if score > best_score:
            best_score = score
            best = {
                "path": row["path"],
                "title": title,
                "matched_terms": matched,
                "core_topic_matches": anchor_matches,
                "title_similarity": round(ratio, 3),
                "intent_score": round(score, 2),
            }

    if not best:
        return None

    if anchors:
        # Anchor match is required and already guaranteed. Require either
        # meaningful title similarity or at least one additional specific term.
        additional = [
            t for t in best["matched_terms"]
            if t not in GENERIC_QUERY_TERMS and t not in anchors
        ]
        if best["title_similarity"] >= 0.42 or additional:
            return best
        return None

    specific = [t for t in best["matched_terms"] if t not in GENERIC_QUERY_TERMS]
    if len(specific) >= 2:
        return best
    if best["title_similarity"] >= 0.72:
        return best
    return None


def attach_run_context(record: dict, *, research: dict | None, attempts: list[dict] | None, action_type: str) -> dict:
    record["research"] = research
    record["review_attempts"] = attempts or []
    record["action_type"] = action_type

    steps = record.setdefault("steps", [])
    research_detail = "新規テーマ候補なし"
    research_status = "done"
    if research:
        if research.get("duplicate_existing"):
            d = research["duplicate_existing"]
            research_detail = f"新規候補「{research.get('title')}」は既存「{d.get('title')}」と検索意図が重なるため、既存改善へ切替"
        elif research.get("create"):
            research_detail = f"新規候補「{research.get('title')}」を機会スコア {research.get('opportunity_score')} 点で発見"
        else:
            research_detail = str(research.get("decision_reason") or "新規記事化しないと判断")
    steps.insert(1, {
        "key": "research",
        "label": "サイト棚卸し＋Webリサーチ",
        "status": research_status,
        "detail": research_detail,
    })

    attempts = attempts or []
    if len(attempts) > 1:
        reviewer_index = next((i for i, st in enumerate(steps) if st.get("key") == "reviewer"), len(steps))
        retry_steps = []
        for i, attempt in enumerate(attempts[1:], start=1):
            retry_steps.append({
                "key": f"revision_{i}",
                "label": f"Reviewer指摘で再修正 {i}",
                "status": "done",
                "detail": f"前回指摘を反映して再編集 → Reviewer {attempt.get('score')}点",
            })
        steps[reviewer_index:reviewer_index] = retry_steps
    return record


def discover_new_topic(rows: list[dict]) -> dict | None:
    if not CONFIG.get("research_new_topics_every_run"):
        return None
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None

    from openai import OpenAI
    client = OpenAI(api_key=key, timeout=240.0, max_retries=2)
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    existing = [{"path": r["path"], "title": r["title"]} for r in rows]
    coverage = build_site_coverage(rows)

    prompt = f"""
あなたは「福岡遺品整理ガイド」の編集長兼SEOリサーチャーです。
サイトの目標は次です:
{CONFIG.get("content_mission")}

記事数を増やすこと自体は目的ではありません。
毎回web検索を行い、既存サイトに本当に不足している新規テーマを1つだけ調査してください。

調査範囲:
- 福岡県を最優先
- 九州7県: {", ".join(CONFIG.get("kyushu_prefectures", []))}
- 国、自治体、e-Gov、国民生活センター等の一次情報
- 遺品整理、生前整理、特殊清掃、供養、費用、地域制度、遠方の実家整理、相続・廃棄物手続き等
- 現在の制度変更・自治体ルール・実務上の困りごと
- 福岡の読者にも関係がある九州域内の地域差

禁止:
- 地名だけ差し替えた薄い量産
- 既存記事と同じ検索意図
- 一次情報で裏付けられないテーマ
- 架空の業者比較・ランキング・口コミ・実績
- 「九州No.1」等の未検証な自称

現在のサイトカバレッジ:
{json.dumps(coverage, ensure_ascii=False)}

既存記事:
{json.dumps(existing, ensure_ascii=False)}

選定ルール:
- まず既存サイト構造の「穴」を埋める。すでに強いクラスターへ似た記事を増やさない。
- areaカテゴリでは fukuoka_area_gaps と既存地域記事の重複を必ず確認する。
- 九州展開は、福岡の基礎カバレッジを壊さず、九州7県で一次情報に基づく独自価値がある時だけ行う。\n- 福岡県外は地名差替え型の個別市記事を量産せず、九州比較・制度差・遠方実家整理など福岡の読者にも意味がある広域テーマを優先する
- duplicate_title_hints に近いテーマは新規記事化せず、既存記事統合・改善を優先する。
- 「遺品」「親が亡くなった」「処分」「手続き」「家の片付け」などの一般語が重なるだけでは重複と判定しない。
- core_topic_terms には検索意図の中心語だけを入れる。例: 相続放棄の記事なら「相続放棄」「単純承認」。
- 新規候補と既存記事を同一検索意図と判断するには、原則としてcore_topic_termsの少なくとも1つが既存記事タイトルにも存在することを要求する。
- 同じ市を複数記事で扱う場合は、検索意図が明確に違う場合だけ許可する。
- 「費用」「業者選び」など全地域共通の一般論を地域名だけ変えて量産しない。

許可カテゴリ:
{json.dumps(CONFIG.get("new_article_categories", {}), ensure_ascii=False)}

JSONのみ:
{{
  "create": true,
  "opportunity_score": 0,
  "category_slug": "ihinseiri",
  "slug": "英小文字数字ハイフンのみ",
  "title": "記事タイトル",
  "search_intent": "読者が解決したいこと",
  "why_now": "今このテーマを扱う理由",
  "missing_value": "既存サイトに足りない価値",
  "primary_sources": [{{"name":"一次情報機関","url":"https://..."}}],
  "research_findings": ["調査で確認した重要事項"],
  "target_queries": ["想定検索語"],
  "core_topic_terms": ["検索意図の中心となる固有主題。例: 相続放棄, 単純承認"],
  "duplicate_risk": "low",
  "decision_reason": "新規記事にする/しない判断理由"
}}

opportunity_score は需要、独自性、一次情報の強さ、既存記事との差分を厳しく採点してください。
価値が弱ければ create=false にしてください。
"""
    resp = client.responses.create(model=model, tools=[{"type": "web_search"}], input=prompt)
    data = json.loads(strip_json_fence(resp.output_text))
    if not isinstance(data, dict):
        return None
    data["site_coverage"] = coverage
    if not data.get("create"):
        return data

    slug = str(data.get("slug", "")).strip().lower()
    category = str(data.get("category_slug", "")).strip()
    title = str(data.get("title", "")).strip()
    if category not in CONFIG.get("new_article_categories", {}):
        data["create"] = False
        data["decision_reason"] = "許可カテゴリ外"
        return data
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", slug):
        data["create"] = False
        data["decision_reason"] = "slug形式が不正"
        return data
    if not title:
        data["create"] = False
        data["decision_reason"] = "タイトルが空"
        return data

    highest = 0.0
    nearest = None
    for row in rows:
        ratio = SequenceMatcher(None, title, row["title"]).ratio()
        if ratio > highest:
            highest = ratio
            nearest = row
    data["nearest_existing"] = {
        "title": nearest["title"],
        "path": nearest["path"],
        "similarity": round(highest, 3),
    } if nearest else None
    if highest >= 0.62:
        data["create"] = False
        data["duplicate_existing"] = data.get("nearest_existing")
        data["decision_reason"] = f"既存記事と検索意図が近いため新規作成せず既存改善（タイトル類似度 {highest:.3f}）"
        return data

    intent_match = find_existing_intent_match(data, rows)
    if intent_match:
        data["create"] = False
        data["duplicate_existing"] = intent_match
        data["decision_reason"] = (
            "新規テーマとしては価値があるが、既存記事と検索意図が重なるため、"
            "新規ページを増やさず既存記事の一次情報・実務性を強化する"
        )
        return data

    src = [x.get("url", "") for x in data.get("primary_sources", []) if isinstance(x, dict)]
    if not any(
        u.startswith("http") and any(d in urlparse(u).netloc for d in CONFIG["preferred_source_domains"])
        for u in src
    ):
        data["create"] = False
        data["decision_reason"] = "優先一次情報を確認できない"
        return data
    return data


def new_article_path(topic: dict) -> str:
    today = datetime.now(ZoneInfo(CONFIG["timezone"])).strftime("%Y%m%d")
    return f"blog/{topic['category_slug']}/article-{today}-{topic['slug']}.html"


def call_new_article_writer(topic: dict, rows: list[dict]) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=240.0, max_retries=2)
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    category_name = CONFIG["new_article_categories"][topic["category_slug"]]
    path = new_article_path(topic)

    prompt = f"""
あなたは「福岡遺品整理ガイド」の上級編集者です。
以下のリサーチ済みテーマから、公開可能な新規記事をゼロから作成してください。

サイト目標:
{CONFIG.get("content_mission")}

テーマ:
{json.dumps(topic, ensure_ascii=False)}

現在のサイト構造・地域カバレッジ:
{json.dumps(build_site_coverage(rows), ensure_ascii=False)}

新規記事の構造ルール:
- どの親ハブ・カテゴリクラスターの子ページになるかを明確にする
- area記事なら未カバー地域または明確に別検索意図のテーマだけ作る
- 既存地域記事と重なる場合は作らない
- 親ハブと関連する兄弟記事への内部リンクを本文内に入れる
- 地域固有の自治体ルール・搬出条件・相談窓口などを中心にする
- 福岡県外は九州広域で意味があるテーマを優先し、地名だけ変えた記事は禁止

公開予定パス: {path}
カテゴリ: {category_name}

必須:
- web検索を再度行い、重要な事実を一次情報で検証する
- 福岡を核に、必要な場合のみ九州7県の制度差を扱う
- 読者が最終的に何をすればよいかまで具体化する
- 法律・制度・行政・料金・統計は出典なしで断定しない
- 架空の業者、口コミ、実績、監修者、体験談を作らない
- 既存記事の言い換え記事にしない
- 不自然なキーワード詰め込みをしない
- editorial-info と reference-links を必ず含める
- 参考情報は本文近くにもリンクし、末尾にもまとめる
- H1は1つだけ
- 既存記事と同じく、パンくず・article-meta・article-hero-image・見出し階層を自然に構成する
- 記事内に広告コードは書かない（システム側で挿入する）
- hero画像は最初のfigure内に /images/ogp-default.png を仮指定する
- about.htmlへの編集方針リンクをeditorial-info内に入れる
- internal_linksには、既存サイト内から本当に関連する記事を2〜3本選ぶ
- areaカテゴリでは /area/ と /blog/area/ を親ハブとして扱う

返答JSONのみ:
{{
  "seo": {{
    "title": "titleタグ。末尾に｜福岡遺品整理ガイド",
    "description": "検索結果用説明",
    "og_title": "OGタイトル",
    "og_description": "OG説明"
  }},
  "h1": "記事H1",
  "summary": "一覧カード用に80〜130文字",
  "keywords": ["検索・サイト内検索用語"],
  "article_html": "<article class=\\"article-content\\">...</article>",
  "change_summary": ["新規記事で提供した価値"],
  "primary_sources": [{{"name":"機関名","url":"https://..."}}],
  "internal_links": ["/blog/..."],
  "image": {{
    "action": "generate または keep",
    "prompt": "文字なしのアイキャッチ生成指示",
    "alt": "画像alt"
  }},
  "decision_reason": "この構成・内容にした理由"
}}
"""
    resp = client.responses.create(model=model, tools=[{"type": "web_search"}], input=prompt)
    data = json.loads(strip_json_fence(resp.output_text))
    data["article_html"] = sanitize_article_html(str(data.get("article_html", "")))
    data["_original_html"] = ""
    return data


def validate_new_article_output(topic: dict, data: dict) -> None:
    article_html = str(data.get("article_html", ""))
    if not article_html.startswith("<article") or "</article>" not in article_html:
        raise RuntimeError("new article missing complete article element")
    if re.search(r"<script\b", article_html, re.I):
        raise RuntimeError("new article must not put script or JSON-LD inside article_html")
    if len(H1_RE.findall(article_html)) != 1:
        raise RuntimeError("new article must contain exactly one H1")
    for marker in ('class="editorial-info"', 'class="reference-links"'):
        if marker not in article_html:
            raise RuntimeError("new article missing required marker: " + marker)
    if 'href="/about.html"' not in article_html:
        raise RuntimeError("new article missing editorial policy link")
    seo = data.get("seo") or {}
    if not str(seo.get("title", "")).strip():
        raise RuntimeError("new article missing SEO title")
    if len(str(seo.get("description", "")).strip()) < 40:
        raise RuntimeError("new article description too short")
    src = [x.get("url", "") for x in data.get("primary_sources", []) if isinstance(x, dict)]
    if not src:
        raise RuntimeError("new article has no primary sources")
    if not any(
        u.startswith("http") and any(d in urlparse(u).netloc for d in CONFIG["preferred_source_domains"])
        for u in src
    ):
        raise RuntimeError("new article has no preferred primary source")
    if len(visible(article_html).replace(" ", "")) < 3000:
        raise RuntimeError("new article is too thin")


def inject_middle_ad(article_html: str, genre: str) -> str:
    closes = [m.end() for m in re.finditer(r"</section>", article_html, re.I)]
    if not closes:
        return article_html
    pos = closes[len(closes) // 2]
    slot = f'\n<div class="fkg-ad" data-genre="{escape(genre, quote=True)}" data-placement="article_middle"></div>\n'
    return article_html[:pos] + slot + article_html[pos:]


def build_new_article_page(topic: dict, data: dict) -> str:
    path = new_article_path(topic)
    seo = data["seo"]
    h1 = str(data.get("h1") or topic["title"]).strip()
    category_slug = topic["category_slug"]
    category_name = CONFIG["new_article_categories"][category_slug]
    canonical = canonical_url_for(path)
    today_iso = datetime.now(ZoneInfo(CONFIG["timezone"])).date().isoformat()
    today_jp = datetime.now(ZoneInfo(CONFIG["timezone"])).strftime("%Y年%-m月%-d日")
    article_html = ensure_new_article_shell(data["article_html"], topic, data)
    article_html = ensure_new_article_links(article_html, topic, data)
    article_html = inject_middle_ad(article_html, category_name)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(str(seo["title"]))}</title>
  <meta name="description" content="{escape(str(seo["description"]), quote=True)}">
  <link rel="canonical" href="{escape(canonical, quote=True)}">
  <meta property="og:title" content="{escape(str(seo.get("og_title") or seo["title"]), quote=True)}">
  <meta property="og:description" content="{escape(str(seo.get("og_description") or seo["description"]), quote=True)}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{escape(canonical, quote=True)}">
  <meta property="og:image" content="{CONFIG["site_url"].rstrip("/")}/images/ogp-default.png">
  <meta property="og:site_name" content="{CONFIG["site_name"]}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="stylesheet" href="/css/style.css?v=20260814a">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-S1QGZ4ETK0"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-S1QGZ4ETK0');</script>
  <script type="application/ld+json">
  {json.dumps({
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": h1,
      "description": str(seo["description"]),
      "image": CONFIG["site_url"].rstrip("/") + "/images/ogp-default.png",
      "datePublished": today_iso,
      "dateModified": today_iso,
      "author": {"@type": "Organization", "name": "福岡遺品整理ガイド編集部"},
      "mainEntityOfPage": canonical,
  }, ensure_ascii=False, indent=2)}
  </script>
</head>
<body>
<header class="header">
  <div class="header-inner">
    <a href="/" class="header-logo">福岡遺品整理ガイド</a>
    <nav class="header-nav" id="headerNav">
      <a href="/area/">地域別情報</a><a href="/cost/">費用相場</a><a href="/guide/">お役立ちガイド</a><a href="/blog/">記事を検索</a><a href="/for-business/">業者様向け</a><a href="/contact/" class="header-cta">無料相談する</a>
    </nav>
    <button class="mobile-menu-btn" id="menuBtn" aria-label="メニュー"><span></span><span></span><span></span></button>
  </div>
</header>
<main class="article-page">
  <div class="list-container">
    <div class="fkg-ad" data-genre="{escape(category_name, quote=True)}" data-placement="article_top"></div>
    {article_html}
    <div class="fkg-ad" data-genre="{escape(category_name, quote=True)}" data-placement="article_bottom"></div>
  </div>
</main>
<footer class="footer">
  <div class="footer-inner">
    <div><div class="footer-brand">福岡遺品整理ガイド</div><p class="footer-desc">福岡を核に、九州の遺品整理・特殊清掃・生前整理に役立つ実務情報を提供します。</p></div>
    <div class="footer-col"><h3>カテゴリ</h3><ul><li><a href="/guide/">遺品整理ガイド</a></li><li><a href="/guide/seizenseiri.html">生前整理</a></li><li><a href="/guide/tokushu-seisou.html">特殊清掃</a></li></ul></div>
    <div class="footer-col"><h3>お役立ち情報</h3><ul><li><a href="/cost/">費用相場</a></li><li><a href="/area/">地域別情報</a></li><li><a href="/blog/">ブログ記事一覧</a></li></ul></div>
    <div class="footer-col"><h3>サイト情報</h3><ul><li><a href="/about.html">編集方針・運営情報</a></li><li><a href="/contact/">お問い合わせ</a></li><li><a href="/privacy-policy.html">プライバシーポリシー</a></li></ul></div>
  </div>
  <div class="footer-bottom">&copy; 2026 福岡遺品整理ガイド All Rights Reserved.</div>
</footer>
<script src="/ad-widget.js" defer></script>
<script>document.getElementById('menuBtn').addEventListener('click',function(){{document.getElementById('headerNav').classList.toggle('active');}});</script>
</body>
</html>
"""


def call_revision_editor(candidate: dict, current_html: str, prior_editor: dict, review: dict, rows: list[dict], attempt: int) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=240.0, max_retries=2)
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    article_match = ARTICLE_RE.search(current_html)
    if not article_match:
        raise RuntimeError("revision source article-content not found")

    prompt = f"""
あなたは前回案を改善する担当Editorです。
Reviewerに落ちたから翌日まで放置するのではなく、このRun内ですぐ修正してください。

対象: {candidate["path"]}
再修正回数: {attempt}
Reviewer:
{json.dumps(review, ensure_ascii=False)}

前回Editorの判断:
{json.dumps({k:v for k,v in prior_editor.items() if not k.startswith("_")}, ensure_ascii=False)}

現在案:
---BEGIN ARTICLE---
{article_match.group(1)}
---END ARTICLE---

必須:
- Reviewerのissuesを1件ずつ解消する
- web検索で一次情報を再確認する
- Reviewerが指摘していない良い部分は壊さない
- 不確かな数値・断定は削除するか一次情報を付ける
- SEO目的だけの水増しをしない
- editorial-info / reference-links / CTA /広告枠の主要構造は維持\n- article要素の開始タグとclassは現在案から変更しない
- article_html内にscriptタグ・JSON-LDを入れない
- canonical、OG URL、head内JSON-LDはシステム側で最終到達URLへ同期するため、本文側で新しく作らない
- 内部リンクはリダイレクト元ではなく最終到達URLを使う
- 新規記事の場合も既存記事の場合も、公開基準88点以上を目指す

JSONのみ:
{{
  "seo": {{
    "title": "titleタグ",
    "description": "meta description",
    "og_title": "OG title",
    "og_description": "OG description"
  }},
  "h1": "H1",
  "summary": "一覧用要約",
  "keywords": ["検索語"],
  "article_html": "現在案のarticle開始タグ・classを維持した完全な<article>...</article>",
  "change_summary": ["今回の再修正内容"],
  "primary_sources": [{{"name":"機関名","url":"https://..."}}],
  "internal_links": ["/blog/..."],
  "image": {{
    "action": "keep または generate",
    "prompt": "",
    "alt": ""
  }},
  "decision_reason": "Reviewer指摘をどう解消したか"
}}
"""
    resp = client.responses.create(model=model, tools=[{"type": "web_search"}], input=prompt)
    data = json.loads(strip_json_fence(resp.output_text))
    data["article_html"] = sanitize_article_html(str(data.get("article_html", "")))
    data["_original_html"] = current_html
    return data


def review_passed(review: dict) -> bool:
    return bool(review.get("approve")) and int(review.get("score", 0) or 0) >= int(CONFIG.get("minimum_reviewer_score", 88))


def add_sitemap_url(path: str) -> None:
    p = ROOT / "sitemap.xml"
    if not p.exists():
        return
    url = canonical_url_for(path)
    xml = p.read_text(encoding="utf-8")
    if f"<loc>{url}</loc>" in xml:
        update_sitemap(path)
        return
    today = datetime.now(ZoneInfo(CONFIG["timezone"])).date().isoformat()
    block = f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
"""
    xml = xml.replace("</urlset>", block + "</urlset>")
    p.write_text(xml, encoding="utf-8")


def add_search_entry(topic: dict, data: dict, path: str, thumbnail: str) -> None:
    p = ROOT / "js/search-data.json"
    if not p.exists():
        return
    rows = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return
    url = public_path_for(path)
    rows = [r for r in rows if r.get("url") != url]
    rows.insert(0, {
        "title": str(data.get("h1") or topic["title"]),
        "desc": str(data.get("summary") or data["seo"]["description"]),
        "url": url,
        "category": topic["category_slug"],
        "categorySlug": topic["category_slug"],
        "date": datetime.now(ZoneInfo(CONFIG["timezone"])).strftime("%Y-%m-%d"),
        "thumbnail": thumbnail,
        "keywords": " ".join(str(x) for x in data.get("keywords", [])),
        "text": visible(data["article_html"]),
    })
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def article_card_html(topic: dict, data: dict, path: str, thumbnail: str) -> str:
    category_name = CONFIG["new_article_categories"][topic["category_slug"]]
    title = escape(str(data.get("h1") or topic["title"]))
    summary = escape(str(data.get("summary") or data["seo"]["description"]))
    date_label = datetime.now(ZoneInfo(CONFIG["timezone"])).strftime("%Y年%-m月%-d日")
    return f"""
        <a href="{public_path_for(path)}" class="article-card" data-category="{escape(topic['category_slug'], quote=True)}">
          <div class="article-card-img"><img src="{escape(thumbnail, quote=True)}" alt="{title}" loading="lazy" width="800" height="533"></div>
          <div class="article-card-body">
            <span class="article-card-tag">{escape(category_name)}</span>
            <h3>{title}</h3>
            <p>{summary}</p>
            <span class="article-card-date">{date_label} 更新</span>
          </div>
        </a>
"""




def ensure_new_article_shell(article_html: str, topic: dict, data: dict) -> str:
    category_slug = topic["category_slug"]
    category_name = CONFIG["new_article_categories"][category_slug]
    h1 = str(data.get("h1") or topic.get("title") or "").strip()
    today_jp = datetime.now(ZoneInfo(CONFIG["timezone"])).strftime("%Y年%-m月%-d日")
    category_url = f"/blog/{category_slug}/"

    open_match = re.search(r"<article\b[^>]*>", article_html, re.I)
    if not open_match:
        return article_html

    inserts = []

    if 'class="breadcrumb"' not in article_html and 'class="article-breadcrumb"' not in article_html:
        inserts.append(
            '<nav class="breadcrumb" aria-label="パンくずリスト">'
            '<a href="/">ホーム</a> &gt; '
            '<a href="/blog/">ブログ</a> &gt; '
            f'<a href="{escape(category_url, quote=True)}">{escape(category_name)}</a> &gt; '
            f'<span>{escape(h1)}</span>'
            '</nav>'
        )

    if inserts:
        article_html = article_html[:open_match.end()] + "\n" + "\n".join(inserts) + article_html[open_match.end():]

    if 'class="article-meta"' not in article_html:
        article_html = re.sub(
            r"(</h1>)",
            r'\1\n<p class="article-meta">更新日：' + today_jp + ' | カテゴリ：<a href="' + category_url + '">' + category_name + '</a></p>',
            article_html,
            count=1,
            flags=re.I,
        )

    if 'class="article-hero-image"' not in article_html:
        hero = (
            '\n<figure class="article-hero-image">'
            '<img src="/images/ogp-default.png" alt="' + escape(h1, quote=True) + '" '
            'width="800" height="450" loading="lazy">'
            '</figure>\n'
        )
        meta_match = re.search(r'<p\s+class=["\']article-meta["\'][^>]*>.*?</p>', article_html, re.I | re.S)
        if meta_match:
            article_html = article_html[:meta_match.end()] + hero + article_html[meta_match.end():]
        else:
            article_html = re.sub(r"(</h1>)", r"\1" + hero, article_html, count=1, flags=re.I)

    return article_html


def ensure_new_article_links(article_html: str, topic: dict, data: dict) -> str:
    slug = topic["category_slug"]
    parent_hubs = {
        "ihinseiri": [("/guide/", "遺品整理ガイド"), ("/blog/ihinseiri/", "遺品整理の記事一覧")],
        "tokushu-seisou": [("/guide/tokushu-seisou", "特殊清掃ガイド"), ("/blog/tokushu-seisou/", "特殊清掃の記事一覧")],
        "seizenseiri": [("/guide/seizenseiri", "生前整理ガイド"), ("/blog/seizenseiri/", "生前整理の記事一覧")],
        "kuyo": [("/guide/kuyo", "遺品供養ガイド"), ("/blog/kuyo/", "遺品供養の記事一覧")],
        "cost": [("/cost/", "遺品整理の費用相場"), ("/blog/cost/", "費用の記事一覧")],
        "area": [("/area/", "地域別情報"), ("/blog/area/", "地域別の記事一覧")],
    }
    links = list(parent_hubs.get(slug, []))

    for raw in data.get("internal_links", []) or []:
        url = str(raw).strip()
        if not url.startswith("/") or url.startswith("//"):
            continue
        if url.endswith(".html"):
            url = public_path_for(url)
        if any(existing[0] == url for existing in links):
            continue
        title = next(
            (
                clean_article_title(r["title"])
                for r in article_records()
                if public_path_for(r["path"]) == url or "/" + r["path"] == url
            ),
            "関連する記事",
        )
        links.append((url, title))
        if len(links) >= 5:
            break

    missing = [(url, label) for url, label in links if f'href="{url}"' not in article_html and f"href='{url}'" not in article_html]
    if not missing:
        return article_html

    items = "".join(
        f'<li><a href="{escape(url, quote=True)}">{escape(label)}</a></li>'
        for url, label in missing
    )
    section = (
        '\n<section class="related-links ai-parent-links">'
        '<h2>関連するガイド・記事</h2><ul>' + items + '</ul></section>\n'
    )
    return article_html.replace("</article>", section + "</article>", 1)


def add_area_hub_mapping(topic: dict, data: dict, path: str) -> None:
    if topic.get("category_slug") != "area":
        return
    p = ROOT / "area/index.html"
    if not p.exists():
        return

    html = p.read_text(encoding="utf-8")
    if "const areaArticles = {" not in html:
        return

    title = str(data.get("h1") or topic.get("title") or "").strip()
    public_url = public_path_for(path)
    area_names = extract_area_tags()
    matched = [area for area in area_names if area and area in title]

    if not matched:
        return

    changed = False
    title_js = json.dumps(title, ensure_ascii=False)
    url_js = json.dumps(public_url, ensure_ascii=False)

    for area in matched:
        pattern = re.compile(
            rf'("{re.escape(area)}"\s*:\s*\[)(.*?)(\n\s*\])',
            re.S,
        )
        m = pattern.search(html)
        if not m:
            continue
        body = m.group(2)
        if public_url in body or ("/" + path) in body:
            continue
        entry = f'    {{ title: {title_js}, url: {url_js} }}'
        stripped = body.rstrip()
        if stripped.strip():
            if not stripped.rstrip().endswith(","):
                stripped += ","
            new_body = stripped + "\n" + entry
        else:
            new_body = "\n" + entry
        html = html[:m.start(2)] + new_body + html[m.end(2):]
        changed = True

    if changed:
        p.write_text(html, encoding="utf-8")


def add_article_to_indexes(topic: dict, data: dict, path: str, thumbnail: str) -> None:
    card = article_card_html(topic, data, path, thumbnail)
    for rel in ("blog/index.html", f"blog/{topic['category_slug']}/index.html"):
        p = ROOT / rel
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8")
        if f'href="{public_path_for(path)}"' in html or f'href="/{path}"' in html:
            continue
        pattern = re.compile(r'(<div\s+class=["\']article-grid["\'][^>]*>)', re.I)
        if pattern.search(html):
            html = pattern.sub(lambda m: m.group(1) + "\n" + card, html, count=1)
            p.write_text(html, encoding="utf-8")


def create_new_article(topic: dict, rows: list[dict], mode: str = "improve") -> dict:
    path = new_article_path(topic)
    if (ROOT / path).exists():
        raise RuntimeError("new article path already exists: " + path)

    candidate = {
        "path": path,
        "title": topic["title"],
        "quality": 100,
        "priority_score": topic.get("opportunity_score"),
        "gsc": None,
        "candidate_type": "new_article",
        "research_reasons": [
            topic.get("why_now", ""),
            topic.get("missing_value", ""),
            topic.get("decision_reason", ""),
        ],
    }

    data = call_new_article_writer(topic, rows)
    validate_new_article_output(topic, data)
    proposed = build_new_article_page(topic, data)
    original_for_review = "新規記事のため変更前ページなし"
    attempts = []
    max_revisions = int(CONFIG.get("max_revision_attempts", 2))

    for round_index in range(max_revisions + 1):
        review = call_reviewer(candidate, original_for_review, proposed, data)
        attempts.append({
            "attempt": round_index + 1,
            "score": review.get("score"),
            "approve": review.get("approve"),
            "issues": review.get("issues", []),
            "strengths": review.get("strengths", []),
        })
        if review_passed(review):
            break
        if round_index >= max_revisions:
            record = make_run_record(
                mode=mode,
                candidate=candidate,
                status="rejected",
                outcome="新規記事を公開見送り",
                outcome_reason=f"最大{max_revisions}回再修正後もReviewer {review.get('score')}点で基準未達",
                editor=data,
                reviewer=review,
                published=False,
            )
            record = attach_run_context(record, research=topic, attempts=attempts, action_type="new_article")
            append_run_log(record)
            return {"path": path, "published": False, "review": review, "research": topic}

        data = call_revision_editor(candidate, proposed, data, review, rows, round_index + 1)
        validate_new_article_output(topic, data)
        proposed = build_new_article_page(topic, data)

    proposed, image_path = generate_image_if_needed(candidate, data, proposed)
    seo = data["seo"]
    image_url = CONFIG["site_url"].rstrip("/") + "/" + image_path if image_path else CONFIG["site_url"].rstrip("/") + "/images/ogp-default.png"
    proposed = normalize_managed_metadata(
        proposed,
        path=candidate["path"],
        title=seo["title"],
        description=seo["description"],
        image_url=image_url,
    )

    dest = ROOT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(proposed, encoding="utf-8")
    add_sitemap_url(path)
    thumbnail = "/" + image_path if image_path else "/images/ogp-default.png"
    add_search_entry(topic, data, path, thumbnail)
    add_article_to_indexes(topic, data, path, thumbnail)
    add_area_hub_mapping(topic, data, path)

    activity = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "path": path,
        "title_before": None,
        "title_after": data.get("h1") or topic["title"],
        "changes": data.get("change_summary", []),
        "sources": data.get("primary_sources", []),
        "internal_links": data.get("internal_links", []),
        "image_generated": bool(image_path),
        "image_path": image_path,
        "review_score": review.get("score"),
        "review_strengths": review.get("strengths", []),
        "status": "validated_for_auto_publish",
        "action_type": "new_article",
    }
    act = _load_list_log(ACTIVITY_LOG)
    act.insert(0, activity)
    _write_list_log(ACTIVITY_LOG, act, 180)

    record = make_run_record(
        mode=mode,
        candidate=candidate,
        status="validated",
        outcome="新規記事を公開候補として承認",
        outcome_reason=f"新規テーマを調査・執筆し、Reviewer {review.get('score')}点で公開基準を通過",
        editor=data,
        reviewer=review,
        published=True,
        image_path=image_path,
    )
    record = attach_run_context(record, research=topic, attempts=attempts, action_type="new_article")
    append_run_log(record)

    return {
        "path": path,
        "published": True,
        "review": review,
        "research": topic,
        "change_summary": data.get("change_summary", []),
    }


def _load_list_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _write_list_log(path: Path, rows: list[dict], limit: int = 180) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows[:limit], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def candidate_selection_reasons(candidate: dict) -> list[str]:
    if candidate.get("candidate_type") == "new_article":
        reasons = [str(x).strip() for x in candidate.get("research_reasons", []) if str(x).strip()]
        return reasons or ["Web・一次情報リサーチで新規記事の価値が高いと判定"]
    reasons = []
    quality = int(candidate.get("quality", 100))
    if quality < 100:
        reasons.append(f"記事品質スコアが {quality}/100 で改善余地あり")
    gsc = candidate.get("gsc") or {}
    if gsc:
        imp = float(gsc.get("impressions", 0) or 0)
        pos = float(gsc.get("position", 0) or 0)
        ctr = float(gsc.get("ctr", 0) or 0)
        if imp >= CONFIG["min_impressions_for_gsc_priority"]:
            reasons.append(f"Google検索で {int(imp)} 回表示され、改善判断に使えるデータ量がある")
        if CONFIG["position_opportunity_min"] <= pos <= CONFIG["position_opportunity_max"]:
            reasons.append(f"Google平均掲載順位 {pos:.1f} 位で、上位化の余地が大きい")
        if imp >= 100 and ctr < 0.03:
            reasons.append(f"表示 {int(imp)} 回に対して検索CTR {ctr*100:.2f}% と低く、クリック改善余地がある")
    if not reasons:
        reasons.append("サイト全体の品質・検索データを合算した優先度スコアが最上位")
    return reasons



def recent_rejection_count(path: str, lookback: int = 6) -> int:
    rows = _load_list_log(RUN_LOG)[:lookback]
    return sum(
        1 for x in rows
        if (x.get("candidate") or {}).get("path") == path
        and x.get("status") == "rejected"
    )


def choose_existing_candidate(report: dict) -> dict | None:
    candidates = report.get("top_improvement_candidates", [])
    for candidate in candidates:
        if candidate.get("priority_score", 0) <= 0:
            continue
        rejects = recent_rejection_count(candidate["path"])
        if rejects >= 2:
            print("Cooldown repeated rejected candidate:", candidate["path"], "rejects=", rejects)
            continue
        return candidate
    return None


def should_create_new_article(topic: dict | None, existing: dict | None) -> bool:
    if not CONFIG.get("allow_scheduled_new_articles"):
        return False
    if not topic or not topic.get("create"):
        return False
    score = float(topic.get("opportunity_score", 0) or 0)
    minimum = float(CONFIG.get("new_article_minimum_score", 88))
    if score < minimum:
        return False
    # A genuinely strong, non-duplicate opportunity should not wait for a calendar slot.
    if score >= 92:
        return True
    if existing is None:
        return True
    weekday = datetime.now(ZoneInfo(CONFIG["timezone"])).weekday()
    return weekday in set(CONFIG.get("new_article_days_jst", [0, 2, 4, 6]))


def append_run_log(item: dict) -> None:
    log = _load_list_log(RUN_LOG)
    run_id = str(item.get("run_id") or "")
    if run_id:
        log = [x for x in log if str(x.get("run_id") or "") != run_id]
    log.insert(0, item)
    _write_list_log(RUN_LOG, log, 240)


def make_run_record(
    *,
    mode: str,
    candidate: dict | None,
    status: str,
    outcome: str,
    outcome_reason: str,
    editor: dict | None = None,
    reviewer: dict | None = None,
    published: bool = False,
    image_path: str | None = None,
    error: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    run_id = os.getenv("GITHUB_RUN_ID")
    trigger = os.getenv("GITHUB_EVENT_NAME") or "unknown"
    gsc = (candidate or {}).get("gsc") or {}
    editor = editor or {}
    reviewer = reviewer or {}
    threshold = int(CONFIG.get("minimum_reviewer_score", 88))

    steps = [
        {
            "key": "search_console",
            "label": "Search Console取得",
            "status": "done",
            "detail": "最新の検索パフォーマンスを取得して候補選定に使用",
        }
    ]

    if candidate:
        steps.append({
            "key": "candidate",
            "label": "改善候補選定",
            "status": "done",
            "detail": f"{candidate.get('title') or candidate.get('path')} を優先度 {candidate.get('priority_score')} で選定",
        })
    else:
        steps.append({
            "key": "candidate",
            "label": "改善候補選定",
            "status": "skipped",
            "detail": outcome_reason,
        })

    if editor:
        steps.append({
            "key": "editor",
            "label": "Editor AI",
            "status": "done",
            "detail": editor.get("decision_reason") or "一次情報を調査し、改善案を作成",
        })
    else:
        steps.append({
            "key": "editor",
            "label": "Editor AI",
            "status": "error" if error else "skipped",
            "detail": error or "改善候補なしのため未実行",
        })

    if reviewer:
        score = int(reviewer.get("score", 0) or 0)
        approved = bool(reviewer.get("approve")) and score >= threshold
        steps.append({
            "key": "reviewer",
            "label": "Reviewer AI",
            "status": "done" if approved else "rejected",
            "detail": f"{score}点 / 公開基準 {threshold}点",
        })
    else:
        steps.append({
            "key": "reviewer",
            "label": "Reviewer AI",
            "status": "skipped",
            "detail": "Editor未実行のため未審査",
        })

    if published:
        steps.extend([
            {
                "key": "gate",
                "label": "品質Gate",
                "status": "pending",
                "detail": "Reviewer合格。GitHub Actionsの品質・AdSense・HTML Gateへ進行",
            },
            {
                "key": "publish",
                "label": "本番反映",
                "status": "pending",
                "detail": "Gate合格時のみmainへ自動反映",
            },
        ])
    else:
        steps.extend([
            {
                "key": "gate",
                "label": "品質Gate",
                "status": "skipped",
                "detail": "公開候補がないため本番変更用Gateは不要",
            },
            {
                "key": "publish",
                "label": "本番反映",
                "status": "skipped",
                "detail": outcome_reason,
            },
        ])

    return {
        "timestamp": now,
        "started_at": os.getenv("AI_RUN_STARTED_AT") or now,
        "finished_at": now,
        "run_id": run_id,
        "trigger": trigger,
        "mode": mode,
        "status": status,
        "outcome": outcome,
        "outcome_reason": outcome_reason,
        "candidate": {
            "path": candidate.get("path"),
            "title": candidate.get("title"),
            "priority_score": candidate.get("priority_score"),
            "quality": candidate.get("quality"),
            "gsc": {
                "clicks": gsc.get("clicks"),
                "impressions": gsc.get("impressions"),
                "ctr": gsc.get("ctr"),
                "position": gsc.get("position"),
            } if gsc else None,
            "selection_reasons": candidate_selection_reasons(candidate),
        } if candidate else None,
        "editor": {
            "status": "done" if editor else ("error" if error else "skipped"),
            "decision_reason": editor.get("decision_reason"),
            "changes": editor.get("change_summary", []),
            "sources": editor.get("primary_sources", []),
            "internal_links": editor.get("internal_links", []),
            "image_action": (editor.get("image") or {}).get("action"),
            "title_after": (editor.get("seo") or {}).get("title"),
        } if editor else {
            "status": "error" if error else "skipped",
            "decision_reason": error,
            "changes": [],
            "sources": [],
            "internal_links": [],
            "image_action": None,
            "title_after": None,
        },
        "reviewer": {
            "status": "approved" if reviewer and reviewer.get("approve") and int(reviewer.get("score", 0) or 0) >= threshold else ("rejected" if reviewer else "skipped"),
            "approve": reviewer.get("approve") if reviewer else None,
            "score": reviewer.get("score") if reviewer else None,
            "threshold": threshold,
            "issues": reviewer.get("issues", []) if reviewer else [],
            "strengths": reviewer.get("strengths", []) if reviewer else [],
            "seo_assessment": reviewer.get("seo_assessment") if reviewer else None,
            "factual_assessment": reviewer.get("factual_assessment") if reviewer else None,
        },
        "steps": steps,
        "published": published,
        "image_generated": bool(image_path),
        "image_path": image_path,
        "error": error,
    }


def append_activity(candidate: dict, data: dict, review: dict, image_path: str | None) -> None:
    log = _load_list_log(ACTIVITY_LOG)
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
    _write_list_log(ACTIVITY_LOG, log, 180)


def improve(candidate: dict, rows: list[dict], mode: str = "improve", research: dict | None = None) -> dict:
    original_html = (ROOT / candidate["path"]).read_text(encoding="utf-8")
    data = call_editor(candidate, rows)
    validate_editor_output(candidate, data)
    proposed = build_proposed_html(candidate, data)

    attempts = []
    max_revisions = int(CONFIG.get("max_revision_attempts", 2))
    min_score = int(CONFIG.get("minimum_reviewer_score", 88))
    review = {}

    for round_index in range(max_revisions + 1):
        review = call_reviewer(candidate, original_html, proposed, data)
        attempts.append({
            "attempt": round_index + 1,
            "score": review.get("score"),
            "approve": review.get("approve"),
            "issues": review.get("issues", []),
            "strengths": review.get("strengths", []),
            "editor_reason": data.get("decision_reason"),
            "changes": data.get("change_summary", []),
        })
        if review_passed(review):
            break

        if round_index >= max_revisions:
            score = int(review.get("score", 0) or 0)
            reason = f"Reviewer指摘で{max_revisions}回再修正したが、最終{score}点で公開基準{min_score}点に未達"
            result = {
                "path": candidate["path"],
                "published": False,
                "review": review,
                "change_summary": data.get("change_summary", []),
                "review_attempts": attempts,
            }
            (PRIVATE_DIR / "last-ai-change.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            record = make_run_record(
                mode=mode,
                candidate=candidate,
                status="rejected",
                outcome="再修正後も公開見送り",
                outcome_reason=reason,
                editor=data,
                reviewer=review,
                published=False,
            )
            record = attach_run_context(record, research=research, attempts=attempts, action_type="improvement")
            append_run_log(record)
            print("Reviewer rejected after retries", candidate["path"], score)
            return result

        data = call_revision_editor(candidate, proposed, data, review, rows, round_index + 1)
        validate_editor_output(candidate, data)
        proposed = build_proposed_html(candidate, data)
        print("Revised after reviewer feedback", candidate["path"], "attempt=", round_index + 2)

    proposed, image_path = generate_image_if_needed(candidate, data, proposed)
    seo = data["seo"]
    image_url = CONFIG["site_url"].rstrip("/") + "/" + image_path if image_path else None
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
        "review_attempts": attempts,
        "change_summary": data.get("change_summary", []),
        "primary_sources": data.get("primary_sources", []),
        "image_path": image_path,
        "seo": seo,
    }
    (PRIVATE_DIR / "last-ai-change.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    record = make_run_record(
        mode=mode,
        candidate=candidate,
        status="validated",
        outcome="再修正を含め公開候補として承認",
        outcome_reason=f"Reviewer {review.get('score')}点で基準{min_score}点を通過。品質Gateへ進行",
        editor=data,
        reviewer=review,
        published=True,
        image_path=image_path,
    )
    record = attach_run_context(record, research=research, attempts=attempts, action_type="improvement")
    append_run_log(record)
    print("Validated full-page improvement", candidate["path"], "score=", review.get("score"), "attempts=", len(attempts))
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["audit", "improve", "discover"], default="audit")
    args = ap.parse_args()

    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    rows = article_records()
    coverage = build_site_coverage(rows)
    (PRIVATE_DIR / "site-coverage-latest.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    public_coverage = ROOT / "data/site-coverage.json"
    public_coverage.write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    gsc = load_gsc()
    rep = make_report(rows, gsc)
    (PRIVATE_DIR / "content-os-latest.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (PRIVATE_DIR / "site-coverage-latest.json").write_text(
        json.dumps(rep.get("coverage", {}), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    try:
        if args.mode == "audit":
            append_run_log(make_run_record(
                mode=args.mode,
                candidate=None,
                status="analysis_only",
                outcome="監査のみ",
                outcome_reason="auditモードのため公開変更なし",
                published=False,
            ))
            print("Analysis complete; no article modified.")
            return 0

        topic = discover_new_topic(rows)
        if topic is not None:
            coverage = rep.get("coverage", {})
            topic["coverage_summary"] = {
                "category_counts": coverage.get("category_counts", {}),
                "fukuoka_area_gaps": coverage.get("fukuoka_area_gaps", []),
                "kyushu_prefecture_counts": {
                    k: v.get("article_count", 0)
                    for k, v in (coverage.get("kyushu_prefecture_coverage", {}) or {}).items()
                },
            }
        (PRIVATE_DIR / "new-topic-latest.json").write_text(
            json.dumps(topic or {}, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        if args.mode == "discover":
            reason = (topic or {}).get("decision_reason") or "新規テーマ調査のみ"
            record = make_run_record(
                mode=args.mode,
                candidate=None,
                status="analysis_only",
                outcome="新規テーマ調査",
                outcome_reason=reason,
                published=False,
            )
            record = attach_run_context(record, research=topic, attempts=[], action_type="research")
            append_run_log(record)
            print("Discovery complete; no article modified.")
            return 0

        candidate = choose_existing_candidate(rep)

        duplicate_path = ((topic or {}).get("duplicate_existing") or {}).get("path")
        if duplicate_path:
            ranked_by_path = {x["path"]: x for x in rep.get("top_improvement_candidates", [])}
            duplicate_candidate = ranked_by_path.get(duplicate_path)
            if not duplicate_candidate:
                base_row = next((x for x in rows if x["path"] == duplicate_path), None)
                if base_row:
                    duplicate_candidate = dict(base_row)
                    duplicate_candidate["gsc"] = gsc.get(duplicate_path)
                    duplicate_candidate["priority_score"] = candidate_score(base_row, duplicate_candidate["gsc"])
            if duplicate_candidate:
                print("Action selected: IMPROVE RESEARCH-MATCH", duplicate_candidate["path"])
                improve(duplicate_candidate, rows, args.mode, research=topic)
                return 0

        if should_create_new_article(topic, candidate):
            print("Action selected: NEW ARTICLE", topic.get("title"), "score=", topic.get("opportunity_score"))
            create_new_article(topic, rows, args.mode)
            return 0

        if candidate:
            print("Action selected: IMPROVE", candidate["path"], "priority=", candidate.get("priority_score"))
            improve(candidate, rows, args.mode, research=topic)
            return 0

        if topic and topic.get("create") and float(topic.get("opportunity_score", 0) or 0) >= float(CONFIG.get("new_article_minimum_score", 88)):
            print("No existing candidate; creating researched new article.")
            create_new_article(topic, rows, args.mode)
            return 0

        reason = "既存記事の有効な改善候補も、公開基準を満たす新規テーマも見つからなかった"
        record = make_run_record(
            mode=args.mode,
            candidate=None,
            status="no_candidate",
            outcome="変更なし",
            outcome_reason=reason,
            published=False,
        )
        record = attach_run_context(record, research=topic, attempts=[], action_type="none")
        append_run_log(record)
        print(reason)
        return 0

    except Exception as exc:
        candidate = choose_existing_candidate(rep)
        record = make_run_record(
            mode=args.mode,
            candidate=candidate,
            status="error",
            outcome="実行エラー",
            outcome_reason=str(exc),
            published=False,
            error=str(exc),
        )
        try:
            record["research"] = locals().get("topic")
        except Exception:
            pass
        append_run_log(record)
        raise


if __name__ == "__main__":
    sys.exit(main())
