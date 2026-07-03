# Spec: Block-Native Claim Citations

## Description

Claim-level provenance. Every non-common-knowledge factual claim on an ingested page
carries a `cite::` reference attached to the claim block itself, giving audit a
mechanical claim-to-source map. This is the per-claim detail behind the page-level
`source-file::` roll-up (schema REQ-585). The convention is block-native by design:
no footnote keys, no separate citations section to keep in sync.

---

## Requirements

### Convention

- REQ-900: A citation SHALL be a `cite::` property attached to the claim block.
  In Logseq mode it is a block property on the claim block:
  ```
  - Solar capacity grew 24% in 2024.
    cite:: ingested/papers/iea-2024.md#p12
  ```
  In Obsidian mode it is an indented child bullet directly under the claim:
  ```
  - Solar capacity grew 24% in 2024.
    - cite:: ingested/papers/iea-2024.md#p12
  ```
- REQ-901: The `cite::` value SHALL be one or more comma-separated refs. Each ref is
  either a relative path into `ingested/` with an OPTIONAL `#<locator>` suffix
  (free-text page, section, or table pointer, e.g. `#p12` or `#sec-3.2`), or a live-web
  ref of the form `url:<https://...>`.
- REQ-902: On ingested pages, every non-common-knowledge factual claim SHALL carry a
  `cite::`. Common knowledge (field-standard definitions, widely-taught facts) and
  clearly-marked synthesis/opinion blocks are exempt. When unsure, cite: citing
  slightly too much is cheap; an unsupported claim is not. Classification of a claim
  as exempt is a judgment call made at audit time, not a lint failure.
- REQ-903: Refs on the same claim count as INDEPENDENT (for corroboration per schema
  REQ-586) only when they originate from different sources: different authors,
  publishers, or datasets. Two exports of the same underlying work are ONE source.
- REQ-904: The page-level `source-file::` value SHALL equal the union of the page's
  `ingested/` cite targets (paths only, locators stripped, deduplicated). This
  invariant is mechanically checkable and enforced by the ingest quality gate.
- REQ-905: Cite refs are plain text, NOT `[[links]]`: they point at source files,
  not wiki pages, and must not create graph nodes.

---

## Scenarios

### Scenario 1: Cited claim, Logseq mode

```
GIVEN an ingest of ingested/papers/iea-2024.md in Logseq mode
WHEN a page block states a factual claim extracted from the source
THEN the block carries a child property line `cite:: ingested/papers/iea-2024.md#<locator>`
AND the page's source-file:: lists ingested/papers/iea-2024.md
```

### Scenario 2: Union invariant violated

```
GIVEN a page whose blocks cite ingested/papers/a.md and ingested/papers/b.md
AND the page's source-file:: lists only ingested/papers/a.md
WHEN check_citations.py runs
THEN it reports a source-file/cite mismatch for the page (missing b.md)
AND the ingest quality gate treats the mismatch as blocking
```

### Scenario 3: Corroborated claim

```
GIVEN a claim block with cite:: ingested/papers/a.md, ingested/articles/b.md
AND a.md and b.md are independent sources rated medium
WHEN reliability is assessed per schema REQ-586
THEN that claim rates high (2+ independent medium-or-better sources)
```

---

## Acceptance Criteria

- Cited claim blocks parse identically (one grep shape) in both tool modes
- check_citations.py can extract the full claim-to-source map without LLM judgment
- The source-file-equals-union invariant holds on every page the ingest touches
