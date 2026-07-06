---
name: wiki-ingest-voice
description: Consume unprocessed voice_notes rows from archive.db and route each transcript to a 2-4 line summary on today's journal page with [[links]] and the provenance id. Wiki page updates are offered per row at the checkpoint with the full sentence shown; people rows always need individual confirmation; assessments of people are never promoted. Interactive only, no --auto. Personal-tier skill, installed via setup.sh --with-personal.
---

# wiki-ingest-voice

Drain the voice queue: read unprocessed `voice_notes` rows from archive.db,
summarize each transcript onto today's journal page, offer any substantive
wiki page updates one row at a time, hand extracted TODOs to the human, and
mark rows processed only after the writes are committed. The voice variant of
wiki-ingest: the base ingest contract applies unchanged; the source is a
database row instead of a `raw/` file.

Spec: openspec/specs/ingest.md Voice Sources REQ-080..087 (the base contract
REQ-010..075 applies except the file lifecycle); openspec/specs/storage.md
REQ-1100..1141 (two-plane contract, `voice_notes` schema, dead-man status
line); specs/schema.md REQ-586b (capture-backed reliability); specs/audit.md
REQ-927 (capture-backed verdict).

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST. Voice adds the optional `archive_db` key (config REQ-626, default
  `~/archive/archive.db` per `docs/voice-pipeline.md`).
- [architecture](../wiki-core/references/architecture.md): L1/L2 routing rule,
  credential boundary, namespace scope rule.
- [formats](../wiki-core/references/formats.md): tool-specific formats,
  required properties, routing-line format, write discipline.
- [trust](../wiki-core/references/trust.md): `reliability::` rubric and
  roll-up; voice claims are capture-backed and default `low` (REQ-586b).
- [citations](../wiki-ingest/references/citations.md): block-native `cite::`
  and the source-file union invariant; capture refs
  (`archive.db:voice_notes/<id>`) count as cite targets exactly like
  `ingested/` paths (ingest REQ-086, citations REQ-904).

## Standing rules (never overridden, in any mode, by any confirmation)

- **Interactive only (REQ-081).** There is NO `--auto` path for voice. When
  `--auto` is passed, state that voice sources are interactive-only and run
  the checkpoint anyway.
- **The journal is the default destination (REQ-082).** A voice note becomes
  a 2-4 line summary on today's journal page. Wiki pages are the exception,
  never the default.
- **Wiki writes are per-row opt-in (REQ-083).** Show the full sentence(s) to
  be written, no truncation; write nothing to a wiki page without an explicit
  yes for that specific row.
- **People rows are confirmed individually (REQ-084).** Any row touching a
  people page or naming a person never rides a batch confirmation.
- **Assessments of people are never promoted (REQ-085).** Their health,
  family, grades, conflicts, or performance stay in the transcript
  (archive.db) only, REGARDLESS of confirmation. This is a standing content
  rule, not a pattern gate: it binds even when the user says yes.
- **The tool never writes to `para/` or `notes/` (REQ-087, namespaces
  REQ-966).** TODOs are offered for the human to place.
- **archive.db is append-only (storage REQ-1110).** The only mutation this
  workflow performs is flipping a row's `processed` flag. Never edit or
  delete captured fields. All database access uses python3's stdlib
  `sqlite3` module (REQ-1104), never an external client.
- **Kill criterion (issue #57).** If two voice-sourced wiki claims are found
  wrong within one month, stop offering wiki updates: voice drops to
  journal-only until the checkpoint is redesigned.

<role>
Wiki maintainer processing the owner's own voice memos. You start from stored
transcripts, keep the human in the loop before anything is written, route
conservatively (journal first), and treat anything said about other people as
private by default.
</role>

<workflow>
## Phase 0 - Queue and pipeline status

- Read `llm-wiki.yml` ([config](../wiki-core/references/config.md)): `tool`,
  `wiki_path`, `pages_dir`, and `archive_db` (default `~/archive/archive.db`).
- If the archive_db file does not exist, the voice queue is empty (not an
  error): report the pipeline status line and stop.
- Read the unprocessed queue, oldest first (REQ-080; python3 stdlib only,
  REQ-1104):

  ```
  python3 - "$ARCHIVE_DB" <<'PY'
  import sys, sqlite3
  db = sqlite3.connect(sys.argv[1])
  for row in db.execute(
          "SELECT id, recorded_at, duration, transcript FROM voice_notes "
          "WHERE processed = 0 ORDER BY id"):
      print("--- id=%s recorded_at=%s duration=%.0fs" % row[:3])
      print(row[3])
  PY
  ```

- Gather the dead-man status inputs (storage REQ-1140):
  - newest file age in the voice inbox (`~/voice-inbox/` per
    `docs/voice-pipeline.md`; report `inbox n/a` when the directory is
    absent),
  - the unprocessed row count from the query above,
  - the age of the last index rebuild (from index.db's staleness stamp;
    report `index n/a` until the index layer (v3.0 P-4) is installed).

  Format: `pipeline: inbox newest 2h | unprocessed 3 | index rebuilt 26h ago`

- If `--auto` was passed: state that voice sources are interactive-only
  (REQ-081) and continue in interactive mode.
- An empty queue is a normal run: write nothing, print the status line (the
  silence tripwire is the point), and stop.

## Phase 1 - Per-note analysis (from the stored transcript)

Transcription is outside this workflow (deterministic and re-runnable); start
from the stored transcript (REQ-080). Per note:

- Draft the 2-4 line journal summary: what was said, in your words, with
  `[[links]]` to existing pages where they resolve, ending with the
  provenance id `archive.db:voice_notes/<id>` (REQ-082).
- Identify substantive content that belongs on a wiki page. Run the normal
  ingest scan for those candidates: read the Schema page, glob for existing
  pages, contradiction check before any generation (base contract
  REQ-020..024). For each candidate, record the EXACT sentence(s) that would
  be written and the target page.
- Flag every candidate that touches a people page or names a person: these
  are individual-confirmation rows (REQ-084).
- Strike from the candidate list anything that assesses a person (health,
  family, grades, conflicts, performance): mark it transcript-only
  (REQ-085). It is listed at the checkpoint as retained, never as an offer.
- Extract TODOs verbatim for the checkpoint hand-over (REQ-087).
- A voice claim is capture-backed: `reliability:: low` default (schema
  REQ-586b). A transcript is what was said, not a source for what is true;
  anything important needs a real source through normal ingest later.

## Checkpoint - always run, one consolidated pause (REQ-025/081)

Present ONE checkpoint for the whole queue:

| # | Note (id, recorded, length) | Journal summary (full text) | Wiki updates offered | Retained in transcript | TODOs |
|---|-----------------------------|-----------------------------|----------------------|------------------------|-------|

- **Journal summaries** MAY be batch-confirmed ("journal ok for all")
  (REQ-082).
- **Each wiki update** is its own decision: show the full sentence(s), the
  target page, and the cite target `archive.db:voice_notes/<id>`; require an
  explicit yes per row (REQ-083). People rows are asked one at a time even
  when everything else was batch-confirmed (REQ-084).
- **Retained items** (REQ-085) are listed by count and category only (e.g.
  "1 assessment of a named person, stays in the transcript"); they are not
  offers and a yes does not promote them.
- **TODOs** are offered as a list for the human to place: today's journal
  (the skill can append them there on request, as plain journal blocks) or a
  `para/` page the human edits themself. The skill never writes to `para/`
  or `notes/` (REQ-087).
- Apply the user's guidance to the plan; never proceed on silence.

## Phase 3 - Writes

- **Journal block** on today's journal page, opening with the pipeline
  status line (storage REQ-1140), then one summary block per confirmed note
  with its `[[links]]` and provenance id. Tool-specific journal format per
  [formats](../wiki-core/references/formats.md); append-only, never touch
  existing journal content.
- **Confirmed wiki updates** go through the NORMAL ingest write path (base
  contract REQ-030..039): required properties and `schema-spec-version`
  stamp on new pages (`source:: ingest`, the schema enum has no voice
  value; the capture ref is what records the voice origin), append-only
  updates, hub routing line, exact `## Cross-References` heading,
  `updated::` refresh. Provenance per REQ-086:
  - `cite:: archive.db:voice_notes/<id>` on each claim block written,
  - the page's `source-file::` includes the `archive.db:` ref exactly when
    a block cites it (union invariant, citations REQ-904),
  - `reliability:: low` unless a real ingested source also supports the
    claim (schema REQ-586b; page roll-up as usual).
- Declined rows stay in the journal summary or the transcript (REQ-083);
  nothing else is written for them.

## Phase 4 - Quality gate

Blocking failures stop the affected write; the journal and the other notes
proceed (mirroring the per-source blocking of the base contract, REQ-044).

- Credential patterns in any text to be written (REQ-042): a match blocks
  that write.
- Secret gate over promoted text: transcripts mention other people, so scan
  what leaves the checkpoint. Write the planned journal block plus each
  confirmed wiki text to a temp file and run

  ```
  python3 skills/wiki-core/scripts/secret_scan.py <temp-file>
  ```

  Exit 2 blocks that write until redacted; exit 1 (PII advisories, e.g.
  email addresses) requires explicit confirmation at the checkpoint before
  writing. The transcript itself is NOT scanned or redacted: it stays in
  archive.db untouched (REQ-1110).
- Citation gate: after page writes, run

  ```
  python3 skills/wiki-core/scripts/check_citations.py --config <llm-wiki.yml>
  ```

  Capture refs count as cite targets (REQ-086/904). Exit 2 (union mismatch)
  blocks the commit: fix the pages and re-run. Exit 1 advisories are
  presented, never block.
- Required properties on new pages (REQ-040), at least one outgoing
  cross-reference per touched page (REQ-041), routing line present (REQ-041a
  warning).

## Phase 5 - Commit, mark processed, report

- Stage the journal edit and all page edits and commit as ONE atomic commit:
  `wiki: ingest-voice <n> notes (ids <id,...>) -> journal + <m> pages`
- Mark rows processed ONLY after the commit succeeds (REQ-080):

  ```
  python3 - "$ARCHIVE_DB" <id> [<id> ...] <<'PY'
  import sys, sqlite3
  db = sqlite3.connect(sys.argv[1])
  db.executemany("UPDATE voice_notes SET processed = 1 WHERE id = ?",
                 [(i,) for i in sys.argv[2:]])
  db.commit()
  PY
  ```

  A failed or aborted run leaves its rows unprocessed; the queue is
  resumable and the next run picks them up (REQ-080).
- Report, OPENING with the dead-man status line (recomputed after the run),
  then: journal summaries written, wiki updates confirmed vs declined (page
  names), retained-in-transcript count (categories only, never the content),
  TODOs handed over, gate findings.
- Run log entry on the Dashboard page:
  `## [YYYY-MM-DD] ingest-voice | <n> notes -> journal + <m> pages | mode interactive`
  (voice runs are always interactive, REQ-081; the entry keeps the mode
  field so the wiki-ingest success signal reads one consistent log).
</workflow>
