# Golden transcript: wiki-triage queue classification

model: not validated on haiku yet (pinned 2026-07-08 from the REQ-076
design, issue #108; record the first haiku run's verdict here).

Pinned queue: the three frozen fixture sources dropped together into a
scratch vault's `raw/`:

- `raw/miller-chen-2025-two-stage-retrieval.md`
  (from `tests/golden/source/`)
- `raw/note-tidy-data.md` (keep the filename; the `note-` prefix marks
  the promotion seam)
- `raw/chen-okafor-2026-index-maintenance.md`

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults, all seven default namespaces, empty `ingested/`),
the `wiki-triage` agent dispatched once for the whole queue (ingest
REQ-076) with the scaffold's hub-index routing lines (empty indexes) and
the Schema page list as context.

This golden pins the MUST-FLAG / MUST-NOT-FLAG behavior of the
queue-decidable triggers, not wording. Scoring: a run FAILS iff a
must-flag row comes back `routine`, a must-not-flag row comes back
`complex`, a type is wrong, or the agent claims wiki-state knowledge it
was not given (supersedes/conflicts judgments belong to the checkpoint).
Slug wording, priority order, and reason phrasing are cosmetic.

Early-warning calibration (issue #108 premortem): in live use, a
sustained weekly flag rate below 5% or above 40% means the triggers need
re-tuning; this fixture queue intentionally sits at 2 of 3 flagged.

---

## Expected classification table

| file | slug | type | priority | flag | reason |
|------|------|------|----------|------|--------|
| miller-chen-2025-two-stage-retrieval.md | miller-chen-2025-two-stage-retrieval.md | papers | 1 | complex (MUST FLAG) | multi-source topic: chen-okafor in the same queue covers two-stage retrieval / index routing; corroboration decisions likely |
| note-tidy-data.md | note-tidy-data.md | notes | 2 | routine (MUST NOT FLAG) | short promoted personal note, no topic overlap in queue or hub index |
| chen-okafor-2026-index-maintenance.md | chen-okafor-2026-index-maintenance.md | papers | 3 | complex (MUST FLAG) | dense paper (five findings, method, limitations) AND same topic as miller-chen in this queue |

Notes the recording pins:

- Both papers flag on the MULTI-SOURCE TOPIC trigger because they sit in
  the SAME queue; the flag is symmetric (the checkpoint, not triage,
  decides who corroborates or contradicts whom).
- `note-` prefix wins the type call (promotion seam): `notes`, never
  `papers`, even though the vault's `default_source_type` is `papers`.
- Slugs are already kebab-case, so they pass through unchanged (REQ-070a
  renames only when needed).
- No HIGH BLAST RADIUS flag: the scaffold's hub indexes are empty, so no
  topic maps to a hub or Schema page itself.
- The agent returns the table and nothing else; it reads only the queue
  files and the provided context, and writes nothing.
