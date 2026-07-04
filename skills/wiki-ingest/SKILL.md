---
name: wiki-ingest
description: Process a source (URL, file, text, or the raw/ queue) and distribute extracted knowledge across wiki pages with provenance, interactive by default with an --auto flag, plus an import mode for existing notes. Not yet implemented.
---

# wiki-ingest

STUB. This skill will be the write path: analyze a source (URL, file path, raw
text, or draining the `raw/` queue when the source pipeline is configured), apply
L1/L2 routing to extracted facts, plan page operations and pause at an interactive
checkpoint (skippable with `--auto`), create and update pages append-only with
routing lines, provenance (`source-file::`, `reliability::`, Pending Review), and
the pre-archive secret gate, then archive sources to `ingested/` in one atomic
commit. It also absorbs the legacy `/wiki import` workflow as an import mode.
Implementation lands with issue #14.

Spec: openspec/specs/ingest.md REQ-010..075
