import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import content_os as app


class BoundedRepairTests(unittest.TestCase):
    def test_patch_is_local_and_ambiguous_patch_rejected(self):
        self.assertEqual(app.apply_article_replacements('<article>A B</article>', [{'old': 'B', 'new': 'C'}]), '<article>A C</article>')
        with self.assertRaises(ValueError):
            app.apply_article_replacements('AA', [{'old': 'A', 'new': 'B'}])

    def test_repeated_feedback_requires_no_improvement(self):
        a = {'score': 72, 'issues': ['same metadata problem']}
        self.assertTrue(app.repeated_review_issues([a, a]))
        self.assertFalse(app.repeated_review_issues([a, {**a, 'score': 85}]))

    def test_metadata_fixes_survive_rebuild(self):
        html = '<html><head><title>old</title><link rel="alternate" hreflang="ja" href="/x.html"></head><body><article><h1>title</h1><a href="/about.html">author</a></article></body></html>'
        out = app.normalize_managed_metadata(html, path='blog/cost/article-test.html', title='title', description='description')
        self.assertNotIn('hreflang', out)
        self.assertNotIn('href="/about.html"', out)
        graphs = [json.loads(m.group(2)) for m in app.JSONLD_RE.finditer(out)]
        article = next(x for g in graphs for x in g.get('@graph', []) if x['@type'] == 'Article')
        self.assertIn('publisher', article)
        self.assertEqual(article['author']['url'], article['publisher']['url'])

    def test_usage_persists_even_without_response(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'PRIVATE_DIR', Path(tmp)), patch.object(app, 'API_USAGE', []):
            response = types.SimpleNamespace(usage={'input_tokens': 100, 'output_tokens': 20}, model='test', output=[])
            app.record_api_usage('reviewer', response)
            app.record_api_usage('revision', error=TimeoutError())
            rows = [json.loads(x) for x in (Path(tmp) / 'repair/usage.jsonl').read_text().splitlines()]
            self.assertEqual(rows[0]['usage']['input_tokens'], 100)
            self.assertIsNone(rows[1]['usage'])

    def test_bound_survives_runner_restart_and_excludes_candidate(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'PRIVATE_DIR', Path(tmp)), patch.object(app, 'append_run_log'):
            state = {'candidate': {'path': 'blog/cost/article-test.html'}, 'created_at': '2026-10-10', 'action_type': 'improvement', 'attempts': [], 'repair_policy': app.REPAIR_POLICY_VERSION}
            app.block_repair(state, 'improve', 'limit')
            self.assertEqual(app.pending_repairs(), [])
            self.assertTrue(app.path_is_in_cooldown(state['candidate']['path'])[0])

    def test_summary_does_not_duplicate_article(self):
        self.assertEqual(app.editor_summary({'article_html': 'large', '_original_html': 'large', 'seo': {}}), {'seo': {}})


if __name__ == '__main__':
    unittest.main()
