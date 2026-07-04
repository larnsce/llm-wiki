# Spec: /wiki-update - Deliberate Revision

## Description

Revise an EXISTING page to correct or supersede content. This is the only sanctioned
non-append edit path (ingest stays append-only, REQ-032). Diff-first and
source-required: a factual change needs evidence, and superseded claims stay legible
so the history of a belief can be read on the page, not just in git.

---

## Requirements

- REQ-950: `/wiki-update <page>` SHALL be the ONLY workflow permitted to modify or
  supersede existing content blocks. All other write paths remain append-only.
- REQ-951: A factual change SHALL require a source: an `ingested/` file or a URL. If
  none is given, the system SHALL ask for one and MUST NOT proceed without it.
  Non-factual edits (typos, formatting, link fixes) are exempt.
- REQ-952: The system SHALL show a before/after diff of the proposed edit and wait
  for explicit confirmation. It MUST NOT write before the user approves.
- REQ-953: When new information CONTRADICTS an existing cited claim, the system SHALL
  NOT erase the old claim silently: it marks the claim superseded (strikethrough or a
  `superseded YYYY-MM-DD` child note) and adds the new claim with its `cite::`, so the
  belief history stays legible on the page. Git already holds the literal prior text.
- REQ-954: After an approved write, the system SHALL: set or adjust `cite::` on
  changed claims, update `source-file::`, `reliability::` (per schema REQ-586), and
  `updated::`, re-check `## Pending Review` (resolving items the new source supports),
  append a log entry (`## [YYYY-MM-DD] update | <page> | <one-line reason>`), and git
  commit referencing the source.

---

## Scenarios

### Scenario 1: Sourceless factual change refused

```
GIVEN a user asks to change a cited statistic on a page
AND provides no source
WHEN /wiki-update runs
THEN the system asks for an ingested/ file or URL
AND makes no edit until one is provided
```

### Scenario 2: Supersession stays legible

```
GIVEN a page claims X citing ingested/papers/old.md
AND a newer source ingested/papers/new.md establishes not-X
WHEN the user approves the update diff
THEN the old claim remains visible, marked superseded with a date
AND the new claim appears with cite:: ingested/papers/new.md
AND reliability:: and updated:: are refreshed and the change is committed
```

---

## Acceptance Criteria

- No write ever happens before diff approval
- A factual change without a source is refused
- Superseded claims remain visible on the page
