---
name: wiki-lint
description: Run the two-layer wiki health check. Layer 1 is mechanical (lint.py for the checkable rules, check_canon.py for spec-consistency); layer 2 adds the judgment rules (staleness review, L1/L2 duplicates, naming and routing-description quality, misfiled namespaces). Reports findings by severity; with --fix, proposes fixes per finding and applies them only after user confirmation. Use when the user asks to lint, health-check, or clean up the wiki.
---

# wiki-lint

Two-layer health check for the wiki. The mechanical layer runs first
(scripts, deterministic, report-only); the judgment layer runs on top
(agent reasoning); fixes are always applied agent-side.

Spec: openspec/specs/lint.md REQ-100..253 (15 rules; finding ids = REQ ids)

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool, wiki_path, pages_dir, memory_path, namespaces).
- [architecture](../wiki-core/references/architecture.md): L1/L2 boundary,
  hub-index routing, LRU-Demote invariants (never rename or move a demoted
  page file), namespace scope rule (never lint `para/` or `notes/`;
  `glossary/` gets structure-only rule 15, never the wiki-only rules).
- [formats](../wiki-core/references/formats.md): tool-specific formats,
  routing-line format, Access-Log exemptions.
- [trust](../wiki-core/references/trust.md): provenance properties,
  reliability vs confidence, canonical-url stubs.
- [judgment-rules](references/judgment-rules.md): the non-mechanizable rule
  subset and the --fix playbook for this skill.

<role>
Wiki maintainer for a personal or team knowledge base. You keep the wiki
structurally sound (mechanical layer) and editorially sound (judgment
layer), and you never modify a page without either an explicit --fix
confirmation or a report-only mandate.
</role>

<workflow>
## Phase 0 - Config

- Discover and read `llm-wiki.yml` (config reference above). Abort with the
  standard message if it is missing.

## Phase 1 - Mechanical layer (scripts, report-only)

- Run `python3 skills/wiki-core/scripts/lint.py --json` (add `--strict` if
  the user asks for full severity on unmigrated pages; add `--check-urls`
  if the user wants real HTTP verification of canonical-url targets,
  otherwise the link-rot check runs degraded on URL shape only).
- Run `python3 skills/wiki-core/scripts/check_canon.py` (spec-consistency:
  lint-rule count, property enums, reliability-aggregation rule, and
  schema-spec-version must agree across specs, references, and both
  template Schema pages). The canon surfaces live in the llm-wiki CHECKOUT,
  not in the installed skill bundle: run it from the llm-wiki repo root, or
  pass `--repo <path-to-checkout>` when working from a vault. Exit 2 means
  the CANON drifted; report it separately from page findings, since fixing
  it means editing templates or references, not wiki pages. Exit 3 means
  the script could not find a checkout (or surfaces are missing on disk):
  that is a setup condition, not drift; relay its message instead of
  reporting mismatches. When no checkout exists on the machine, skip this
  step and say so.
- Grandfather mode is the default: findings on pages without the current
  `schema-spec-version::` are floored at info/warning (credential leaks
  excepted; they stay critical). Mention in the report when findings were
  floored, and point to the migration path (wiki-migrate) rather than
  telling the user to fix a wall of pre-v2 pages by hand.

## Phase 2 - Judgment layer (agent, on top of the script report)

Apply the non-mechanizable rules from
[judgment-rules](references/judgment-rules.md):

- Rule 2 Stale Detection (REQ-120..123): `updated::` older than 90 days AND
  `confidence:: high`; judge whether content is actually outdated before
  proposing the downgrade to `stale`.
- Rule 9 L1/L2 Duplicates (REQ-190..192): compare wiki content against the
  L1 memory files under `memory_path` (skip gracefully when unset) and flag
  substantially duplicated information.
- Proper-noun-leaf review (rule 13, REQ-231): lint.py flags leaf name
  segments only for separator violations and leaves casing and spaces to
  this layer. Review every naming-hygiene leaf finding and DISMISS
  proper-noun leaves: a capitalized or `@`-prefixed leaf naming a person,
  tool, paper, or citekey (`wiki/tools/Claude Code`,
  `notes/literature/@Forte2022`) is NOT a violation (schema REQ-580b,
  namespaces REQ-976). Conversely, flag uppercase or spaced leaves that are
  NOT proper nouns (e.g. `wiki/tech/My Notes`), which the mechanical layer
  deliberately does not catch.
- Naming quality, routing-description quality, misfiled namespaces,
  entity mentions that should be `[[links]]` (REQ-572), missing
  Cross-References sections (REQ-573).

## Phase 3 - Report

- Group all findings by severity: critical first, then warning, then info
  (REQ-200). Use the REQ id as the finding id.
- Totals: pages scanned, healthy pages, issues by rule and severity
  (REQ-201). For each finding: page, rule, severity, suggested fix
  (REQ-202).

## Phase 4 - Fixes (only with --fix, always confirmed)

- Propose a concrete fix per finding, then apply only after the user
  confirms. NEVER auto-fix critical findings silently; credential leaks are
  never auto-fixed at all (REQ-164), they must be moved to L1 memory by the
  user.
- Only rules 1, 2, 4, 5, 8, 10, 11 are fixable (REQ-112, 123, 142/143,
  152, 181, 196, 198); rules 3, 6, 7, 9, 12, and 15 require human
  judgment (a rule 15 fix is a terminology decision, glossary REQ-1000). The
  exact fix recipes are in
  [judgment-rules](references/judgment-rules.md).
- Git commit after applying fixes, and report what changed (REQ-203).

## Phase 5 - Dashboard

- Update the Dashboard page with current health metrics: last lint date,
  total pages, issues by severity, pages needing attention (REQ-210..211).
</workflow>
