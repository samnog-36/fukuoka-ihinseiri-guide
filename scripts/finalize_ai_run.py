from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data/ai-run-log.json"


def load_rows() -> list[dict]:
    if not LOG.exists():
        return []
    try:
        data = json.loads(LOG.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_rows(rows: list[dict]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(rows[:240], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_current(rows: list[dict]) -> dict | None:
    run_id = str(os.getenv("GITHUB_RUN_ID") or "")
    if run_id:
        for row in rows:
            if str(row.get("run_id") or "") == run_id:
                return row
    return rows[0] if rows else None


def set_step(row: dict, key: str, status: str, detail: str) -> None:
    steps = row.setdefault("steps", [])
    for step in steps:
        if step.get("key") == key:
            step["status"] = status
            step["detail"] = detail
            return
    steps.append({"key": key, "label": key, "status": status, "detail": detail})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["ai-error", "gate-pass", "gate-fail", "publish-ready", "published", "publish-fail"], required=True)
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    rows = load_rows()
    row = find_current(rows)
    if not row:
        print("No AI run log row found; nothing to finalize.")
        return 0

    reason = args.reason.strip()
    now = datetime.now(timezone.utc).isoformat()

    if args.stage == "ai-error":
        row["status"] = "error"
        row["outcome"] = "AI処理エラー"
        if reason:
            row["outcome_reason"] = reason
        set_step(row, "gate", "skipped", "AI処理エラーのため品質Gate未実行")
        set_step(row, "publish", "skipped", "AI処理エラーのため公開なし")

    elif args.stage == "gate-pass":
        # Only a Reviewer-approved content candidate actually advances
        # through the publish gate. Rejected/no-change runs keep their
        # original "skipped" flow instead of being rewritten as gate-passed.
        if row.get("published"):
            set_step(row, "gate", "done", "品質・AdSense・HTML Gateを通過")
            set_step(row, "publish", "pending", "mainへの自動反映待ち")

    elif args.stage == "gate-fail":
        row["status"] = "gate_failed"
        row["outcome"] = "品質Gateで公開停止"
        row["outcome_reason"] = reason or "静的品質Gateに不合格"
        row["published"] = False
        set_step(row, "gate", "error", row["outcome_reason"])
        set_step(row, "publish", "skipped", "品質Gate不合格のため公開なし")

    elif args.stage == "publish-ready":
        set_step(row, "publish", "pending", "PR作成・main自動反映処理中")

    elif args.stage == "published":
        row["status"] = "published"
        row["outcome"] = "本番公開完了"
        if reason:
            row["outcome_reason"] = reason
        row["published"] = True
        set_step(row, "publish", "done", reason or "mainへ自動反映完了")

    elif args.stage == "publish-fail":
        row["status"] = "publish_failed"
        row["outcome"] = "本番反映失敗"
        row["outcome_reason"] = reason or "GitHub PR/merge処理に失敗"
        set_step(row, "publish", "error", row["outcome_reason"])

    row["finished_at"] = now
    row["timestamp"] = now
    save_rows(rows)
    print("Finalized AI run", row.get("run_id"), args.stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
