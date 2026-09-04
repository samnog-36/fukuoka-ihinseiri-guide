from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]

ARTICLE_UPDATES = {
    "/blog/ihinseiri/article-20260706-trouble-avoid.html": {
        "old_titles": [
            "遺品整理でよくあるトラブル7選と回避方法｜福岡の事例から学ぶ",
            "遺品整理でよくあるトラブル7選と回避方法",
        ],
        "title": "遺品整理の契約トラブルを避けるチェックリスト｜福岡で確認したい7項目",
        "description": "見積もり、追加料金、廃棄物の許可、買取、残す遺品、解約条件など、契約前に確認したい項目を公式情報をもとに整理。",
    },
    "/blog/cost/article-20260803-mitsumorisho-mikata.html": {
        "old_titles": [
            "遺品整理の見積書の見方｜見積もりを確認するポイントと契約トラブルを避けるチェックリスト【2026年版】",
            "遺品整理の見積書の見方｜悪徳業者を見抜くポイントと契約トラブルを避けるチェックリスト【2026年版】",
        ],
        "title": "遺品整理の見積書の見方｜金額より先に確認したい9項目【福岡】",
        "description": "作業範囲、追加料金、廃棄物の扱い、買取、支払時期、キャンセル条件を同じ条件で比較する方法を解説。",
    },
}


def update_html_text() -> list[str]:
    changed = []
    for path in sorted(ROOT.rglob("*.html")):
        old = path.read_text(encoding="utf-8")
        text = old
        for update in ARTICLE_UPDATES.values():
            for old_title in update["old_titles"]:
                text = text.replace(old_title, update["title"])
        if text != old:
            path.write_text(text, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def update_search_data() -> bool:
    path = ROOT / "js/search-data.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False

    def walk(value):
        nonlocal changed
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            url = value.get("url")
            if url in ARTICLE_UPDATES:
                update = ARTICLE_UPDATES[url]
                if value.get("title") != update["title"]:
                    value["title"] = update["title"]
                    changed = True
                for key in ("desc", "description"):
                    if key in value and value.get(key) != update["description"]:
                        value[key] = update["description"]
                        changed = True
            for child in value.values():
                walk(child)

    walk(data)
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def update_feed() -> bool:
    path = ROOT / "feed.xml"
    if not path.exists():
        return False
    old = path.read_text(encoding="utf-8")
    text = old
    for update in ARTICLE_UPDATES.values():
        for old_title in update["old_titles"]:
            text = text.replace(old_title, update["title"])
    if text != old:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    html_changed = update_html_text()
    search_changed = update_search_data()
    feed_changed = update_feed()
    print(f"HTML title references updated: {len(html_changed)}")
    print(f"search-data updated: {search_changed}")
    print(f"feed updated: {feed_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
