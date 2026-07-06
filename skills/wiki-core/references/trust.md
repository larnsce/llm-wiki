# Trust layer: provenance, reliability, confidence, Pending Review

Spec: openspec/specs/schema.md REQ-584..589 (provenance and trust);
openspec/specs/ingest.md REQ-070..075 (source pipeline);
openspec/specs/citations.md REQ-900..905 (claim citations)

The trust layer applies when the source pipeline is configured (`raw_dir` /
`ingested_dir` in `llm-wiki.yml`, see [config.md](config.md)). It records where a
page came from and how strong its sources are.

## Source lifecycle

A source file lives in `raw/` while pending and is MOVED to `ingested/<type>/` once
its knowledge is written into wiki pages (REQ-589). Presence in `ingested/` means
processed; the move is the atomic provenance commit and rides the SAME git commit as
the page edits it produced. Source files are IMMUTABLE: the wiki reads and links
them by path, never edits them. `raw/` and `ingested/` live beside the pages
directory, which keeps sources out of the pages tree; keeping them out of the
tool's INDEX takes a tool setting on top (Logseq: `:hidden` in
`logseq/config.edn`, written by setup, REQ-787; Obsidian: Files and links ->
Excluded files, manual).

## source-file::

An ingested page carries `source-file::` with comma-separated relative path(s) into
`ingested/` (e.g. `ingested/papers/smith-2024.md`); plain text, NOT a `[[link]]`
(REQ-585). Hand-written pages omit it. Distinct from `source::`, which records the
METHOD (memory-migration | ingest | manual); `source-file::` records WHICH origin
file.

## cite:: (claim-level provenance)

Every non-common-knowledge factual claim block on an ingested page carries a
`cite::` reference attached to the claim block itself (specs/citations.md
REQ-900..905): a Logseq block property, or an Obsidian indented child bullet.
Refs are comma-separated `ingested/` paths with an optional `#locator`, or
`url:<https://...>`; plain text, never a `[[link]]`. The page-level
`source-file::` equals the union of the page's ingested/ cite targets (paths
only, locators stripped, deduplicated); the invariant is mechanical and
enforced by the ingest quality gate (`check_citations.py`). Refs on one claim
count as independent for corroboration only when they originate from
different sources. Common knowledge and clearly-marked synthesis are exempt;
exemption is an audit-time judgment call, not a lint failure.

## reliability::

An ingested page carries `reliability::` (`high | medium | low`), rating the QUALITY
of its sources (REQ-586). Assessed per claim, rolled up to the page:

- Per-source rubric: `high` = peer-reviewed primary / official standard; `medium` =
  single secondary / preprint / expert post (personal synthesis from promoted
  para/notes content defaults here); `low` = speculative / anecdotal / forum /
  model-only.
- Claim level: a claim supported by 2+ INDEPENDENT sources rated `medium` or better
  is `high` (corroboration); otherwise the claim takes its source's rubric rating.
- Page level: the MINIMUM across the page's claims (most conservative roll-up).

Reliability judgments are qualitative; never derive them from citation-count
thresholds. An optional `s2-metrics::` property may record raw Semantic Scholar
figures verbatim, but it is advisory only (REQ-586a).

## confidence:: is a separate axis

`confidence::` answers "is this content current and verified" (with the 90-day
staleness lifecycle, schema REQ-533); `reliability::` answers "how good were the
sources". They MUST NOT be cross-derived or converted into each other (REQ-587). A
page may be `confidence:: high` with `reliability:: low` or the reverse.

## Pending Review

When a page rests on a SINGLE source AND `reliability::` is not `high`, it carries a
`## Pending Review` section listing the SPECIFIC claims that need corroboration
(REQ-588). When a corroborating source is later ingested: re-check each flagged
claim, remove resolved ones, delete the section when all resolve, and recompute
`reliability::` per REQ-586.

Example (Logseq):

```
- type:: knowledge
- domain:: tech
- confidence:: high
- source-file:: ingested/papers/smith-2024.md
- reliability:: medium
- ## Body
  - Synthesised claim from the source.
- ## Pending Review
  - "single-source claim X" -- needs a second independent source before reliability rises to high
```

Obsidian uses the same fields in YAML frontmatter (`source-file:`, `reliability:`)
with a standard `## Pending Review` section.

## Stub pages (canonical-url)

A page whose source of truth is an external URL the user maintains may carry
`canonical-url::` instead ("stub, don't ingest"; REQ-584). Such a page carries no
`source-file::` and is exempt from the ingested-page requirements above.
