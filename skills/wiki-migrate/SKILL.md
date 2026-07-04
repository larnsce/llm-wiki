---
name: wiki-migrate
description: One-time, interactive v1-to-v2 corpus migration. Drives migrate_wiki.py through dry-run, report, per-page diff preview, confirmation, --apply, and git commit, then compares wiki-lint violation counts before and after. Use when an existing wiki predates schema-spec-version 2.0.0 and lint reports grandfathered findings, or when the user asks to migrate or upgrade their corpus.
---

# wiki-migrate

Interactive guidance layer for the one-time v1-to-v2 corpus migration. The
mechanical work is delegated to the non-interactive converter; this skill
drives it conversationally and never re-implements its logic:

- `../wiki-core/scripts/migrate_wiki.py`: the converter. Dry-run by default,
  `--apply` writes, `--page <name>` restricts to one page, `--json` for
  machine-readable output. Append-only: it adds and normalizes page
  properties, never deletes or rewrites content lines, and never invents
  reliability or confidence ratings (gaps become a `needs-review::` marker).
- `../wiki-core/scripts/lint.py`: the before/after violation-count
  comparison (grandfather severity floor by default, `--strict` for full
  severity).

Spec: no dedicated spec file; the contract is GitHub issue #21 plus
openspec/specs/schema.md (the v2 page contract) and openspec/specs/lint.md
(the grandfather severity floor).

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool, wiki_path, pages_dir, namespaces).
- [formats](../wiki-core/references/formats.md): tool-specific file naming and
  property syntax, needed when previewing diffs.
- [trust](../wiki-core/references/trust.md): why ratings are never fabricated;
  confidence vs reliability are independent axes a human must set.

<role>
Migration steward for a personal or team knowledge base. You take an existing
v1-authored corpus to the v2 schema contract without ever losing content:
every write is previewed and confirmed, the converter is append-only and
idempotent, and anything non-mechanical is handed to the user as an explicit
follow-up list instead of being guessed at.
</role>

<workflow>
## Phase 0 - Config and baseline

- Discover and read `llm-wiki.yml` (config reference above). Abort with the
  standard message if it is missing.
- Record the lint baseline BEFORE touching anything:
  `python3 ../wiki-core/scripts/lint.py --json` (grandfathered counts) and
  once more with `--strict` (the true violation count the corpus would face
  at full severity). Keep both totals for the Phase 4 comparison.

## Phase 1 - Dry run and report

- Run `python3 ../wiki-core/scripts/migrate_wiki.py --json`. This writes
  nothing; exit 1 means changes are pending or manual follow-ups exist,
  exit 0 means the corpus is already migrated.
- Present the report grouped per page: mechanical changes (version stamp,
  key/date/enum normalization, `needs-review::` markers, Schema-page section
  appends) separately from manual follow-ups (prose citations, missing
  Logseq block prefixes, format mixing, unparseable dates).
- If the Schema page was reported as diverged too far from the v2 template,
  route the user to the wiki-setup skill, Phase 5 (append-only Schema
  upgrade by hand) before re-running.

## Phase 2 - Per-page preview and confirmation

- For each page the user wants to inspect (or for all pages when the corpus
  is small), show a diff preview: re-run with `--page <name>` and render the
  reported changes against the current page text. Never show a fabricated
  diff; the preview must come from the converter's own report.
- Ask for confirmation before applying. Offer three scopes: apply
  everything, apply page-by-page (`--apply --page <name>`), or stop here.
- Migration is opt-in per run; nothing is ever applied without an explicit
  confirmation.

## Phase 3 - Apply and commit

- Confirm the vault is a git repository with a clean working tree
  (`git status --porcelain`). If it is dirty, stop and ask the user to
  commit or stash; the converter refuses a dirty tree by design.
- Run `python3 ../wiki-core/scripts/migrate_wiki.py --apply` (plus `--page`
  when scoped). Report what was written.
- Verify idempotence: re-run without `--apply`; the report must show zero
  mechanical changes. If it does not, stop and investigate before
  committing.
- Git commit in the vault using the converter's suggested commit message
  (one commit for the whole migration, or one per page in page-by-page
  mode).

## Phase 4 - Verify: lint before vs after

- Re-run `python3 ../wiki-core/scripts/lint.py --json`. Migrated pages now
  carry `schema-spec-version:: 2.0.0`, so they are held to full severity;
  the grandfather floor no longer applies to them.
- Compare against the Phase 0 baseline and report three numbers side by
  side: baseline grandfathered totals, baseline `--strict` totals, and the
  post-migration totals. The mechanical wins (dates, enums, property keys)
  should be gone; what remains is the real work list.
- Walk the remaining findings and the `needs-review::` markers with the
  user and turn them into a remediation plan: which pages need ratings set
  by hand, which need citations restructured, which need block-prefix
  restructuring. Point at docs/migration.md for the checklist.

## Phase 5 - Release gate (v2.0.0)

- State the gate explicitly when the migration ran against the maintainer's
  real vault: v2.0.0 is tagged ONLY after a real-vault (non-fixture) run
  returns a manageable violation count with a documented remediation path
  for every remaining finding. A wall of unexplained violations blocks the
  tag; fixture-only green runs do not satisfy the gate.
</workflow>
