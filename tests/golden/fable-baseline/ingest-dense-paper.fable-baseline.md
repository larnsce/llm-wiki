# Fable baseline: wiki-ingest checkpoint for the dense paper (non-empty vault)

model: claude-fable-5 (Fable 5; recorded from a live session)
recorded: 2026-07-08
pinned source: `tests/golden/source/chen-okafor-2026-index-maintenance.md`
(inferred type: `papers`). This is the FIRST recording for this fixture;
there is no older golden.

Conditions of the recorded run: logseq-mode vault scaffolded with
init_wiki.py defaults, then pre-loaded with the miller-chen ingest
applied verbatim from `ingest-checkpoint.golden.md` dated 2026-07-07:
`wiki/tech/two-stage-retrieval` exists with its four claims, all four
listed under `## Pending Review`, `reliability:: medium`,
`author:: Miller, A., Chen, B.`, hub routing line present, source at
`ingested/papers/miller-chen-2025-two-stage-retrieval.md`. Source
pipeline configured, no Semantic Scholar MCP, empty `memory_path`,
interactive mode, run date 2026-07-08, wiki-ingest SKILL.md as of
v3.4.1.

Scoring: rubric in `tests/golden/README.md`. This fixture exists to pin
four judgment calls: (1) a same-team replication is NOT independent
corroboration and resolves nothing; (2) contradictions are recorded and
scoped, not silently merged and not treated as corroboration; (3) a
discussion-section conjecture is not recorded as a claim; (4) a
peer-reviewed single source rates `high`, so a new single-source page
built on it carries NO `## Pending Review` (REQ-588 requires the
section only when reliability is not high).

---

## Checkpoint table (Phase 2 output, verbatim plan-table format)

| # | Source | Proposed page touches | Reliability (one-line rationale) | Contradictions |
|---|--------|-----------------------|----------------------------------|----------------|
| 1 | chen-okafor-2026-index-maintenance.md (papers) | 5 touches: create wiki/tech/index-maintenance (knowledge, claims cited to ingested/papers/chen-okafor-2026-index-maintenance.md); create wiki/people/B. Chen (author recurrence, REQ-024a); update wiki/tech/two-stage-retrieval (same-team replication note + two scoped refinements, append-only); update hubs wiki/tech and wiki/people (routing lines) | high: peer-reviewed venue (AKS '26); simulation-only, and findings 1 and 5 share the Miller-Chen codebase, so nothing here independently corroborates the earlier paper | 2: (1) above ~5 ingests/week a 30-day staleness window beat the 90-day window the existing page records (scoped refinement, not a flat reversal); (2) the recorded 18% rewrite link-loss figure did not reproduce as stated (4% with stable block ids, 22% without) |

Journal: journals/2026_07_08 <- 1 bullet in the Ingested block

Question asked (verbatim from REQ-025): "What should I emphasize, skip,
or route to L1 Memory?"

## Expanded plan for row 1

Corroboration and independence (the load-bearing judgment):

- `ingested/` already holds miller-chen-2025 on the same topic, so this
  ingest is corroboration territory (Phase 2): plan UPDATES to the
  existing page, never a duplicate page.
- Finding 1 (68% token reduction) restates the existing 71% claim, BUT
  the paper shares an author (Chen, B.) and declares in Method and
  Limitations that the simulation codebase and vault generator are
  reused unchanged. Schema REQ-586 requires 2+ INDEPENDENT sources for
  a claim to rise to `high`; the same team re-running the same code is
  one line of evidence, not two (same principle as REQ-586b's
  same-speaker rule). Therefore: NO reliability upgrade on any existing
  claim, and NO Pending Review item resolves. The replication is
  recorded as an appended claim, explicitly marked same-team.
- Finding 5 does not corroborate the existing 18% link-loss claim; it
  CONTESTS its precision. A contested claim stays open in
  `## Pending Review` (annotated), and rewriting or deleting the
  original claim is /wiki-update territory, not ingest (REQ-032
  append-only).
- The Discussion conjecture (distinctiveness effects might disappear
  under embedding-based routing) is explicitly untested speculation:
  NOT recorded as a claim on any page (recording it would drag the
  page roll-up toward `low` for a non-finding). It neither corroborates
  nor contradicts the existing distinctiveness claim. Mentioned in the
  report only.

Pages to create:

- `wiki/tech/index-maintenance` (file `wiki___tech___index-maintenance.md`)
  - type:: knowledge, domain:: tech, confidence:: medium,
    created/updated:: 2026-07-08, journal:: link to journals/2026_07_08,
    author:: Chen, B., Okafor, D.
  - source-file:: ingested/papers/chen-okafor-2026-index-maintenance.md
  - reliability:: high (peer-reviewed primary source; claim-level =
    source rubric rating, page minimum = high)
  - NO `## Pending Review` section: REQ-588 requires it only for a
    single-source page whose reliability is NOT high. (A model that adds
    one here fails axis (b) of the rubric in the other direction.)
  - Claims to record, born cited:
    1. Eager routing-line regeneration (on every page write) held
       routing precision at 0.94 over 26 simulated weeks, vs 0.79 for
       nightly batch and 0.58 for write-once (simulation).
       cite:: ingested/papers/chen-okafor-2026-index-maintenance.md#key-findings-2
    2. Index entries older than the median page age of their namespace
       predicted 74% of misroutes, making entry age a usable
       maintenance trigger (simulation).
       cite:: ingested/papers/chen-okafor-2026-index-maintenance.md#key-findings-3
    3. Staleness review windows interact with ingest rate: above about
       five ingested sources per week, a 30-day window improved answer
       quality by 6 points over 90 days at 2.1x maintenance cost; at or
       below that rate the 90-day window remained the better trade-off
       (simulation).
       cite:: ingested/papers/chen-okafor-2026-index-maintenance.md#key-findings-4
- `wiki/people/B. Chen` (proper-noun leaf; author recurrence: second
  source with Chen in `author::`, REQ-024a)
  - type:: entity, entity-type:: person
  - One-line who-this-is citing both ingested files
    (cite:: ingested/papers/miller-chen-2025-two-stage-retrieval.md,
    ingested/papers/chen-okafor-2026-index-maintenance.md), links to
    [[wiki/tech/two-stage-retrieval]] and [[wiki/tech/index-maintenance]]
  - people-hub routing line

Pages to update (append-only):

- `wiki/tech/two-stage-retrieval`:
  - Append claim: a same-team follow-up (shared codebase, 400 vaults)
    reproduced the token-reduction result at a mean of 68% (range
    55-82%); NOT independent corroboration (schema REQ-586), so the
    Pending Review item stays open.
    cite:: ingested/papers/chen-okafor-2026-index-maintenance.md#key-findings-1
  - Append scoped refinement: the ~90-day window held only at low
    ingest rates; above ~5 sources/week a 30-day window scored better
    (see [[wiki/tech/index-maintenance]]).
    cite:: ingested/papers/chen-okafor-2026-index-maintenance.md#key-findings-4
  - Append contested-precision note: the 18% link-loss figure did not
    reproduce as stated; link loss split 4% vs 22% by block-identifier
    preservation, suggesting the original figure averages two regimes.
    cite:: ingested/papers/chen-okafor-2026-index-maintenance.md#key-findings-5
  - `## Pending Review`: ALL FOUR original items stay open. The
    token-reduction and link-loss items gain a one-line annotation
    (same-team replication recorded / precision contested); nothing is
    removed, nothing resolves, no claim rises to `high`.
  - source-file:: appends ingested/papers/chen-okafor-2026-index-maintenance.md
    (union invariant REQ-904); author:: appends Okafor, D. (REQ-033c);
    reliability:: stays medium (page minimum across claims: the original
    single-source medium claims are unchanged); updated:: and journal::
    refreshed to 2026-07-08.
- `wiki/tech` hub: add routing line
  `[[wiki/tech/index-maintenance]] -- routing-index upkeep: eager regeneration wins, entry-age misroute predictor, staleness x ingest rate #retrieval #maintenance`
  (existing two-stage-retrieval line still accurate; not rewritten).
- `wiki/people` hub: add routing line
  `[[wiki/people/B. Chen]] -- PKB retrieval researcher, co-author of both retrieval sources in this vault #people`

Cross-references to add:

- `[[wiki/tech/index-maintenance]]` <-> `[[wiki/tech/two-stage-retrieval]]`
  (both directions, under `## Cross-References`), both pages ->
  `[[wiki/people/B. Chen]]`, new pages -> their hubs.

Reliability rationale (Phase 1): per-source rubric rates a peer-reviewed
primary source `high`; the simulation-only scope is carried in the claim
wording, not the rating. The rating does NOT transfer sideways: the
existing page's claims keep their `medium` because the new source is not
independent of theirs where it overlaps, and contests them where it does
not.

L1 candidates: none routed (empty memory_path in the recorded vault).
The eager-regeneration finding is the closest call (it reads like an
operational rule) but it is a simulation research result, not a gotcha
from this vault's own operation: wiki.

Contradictions: the two in the table row; both recorded for the user
BEFORE any generation, neither silently merged into existing claims.

Warnings to carry into the report: none on page-touch count (5, within
the 5-15 target). Report notes: Discussion conjecture skipped as
untested speculation; literature-note reminder not applicable.
