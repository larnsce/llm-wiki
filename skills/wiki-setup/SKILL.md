---
name: wiki-setup
description: Initialize or upgrade an llm-wiki (Logseq or Obsidian). Discovers and validates llm-wiki.yml, scaffolds a fresh wiki via init_wiki.py, writes the global pointer file so skills work from any directory, detects a legacy v1 .claude/commands/wiki.md install and offers removal, and applies the append-only Schema-page v2 upgrade to existing vaults. Use when the user wants to set up, repair, migrate, or upgrade their wiki.
---

# wiki-setup

Interactive guidance layer for install and upgrade. The mechanical work is
delegated to the non-interactive tools; this skill drives them conversationally
and never re-implements their logic:

- `setup.sh` (repo root): installs the skill suite itself (copy or symlink into
  `.claude/skills/`). If the user needs skills installed or updated, point them
  at `./setup.sh --help` or run it for them.
- `../wiki-core/scripts/find_config.py`: config discovery.
- `../wiki-core/scripts/check_config.py`: config validation.
- `../wiki-core/scripts/init_wiki.py`: fresh scaffolding (pages, source
  pipeline, .gitignore, llm-wiki.yml).

Spec: openspec/specs/setup.md REQ-700..821

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discovery order, required and
  optional keys, validation rules, the global pointer file.
- [formats](../wiki-core/references/formats.md): tool-specific file naming and
  property syntax, needed when inspecting or upgrading an existing vault.

<role>
Setup steward for a personal or team knowledge base. You take a user from
nothing (or from a v1 install) to a working, validated wiki without ever
overwriting their content: scaffolding is skip-on-exists, upgrades are
append-only, and every destructive step (legacy file removal, config overwrite)
requires explicit confirmation.
</role>

<workflow>
## Phase 0 - Discover what exists

- Run `python3 ../wiki-core/scripts/find_config.py --json`.
- Three outcomes:
  - found: an existing wiki; continue with Phase 1 (validate/upgrade path).
  - not found: no wiki yet; continue with Phase 2 (fresh init).
  - error (`LLM_WIKI_CONFIG` set but invalid): report it and ask the user to
    fix or unset the variable before anything else; do not silently fall
    through to another discovery step.
- Note the discovery method (env, walk-up, pointer). If the config was found by
  walk-up only and no pointer file exists, plan Phase 3 so the wiki also works
  from unrelated directories.

## Phase 1 - Validate an existing config

- Run `python3 ../wiki-core/scripts/check_config.py --json`.
- Report criticals and warnings verbatim; the script emits copy-paste snippets
  (for example the source-pipeline block for configs predating REQ-623).
- Offer to apply fixes to `llm-wiki.yml`: append missing optional keys, correct
  invalid values. Ask before writing; show the exact diff.
- If the config is valid and the user asked for an upgrade, continue with
  Phase 5 (Schema-page v2 upgrade). Otherwise confirm what the user wants:
  repair, upgrade, or a second wiki (fresh init at a different path).

## Phase 2 - Fresh init

- Ask minimally: tool (logseq or obsidian), wiki path (tool-specific default),
  namespaces (default list from
  [config](../wiki-core/references/config.md)), optional memory path.
- Offer the optional human layer as one question: "Also scaffold the human
  para/ (PARA tasks/projects) and notes/ (Zettelkasten) layer? The wiki
  toolchain never writes to those namespaces; see
  docs/para-notes-workflow.md in the repository for the workflow." Intended
  for a fresh, empty graph; there is no migration for existing para/notes
  content. If accepted, add `--with-para-notes` to the init_wiki.py call: it
  scaffolds human-editable `para/schema` and `notes/schema` seed pages (plus
  the para/notes directory trees on Obsidian) and writes the
  `para_dir`/`notes_dir` keys into llm-wiki.yml (config.md REQ-625,
  namespaces.md REQ-980).
- Run `python3 ../wiki-core/scripts/init_wiki.py --wiki-path <path> --tool
  <tool> [--namespaces ...] [--memory-path ...] [--with-para-notes]`.
- Exit code semantics: 0 clean, 1 files were skipped because they already
  exist (nothing was overwritten, REQ-786; tell the user which), 2 critical
  (report and stop).
- Offer `git init` plus a best-effort initial commit in the wiki (REQ-760..765,
  REQ-810..812). Skip silently when `.git` already exists.

## Phase 3 - Global pointer file

- Offer to write `~/.config/llm-wiki/config.yml` containing only
  `wiki_path: <wiki root>` (REQ-805; discovery contract in
  [config](../wiki-core/references/config.md)).
- If a pointer file exists and points elsewhere, show both paths and ask which
  wiki should be the global default; never overwrite without confirmation.

## Phase 4 - Legacy v1 detection

- Check `~/.claude/commands/wiki.md` and, when working inside a project,
  `<project>/.claude/commands/wiki.md`.
- If found: explain that the old single-command file keeps working but is
  unsupported and is replaced by the skill suite, then offer removal
  (REQ-806). Remove only on explicit confirmation.

## Phase 5 - Schema-page v2 upgrade (append-only)

For an existing vault whose Schema page predates v2:

- Read the vault's Schema page (`wiki/schema`; file naming per
  [formats](../wiki-core/references/formats.md)) and the current template
  `templates/<tool>/Schema.md` in the repo.
- Determine the vault's schema generation from the page's
  `schema-spec-version::` property (`schema-spec-version:` in Obsidian YAML).
  A missing property, or a value below the template's, means the page
  predates v2 and needs the upgrade.
- Identify template sections missing from the vault's page by comparing the
  section headings against the template. New in v2 (the provenance block):
  Provenance Properties, Reliability Rubric, Trust Axes, Pending Review
  Convention, Source Lifecycle.
- APPEND the missing sections in template order. Never rewrite, reorder, or
  delete existing sections; user customizations to the Schema page stay
  untouched. Set `schema-spec-version::` to the template's value and update
  the `last-updated` property; touch nothing else in the property block.
- Show the additions before writing and get confirmation.
- If the vault also lacks the source-pipeline scaffold (`raw/`,
  `ingested/<type>/`), offer to re-run init_wiki.py at the same path: it is
  skip-on-exists, so it fills gaps without touching existing pages.

## Phase 6 - Verify and report

- Re-run `check_config.py --json`; the goal is zero criticals.
- From a directory outside the wiki, confirm `find_config.py` resolves the
  config (via walk-up or the pointer file).
- Summarize: wiki path, config path, pointer file, what was created, skipped,
  appended, or removed (REQ-820).
- Suggest next steps: open the wiki in the tool, run /wiki-ingest on a first
  source, run /wiki-maintain for a status report (REQ-821).
</workflow>
