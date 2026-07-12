# Golden-transcript tests

The mechanical harness (`skills/wiki-core/scripts/test_pipeline.sh`) covers
the validators. It cannot cover the LLM-side behaviors of `/wiki-ingest`:
which pages the analysis plans to touch, and how it rates a source's
reliability. This directory is the lightweight regression net for those
behaviors.

## Contents

Each golden file is paired with one frozen source under `source/`. Never
edit a source; the golden output is only comparable while the input is
frozen.

- `source/miller-chen-2025-two-stage-retrieval.md`: pinned fixture source,
  a short FAKE paper written for this suite.
- `ingest-checkpoint.golden.md`: the expected structured checkpoint output
  for that source: the plan-table row (page touches, reliability rating
  with one-line rationale, contradictions) in the format from
  `skills/wiki-ingest/SKILL.md`, plus the expanded page-operation plan
  including the planned per-claim `cite::` targets (v2.1, ingest
  REQ-033b).
- `source/note-tidy-data.md`: pinned fixture source, a short FAKE promoted
  note (three claims about tidy-data principles); it enters the queue as
  `raw/note-tidy-data.md` so the filename triggers the promotion seam.
- `promotion-seam.golden.md`: the expected checkpoint row and expanded
  plan for that promoted note (v2.2, namespaces REQ-970..973): the
  wiki/learning/tidy-data page touch, the `medium` personal-synthesis
  reliability default (schema REQ-586), and the planned cite targets.
- `source/voice-note-1-transcript.txt`: pinned fixture transcript, a FAKE
  rambling voice memo written for this suite; it enters as `voice_notes`
  row id 1 of a scratch archive.db (insert snippet in the golden file).
- `ingest-voice.golden.md`: the expected `/wiki-ingest-voice` checkpoint
  for that row (v3.0 P-3, ingest REQ-080..087): journal-default summary,
  per-row wiki offers with the capture-backed `low` reliability, the
  individual confirmation for the row naming a person, the
  sensitive-content refusal, the TODO hand-over, and the dead-man status
  line (storage REQ-1140).
- `source/chen-okafor-2026-index-maintenance.md`: pinned DENSE fixture
  source, a FAKE peer-reviewed follow-up paper to the miller-chen
  fixture (issue #108). Unlike the other sources it is ingested into a
  NON-empty vault: scaffold as usual, apply the miller-chen expanded
  plan from `ingest-checkpoint.golden.md` verbatim (create
  `wiki/tech/two-stage-retrieval` with its four Pending Review claims,
  add the hub routing line, move the source to
  `ingested/papers/miller-chen-2025-two-stage-retrieval.md`, set
  `author:: Miller, A., Chen, B.`), then drop this fixture into `raw/`
  and run `/wiki-ingest`. It packs the judgment calls the model
  comparison needs to observe: a same-team replication that must NOT
  count as independent corroboration (schema REQ-586; the shared
  codebase is declared in its Limitations), a scoped contradiction of
  the 90-day staleness claim, a conditional partial contradiction of
  the 18% link-loss claim, a discussion-section conjecture that must
  not be recorded as a finding, and an author-recurrence trigger
  (Chen's second source, ingest REQ-024a).

- `triage.golden.md`: the expected `wiki-triage` classification for the
  three fixture sources dropped into one queue (ingest REQ-076, issue
  #108): must-flag / must-not-flag rows for the queue-decidable
  complexity triggers. No new source fixture; it reuses the three above.
- `source/voice-note-2-transcript.txt`: pinned fixture transcript, a FAKE
  post-seminar memo written for this suite; it enters as `voice_notes`
  row id 2 (row 1 is the existing voice fixture, marked processed).
- `chat-voice.golden.md`: the expected `/wiki-chat-voice` picker and
  closing checkpoint for a SCRIPTED mini-conversation over both voice
  fixtures (issue #117, ingest REQ-1200..1207): the read-only picker with
  runtime digests, no writes during the conversation, note-id-only
  provenance (the conversation is never a cite target), the same-speaker
  non-corroboration keeping `reliability:: low`, and the processed-flip
  offer for the unprocessed row only. The user turns are fixed in the
  golden header so the close stays comparable.

## Model baselines (`fable-baseline/`)

`fable-baseline/` holds frozen reference checkpoints recorded on
`claude-fable-5` (2026-07-08), one per fixture source above. They are
the comparison instrument for the model-tiering trial (issue #108): run
the same fixture on a candidate model, diff its checkpoint against the
Fable baseline, and score with the rubric below. Never regenerate these
baselines on a cheaper model; that would re-baseline the net to the
cheaper model's own calibration and the test could then only confirm
that the model agrees with itself. A generous-direction `reliability::`
diff means the task escalates to a stronger model, not that the
baseline updates.

## Scoring rubric (written before the first baseline run)

A divergence between a candidate model's checkpoint and the paired
baseline is a FAILURE if and only if it (a) changes a `reliability::`
value (page or claim level, either direction), (b) misses a `## Pending
Review` section or claim that the baseline requires (or resolves one
the baseline keeps open), or (c) accepts corroboration the baseline
rejects as non-independent (same team, same codebase, same speaker) or
records a conjecture as a finding. Everything else, including page
naming, table wording, claim ordering, section layout, and which
namespace hub carries the routing line, is cosmetic: note it, do not
fail it.

## When to re-run

Re-run the golden check after any change to:

- `skills/wiki-ingest/SKILL.md` or its `references/` files
- the wiki-core references it links (formats, trust, architecture, config)
- the model or model version used to run the skill

## How to regenerate and compare

1. Scaffold a scratch vault with the same conditions the golden file
   records (logseq mode, default namespaces, fixed date):

   ```
   python3 skills/wiki-core/scripts/init_wiki.py \
     --wiki-path /tmp/golden-vault --tool logseq --date <today>
   cp tests/golden/source/miller-chen-2025-two-stage-retrieval.md \
     /tmp/golden-vault/raw/
   ```

   For `promotion-seam.golden.md`, copy `tests/golden/source/note-tidy-data.md`
   instead (keep the filename: the `note-` prefix is what marks the source
   as promoted).

   For `ingest-voice.golden.md`, copy no file: create the scratch
   archive.db with the insert snippet recorded in the golden file, add
   `archive_db: /tmp/golden-archive.db` to the scratch vault's
   `llm-wiki.yml`, and run `/wiki-ingest-voice` instead of `/wiki-ingest`.

   For `chat-voice.golden.md`, same scratch-archive.db pattern (its own
   two-row insert snippet is in the golden header), plus apply
   `ingest-voice.golden.md` wiki offer 1 to the vault first, then run
   `/wiki-chat-voice` and play the scripted user turns from the golden
   header verbatim.

2. In a Claude Code session pointed at that vault, run `/wiki-ingest` in
   interactive mode and stop at the batch checkpoint (Phase 1-2 only; do
   not confirm the write).

3. Record the checkpoint table and the expanded plan for row 1 in the same
   structure as the paired golden file.

4. Diff against the golden file. Judge the diff:
   - Formatting drift, synonym-level wording changes: fine; update the
     golden file if the new wording is better.
   - Changed page touches, changed reliability rating, dropped Pending
     Review claims, invented contradictions: a real behavior change.
     Re-review the prompt or model change that caused it before accepting.

5. If the new behavior is accepted, commit the updated golden file in the
   same change that altered the prompt, so the transcript and the prompt
   version stay paired.

A diff is a re-review signal, not automatically a failure.
