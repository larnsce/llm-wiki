---
name: wiki-audit
description: Verify a wiki page claim by claim against its cited sources using parallel verification subagents, read-only by default. Not yet implemented (v2.1).
---

# wiki-audit

STUB. This skill will verify a page's claims against its cited sources: build the
claim-to-source map mechanically from the block-native `cite::` references,
dispatch one verification subagent per cited source in parallel, reconcile the
verdicts with the trust layer (`reliability::`, Pending Review), and report
supported, unsupported, and contradicted claims; read-only by default, writing only
with `--fix`. Scheduled for v2.1; implementation lands with issue #18.

Spec: openspec/specs/audit.md REQ-920..926
