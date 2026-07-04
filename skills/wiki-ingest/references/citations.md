# Block-native claim citations (cite::)

Reference for the wiki-ingest citation emission and the citation gate step
(specs/citations.md REQ-900..905, specs/ingest.md REQ-033b). Implements
issue #17, the first half of the re-authored #8.

## The convention

Every non-common-knowledge factual claim block written onto an ingested page
carries a `cite::` reference attached to the claim block itself (REQ-900).
Pages are born cited (ingest REQ-033b): the reference is written at write
time, never backfilled later. No footnote keys, no separate citations
section to keep in sync.

Logseq mode, a block property on the claim block:

```
- Solar capacity grew 24% in 2024.
  cite:: ingested/papers/iea-2024.md#p12
```

Obsidian mode, an indented child bullet directly under the claim:

```
- Solar capacity grew 24% in 2024.
  - cite:: ingested/papers/iea-2024.md#p12
```

Both shapes match one grep: `^\s*(- )?cite:: `.

## Ref format (REQ-901, REQ-905)

The value is one or more comma-separated refs. Each ref is either:

- a relative path into `ingested/` with an OPTIONAL `#<locator>` suffix, a
  free-text page, section, or table pointer (`#p12`, `#sec-3.2`), or
- a live-web ref of the form `url:<https://...>`.

Refs are plain text, NOT `[[links]]`: they point at source files, not wiki
pages, and must not create graph nodes (REQ-905). At write time the ref uses
the path the source WILL live at (`ingested/<type>/<filename>`, matching
`source-file::` per REQ-073); the gate accepts the target while the file is
still pending in `raw_dir`.

## What to cite, what is exempt (REQ-902)

Cite every non-common-knowledge factual claim. Exempt: common knowledge
(field-standard definitions, widely-taught facts) and clearly-marked
synthesis or opinion blocks. When unsure, cite: citing slightly too much is
cheap; an unsupported claim is not. Classifying a claim as exempt is a
judgment call made at audit time, not a lint failure; the checker reports
coverage gaps as warnings, never as blocking findings.

## Independence for corroboration (REQ-903)

Refs on the same claim count as INDEPENDENT (for the reliability
corroboration rule, schema REQ-586) only when they originate from different
sources: different authors, publishers, or datasets. Two exports of the same
underlying work are ONE source.

## The union invariant (REQ-904)

The page-level `source-file::` equals the union of the page's ingested/ cite
targets (paths only, locators stripped, deduplicated). This is mechanical:
when Phase 3 adds a claim citing a new source, it appends that source's path
to `source-file::` in the same edit. The invariant is enforced by the
quality gate; a mismatch blocks the write/commit.

## The gate step (check_citations.py)

Phase 4 runs, after the pages are written and before the archive move:

```
python3 skills/wiki-core/scripts/check_citations.py --config <llm-wiki.yml>
```

Handle the exit code:

- **Exit 2 (blocking):** a source-file union mismatch (REQ-904) or a cite
  target that resolves to no file (REQ-901). Do NOT archive, do NOT commit;
  fix the pages (or the plan) and re-run the gate. This blocks exactly like
  the credential and secret gates (ingest REQ-044).
- **Exit 1 (advisory):** coverage gaps (uncited claim blocks, REQ-902) or
  ref-shape warnings. Present them; exemption is a judgment call, so these
  never block. In `--auto` mode carry them into the Phase 5 report.
- **Exit 0 (clean):** proceed.

Staging note: pages written before v2.1 carry `source-file::` but no
`cite::` lines. The checker reports them as coverage gaps (advisory) and
skips the union check until a page carries at least one `cite::` line, so
the gate does not fail an existing vault retroactively.
