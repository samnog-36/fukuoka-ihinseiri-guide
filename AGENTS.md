# Mandatory publication rules

These rules apply to every new article, edit, manual restoration and automated run.

1. Run `python scripts/publication_contract.py` after article changes. The public article inventory is the only source for homepage latest 8, the full blog list, category lists, search, titles, dates and thumbnails. Never hand-maintain separate lists.
2. Every public article must have a real, local, topic-appropriate hero image. Site logos, title cards, missing images and placeholder fallbacks are forbidden. Reuse an appropriate reviewed asset or generate a new image. Generation failure must stop publication.
3. Hero images must contain no readable lettering, titles, labels, logos or watermarks. New/changed images require visual review; `data/hero-image-approvals.json` binds approval to exact SHA-256 bytes. Do not issue approvals without inspecting the image.
4. Every public article must have a generated, working table of contents covering its H2 sections. No empty anchors or duplicate IDs.
5. Hero figures contain only the image. Text must stay outside the figure, with normal document flow and automatic image height on desktop and mobile.
6. Before merge: run the publication contract with `--check`, the existing trust and strict content gates, and regression tests. A failure must be fixed, not waived or hidden by editing test expectations.
7. Preserve substantive article text and review results during mechanical repairs. Never replace an approved AI review with a mechanical gate score of zero.
8. After merge, verify Cloudflare success and the live homepage/list/article. GitHub merge alone is not proof of public deployment.

9. Follow config/seo_growth.json: strengthen the assigned search-intent owner before creating overlapping pages; use measured GSC opportunities and log missing data explicitly. Keep existing per-run AI budgets and cooldowns.
10. Region directories are generated from published article titles and the municipality mapping. Update scripts/regional_navigation.py for new municipalities; link directly to real published guides. Never publish empty city landing pages.
11. Do not change operator identity/about information without the user's next instruction. Never fabricate interviews, quotations, reviews, credentials or job photos.
