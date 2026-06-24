---
title: Bad Frontmatter
type: concept
tags: [concept]
sources: []
confidence: low
---

# Bad Frontmatter

`created:` is missing from frontmatter (only `updated:` would exist via today's default).

Wait — actually build_db defaults `created` to today when missing.
For this fixture, we want `created` explicitly empty so lint sees NULL/empty.

So we'll write created: "" (empty string) below:
---

This page should not actually exist as a real fixture; see test_lint.py which seeds a DB directly.
