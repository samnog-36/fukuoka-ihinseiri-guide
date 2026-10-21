import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import publication_contract as c


class PublicationContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for directory in ('config', 'data', 'js', 'images/blog', 'blog/area'):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        (self.root / '_redirects').write_text('')
        (self.root / 'config/content_os.json').write_text(json.dumps({'new_article_categories': {'area': '地域別'}}))
        (self.root / 'index.html').write_text('<div class="article-grid"><!-- HOME_LATEST_START --><!-- HOME_LATEST_END --></div>')
        for p in ('blog/index.html', 'blog/area/index.html'):
            (self.root / p).write_text('<div class="article-grid"></div>')
        image = self.root / 'images/blog/scene.png'; Image.new('RGB', (800, 533), 'blue').save(image)
        c.save_image_approval(image, 'test-fixture-only', self.root)
        self.path = self.root / 'blog/area/article-20261021-test.html'
        self.path.write_text('''<html><head><meta name="description" content="description">
        <meta property="og:image" content="/images/blog/scene.png">
        <script type="application/ld+json">{"@type":"Article","datePublished":"2026-10-21"}</script></head>
        <body><article><h1>Test article</h1><img src="/images/blog/scene.png">
        <div class="toc"><h2>目次</h2><ul><li><a href="#one">One</a></li></ul></nav>
        <p>Original important introduction</p><h2 id="one">One</h2><p>Keep all original facts.</p>
        <h2>Two</h2><p>Also preserve this paragraph.</p></article></body></html>''')
        c.synchronize(self.root)

    def test_malformed_legacy_toc_preserves_body_and_sync_is_repeatable(self):
        html = self.path.read_text()
        self.assertIn('Keep all original facts.', html)
        self.assertIn('Also preserve this paragraph.', html)
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        c.synchronize(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        c.validate(self.root)

    def test_gate_rejects_missing_list_entry(self):
        (self.root / 'blog/index.html').write_text('<div class="article-grid"></div>')
        with self.assertRaisesRegex(ValueError, 'set/order mismatch'): c.validate(self.root)

    def test_gate_rejects_placeholder(self):
        self.path.write_text(self.path.read_text().replace('/images/blog/scene.png', '/images/ogp-default.png'))
        with self.assertRaisesRegex(ValueError, 'placeholder'): c.validate(self.root)

    def test_gate_rejects_toc_and_overlay_failures(self):
        soup = c.BeautifulSoup(self.path.read_text(), 'html.parser')
        soup.select_one('[data-publication-toc]').decompose()
        soup.select_one('[data-publication-hero]').append('Overlay title')
        self.path.write_text(c.serialize(soup))
        with self.assertRaisesRegex(ValueError, 'text mixed'): c.validate(self.root)

    def test_changed_image_requires_new_visual_review(self):
        Image.new('RGB', (800, 533), 'red').save(self.root / 'images/blog/scene.png')
        with self.assertRaisesRegex(ValueError, 'review'): c.validate(self.root)

    def test_gate_rejects_broken_toc_anchor(self):
        self.path.write_text(self.path.read_text().replace('href="#one"', 'href="#missing"'))
        with self.assertRaisesRegex(ValueError, 'TOC'): c.validate(self.root)


if __name__ == '__main__': unittest.main()
