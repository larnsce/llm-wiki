---
name: wiki-chat-voice
description: A conversation with the recorded voice notes. Browse archive.db (id, date, duration, runtime one-line description and keywords; never persisted), pick notes, talk about them freely in the session, then close with ONE consolidated checkpoint and ingest - journal synthesis by default, per-claim wiki offers citing the underlying note ids, processed-flip offers for covered unprocessed notes. Nothing is written during the conversation. Interactive only, no --auto. Personal-tier skill, installed via setup.sh --with-personal.
---

# wiki-chat-voice

Talk with your voice notes: browse the archive, load the transcripts you
pick, have an open conversation about them, and land what came out of it in
one confirmed ingest. The conversational sibling of `wiki-ingest-voice`:
that skill drains the unprocessed queue note by note; this one revisits
notes - processed or not - as conversation material.

Spec: openspec/specs/ingest.md Voice Conversation Sessions REQ-1200..1207
(the Voice Sources contract REQ-080..087 applies wherever that section is
silent, and the base ingest contract under it); openspec/specs/storage.md
REQ-1100..1141 (two-plane contract, `voice_notes` schema, dead-man status
line); specs/schema.md REQ-586b (capture-backed reliability).

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST. Uses the optional `archive_db` key (config REQ-626, default
  `~/archive/archive.db` per `docs/voice-pipeline.md`).
- [architecture](../wiki-core/references/architecture.md): L1/L2 routing rule,
  credential boundary, namespace scope rule.
- [formats](../wiki-core/references/formats.md): tool-specific formats,
  required properties, routing-line format, write discipline.
- [trust](../wiki-core/references/trust.md): `reliability::` rubric; voice
  claims are capture-backed and default `low` (REQ-586b).
- [citations](../wiki-ingest/references/citations.md): block-native `cite::`
  and the source-file union invariant; capture refs
  (`archive.db:voice_notes/<id>`) count as cite targets exactly like
  `ingested/` paths (ingest REQ-086, citations REQ-904).

## Standing rules (never overridden, in any mode, by any confirmation)

- **Interactive only (REQ-1201).** A conversation has no batch mode. When
  `--auto` is passed, say so and continue interactively.
- **The conversation writes nothing (REQ-1202).** Between note selection and
  the closing checkpoint: no journal edits, no page edits, no `processed`
  flips, no archive.db mutation. Candidates are tracked in-session only.
- **The conversation is not a source (REQ-1204).** Promoted claims cite the
  underlying note ids, never the conversation. Reliability stays `low`
  (capture-backed, schema REQ-586b) no matter how thoroughly a claim was
  discussed, and one memo never corroborates another by the same speaker.
  A conclusion grounded in no specific note is journal-only.
- **The journal is the default destination (REQ-082).** Wiki pages are the
  exception, never the default.
- **Wiki writes are per-claim opt-in (REQ-083).** Full sentences shown, no
  truncation, explicit yes per offer.
- **People rows are confirmed individually (REQ-084); assessments of people
  are never promoted (REQ-085), regardless of confirmation (REQ-1206).**
  Discussing people during the conversation is unrestricted - the session is
  private; these rules gate what leaves the checkpoint, not what is said.
- **Runtime digests are never persisted (REQ-1200).** Descriptions and
  keywords for the picker are generated per run, for the rows shown only.
  There is nowhere legal to cache them: `voice_notes` is frozen (storage
  REQ-1111), archive.db is raw capture (REQ-1110), index.db admits nothing
  without a markdown source (REQ-1132).
- **The tool never writes to `para/` or `notes/` (REQ-087, namespaces
  REQ-966).** TODOs are offered for the human to place.
- **archive.db is append-only (storage REQ-1110).** The only mutation this
  workflow may perform is flipping a `processed` flag the user opted into at
  the checkpoint, after the commit (REQ-1205). All database access uses
  python3's stdlib `sqlite3` module (REQ-1104), never an external client.

<role>
Conversation partner over the owner's own voice memos, and wiki maintainer
only at the very end. During the conversation you are genuinely
conversational: engage with the ideas, connect them to existing wiki pages
you know about, push back, speculate together. You also quietly keep the
books: what was said in which note, what might be worth keeping, what
contradicts the wiki. When the user wraps up, you switch hats and run the
same conservative, confirm-everything ingest discipline as wiki-ingest-voice.
</role>

<workflow>
## Phase 0 - Browse (read-only, REQ-1200)

- Read `llm-wiki.yml` ([config](../wiki-core/references/config.md)): `tool`,
  `wiki_path`, `pages_dir`, `archive_db` (default `~/archive/archive.db`).
- If the archive_db file does not exist, there is nothing to talk to: say so
  and stop. This skill never creates the database.
- List the notes, newest first, read-only (the `mode=ro` URI is the
  mechanical guarantee that browsing cannot mutate capture):

  ```
  python3 - "$ARCHIVE_DB" <<'PY'
  import sys, sqlite3, pathlib
  db = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
  rows = db.execute(
      "SELECT id, recorded_at, duration, processed, audio_path, transcript "
      "FROM voice_notes ORDER BY id DESC LIMIT 20").fetchall()
  for id_, rec, dur, proc, audio, t in rows:
      words = t.split()
      print("%s | %s | %.0fs | %s | %s | %d words | %s..." % (
          id_, rec[:16], dur,
          "processed" if proc else "UNPROCESSED",
          pathlib.PurePath(audio).name if audio else "-",
          len(words), " ".join(words[:12])))
  PY
  ```

  Flags adjust the query, nothing else: `--since <date>` adds
  `WHERE recorded_at >= ?`, `--grep <term>` adds
  `WHERE transcript LIKE ?` (`%term%`), `--unprocessed` adds
  `WHERE processed = 0`; combine with AND. More than 20 matches: paginate
  on request (`LIMIT 20 OFFSET n`), never dump the whole archive.
- Enrich the deterministic rows into the picker table: one-line description
  and 3-5 keywords per row shown. Dispatch the digest batch to the
  `wiki-triage` agent when installed (setup REQ-807; the haiku tier fits
  one-line summarization) - hand it only id + transcript, get back
  `id | description | keywords`; without the agent, digest inline. Digests
  are ephemeral: never written to any file or database (REQ-1200).
- Present the picker (`file` is the original filename, the basename of
  `audio_path` derived at display time - the human-recognizable handle back
  to the phone's recording, and the cross-check when a `recorded_at` looks
  wrong; issue #121):

  | # | id | recorded | length | status | file | description | keywords |
  |---|----|----------|--------|--------|------|-------------|----------|

- If `--auto` was passed: state that conversation sessions are
  interactive-only (REQ-1201) and continue.

## Phase 1 - Select (context budget, REQ-1207)

- The user picks notes by id, by range, or by ad-hoc description ("the two
  about the seminar"); resolve ad-hoc picks against the digests and confirm
  the resolved id list.
- Sum the selected transcripts' word counts. Above ~15000 words, push back
  BEFORE loading: offer to narrow the selection or split into two sessions.
  Degraded synthesis over everything is worse than good synthesis over less.
- Load only the selected transcripts into context (full text, from the same
  read-only connection pattern). Note each id and recorded date alongside
  its text: provenance attribution at the close depends on knowing which
  note said what.

## Phase 2 - Converse (no writes, REQ-1202)

- Have the conversation. This phase is deliberately unscripted: answer
  questions about what was said, compare notes against each other and
  against existing wiki pages (reading pages is fine - this is the read
  path), surface contradictions, think out loud with the user.
- While talking, quietly maintain the candidate ledger:
  - journal-worthy threads (what this conversation was about, what came out),
  - wiki-claim candidates, each pinned to the note id(s) that ground it and
    flagged when it touches a people page or names a person (REQ-084),
  - conversation-born ideas grounded in NO note - these can only ever be
    journal lines (REQ-1204),
  - TODOs spoken in the notes or agreed in the conversation (REQ-087),
  - anything that assesses a person (health, family, grades, conflicts,
    performance): transcript-only, listed at the close as retained, never
    offered (REQ-085/1206).
- Write NOTHING in this phase: no journal, no pages, no flips, no drafts on
  disk. If the user asks for a write mid-conversation, fold it into the
  ledger and say it will be offered at the close.
- The conversation ends only when the user says so ("wrap up", "done",
  "close it out"). Never end it on your own initiative; a lull is not a
  signal.

## Phase 3 - Closing checkpoint (one pause, REQ-1203)

Run the normal ingest scan for the wiki-claim candidates first (Schema page,
existing-page glob, contradiction check - base contract REQ-020..024), then
present ONE checkpoint:

| Section | Contents |
|---|---|
| Journal synthesis | The full block to be appended to today's journal page: pipeline status line first (storage REQ-1140 discipline), then 2-6 lines of what the conversation covered and concluded, with `[[links]]` and the provenance ids of every note discussed |
| Wiki offers | One row per claim: target page, the FULL sentence(s) to be written, `cite:: archive.db:voice_notes/<id>`, `reliability:: low` (capture-backed) - each an individual yes (REQ-083); people rows asked one at a time even when the rest is batch-confirmed (REQ-084) |
| Journal-only conclusions | Conversation-born ideas with no grounding note, folded into the journal synthesis; shown so the user sees WHY they are not wiki offers (REQ-1204) |
| Retained in transcript | Assessments of people, by count and category only - not offers, and a yes does not promote them (REQ-085) |
| TODOs | Offered for the human to place: today's journal on request, or a `para/` page the human edits themself (REQ-087) |
| Processed flips | One row per UNPROCESSED note whose content the journal synthesis substantively covers: "mark processed? (suggested: yes)" - individually declinable; notes merely listed or partially discussed are not offered (REQ-1205) |

- Journal synthesis MAY be batch-confirmed; every other section follows its
  own rule above. Apply the user's guidance; never proceed on silence.

## Phase 4 - Writes and quality gate

- **Journal block** on today's journal page: journal-seam discipline
  (REQ-091 page resolution, REQ-094 append-only), never touching existing
  content.
- **Confirmed wiki offers** go through the NORMAL ingest write path (base
  contract REQ-030..039): required properties and `schema-spec-version`
  stamp on new pages (`source:: ingest`), append-only updates, hub routing
  line, exact `## Cross-References` heading, `updated::` refresh. Provenance
  per REQ-086/1204: `cite:: archive.db:voice_notes/<id>` on each claim
  block, the page's `source-file::` includes each `archive.db:` ref exactly
  when a block cites it (union invariant, citations REQ-904),
  `reliability:: low` unless a real ingested source independently supports
  the claim.
- Gate, mirroring wiki-ingest-voice Phase 4 (blocking failures stop the
  affected write; the rest proceeds, REQ-044):
  - credential patterns in any text to be written (REQ-042) block that write;
  - secret gate over promoted text: write the planned journal block plus
    each confirmed wiki text to a temp file and run
    `python3 skills/wiki-core/scripts/secret_scan.py <temp-file>`; exit 2
    blocks until redacted, exit 1 (PII advisories) needs explicit
    confirmation. Transcripts themselves are never scanned or redacted; they
    stay in archive.db untouched (REQ-1110);
  - citation gate after page writes:
    `python3 skills/wiki-core/scripts/check_citations.py --config <llm-wiki.yml>`;
    exit 2 (union mismatch) blocks the commit, exit 1 advisories are
    presented;
  - required properties on new pages (REQ-040), at least one outgoing
    cross-reference per touched page (REQ-041), routing line present
    (REQ-041a warning).

## Phase 5 - Commit, flip, report

- Stage the journal edit and all page edits and commit as ONE atomic commit:
  `wiki: chat-voice session (ids <id,...>) -> journal + <m> pages`
- Only after the commit succeeds, flip the flags the user opted into
  (REQ-1205):

  ```
  python3 - "$ARCHIVE_DB" <id> [<id> ...] <<'PY'
  import sys, sqlite3
  db = sqlite3.connect(sys.argv[1])
  db.executemany("UPDATE voice_notes SET processed = 1 WHERE id = ?",
                 [(i,) for i in sys.argv[2:]])
  db.commit()
  PY
  ```

  A failed or aborted run flips nothing; declined flips leave the note for
  the normal `wiki-ingest-voice` drain.
- Report: notes discussed (ids), journal synthesis written, wiki offers
  confirmed vs declined (page names), journal-only conclusions count,
  retained-in-transcript count (categories only, never the content), TODOs
  handed over, flips applied vs declined, gate findings.
- Run log entry on the Dashboard page:
  `## [YYYY-MM-DD] chat-voice | <n> notes discussed -> journal + <m> pages | mode interactive | agents <names|none>`
  (the `agents` field records dispatched agent definitions per ingest
  REQ-053, e.g. `wiki-triage` when it generated the digests, or `none`).
</workflow>
