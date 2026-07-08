# Fable baseline: wiki-ingest checkpoint for the pinned paper source

model: claude-fable-5 (Fable 5; recorded from a live session)
recorded: 2026-07-08
pinned source: `tests/golden/source/miller-chen-2025-two-stage-retrieval.md`
(inferred type: `papers`)

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults, all seven default namespaces, empty `ingested/`,
empty `memory_path`), source pipeline configured, no Semantic Scholar
MCP, interactive mode, run date 2026-07-08. Recorded against wiki-ingest
SKILL.md as of v3.4.1 (schema-spec-version 2.0.0), which POSTDATES the
paired golden (recorded 2026-07-04): the journal seam (ingest
REQ-090..095, v3.1.0), `author::` (REQ-033c, v3.4.0), and `journal::`
(schema REQ-585c) additions below are skill changes, not model drift.

Scoring: diff a candidate model's checkpoint against this file and apply
the rubric in `tests/golden/README.md`. Reliability values, Pending
Review presence, and corroboration independence are the failure axes;
everything else is cosmetic.

---

## Checkpoint table (Phase 2 output, verbatim plan-table format)

| # | Source | Proposed page touches | Reliability (one-line rationale) | Contradictions |
|---|--------|-----------------------|----------------------------------|----------------|
| 1 | miller-chen-2025-two-stage-retrieval.md (papers) | 2 touches: create wiki/tech/two-stage-retrieval (knowledge, all claims cited to ingested/papers/miller-chen-2025-two-stage-retrieval.md); update hub wiki/tech (routing line) | medium: single unreviewed preprint on synthetic vaults, no independent corroboration | none |

Journal: journals/2026_07_08 <- 1 bullet in the Ingested block

Question asked (verbatim from REQ-025): "What should I emphasize, skip,
or route to L1 Memory?"

## Expanded plan for row 1

Pages to create:

- `wiki/tech/two-stage-retrieval` (file `wiki___tech___two-stage-retrieval.md`)
  - type:: knowledge, domain:: tech, confidence:: medium,
    created/updated:: 2026-07-08, journal:: link to journals/2026_07_08
    (REQ-093), author:: Miller, A., Chen, B. (REQ-033c)
  - source-file:: ingested/papers/miller-chen-2025-two-stage-retrieval.md
  - reliability:: medium
  - Claims to record (all single-source and not high, so each is listed
    under `## Pending Review`, REQ-588/074), each with its planned
    `cite::` target (locators are the source's Key findings items):
    1. Index-first routing cut tokens loaded per query by a mean of 71%
       (range 58-84%) versus loading the whole namespace.
       cite:: ingested/papers/miller-chen-2025-two-stage-retrieval.md#key-findings-1
    2. Routing precision depends on description distinctiveness (0.92 vs
       0.61 with generic filler descriptions).
       cite:: ingested/papers/miller-chen-2025-two-stage-retrieval.md#key-findings-2
    3. Append-only updates preserved claim-to-source links better than
       in-place rewrites (18% link loss over ten rewrite cycles).
       cite:: ingested/papers/miller-chen-2025-two-stage-retrieval.md#key-findings-3
    4. A staleness review window of about 90 days balanced currency
       against maintenance load (simulation only).
       cite:: ingested/papers/miller-chen-2025-two-stage-retrieval.md#key-findings-4
  - source-file:: equals the union of the ingested/ cite targets (one
    source here), per the REQ-904 invariant

Pages to update:

- `wiki/tech` hub: add routing line to `### Index`:
  `[[wiki/tech/two-stage-retrieval]] -- index-first PKB retrieval, token cost + routing-description evidence #retrieval #pkb`

Cross-references to add:

- `[[wiki/tech]]` from the new page (satisfies the 1-outgoing-link minimum).

Reliability rationale (Phase 1): per-source rubric rates an unreviewed
preprint `medium`; every claim rests on this one source, so no claim is
corroborated to `high`; page roll-up is the minimum across claims =
`medium`. `## Pending Review` is required (single source, not high).

Author handling: authors Miller, A. and Chen, B. recorded as plain-text
`author::`. First source by either author, below the REQ-024a
second-source threshold: no person page planned.

L1 candidates: none (all findings are deep reference knowledge, not
operational gotchas; the scratch vault also configures no memory_path).

Contradictions: none (fresh vault, no existing pages on these topics).

Warnings to carry into the report: page-touch count 2 is below the 5-15
target (REQ-043, non-blocking; the vault is empty, so there are no
existing pages to cross-reference into).
