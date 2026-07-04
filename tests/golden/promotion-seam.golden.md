# Golden transcript: wiki-ingest checkpoint for a promoted note

Pinned source: `tests/golden/source/note-tidy-data.md`, dropped into the
queue as `raw/note-tidy-data.md` so the `note-<name>` filename marks it as
a PROMOTED source (the para/notes promotion seam, specs/namespaces.md
REQ-970..973; seam defaults in
`skills/wiki-ingest/references/promotion-seam.md`). Inferred type: `notes`.

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults, all seven default namespaces, empty `ingested/`,
no `sensitive_source_types` configured), source pipeline configured, no
Semantic Scholar MCP, interactive mode. Pinned 2026-07-04 for the v2.2
promotion seam (issue #24; golden pairing from issue #26) against
wiki-ingest SKILL.md at schema-spec-version 2.0.0. The plan below is the
expected shape the next recorded run must show, paired with the SKILL.md
version that ships the seam.

A diff against this file after a prompt or model change is a re-review
signal, not automatically a failure. See `tests/golden/README.md`.

---

## Checkpoint table (Phase 2 output, verbatim plan-table format)

| # | Source | Proposed page touches | Reliability (one-line rationale) | Contradictions |
|---|--------|-----------------------|----------------------------------|----------------|
| 1 | note-tidy-data.md (notes, promoted) | 2 touches: create wiki/learning/tidy-data (knowledge, all claims cited to ingested/notes/note-tidy-data.md); update hub wiki/learning (routing line) | medium: personal synthesis (promoted from para/notes; schema REQ-586) | none |

Question asked (verbatim from REQ-025): "What should I emphasize, skip, or
route to L1 Memory?"

## Expanded plan for row 1

Pages to create:

- `wiki/learning/tidy-data` (file `wiki___learning___tidy-data.md`)
  - type:: knowledge, domain:: learning, confidence:: medium,
    created/updated:: run date
  - source-file:: ingested/notes/note-tidy-data.md
  - reliability:: medium
  - Claims to record (all single-source and not high, so each is listed
    under `## Pending Review`, ingest REQ-074), each written with its
    planned `cite::` target (born cited, ingest REQ-033b; the promotion
    seam exempts a promoted source from nothing, REQ-972; locators are the
    source's takeaways items):
    1. A table is tidy when each variable is a column, each observation is
       a row, and each type of observational unit gets its own table.
       cite:: ingested/notes/note-tidy-data.md#takeaways-1
    2. Most messy tables fail in a few recurring ways: values in column
       headers, several variables packed into one column, or two kinds of
       observational unit mixed in one table.
       cite:: ingested/notes/note-tidy-data.md#takeaways-2
    3. Reshaping to tidy form once, at the start of a project, removed
       most of the repeated cleanup work downstream.
       cite:: ingested/notes/note-tidy-data.md#takeaways-3
  - source-file:: equals the union of the ingested/ cite targets (one
    source here), per the REQ-904 invariant checked by the quality gate.

Pages to update:

- `wiki/learning` hub: add routing line to `### Index`:
  `[[wiki/learning/tidy-data]] -- tidy-data principles, messy-table failure modes, reshape-once workflow #data #workflow`

Cross-references to add:

- `[[wiki/learning]]` from the new page (satisfies the 1-outgoing-link
  minimum).

Reliability rationale (Phase 1): the source is personal synthesis promoted
from `notes/` (filename `raw/note-tidy-data.md`, namespaces REQ-970); the
rubric's personal-synthesis case (schema REQ-586) sets the default
`medium`, and nothing in the note carries external citations that would
justify higher (namespaces REQ-971; the rubric decides, medium is a
default, not a hard floor). Claim-level rating with the page-minimum
roll-up = `medium`. `## Pending Review` is required (single source, not
high).

Seam-specific expectations:

- Type inferred as `notes` per the promotion seam; `notes` is candidate
  `sensitive_source_types` material, but the recorded vault does not list
  it, so the standard tracked lifecycle applies (the pre-archive secret
  gate still scans the bytes, ingest REQ-045).
- No literature-note reminder (REQ-973): the filename carries no
  `@<citekey>` and the note has no `citekey::` or `type:: literature`
  metadata.
- Lifecycle is the standard `raw/` to `ingested/notes/` atomic
  move-plus-commit (REQ-972, schema REQ-589, ingest REQ-075).

L1 candidates: none (the three takeaways are deep reference knowledge, not
operational gotchas).

Contradictions: none (fresh vault, no existing pages on these topics).

Warnings to carry into the report: page-touch count 2 is below the 5-15
target (REQ-043, non-blocking; the vault is empty, so there are no
existing pages to cross-reference into).
