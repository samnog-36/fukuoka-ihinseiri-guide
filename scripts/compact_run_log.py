"""Bound public dashboard data; full historical snapshots remain in Git."""
import copy
import json
from pathlib import Path


def compact_rows(rows):
    result = copy.deepcopy(rows[:240])
    for row in result:
        attempts = row.get('review_attempts') or []
        row['review_attempt_count'] = max(row.get('review_attempt_count', 0), len(attempts))
        own = [a for a in attempts if str(a.get('run_id')) == str(row.get('run_id'))]
        row['review_attempts'] = (own or attempts)[-5:]
        research = row.get('research')
        if isinstance(research, dict):
            research.pop('site_coverage', None)
        for step in row.get('steps', []):
            if isinstance(step.get('detail'), str) and len(step['detail']) > 1800:
                step['detail'] = step['detail'][:1800] + '…（詳細は審査結果を参照）'
    return result


def write_log(path, rows):
    data = json.dumps(compact_rows(rows), ensure_ascii=False, separators=(',', ':')) + '\n'
    if len(data.encode('utf-8')) >= 20 * 1024 * 1024:
        raise ValueError('Public AI log exceeds 20 MiB safety limit; preserve history in Git/checkpoints')
    path.write_text(data, encoding='utf-8')


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'data/ai-run-log.json'
    write_log(path, json.loads(path.read_text(encoding='utf-8')))
