import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import content_os as app

class ContinuousGrowthTests(unittest.TestCase):
    def test_search_data_matches_clean_urls_and_html_files(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(app,'PRIVATE_DIR',Path(temp)):
            base=app.CONFIG['site_url']
            Path(temp,'search_console_latest.json').write_text(json.dumps({'pages':[
                {'page':base+'/blog/cost/article-test','clicks':5,'impressions':100,'position':10,'queries':[]},
                {'page':base+'/blog/cost/article-test.html','clicks':3,'impressions':50,'position':4,'queries':[]},
                {'page':base+'.invalid/blog/cost/article-test','clicks':999,'impressions':999,'position':1}]}))
            data=app.gsc_for_path(app.load_gsc(),'blog/cost/article-test.html')
            self.assertEqual(data['impressions'],150)
            self.assertEqual(data['clicks'],8)
            self.assertEqual(data['position'],8)
            self.assertAlmostEqual(data['ctr'],8/150)

    def test_each_hour_can_start_new_work_and_balances_improvement(self):
        topic={'create':True,'opportunity_score':95}
        with patch.dict(app.CONFIG,continuous_growth_enabled=True,existing_improvements_between_new_articles=2):
            with patch.object(app,'_load_list_log',return_value=[{'status':'published','action_type':'new_article'}]):
                self.assertFalse(app.should_create_new_article(topic,{'path':'existing.html'}))
                self.assertTrue(app.should_create_new_article(topic,None))
            with patch.object(app,'_load_list_log',return_value=[
                {'status':'published','action_type':'improvement'},
                {'status':'published','action_type':'improvement'},
                {'status':'published','action_type':'new_article'}]):
                self.assertTrue(app.should_create_new_article(topic,{'path':'existing.html'}))
                self.assertFalse(app.should_create_new_article({'create':True,'opportunity_score':70},None))

    def test_candidate_pool_is_not_exhausted_by_25_recent_updates(self):
        rows=[{'path':f'blog/cost/article-{n}.html','title':str(n),'quality':80} for n in range(40)]
        with patch.object(app,'build_site_coverage',return_value={}):
            report=app.make_report(rows,{})
        self.assertEqual(len(report['top_improvement_candidates']),40)

if __name__=='__main__':unittest.main()
