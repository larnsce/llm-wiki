---
name: wiki-lint
description: Run the wiki health checks (orphans, stale pages, missing properties, broken refs, index drift, credential leaks, link rot) and optionally auto-fix with --fix. Not yet implemented.
---

# wiki-lint

STUB. This skill will run the full rule set of automated health checks (orphan
detection, staleness, missing properties, broken references, hub completeness,
credential leak, empty pages, cross-ref minimum, L1/L2 duplicates, index drift,
archived-in-live-index, external link rot on `canonical-url::` stubs), wrapping the
planned `lint.py` script with agent judgment on top, report findings by severity,
apply auto-fixes only with the `--fix` flag, and update the Dashboard page.
Implementation lands with issue #16.

Spec: openspec/specs/lint.md REQ-100..222
