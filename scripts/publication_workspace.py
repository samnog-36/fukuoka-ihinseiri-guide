"""Handle only the generated publication files in an isolated Actions checkout."""
import argparse
from pathlib import Path
import subprocess

PATHS = ['blog', 'area', 'cost', 'guide', 'images/blog', 'sitemap.xml', 'js/search-data.json', 'data/ai-activity-log.json', '_redirects']


def git(*args):
    return subprocess.check_output(['git', *args])


def untracked():
    return [Path(p.decode()) for p in git('ls-files', '--others', '--exclude-standard', '-z', '--', *PATHS).split(b'\0') if p]


def normalize():
    changed = [Path(p.decode()) for p in git('diff', '--name-only', '-z', 'HEAD', '--', *PATHS).split(b'\0') if p]
    for path in set(changed + untracked()):
        if path.is_file() and (path.suffix in {'.html', '.xml', '.json'} or path.name == '_redirects'):
            text = path.read_text(encoding='utf-8')
            clean = '\n'.join(line.rstrip() for line in text.splitlines()).rstrip() + '\n'
            if clean != text:
                path.write_text(clean, encoding='utf-8')


def discard():
    # git restore alone leaves new HTML/images behind: remove only new generated files.
    created = untracked()
    tracked = [p.decode() for p in git('ls-files', '-z', '--', *PATHS).split(b'\0') if p]
    if tracked:
        subprocess.run(['git', 'restore', '--source=HEAD', '--staged', '--worktree', '--', *tracked], check=True)
    for path in created:
        path.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['normalize', 'discard'])
    globals()[parser.parse_args().action]()
