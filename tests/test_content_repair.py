import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPT))
import content_os as app
import finalize_ai_run as finalize


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.candidate = {'path': 'blog/cost/article-test.html', 'title': 'test'}
        self.topic = {'title': 'test', 'category_slug': 'cost', 'slug': 'test'}
        self.data = {'article_html': '<article>draft</article>', 'change_summary': ['draft']}
        self.patches = [
            patch.object(app, 'ROOT', self.root),
            patch.object(app, 'PRIVATE_DIR', self.root / 'private'),
            patch.dict(app.CONFIG, max_revision_attempts=1),
            patch.object(app, 'validate_new_article_output'),
            patch.object(app, 'build_new_article_page', side_effect=lambda t, d: d['article_html']),
            patch.object(app, 'append_run_log'),
            patch.object(app, 'call_new_article_writer', return_value=self.data),
            patch.object(app, 'call_revision_editor', return_value={**self.data, 'article_html': '<article>fixed</article>'}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def run_review(self):
        return app.review_with_repairs(self.candidate, [], 'improve', self.topic, 'new_article')

    def test_rejection_resumes_same_draft_and_history_next_run(self):
        reject = {'approve': False, 'score': 78, 'issues': ['source missing']}
        with patch.object(app, 'call_reviewer', side_effect=[reject, {**reject, 'score': 84}]):
            self.assertIsNone(self.run_review())
        state = app.pending_repairs()[0]
        self.assertEqual(state['review']['score'], 84)
        self.assertEqual(state['data']['article_html'], '<article>fixed</article>')
        self.assertEqual(app.append_run_log.call_args.args[0]['status'], 'repair_pending')
        with patch.object(app, 'call_reviewer', return_value={'approve': True, 'score': 91}):
            result = self.run_review()
        self.assertEqual([a['score'] for a in result[3]], [78, 84, 91])
        app.call_new_article_writer.assert_called_once()
        self.assertEqual(app.call_revision_editor.call_count, 2)
        app.mark_repair_ready(self.candidate['path'], result[1])
        self.assertEqual(len(app.pending_repairs()), 1)  # Not published yet.
        target = self.root / self.candidate['path']
        target.parent.mkdir(parents=True)
        target.write_text(result[1])
        self.assertEqual(app.pending_repairs(), [])  # Exact published bytes retire checkpoint.

    def test_api_error_preserves_original_draft_and_issues(self):
        reject = {'approve': False, 'score': 77, 'issues': ['specific issue']}
        with patch.object(app, 'call_reviewer', return_value=reject), patch.object(app, 'call_revision_editor', side_effect=TimeoutError('timeout')):
            with self.assertRaises(TimeoutError):
                self.run_review()
        state = app.pending_repairs()[0]
        self.assertEqual(state['review']['issues'], ['specific issue'])
        self.assertEqual(state['data'], self.data)

    def test_approval_flag_and_score_both_required(self):
        self.assertFalse(app.review_passed({'approve': True, 'score': 87}))
        self.assertFalse(app.review_passed({'approve': False, 'score': 95}))
        self.assertTrue(app.review_passed({'approve': True, 'score': 88}))

    def test_total_revision_limit_persists_across_runs(self):
        reject = {'approve': False, 'score': 70, 'issues': ['missing source']}
        with patch.object(app, 'call_reviewer', side_effect=[reject, {**reject, 'score': 75}]):
            self.run_review()
        with patch.object(app, 'call_reviewer', return_value={**reject, 'score': 80}):
            self.assertIsNone(self.run_review())
        self.assertEqual(app.call_revision_editor.call_count, 2)
        self.assertEqual(app.pending_repairs(), [])
        with patch.object(app, 'call_reviewer') as reviewer:
            self.assertIsNone(self.run_review())
            reviewer.assert_not_called()
        self.assertTrue(app.repair_blocked(self.candidate['path']))

    def test_revision_prompt_runs_and_escalates_model(self):
        # Executes the f-string: syntax-only checks missed its invalid format specifier.
        responses = types.SimpleNamespace(create=lambda **kw: self.capture_response(kw))
        fake = types.SimpleNamespace(OpenAI=lambda **kw: types.SimpleNamespace(responses=responses))
        with patch.dict(sys.modules, openai=fake), patch.dict(os.environ, OPENAI_API_KEY='test', OPENAI_REPAIR_MODEL='repair-model'), patch.object(app, 'inventory_for_internal_links', return_value=[]):
            self.patches[-1].stop()
            app.call_revision_editor(self.candidate, '<article>draft</article>', {}, {'issues': ['fix']}, [], 2)
            self.patches[-1].start()
        self.assertEqual(self.api_input['model'], 'repair-model')
        self.assertIn('"issue_number": 1', self.api_input['input'])

    def capture_response(self, kw):
        self.api_input = kw
        return types.SimpleNamespace(output_text=json.dumps(self.data))

    def test_hourly_idle_does_not_rewrite_previous_run(self):
        with patch.dict(os.environ, GITHUB_RUN_ID='new-run'):
            self.assertIsNone(finalize.find_current([{'run_id': 'old-run'}]))

    def test_new_article_url_is_stable_on_a_later_day(self):
        self.assertEqual(app.new_article_path({**self.topic, '_article_path': self.candidate['path']}), self.candidate['path'])


if __name__ == '__main__':
    unittest.main()
