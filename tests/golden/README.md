# Golden-transcript tests

The mechanical harness (`skills/wiki-core/scripts/test_pipeline.sh`) covers
the validators. It cannot cover the LLM-side behaviors of `/wiki-ingest`:
which pages the analysis plans to touch, and how it rates a source's
reliability. This directory is the lightweight regression net for those
behaviors.

## Contents

- `source/miller-chen-2025-two-stage-retrieval.md`: the pinned fixture
  source, a short FAKE paper written for this suite. Never edit it; the
  golden output is only comparable while the input is frozen.
- `ingest-checkpoint.golden.md`: the expected structured checkpoint output
  for that source: the plan-table row (page touches, reliability rating
  with one-line rationale, contradictions) in the format from
  `skills/wiki-ingest/SKILL.md`, plus the expanded page-operation plan
  including the planned per-claim `cite::` targets (v2.1, ingest
  REQ-033b).

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

2. In a Claude Code session pointed at that vault, run `/wiki-ingest` in
   interactive mode and stop at the batch checkpoint (Phase 1-2 only; do
   not confirm the write).

3. Record the checkpoint table and the expanded plan for row 1 in the same
   structure as `ingest-checkpoint.golden.md`.

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
