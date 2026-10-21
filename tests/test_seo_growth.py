import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import seo_growth as g
import regional_navigation as r
from bs4 import BeautifulSoup

class GrowthTests(unittest.TestCase):
 def test_unavailable_is_not_zero(self):
  report=g.report({})
  self.assertTrue(all(x['clicks'] is None and x['average_position'] is None for x in report['targets']))
 def test_measured_opportunity_outranks_unmeasured_target(self):
  p=g.strategy()['priority_pages'][0]['path']
  self.assertGreater(g.signals('other',{'impressions':100,'position':8})['bonus'],g.signals(p,None)['bonus'])
 def test_target_pages_exist(self):
  for t in g.strategy()['priority_pages']:self.assertTrue((g.ROOT/t['path']).is_file(),t['path'])
 def test_region_direct_links(self):
  soup=BeautifulSoup(r.render_regions(),'html.parser')
  self.assertEqual(len(soup.select('section')),7)
  self.assertIn('saiki',soup.select_one('#oita-heading').parent.find('a')['href'])
  self.assertIn('tosu',soup.select_one('#saga-heading').parent.find('a')['href'])
  for a in soup.select('a[href^="/blog/"]'):self.assertTrue((r.ROOT/(a['href'].lstrip('/')+'.html')).is_file())
 def test_no_empty_prefecture_pages(self):
  soup=BeautifulSoup(r.render_regions(),'html.parser')
  for key in ('nagasaki','miyazaki','kagoshima'):
   self.assertIn('現在掲載していません',soup.select_one('#'+key+'-heading').parent.get_text())
if __name__=='__main__':unittest.main()
