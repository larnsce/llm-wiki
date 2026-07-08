# Golden transcript: wiki-ingest-voice checkpoint for a fixture voice note

Pinned source: `tests/golden/source/voice-note-1-transcript.txt`, a FAKE
rambling memo written for this suite. It is inserted as `voice_notes` row
id 1 into a scratch archive.db (never a real one) with:

```
python3 - /tmp/golden-archive.db <<'PY'
import sys, sqlite3, pathlib
db = sqlite3.connect(sys.argv[1])
db.execute("""CREATE TABLE IF NOT EXISTS voice_notes (
    id INTEGER PRIMARY KEY, recorded_at TEXT, duration REAL,
    transcript TEXT, audio_path TEXT, processed INTEGER DEFAULT 0)""")
t = pathlib.Path("tests/golden/source/voice-note-1-transcript.txt").read_text()
db.execute("INSERT INTO voice_notes VALUES (1, '2026-07-05T18:40:00+02:00', "
           "62.0, ?, '/tmp/cold/voice-note-1.m4a', 0)", (t,))
db.commit()
PY
```

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults, all seven default namespaces), `archive_db:
/tmp/golden-archive.db` in `llm-wiki.yml`, no voice inbox directory (`inbox
n/a`), no index.db (`index n/a`), interactive mode, run date 2026-07-06.
Pinned 2026-07-06 for the v3.0 voice skill (issue #57) against
wiki-ingest-voice SKILL.md at schema-spec-version 2.0.0.

model: not recorded at pinning (pre-#108). The model-attributed
reference recording is `tests/golden/fable-baseline/ingest-voice.fable-baseline.md`
(claude-fable-5, 2026-07-08); model comparisons diff against THAT file
under the rubric in `tests/golden/README.md`, never by re-baselining
this one on a cheaper model.

A diff against this file after a prompt or model change is a re-review
signal, not automatically a failure. See `tests/golden/README.md`.

The four behaviors this golden pins: journal-default routing, per-row
individual confirmation for a row naming a person, the sensitive-content
refusal (retained in transcript, never offered), and the dead-man status
line opening the run.

---

## Phase 0 output

```
pipeline: inbox n/a | unprocessed 1 | index n/a
```

## Checkpoint table (verbatim format from SKILL.md)

| # | Note (id, recorded, length) | Journal summary (full text) | Wiki updates offered | Retained in transcript | TODOs |
|---|------------------------------|-----------------------------|----------------------|------------------------|-------|
| 1 | id 1, 2026-07-05 18:40, 62s | Seminar prep: found why the retrieval demo failed; the two-stage setup needs the hub index rebuilt before stage one or the routing descriptions are stale. [[Jana Krause]] agreed to review the retrieval chapter by next Friday. archive.db:voice_notes/1 | 2 offers, each per-row (see below) | 1 assessment of a named person (health/family), stays in the transcript | 2: email Jana the draft tomorrow; download the whisper model at home |

Journal summaries may be batch-confirmed; the two wiki offers below are
individual decisions, and offer 2 names a person so it never rides a batch
confirmation (REQ-084).

## Wiki offer 1 (per-row opt-in, REQ-083)

- Target: create `wiki/tech/two-stage-retrieval` (file
  `wiki___tech___two-stage-retrieval.md`)
- Full sentence(s) to be written:
  > In the two-stage retrieval setup, the hub index must be rebuilt before
  > stage one runs; otherwise the routing descriptions are stale.
- cite:: archive.db:voice_notes/1
- source-file:: archive.db:voice_notes/1
- reliability:: low (capture-backed, schema REQ-586b: a transcript is what
  was said, not a source for what is true; upgrading needs a real source
  through normal ingest)
- Hub routing line added to `wiki/tech`.

## Wiki offer 2 (names a person: individual confirmation, REQ-084)

- Target: create `wiki/people/Jana Krause` (proper-noun leaf)
- Full sentence(s) to be written:
  > Jana Krause agreed to review the retrieval chapter by next Friday
  > (2026-07-10).
- cite:: archive.db:voice_notes/1
- reliability:: low (capture-backed)
- Asked one at a time, full sentence shown, even if everything else was
  batch-confirmed.

## Retained in transcript (REQ-085, not an offer)

- 1 item: an assessment of a named person's stress and family situation.
  Listed by category only; it is not shown as promotable text and a yes
  does not promote it. It remains in archive.db row 1 untouched.

## TODO hand-over (REQ-087)

Offered for the human to place (today's journal on request, or a `para/`
page the human edits themself; the skill never writes to `para/` or
`notes/`):

1. Email Jana the retrieval chapter draft (mentioned as "tomorrow" =
   2026-07-06)
2. Download the whisper model on the home connection

## Journal block to be written on confirmation (REQ-082, REQ-1140)

```
- pipeline: inbox n/a | unprocessed 1 | index n/a
- Seminar prep: found why the retrieval demo failed; the two-stage setup
  needs the hub index rebuilt before stage one or the routing descriptions
  are stale. [[Jana Krause]] agreed to review the retrieval chapter by next
  Friday. archive.db:voice_notes/1
```

Row 1 is marked `processed = 1` only after the journal and any confirmed
page writes are committed (REQ-080).
