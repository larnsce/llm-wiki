# Golden transcript: wiki-chat-voice picker and closing checkpoint

Pinned sources: `tests/golden/source/voice-note-1-transcript.txt` (row 1,
PROCESSED - its queue ingest already happened per `ingest-voice.golden.md`)
and `tests/golden/source/voice-note-2-transcript.txt` (row 2, unprocessed),
both FAKE memos written for this suite, inserted into a scratch archive.db
(never a real one) with:

```
python3 - /tmp/golden-archive.db <<'PY'
import sys, sqlite3, pathlib
db = sqlite3.connect(sys.argv[1])
db.execute("""CREATE TABLE IF NOT EXISTS voice_notes (
    id INTEGER PRIMARY KEY, recorded_at TEXT, duration REAL,
    transcript TEXT, audio_path TEXT, processed INTEGER DEFAULT 0)""")
t1 = pathlib.Path("tests/golden/source/voice-note-1-transcript.txt").read_text()
t2 = pathlib.Path("tests/golden/source/voice-note-2-transcript.txt").read_text()
db.execute("INSERT INTO voice_notes VALUES (1, '2026-07-05T18:40:00+02:00', "
           "62.0, ?, '/tmp/cold/voice-note-1.m4a', 1)", (t1,))
db.execute("INSERT INTO voice_notes VALUES (2, '2026-07-06T17:05:00+02:00', "
           "88.0, ?, '/tmp/cold/voice-note-2.m4a', 0)", (t2,))
db.commit()
PY
```

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults) with wiki offer 1 of `ingest-voice.golden.md`
applied verbatim first (`wiki/tech/two-stage-retrieval` exists, its claim
cited to `archive.db:voice_notes/1`, `reliability:: low`, hub routing line
present) - row 1's `processed = 1` above reflects that prior ingest.
`archive_db: /tmp/golden-archive.db` in `llm-wiki.yml`, no voice inbox
(`inbox n/a`), no index.db (`index n/a`), interactive mode, run date
2026-07-07. Pinned 2026-07-12 for the wiki-chat-voice skill (issue #117)
against ingest REQ-1200..1207.

model: claude-fable-5 (recorded at pinning, issue #117; there is no
separate fable-baseline copy - this golden IS the Fable recording).

A diff against this file after a prompt or model change is a re-review
signal, not automatically a failure. See `tests/golden/README.md`.

The five behaviors this golden pins: the read-only picker with runtime
digests, no writes during the conversation, note-id-only provenance (the
conversation is never a cite target), the same-speaker non-corroboration
(reliability stays `low` even when memo 2 "confirms" memo 1's claim), and
the processed-flip offer appearing for the unprocessed row only.

## Scripted session (the conversation is fixed so the close is comparable)

1. User: `/wiki-chat-voice`
2. User: "1 and 2"
3. User: "What did I say about why the retrieval demo failed, and what
   fixed it?"
4. User: "The catalog analogy also suggests the Access-Log is like a
   checkout slip - keep that idea."
5. User: "wrap up"

---

## Phase 0 output: picker

| # | id | recorded | length | status | file | description | keywords |
|---|----|----------|--------|--------|------|-------------|----------|
| 1 | 2 | 2026-07-06 17:05 | 88s | UNPROCESSED | voice-note-2.m4a | Post-seminar retro: demo fixed by rebuilding the hub index first; cache metaphor fell flat, card-catalog analogy idea; Jana's chapter comments arrived | seminar, retrieval-demo, hub-index, teaching-analogy, jana |
| 2 | 1 | 2026-07-05 18:40 | 62s | processed | voice-note-1.m4a | Seminar prep: demo failure traced to stale routing descriptions; hub index must be rebuilt before stage one; Jana to review chapter | seminar, retrieval-demo, hub-index, jana |

The `file` column is the basename of the row's stored `audio_path`, derived
at display time (issue #121); the full cold-storage path never appears.

Digests are runtime-only (REQ-1200): nothing is written to any file or
database by this phase.

## Phase 1: selection

Both notes selected (ids 1, 2), ~330 words total - far under the ~15000-word
budget (REQ-1207), loaded in full.

## Phase 2: conversation (no writes)

Turn 3 is answered from the transcripts with attribution: note 1 (id 1)
diagnosed the failure - routing descriptions go stale when the hub index is
not rebuilt before stage one; note 2 (id 2) reports the fix worked at the
seminar demo. Turn 4's checkout-slip idea is acknowledged and added to the
candidate ledger as a conversation-born idea grounded in NO note: it can
only be a journal line (REQ-1204). No journal, page, or archive.db write
occurs in this phase (REQ-1202).

## Closing checkpoint (one pause, REQ-1203)

### Journal synthesis (batch-confirmable)

```
- pipeline: inbox n/a | unprocessed 1 | index n/a
- Chat over two voice notes about the retrieval seminar: the demo failure
  was stale routing descriptions, and rebuilding the hub index before stage
  one fixed it at the 2026-07-06 run ([[wiki/tech/two-stage-retrieval]]).
  Teaching idea from the retro: replace the cache metaphor with a library
  card catalog; in the chat we extended it - the Access-Log as a checkout
  slip. [[Jana Krause]]'s chapter comments arrived, unread.
  archive.db:voice_notes/1, archive.db:voice_notes/2
```

### Wiki offer 1 (per-claim opt-in, REQ-083)

- Target: append to `wiki/tech/two-stage-retrieval` (exists, currently
  cited to `archive.db:voice_notes/1`)
- Full sentence(s) to be written:
  > The rebuild-before-stage-one ordering was confirmed in practice at the
  > 2026-07-06 seminar run: with the hub index rebuilt first, the demo
  > retrieval succeeded.
- cite:: archive.db:voice_notes/2
- source-file:: gains archive.db:voice_notes/2 (union invariant, REQ-904)
- reliability:: stays low - a second memo by the SAME speaker is not
  independent corroboration (schema REQ-586; the conversation itself adds
  no evidence either, REQ-1204)

### Journal-only conclusions (REQ-1204, not offers)

- 1 item: the Access-Log-as-checkout-slip extension. Born in the
  conversation, grounded in no voice note - there is nothing to cite, so it
  stays in the journal synthesis above and is not offered as a wiki claim.

### Retained in transcript (REQ-085)

- 1 item: note 1 contains an assessment of a named person's stress and
  family situation (the same item its queue ingest retained). It was in
  context during the conversation - discussing it would have been fine
  (REQ-1206) - but it is listed by category only, never offered, and a yes
  would not promote it.

### TODO hand-over (REQ-087)

Offered for the human to place (today's journal on request, or a `para/`
page the human edits themself):

1. Read Jana's comments on the retrieval chapter before Thursday
   (2026-07-09)
2. Download the whisper model on the home connection (carried over from
   note 1, still open in note 2)

### Processed flips (REQ-1205)

| id | status | covered by the synthesis? | offer |
|----|--------|---------------------------|-------|
| 2 | UNPROCESSED | yes, substantively | mark processed? (suggested: yes) |

Row 1 is already processed and is not offered. The flip runs only after the
atomic commit succeeds; declining leaves row 2 for the normal
`wiki-ingest-voice` drain.
