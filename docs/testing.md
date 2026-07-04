# Testing the pipeline

Three layers, from fully mechanical to fully human-in-the-loop:

1. the **harness** (`test_pipeline.sh`) asserts the validators mechanically,
2. the **golden-transcript tests** (`tests/golden/`) pin the LLM-side ingest
   analysis,
3. the **manual protocol** exercises the whole literature pipeline end to
   end against a scratch vault.

## 1. The mechanical harness

```
bash skills/wiki-core/scripts/test_pipeline.sh            # quiet, summary only
bash skills/wiki-core/scripts/test_pipeline.sh --verbose  # every command + output
```

Needs only bash, python3, and git. Runs in a few seconds; exits 0 when
every assertion passes, 1 otherwise, with a pass/fail summary block.

What it does:

- scaffolds clean wikis at runtime via `init_wiki.py` for BOTH tool modes
  (logseq and obsidian); clean fixtures are generated, not checked in, so
  they cannot rot against the templates,
- overlays the checked-in defect deltas from `tests/fixtures/defects/<tool>/`
  one at a time (orphan page, broken ref, missing required property, bad
  date format, archived-in-live-index, empty page, credential leak,
  grandfathered page),
- runs every validator: `find_config.py`, `check_config.py`, `lint.py`
  (default, `--strict`, and the grandfather floor), `check_citations.py`
  (cited-clean green; uncited-claim and source-file/cite-mismatch red, from
  `tests/fixtures/citations/<tool>/`), `check_canon.py`
  (including a red case against a mutated temp copy of the canon surfaces),
  and `secret_scan.py`,
- asserts GREEN on the clean fixtures and RED on every planted defect:
  both the exit code and, for lint, that the expected REQ id appears in
  the `--json` findings,
- covers the raw-source secret cases from `tests/fixtures/sources/`: a fake
  AWS key in clipped HTML (blocking), an email + national-ID notes file
  (advisory), and a PDF-shaped binary with an embedded fake token that is
  generated at runtime (no binary is committed). All planted values are
  obviously fake (`AKIAIOSFODNN7EXAMPLE` and friends),
- exercises the `--gitignore-check` helper for the sensitive-source flow.

Fixture layout:

```
tests/fixtures/
  defects/logseq/<defect>/pages/...   overlay files, copied onto a fresh wiki
  defects/obsidian/<defect>/wiki/...  same defects in obsidian layout
  migration/<tool>/...                Title Case pre-migration vaults for the
                                      lowercase rename pass (deliberately old
                                      Wiki/ casing, plus Roam task markers)
  sources/                            raw-source secret-gate cases
  configs/                            invalid llm-wiki.yml cases
```

The `grandfathered` defect and the `migration/` vaults keep the pre-migration
`Wiki/` casing on purpose (that is what they test) and run in bare vaults,
never overlaid on a lowercase scaffold: on a case-insensitive filesystem
`Wiki___Tech.md` and `wiki___tech.md` are the same file.

Adding a defect: create the overlay directory for both tools, then add a
`name:REQ-id` entry to the `LINT_DEFECTS` table in `test_pipeline.sh`.

## 2. Golden-transcript tests (the LLM regression net)

The harness cannot assert what the LLM plans or how it rates a source.
`tests/golden/` pins fixture sources and the expected structured
checkpoint output: planned page touches and the reliability rating with
its rationale, in the plan-table row format from
`skills/wiki-ingest/SKILL.md`. Two pairings: a fake paper
(`ingest-checkpoint.golden.md`) and a promoted note exercising the
para/notes promotion seam (`promotion-seam.golden.md`).

Workflow: after ANY change to the ingest prompts (SKILL.md, its
references) or to the model used to run them, re-run the ingest analysis
on the pinned source and diff the checkpoint against
the paired golden file. A diff is a re-review signal,
not automatically a failure: wording drift is fine, but changed page
touches, a changed reliability rating, or dropped Pending Review claims
mean the change needs a second look before it ships.

Regeneration steps are in `tests/golden/README.md`.

## 3. Manual LLM-in-the-loop protocol (literature pipeline)

The end-to-end path documented in `docs/literature-research.md` (read
paper, ingest, provenance move) has an LLM in the middle and a human at
the checkpoint, so it is verified by running it, not by a script. Run this
protocol after significant changes to wiki-ingest, the trust layer, or the
secret gate; record the results on the tracking issue.

1. Scaffold a scratch vault (never your real wiki):

   ```
   python3 skills/wiki-core/scripts/init_wiki.py \
     --wiki-path /tmp/protocol-vault --tool logseq --date <today>
   cd /tmp/protocol-vault && git init -b main && git add -A \
     && git commit -m "wiki: initial scaffold"
   ```

2. Place the pinned fixture paper in the queue:

   ```
   cp <repo>/tests/golden/source/miller-chen-2025-two-stage-retrieval.md \
     /tmp/protocol-vault/raw/
   ```

3. In a Claude Code session in the vault, run `/wiki-ingest` (interactive,
   no `--auto`).
4. Verify the run PAUSES at the batch checkpoint before any write, and the
   checkpoint shows the plan table (source, proposed page touches,
   reliability with one-line rationale, contradictions) plus the verbatim
   question "What should I emphasize, skip, or route to L1 Memory?".
   Compare against the golden transcript.
5. Confirm the checkpoint (optionally with guidance, e.g. "emphasize the
   routing-precision finding").
6. Verify the written pages: correct tool format, all required properties,
   `source-file::` pointing at `ingested/papers/<file>`, `reliability::`
   set, and a `## Pending Review` section when the page rests on a single
   non-high source. Verify the hub `### Index` gained a routing line.
7. Verify the atomic move-plus-commit: the source file left `raw/`, sits at
   the exact path `source-file::` records, and ONE commit contains both the
   page edits and the file move (`git show --stat HEAD`).
8. Run `/wiki-query` for the new content (e.g. "what do we know about
   two-stage retrieval?") and verify it routes via the hub index line to
   the new page.
9. Run `/wiki-lint` (or `python3 skills/wiki-core/scripts/lint.py --config
   /tmp/protocol-vault/llm-wiki.yml`) and verify the vault is clean.
10. Record what worked, what was ambiguous in the SKILL.md, and the final
    lint output as a comment on the tracking issue.
