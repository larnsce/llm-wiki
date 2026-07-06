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
