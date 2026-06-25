# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-06-25

Fork feature (larnsce). A literature-research workflow guide and an optional
Semantic-Scholar enrichment for the provenance pipeline added in 1.4.0. This is mostly
documentation: how to combine Connected Papers, Semantic Scholar, Elicit, and Zotero with
`/wiki` so discovery stays fast and only read papers cross into the wiki. The only tool change
is an optional `s2-metrics::` property, and it rides inside the existing `larnsce:provenance`
sentinel regions, so the fork seam does not widen.

### Added

- **`docs/literature-research.md`** - the four-tool pipeline (each tool does one stage,
  Claude Code orchestrates), the funnel rule ("discovery feeds Zotero, Zotero feeds ingest,
  only read papers cross the line"), `/wiki query` before discovery, the Semantic Scholar MCP
  setup, and the convention for ingesting an Elicit synthesis as a `knowledge` page (a usage
  habit stated at ingest time, not a new command). Linked from the README Documentation list.
- **Optional `s2-metrics::` property.** When a Semantic Scholar MCP is configured, `/wiki
  ingest` can record a source's raw bibliometric figures (citations, influential citations,
  venue, type, year) verbatim on the page for audit. Documented in both Schema templates and
  specified in `openspec/specs/schema.md` (REQ-586a) and `ingest.md` (REQ-073a).

### Notes

- `s2-metrics::` is ADVISORY. It informs the qualitative `reliability::` judgment but never
  sets it by formula. The enrichment is OPTIONAL: with no Semantic Scholar MCP present, ingest
  skips it and judges reliability from the source alone. Absence of the MCP never blocks ingest.
- Deliberately NOT adopted from the source conversation: the citation-count reliability
  thresholds (`influential >= 5 OR cites >= 100 -> high`). Citation count measures influence
  and age, not correctness or currency; hard thresholds bake in field bias and would weaken
  the axis. The qualitative rubric from 1.4.0 stays the decision; `confidence::` covers currency.
- Deliberately deferred: a `/wiki synthesize` verb for Elicit review outputs. The Elicit
  ingest is a usage convention for now; formalize the verb only if it proves repetitive.
- MCP wiring (`claude mcp add ...`) is user/session config, documented in the guide; the tool
  does not run it.

## [1.4.0] - 2026-06-25

Fork feature (larnsce). A source-provenance pipeline and a trust layer, ported as ideas
from vanillaflava/llm-wiki-skills, adapted to Logseq and this tool's `/wiki` command. The
goal is reproducibility: every synthesised claim traces back to a specific archived source,
and weakly-supported pages are visibly flagged until corroborated. Implemented as additive,
sentinel-wrapped blocks (`larnsce:provenance`) so the fork stays rebaseable against upstream;
the base `## Workflow: ingest (Default)` is left verbatim and only overlaid.

### Added

- **raw/ -> ingested/ source pipeline.** Drop a source in `raw/`, ingest synthesises it into
  wiki pages, then the source file is MOVED into `ingested/<type>/`. The move is the
  provenance record (in `raw/` = pending, in `ingested/` = processed) and rides the same
  atomic git commit as the page edits. `setup.sh` scaffolds the folders and writes
  `raw_dir`/`ingested_dir`/`source_types`/`default_source_type` to `llm-wiki.yml`.
- **Page-level provenance.** Ingested pages gain `source-file::` (plain path into
  `ingested/`, distinct from the existing `source::` which records the ingest METHOD).
- **Trust layer.** A `reliability:: high | medium | low` rating (source quality; lowest of
  multiple sources) and a `## Pending Review` section that flags the specific claims on a
  single-source, non-high page until a corroborating source is ingested.
- **`## Workflow: ingest — provenance extension`** in `wiki.md`: an overlay (Phase 0 queue
  intake, Phase 3 stamping, Phase 5 atomic archive-move) that adds to, never replaces, the
  base ingest workflow.

### Changed

- `templates/logseq/Schema.md` and `templates/obsidian/Schema.md` — new Provenance,
  Reliability Rubric, Trust Axes, Pending Review, and Source Lifecycle sections.
- `openspec/specs/schema.md` — REQ-585..589 (provenance properties, reliability,
  confidence/reliability separation, Pending Review, source lifecycle).
- `openspec/specs/ingest.md` — REQ-070..075 (source-pipeline overlay on the ingest phases).
- `setup.sh` `.gitignore` heredocs — a commented (non-active) PDF-ignore stanza, with a note
  on `git lfs track "*.pdf"` for a versioned-binaries reproducibility setup.

### Notes

- `confidence::` (currency/verification) and `reliability::` (source quality) are kept as two
  SEPARATE axes and are never cross-derived. A page can be `confidence:: high` yet
  `reliability:: low`, or the reverse.
- `raw/` and `ingested/` live beside `pages/`, so Logseq and Obsidian do not render sources
  as wiki pages. Existing pages are untouched until they are re-ingested.
- Deliberately NOT included (deferred): claim-level `[^key]` footnotes, `/wiki audit`,
  `/wiki update`. The footnote idiom fights Logseq's block model; revisit if a public-facing
  per-repo wiki needs claim-level auditability, re-authored Logseq-block-native.

## [1.3.0] - 2026-06-08

Routing transparency. The Access-Log already recorded which pages a query pulled; now it
records *why* each was picked. Loading becomes auditable — not just what loaded, but the
index description or grep term that selected it. Inspired by a reader pointing out that
knowing *when and why* context loads is half the problem.

### Added

- **Routing reason in the Access-Log** — every `query` log line now carries a
  `matched: "<reason>"` field: the matched hub `### Index` routing description / #tag on
  index routing, or the grep term on the L3 fallback (`<date> -- [[page]] -- query --
  matched: "..."`). Shows not just WHICH page loaded but WHY it was selected for the question.
- `status` cache profile now breaks down the most frequent `matched:` reasons per hot page,
  surfacing mis-routing: a page always hit via the same grep term instead of its index line
  signals a weak or missing routing description in its hub `### Index`.

### Changed

- `openspec/specs/query.md` — REQ-450 line format extended; new REQ-450b defines the
  `matched:` reason semantics (<= 60 chars, quoted, parsing-safe).

### Notes

- Backward compatible: legacy Access-Log lines without `matched:` stay valid (the field is
  additive). prune/status parse date + `[[page]]` from fixed positions (split on ` -- `), so
  the suffix never affects LRU aggregation.

## [1.2.0] - 2026-06-07

Two retrieval-scaling mechanisms, the CPU-cache analogy carried through to the index
and eviction layers. As a wiki grows past a few dozen pages, grep-over-everything gets
imprecise; these keep retrieval sharp.

### Added

- **Hub-Index-Routing** — two-stage `query`. Each hub page carries an `### Index` of
  routing lines (`[[page]] -- description #tags`); query reads the cheap index first,
  picks the 3 best pages by description, then reads only those. Full-text grep becomes
  the L3 fallback. `ingest` maintains the routing line for every page (the wiki's page table).
- **LRU-Demote** — new `/wiki prune [--months N]` command. `query` appends every full-page
  read to an append-only `Wiki/Reference/Access-Log`; `prune` evicts pages with no access
  in N months (default 6) from the live index into the hub `### Archive`, marked `archived::`.
  Eviction never deletes, renames, or moves a file — incoming `[[links]]` stay valid and the
  page is still greppable (L3). Re-promotion is automatic on re-hit.
- `openspec/specs/prune.md` — new spec (EARS requirements + BDD scenarios)
- Lint rules 10 (Index Drift) and 11 (Archived-in-Live-Index), both auto-fixable;
  `lint --fix` now backfills missing routing lines into hub indexes
- `status` now reports a hot/cold cache profile (most-queried pages, demote-ready cold pages)
- Access-Log page templates for Logseq and Obsidian; `setup.sh` scaffolds the Access-Log page

### Changed

- Hub page templates (Logseq + Obsidian) now include `### Index` and `### Archive` sections
- `docs/schema-reference.md` — Hub example updated; new "Hub-Index-Routing & LRU-Demote" section
- Specs updated: `query.md` (Phase 0 routing + Phase 1b access logging), `ingest.md`
  (routing-line maintenance), `lint.md` (11 rules), `schema.md` (hub index, `archived::`
  marker, Access-Log page)

### Notes

- Backward compatible. Existing wikis keep working; run `/wiki lint --fix` once to backfill
  routing lines into hubs that predate this release.
- `archived::` is the canonical demote marker and is valid on any page type. `status:: archived`
  is set additionally only where the type's status enum allows it (Entity).

## [1.1.1] - 2026-04-18

### Added

- README badge row — license, release, stars, top language, last commit
- `docs/faq.md` — 10 questions first-time users actually ask (paid plan, L1/L2 rationale, tool choice, credential safety, wiki growth thresholds)
- `docs/troubleshooting.md` — setup, wiki-app integration, Claude Code integration, and wiki-growth issues with symptom → cause → fix format
- README "Documentation" section linking all five docs pages

### Notes

- Documentation-only release. No code, schema, or command changes.
- Focus: adoption friction. The v1.1.0 feedback pointed at missing onboarding docs, not missing features.

## [1.1.0] - 2026-04-10

### Added

- 7 OpenSpec specifications with 162 EARS requirements and 66 BDD scenarios
  - `ingest.md` — 5-phase source processing pipeline
  - `query.md` — Search, synthesis, write-back, source attribution
  - `lint.md` — 9 health checks with auto-fix rules
  - `schema.md` — Page types, property validation, format rules
  - `config.md` — Configuration loading and error handling
  - `setup.md` — Interactive installer specification
  - `l1-l2-routing.md` — L1/L2 boundary decision logic
- GitHub issue templates (bug report, feature request)
- Pull request template with dual-tool testing checklist
- SECURITY.md with responsible disclosure process
- `.gitignore` for editor and OS files
- CHANGELOG.md

### Fixed

- `setup.sh`: Add prerequisite checks for python3 and git
- `setup.sh`: Add `set -eo pipefail` for stricter error handling
- `setup.sh`: Validate namespace names (letters, numbers, hyphens only)
- `setup.sh`: Skip existing wiki pages instead of silently overwriting
- `setup.sh`: Prompt before overwriting existing `llm-wiki.yml`

## [1.0.0] - 2026-04-07

First stable release.

### Added

- `/wiki ingest` — 5-phase source processing pipeline (URL, file, text)
- `/wiki query` — Search, synthesis, and source attribution
- `/wiki lint` — 9 automated health checks with `--fix` auto-repair
- `/wiki status` — Wiki metrics and health dashboard
- `setup.sh` — Interactive installer for Logseq and Obsidian
- L1/L2 dual-layer cache architecture (CPU cache metaphor)
- Templates for both Logseq (outliner) and Obsidian (flat markdown)
- Schema with 5 page types: Entity, Project, Knowledge, Feedback, Hub
- `config.example.yml` for reference configuration

### Security

- Credential leak detection (lint rule 6) scans for tokens, passwords, secrets
- L1/L2 security boundary: credentials stay in L1 (git-excluded), wiki is git-tracked

[1.2.0]: https://github.com/MehmetGoekce/llm-wiki/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/MehmetGoekce/llm-wiki/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/MehmetGoekce/llm-wiki/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/MehmetGoekce/llm-wiki/releases/tag/v1.0.0
