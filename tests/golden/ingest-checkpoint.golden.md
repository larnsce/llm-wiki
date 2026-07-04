# Golden transcript: wiki-ingest checkpoint for the pinned source

Pinned source: `tests/golden/source/miller-chen-2025-two-stage-retrieval.md`
(inferred type: `papers`).

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults, all seven default namespaces, empty `ingested/`),
source pipeline configured, no Semantic Scholar MCP, interactive mode.
Recorded 2026-07-04 against wiki-ingest SKILL.md at schema-spec-version
2.0.0. Updated 2026-07-04 alongside the v2.1 block-native citations change
(issue #17): the plan now carries the planned `cite::` targets per claim
(ingest REQ-033b, born-cited pages), so the next recorded run must show
them; the cite targets below are the expected shape, paired with the
SKILL.md version that introduces them.

A diff against this file after a prompt or model change is a re-review
signal, not automatically a failure. See `tests/golden/README.md`.

---

## Checkpoint table (Phase 2 output, verbatim plan-table format)

| # | Source | Proposed page touches | Reliability (one-line rationale) | Contradictions |
|---|--------|-----------------------|----------------------------------|----------------|
| 1 | miller-chen-2025-two-stage-retrieval.md (papers) | 2 touches: create wiki/tech/two-stage-retrieval (knowledge, all claims cited to ingested/papers/miller-chen-2025-two-stage-retrieval.md); update hub wiki/tech (routing line) | medium: single unreviewed preprint on synthetic vaults, no independent corroboration | none |

Question asked (verbatim from REQ-025): "What should I emphasize, skip, or
route to L1 Memory?"

## Expanded plan for row 1

Pages to create:

- `wiki/tech/two-stage-retrieval` (file `wiki___tech___two-stage-retrieval.md`)
  - type:: knowledge, domain:: tech, confidence:: medium,
    created/updated:: run date
  - source-file:: ingested/papers/miller-chen-2025-two-stage-retrieval.md
  - reliability:: medium
  - Claims to record (all single-source, so each is listed under
    `## Pending Review`), each written with its planned `cite::` target
    (born cited, ingest REQ-033b; locators are the source's Key findings
    items):
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
    source here), per the REQ-904 invariant checked by the quality gate.

Pages to update:

- `wiki/tech` hub: add routing line to `### Index`:
  `[[wiki/tech/two-stage-retrieval]] -- index-first PKB retrieval, token cost + routing-description evidence #retrieval #pkb`

Cross-references to add:

- `[[wiki/tech]]` from the new page (satisfies the 1-outgoing-link minimum).

Reliability rationale (Phase 1): per-source rubric rates an unreviewed
preprint `medium`; every claim rests on this one source, so no claim is
corroborated to `high`; page roll-up is the minimum across claims =
`medium`. `## Pending Review` is required (single source, not high).

L1 candidates: none (all findings are deep reference knowledge, not
operational gotchas).

Contradictions: none (fresh vault, no existing pages on these topics).

Warnings to carry into the report: page-touch count 2 is below the 5-15
target (REQ-043, non-blocking; the vault is empty, so there are no
existing pages to cross-reference into).
