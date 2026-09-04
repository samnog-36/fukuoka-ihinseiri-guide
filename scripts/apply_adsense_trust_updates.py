from __future__ import annotations

"""Deprecated legacy bulk updater.

This script previously inserted the same generic trust/reference blocks across many
articles. That made pages look consistent but did not prove that each individual
claim was supported by a directly relevant primary source.

For AdSense/Search quality work, do not bulk-apply generic citations. Use the
article-specific workflow documented in docs/ARTICLE_PUBLICATION_STANDARD.md and
run the current audit scripts instead.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("This legacy bulk trust updater is deprecated and intentionally makes no changes.")
    print("Use docs/ARTICLE_PUBLICATION_STANDARD.md for article-specific source verification.")
    print("Run: python3 scripts/adsense_quality_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
