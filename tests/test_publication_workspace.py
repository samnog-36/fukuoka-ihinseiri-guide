from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import publication_workspace as app

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.previous = Path.cwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        subprocess.run(['git','init','-q'],check=True)
        Path('blog').mkdir();Path('guide').mkdir()
        Path('blog/old.html').write_text('original\n')
        Path('guide/index.html').write_text('guide\n')
        subprocess.run(['git','add','.'],check=True)
        subprocess.run(['git','-c','user.name=test','-c','user.email=test@example.test','commit','-qm','base'],check=True)
    def tearDown(self):
        os.chdir(self.previous);self.tmp.cleanup()
    def test_failed_draft_cannot_leak_and_other_files_survive(self):
        Path('blog/old.html').write_text('changed\n')
        Path('guide/index.html').write_text('new card\n')
        Path('blog/new.html').write_text('unapproved')
        Path('notes.txt').write_text('keep')
        app.discard()
        self.assertEqual(Path('blog/old.html').read_text(),'original\n')
        self.assertEqual(Path('guide/index.html').read_text(),'guide\n')
        self.assertFalse(Path('blog/new.html').exists())
        self.assertTrue(Path('notes.txt').exists())
    def test_formatting_is_fixed_before_quality_gate(self):
        Path('blog/old.html').write_text('updated\n   \n')
        Path('blog/new.html').write_text('<p>new</p>  \n')
        app.normalize()
        subprocess.run(['git','diff','--check'],check=True)
        self.assertEqual(Path('blog/new.html').read_text(),'<p>new</p>\n')
if __name__ == '__main__': unittest.main()
