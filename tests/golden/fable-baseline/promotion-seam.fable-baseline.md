# Fable baseline: wiki-ingest checkpoint for the promoted note

model: claude-fable-5 (Fable 5; recorded from a live session)
recorded: 2026-07-08
pinned source: `tests/golden/source/note-tidy-data.md`, dropped into the
queue as `raw/note-tidy-data.md` (the `note-` prefix marks it PROMOTED;
inferred type: `notes`)

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults, all seven default namespaces, empty `ingested/`,
no `sensitive_source_types` configured, empty `memory_path`), source
pipeline configured, no Semantic Scholar MCP, interactive mode, run date
2026-07-08. Recorded against wiki-ingest SKILL.md as of v3.4.1; the
journal-seam and `journal::` additions postdate the paired golden
(2026-07-04) and are skill changes, not model drift.

Scoring: rubric in `tests/golden/README.md`.

---

## Checkpoint table (Phase 2 output, verbatim plan-table format)

| # | Source | Proposed page touches | Reliability (one-line rationale) | Contradictions |
|---|--------|-----------------------|----------------------------------|----------------|
| 1 | note-tidy-data.md (notes, promoted) | 2 touches: create wiki/learning/tidy-data (knowledge, all claims cited to ingested/notes/note-tidy-data.md); update hub wiki/learning (routing line) | medium: personal synthesis (promoted from para/notes; schema REQ-586), no external citations to justify higher | none |

Journal: journals/2026_07_08 <- 1 bullet in the Ingested block

Question asked (verbatim from REQ-025): "What should I emphasize, skip,
or route to L1 Memory?"

## Expanded plan for row 1

Pages to create:

- `wiki/learning/tidy-data` (file `wiki___learning___tidy-data.md`)
  - type:: knowledge, domain:: learning, confidence:: medium,
    created/updated:: 2026-07-08, journal:: link to journals/2026_07_08
  - source-file:: ingested/notes/note-tidy-data.md
  - reliability:: medium
  - No author:: (the note is the owner's own synthesis; no external
    author identified, REQ-011a: never guess one)
  - Claims to record (all single-source and not high, so each is listed
    under `## Pending Review`, REQ-588/074), each with its planned
    `cite::` target (locators are the source's takeaways items):
    1. A table is tidy when each variable is a column, each observation
       is a row, and each type of observational unit gets its own table.
       cite:: ingested/notes/note-tidy-data.md#takeaways-1
    2. Most messy tables fail in a few recurring ways: values in column
       headers, several variables packed into one column, or two kinds
       of observational unit mixed in one table.
       cite:: ingested/notes/note-tidy-data.md#takeaways-2
    3. Reshaping to tidy form once, at the start of a project, removed
       most of the repeated cleanup work downstream.
       cite:: ingested/notes/note-tidy-data.md#takeaways-3
  - source-file:: equals the union of the ingested/ cite targets (one
    source here), per the REQ-904 invariant

Pages to update:

- `wiki/learning` hub: add routing line to `### Index`:
  `[[wiki/learning/tidy-data]] -- tidy-data principles, messy-table failure modes, reshape-once workflow #data #workflow`

Cross-references to add:

- `[[wiki/learning]]` from the new page (satisfies the 1-outgoing-link
  minimum).

Reliability rationale (Phase 1): the source is personal synthesis
promoted from `notes/` (filename `raw/note-tidy-data.md`, namespaces
REQ-970); the rubric's personal-synthesis case (schema REQ-586) sets the
default `medium`, and the note carries no external citations that would
justify higher (namespaces REQ-971; medium is a default, not a hard
floor). Claim-level rating with the page-minimum roll-up = `medium`.
`## Pending Review` is required (single source, not high).

Seam-specific expectations:

- Type inferred as `notes` per the promotion seam; the recorded vault
  lists no `sensitive_source_types`, so the standard tracked lifecycle
  applies (the pre-archive secret gate still scans the bytes, REQ-045).
- No literature-note reminder (REQ-973): no `@<citekey>` filename, no
  `citekey::` or `type:: literature` metadata.
- Lifecycle is the standard `raw/` to `ingested/notes/` atomic
  move-plus-commit (REQ-972, schema REQ-589, ingest REQ-075).

L1 candidates: none (the three takeaways are deep reference knowledge,
not operational gotchas).

Contradictions: none (fresh vault, no existing pages on these topics).

Warnings to carry into the report: page-touch count 2 is below the 5-15
target (REQ-043, non-blocking; the vault is empty).
