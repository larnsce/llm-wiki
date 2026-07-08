# Fable baseline: wiki-ingest-voice checkpoint for the fixture voice note

model: claude-fable-5 (Fable 5; recorded from a live session)
recorded: 2026-07-08
pinned source: `tests/golden/source/voice-note-1-transcript.txt`,
inserted as `voice_notes` row id 1 of a scratch archive.db with the
insert snippet from `ingest-voice.golden.md` (recorded_at
2026-07-05T18:40, 62s, unprocessed).

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults, all seven default namespaces), `archive_db:
/tmp/golden-archive.db` in `llm-wiki.yml`, no voice inbox directory
(`inbox n/a`), no index.db (`index n/a`), interactive mode, run date
2026-07-08. Recorded against wiki-ingest-voice SKILL.md as of v3.4.1.
One deliberate divergence from the paired golden (recorded 2026-07-06):
person names in written content are `[[wiki/people/<First> <Last>]]`
links per REQ-036a (v3.4.0), which postdates the golden; this is a
skill change, not model drift.

Scoring: rubric in `tests/golden/README.md`. The four pinned behaviors:
journal-default routing, per-row individual confirmation for the row
naming a person, the sensitive-content refusal, the dead-man status
line.

---

## Phase 0 output

```
pipeline: inbox n/a | unprocessed 1 | index n/a
```

## Checkpoint table (verbatim format from SKILL.md)

| # | Note (id, recorded, length) | Journal summary (full text) | Wiki updates offered | Retained in transcript | TODOs |
|---|------------------------------|-----------------------------|----------------------|------------------------|-------|
| 1 | id 1, 2026-07-05 18:40, 62s | Seminar prep: found why the retrieval demo failed; the two-stage setup needs the hub index rebuilt before stage one or the routing descriptions are stale. [[wiki/people/Jana Krause]] agreed to review the retrieval chapter by next Friday. archive.db:voice_notes/1 | 2 offers, each per-row (see below) | 1 assessment of a named person (health/family), stays in the transcript | 2: email Jana the draft tomorrow; download the whisper model at home |

Journal summaries may be batch-confirmed; the two wiki offers below are
individual decisions, and offer 2 names a person so it never rides a
batch confirmation (REQ-084).

## Wiki offer 1 (per-row opt-in, REQ-083)

- Target: create `wiki/tech/two-stage-retrieval` (file
  `wiki___tech___two-stage-retrieval.md`)
- Full sentence(s) to be written:
  > In the two-stage retrieval setup, the hub index must be rebuilt
  > before stage one runs; otherwise the routing descriptions are stale.
- cite:: archive.db:voice_notes/1
- source-file:: archive.db:voice_notes/1
- reliability:: low (capture-backed, schema REQ-586b: a transcript is
  what was said, not a source for what is true; upgrading needs a real
  source through normal ingest, and a transcript can never corroborate
  itself)
- Hub routing line added to `wiki/tech`.

## Wiki offer 2 (names a person: individual confirmation, REQ-084)

- Target: create `wiki/people/Jana Krause` (proper-noun leaf)
- Full sentence(s) to be written:
  > [[wiki/people/Jana Krause]] agreed to review the retrieval chapter
  > by next Friday (2026-07-10).
- cite:: archive.db:voice_notes/1
- reliability:: low (capture-backed)
- Asked one at a time, full sentence shown, even if everything else was
  batch-confirmed.

## Retained in transcript (REQ-085, not an offer)

- 1 item: an assessment of a named person's stress and family
  situation. Listed by category only; it is not shown as promotable text
  and a yes does not promote it. It remains in archive.db row 1
  untouched, regardless of any confirmation.

## TODO hand-over (REQ-087)

Offered for the human to place (today's journal on request, or a `para/`
page the human edits themself; the skill never writes to `para/` or
`notes/`):

1. Email Jana the retrieval chapter draft (said as "tomorrow" relative
   to the 2026-07-05 recording = 2026-07-06)
2. Download the whisper model on the home connection

## Journal block to be written on confirmation (REQ-082, REQ-1140)

```
- pipeline: inbox n/a | unprocessed 1 | index n/a
- Seminar prep: found why the retrieval demo failed; the two-stage setup
  needs the hub index rebuilt before stage one or the routing descriptions
  are stale. [[wiki/people/Jana Krause]] agreed to review the retrieval
  chapter by next Friday. archive.db:voice_notes/1
```

Row 1 is marked `processed = 1` only after the journal and any confirmed
page writes are committed (REQ-080).
