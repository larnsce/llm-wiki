# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.3.0] - 2026-07-07

### Added

- setup.sh installs the repo's slash commands (setup REQ-804, issue
  #96): `.claude/commands/*.md` (`/lit-sync`, `/data-sync`) are copied
  into `~/.claude/commands/` (or the `--project` equivalent) with
  relative `scripts/` and `docs/` references rewritten to the
  checkout's absolute paths, so the commands work from any directory,
  not only inside the llm-wiki checkout. Always a copy, even in
  `--symlink` mode; the only sanctioned install-time patching, applied
  to the installed copy only.

## [3.2.0] - 2026-07-07

Data enters the vault: R data packages as versioned, self-describing
sources, and a plugin-free Zotero literature sync. Both follow the same
pattern: an external system of record, an idempotent sync script,
machine-managed regions beside untouchable human notes, and a version
stamp.

### Added

- Data-package seam (`openspec/specs/ingest.md` REQ-100..106, config
  REQ-660/661, schema REQ-585d, issues #92..#95): registered R data
  packages (`data_packages` config key) sync into versioned
  `ingested/data/<pkg>-<version>/` snapshots (CSVs materialized from
  `data/*.rda` and copied from `inst/extdata`, per-dataset docs
  extracted from the Rd documentation) and `wiki/data/<pkg>/<dataset>`
  pages with machine-managed description and data-dictionary sections;
  old snapshots stay citable after version updates; retention keeps the
  last `data_snapshots_keep` snapshots and never deletes a referenced
  one; `--check` compares GitHub DESCRIPTION versions for staleness
  (detection automated, writes always confirmed).
- `scripts/data_pkg_sync.R` (base R + tools, no package dependencies)
  and the `/data-sync` command (issue #93); `entity-type:: dataset`
  added to the schema enum on all canon surfaces.
- Query data reads (`openspec/specs/query.md` REQ-470..472, issue #94):
  dataset questions route via the data dictionary; row-level answers
  compute read-only on snapshot CSVs with version-pinned attribution; a
  live R session (mcptools) is explicitly not a query source (live
  plane parked by maintainer decision).
- Plugin-free Zotero literature sync (issue #90): `scripts/lit_sync.py`
  against Zotero's local HTTP API plus the `/lit-sync` command replace
  the abandoned logseq-zoterolocal-plugin; idempotent managed
  properties, incremental annotation sync via `zotero-last-sync::`,
  unpinned citekeys skipped with a warning; `docs/zotero-setup.md`
  rewritten (verified against Zotero 9 conventions, end-to-end run
  tracked in #28).
- `docs/data-package-workflow.md`: the seam end to end, the nightly
  check pattern, and where mcptools fits (interactive analysis) versus
  where it does not (system of record, freshness).

## [3.1.0] - 2026-07-06

The journal seam and dual-register answers, from first live use of the
v2.3/v3.0 stack: the journal becomes the daily surface of the ingest
pipeline, and query answers become readable by anyone.

### Added

- Journal seam (`openspec/specs/ingest.md` REQ-090..095, issues #83/#84/#85):
  every ingest run appends one bullet per source to a single daily
  `Ingested` block on today's journal page, with links to the touched wiki
  pages and an empty child bullet reserved for the user's own notes;
  append-only inside the journal (REQ-094), visible at the checkpoint
  (REQ-092), riding the run's atomic commit (REQ-095).
- Wiki-to-journal back-link (schema REQ-585c, ingest REQ-093, issue #84):
  optional `journal::` property on ingested pages, refreshed like
  `updated::` to the most recent ingest day's journal page; together with
  the journal bullet it forms the bidirectional wiki-journal link pair.
- Dual-register query answers (`openspec/specs/query.md` REQ-435..437,
  issues #82/#88): every /wiki-query answer carries the precise register
  first, then a plain-language version under `In plain terms`; same facts,
  same warnings, no new claims; source and plane attribution appear once,
  shared by both registers.
- Config key `journals_dir` (config REQ-629, default `journals`, issue #86):
  names the journal directory per tool flavor; recognized by page
  enumeration (`wikilib.py`), namespace classification (`lint.py` rule 14),
  and `check_config.py`.

### Changed

- Ingest REQ-060 now names the journal seam as the single sanctioned
  machine write path into journals (append-only); the voice journal summary
  (REQ-082) writes through the same discipline instead of carving its own
  exception (issue #85).

## [3.0.0] - 2026-07-06

The personal pipeline: a SQLite machine plane beside the markdown vault,
voice capture as an ingest source, and two-plane query routing. Completes
the v3.0 milestone (issue #61) under the 2026-07-05 gate waiver (all
adoption-pacing gates dropped except the archive.db backup-before-first-note
rule and the voice per-row confirmation rules, which are implemented as
standing requirements, not gates).

### Added

- Storage-plane contract (`openspec/specs/storage.md`, REQ-1100..1141,
  issue #55): markdown is what a human writes, SQLite is what a machine
  accumulates; `archive.db` (raw capture, irreplaceable, REQ-1120..1122
  durability) and `index.db` (derived, disposable, frozen three-table
  schema) are never merged and never enter git; voice provenance shape
  `archive.db:voice_notes/<id>` with capture-backed `reliability:: low`
  (schema REQ-586b) and the `capture-backed` audit verdict (audit REQ-927);
  the dead-man pipeline status line (REQ-1140/1141).
- Voice pipeline guide (`docs/voice-pipeline.md`, issue #56): whisper.cpp,
  phone sync, archive.db DDL and insert script, nightly watcher, canary
  memo, the Phase 0 exit test; adoption-ordered with durability first.
- `wiki-ingest-voice` skill (issue #57): drains unprocessed `voice_notes`
  rows; journal-default (REQ-082), wiki writes per-row opt-in with the full
  sentence shown (REQ-083), individual confirmation for anything naming a
  person (REQ-084), assessments of people never promoted (REQ-085), TODOs
  human-placed (REQ-087), rows marked processed only after the atomic
  commit (REQ-080), no `--auto` path (REQ-081). Ships behind
  `setup.sh --with-personal` (setup REQ-803); golden transcript pinned
  (`tests/golden/ingest-voice.golden.md`).
- `rebuild_index.py` (issue #58): vault to index.db, concrete frozen schema
  written into storage REQ-1130 (people, meetings, page_properties,
  page_text FTS5, rebuild_stamp); deterministic content-hash stamp so two
  rebuilds from the same vault state produce byte-identical dumps
  (REQ-1131, harness-asserted); `--stale-check`; REQ-1103 placement guard;
  no hooks (REQ-1133).
- Two-plane query routing (`query.md` REQ-460..464, issue #59): aggregate,
  temporal, and full-text questions route to index.db SQL (SELECT-only,
  stdlib sqlite3); staleness checked before every index read; every answer
  names its plane; index hits become page reads before content is quoted.
- Archive layer guide (`docs/archive-layer.md`, issue #60): Google Takeout
  into archive.db (mbox, ics, vcf), tested stdlib importer snippets, lazy
  alias resolution, backup discipline; never-index.db rule (REQ-1132).
- Author provenance (issues #73/#74, from live vault use): optional
  `author::` on ingested pages (schema REQ-585a; extraction REQ-011a,
  emission REQ-033c) and born-cited `wiki/people/` pages for recurring
  authors (ingest REQ-024a).
- Config keys: `archive_db` (REQ-626), `index_db` (REQ-627).
- Capture refs are valid cite targets: `check_citations.py` accepts
  `archive.db:voice_notes/<id>` in the source-file union (ingest REQ-086).

### Fixed

- Live-vault feedback round (issues #66..#70, PR #71): ingest names the
  exact `## Cross-References` heading and the checker tolerates
  `Related`/`See also`; `secret_scan.py` exempts ad/search tracking params
  only in URL query context; ingest Phase 0 slugifies source filenames at
  intake (REQ-070a); `init_wiki.py` writes `:hidden ["raw" "ingested"]`
  into `logseq/config.edn` (setup REQ-787); Logseq page properties are
  written unbulleted (schema REQ-590/591), matching what the app writes.
- Zotero guide verify-once (issue #28, partial): plugin pinned at v3.5.5,
  known-good stamped 2026-07-06, MD-graph annotation-sync caveat recorded.

### Notes

- The section 8 exit test in `docs/voice-pipeline.md` remains the
  recommended first run of the voice loop; the archive.db off-machine copy
  must exist before the first real voice note (REQ-1120, unwaived).
- Harness at 149 assertions (was 108 at v2.2.0); `check_canon.py` gains
  the namespace-contract surface.

## [2.3.0] - 2026-07-06

The glossary layer: hand-run first (G-0), tooling under the same waiver.
Completes the v2.3 milestone.

### Added

- Hand-run glossary (G-0, issue #53): domain and term page templates for
  both modes plus `docs/glossary-workflow.md` (capture with
  `#glossary-todo`, weekly curation, promote selectively, pull-only
  import, staging never as drafting context).
- Glossary tooling (issue #54): `openspec/specs/glossary.md`
  (REQ-1000..1014, human-DECIDED / tool-READABLE / structure-LINTED);
  namespaces REQ-960 amended to exactly four content namespaces WITH the
  check_canon namespace surface and the repo-wide stale-phrase grep gate
  in the same PR (premortem revision 8); lint rule 15 (REQ-250..253:
  table shape, rule enum, staging hygiene; structure only, no auto-fix);
  `init_wiki.py --with-glossary` and the `glossary_dir` config key
  (REQ-628); the `wiki-glossary` skill (curate / promote / import /
  context modes, every write checkpoint-confirmed).

## [2.2.0] - 2026-07-04

The human layer: PARA tasks (`para/`) and Zettelkasten notes (`notes/`) in the
same graph as the machine-written `wiki/`, with a hard namespace contract and
one sanctioned promotion path. Completes the v2.2 milestone (issue #30).

### Added

- Namespaces contract + naming canon (`openspec/specs/namespaces.md`,
  issue #22): REQs renumbered into the globally unique 960..981 range;
  `schema.md` REQ-580 flipped from Title Case to lowercase-hyphenated
  structural names with the proper-noun-leaf exemption (REQ-580a/580b,
  namespaces REQ-976) and the corpus rename pass (REQ-580c); the
  personal-synthesis reliability rubric case (REQ-586); `para_dir` /
  `notes_dir` config keys (config REQ-625).
- Lint rules 13 (naming hygiene: structural segments mechanical, leaf
  proper-noun judgment stays in the wiki-lint skill) and 14 (namespace
  hygiene: strays outside the contract flagged; `para/` and `notes/` exempt
  from every wiki-only rule) (issue #23).
- Promotion seams in wiki-ingest (namespaces REQ-970..973, issue #24):
  `raw/para-<project>.md` / `raw/note-<name>.md` sources default to
  `reliability:: medium` (personal synthesis, schema REQ-586) and run the
  unchanged lifecycle with atomic move+commit, secret gate, and `cite::`
  emission; the literature variant (REQ-973) is a report reminder, never a
  write into `notes/`. New golden pairing pins the promoted-note checkpoint
  (`tests/golden/promotion-seam.golden.md`, issue #26).
- Opt-in para/notes scaffold: `init_wiki.py --with-para-notes` (or
  `setup.sh --init --with-para-notes`) seeds the human layer; without the
  flag the output is unchanged (issue #29).
- `migrate_wiki.py --lowercase` converter pass (issue #25): `Wiki/` to
  `wiki/` renames via git mv, link and hub rewrites, plus Roam task-marker
  conversion (`{{[[TODO]]}}` to `TODO` and variants); dry-run by default,
  idempotent, driven interactively by `/wiki-migrate`.
- Harness at 108 assertions (both tool modes), including migration and
  naming/namespace-hygiene coverage.

### Notes

- The maintainer-verification items on #27 (Logseq Datalog query validation,
  archive-procedure confirmation) and #28 (Zotero plugin verify-once,
  end-to-end loop run) remain open past this release.
- The "real-vault lowercase migration executed" release-gate item (issue #30)
  is moot: the maintainer starts from a fresh empty graph, so there is no
  pre-v2.2 corpus to migrate.

## [2.1.0] - 2026-07-04

Claim-level citations and the two skills that consume them. Completes the
re-authored Patch 2 (issue #8) in its block-native form.

### Added

- `cite::` block-property citation convention (`openspec/specs/citations.md`,
  REQ-900..905): wiki-ingest emits `cite::` on every non-common-knowledge claim
  block; page-level `source-file::` is the union of the page's `ingested/` cite
  targets; born-cited pages per REQ-033b. Planned cite targets appear in the
  ingest checkpoint plan table.
- `check_citations.py`: cite coverage stats (advisory), cite-target resolution,
  the source-file union invariant, and orphaned-cite detection (mechanical);
  wired into the ingest quality gate.
- `wiki-audit` skill: claim-to-source verification via one isolated subagent
  per cited source, verdict rubric (supported / partial / unsupported /
  source-missing), reconciliation with `reliability::` and Pending Review;
  read-only by default, `--fix` writes only after confirmation.
- `wiki-update` skill: diff-first, source-required revision path; factual
  changes without a source are refused; superseded claims stay legible
  (marked, never silently deleted).
- Schema templates gained the Claim Citations section; citation fixtures and
  12 new harness assertions (74 total).

## [2.0.0] - 2026-07-04

The multi-skill suite. The single `/wiki` command (`wiki.md`) is removed and its
workflows are re-homed across eight skills backed by a spec canon, shared scripts,
and a mechanical test harness. BREAKING: the v1 command file is no longer shipped
or supported; see `docs/migration-v2.md`.

Tagged 2026-07-04 with the real-vault gate waived by maintainer decision; running
`migrate_wiki.py` dry-run plus `wiki-lint` against the real vault remains the
recommended first post-release step (issue #21 gate, `docs/migration.md`).

### Added

- **Skill suite** (`skills/`): `wiki-setup`, `wiki-ingest`, `wiki-query`,
  `wiki-lint`, `wiki-maintain` (status + prune), `wiki-migrate`, plus
  `wiki-audit` and `wiki-update` as stubs (implementation in v2.1, issue #18).
  Shared conventions and scripts live in `skills/wiki-core/`.
- **Core scripts** (stdlib-only, both tool modes): `init_wiki.py` (scaffolding),
  `lint.py` (mechanical lint layer with a grandfather severity floor),
  `check_canon.py` (spec-consistency across specs, references, and templates),
  `secret_scan.py` (pre-archive secret gate), `migrate_wiki.py` (v1-to-v2
  corpus converter), `find_config.py`/`check_config.py` (config discovery and
  validation).
- **Interactive ingest**: one consolidated checkpoint before any write
  (ingest.md REQ-025); `--auto` opts out for queue draining (REQ-026);
  `--import` replaces the v1 import verb.
- **Pre-archive secret gate**: source bytes are scanned before any file moves
  into the git-tracked `ingested/` tree (REQ-045); `sensitive_source_types`
  keeps configured types out of git history entirely (REQ-046).
- **Two-layer lint**: mechanical rules via scripts (report-only), judgment
  rules agent-side; 12 rules including canonical-url link rot; fixes are
  proposed per finding and applied only after user confirmation.
- **Corpus migration**: grandfather lint mode plus the one-time converter and
  the `wiki-migrate` skill (`docs/migration.md`).
- **Test harness**: `test_pipeline.sh` (62 assertions, fixtures generated at
  runtime for both tool modes), golden transcripts, `docs/testing.md`.
- **Docs**: `docs/migration-v2.md` (v1 command to skill suite) and
  `docs/design-vs-karpathy.md` (two-way review against the original gist).

### Removed

- **`wiki.md`** (the v1 single command). Every workflow it provided has a
  skill home; an installed legacy copy keeps working but is unsupported, and
  `wiki-setup` offers its removal (setup.md REQ-806).
- **The provenance sentinel comments** that marked fork-overlay regions in the
  templates and workflow text. The fork seam they protected is gone; the
  Schema-page upgrade now keys on section headings and `schema-spec-version::`.

### Deferred to v2.1

- Block-native citations (`cite::`, issue #17) including born-cited pages
  (ingest REQ-033b).
- `wiki-audit` and `wiki-update` implementations (issue #18); both ship as
  stub SKILL.md files in 2.0.0.

## [1.5.0] - 2026-06-25

Fork feature (larnsce). A literature-research workflow guide and an optional
Semantic-Scholar enrichment for the provenance pipeline added in 1.4.0. This is mostly
documentation: how to combine Connected Papers, Semantic Scholar, Elicit, and Zotero with
the wiki command so discovery stays fast and only read papers cross into the wiki. The only
tool change is an optional `s2-metrics::` property, and it rides inside the existing
provenance regions (sentinel comments, removed in 2.0.0), so the fork seam did not widen.

### Added

- **`docs/literature-research.md`** - the four-tool pipeline (each tool does one stage,
  Claude Code orchestrates), the funnel rule ("discovery feeds Zotero, Zotero feeds ingest,
  only read papers cross the line"), a wiki query (now `/wiki-query`) before discovery, the Semantic Scholar MCP
  setup, and the convention for ingesting an Elicit synthesis as a `knowledge` page (a usage
  habit stated at ingest time, not a new command). Linked from the README Documentation list.
- **Optional `s2-metrics::` property.** When a Semantic Scholar MCP is configured, ingest
  (now `/wiki-ingest`) can record a source's raw bibliometric figures (citations, influential citations,
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
from vanillaflava/llm-wiki-skills, adapted to Logseq and this tool's v1 wiki command. The
goal is reproducibility: every synthesised claim traces back to a specific archived source,
and weakly-supported pages are visibly flagged until corroborated. Implemented as additive
provenance regions (sentinel comments, removed in 2.0.0) so the fork stayed rebaseable
against upstream; the base `## Workflow: ingest (Default)` was left verbatim and only
overlaid.

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
- **LRU-Demote** - a new prune verb, `[--months N]` (now `/wiki-maintain prune`). `query` appends every full-page
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

- Backward compatible. Existing wikis keep working; run lint with `--fix` (now `/wiki-lint`) once to backfill
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

- The ingest verb (now `/wiki-ingest`) - 5-phase source processing pipeline (URL, file, text)
- The query verb (now `/wiki-query`) - search, synthesis, and source attribution
- The lint verb (now `/wiki-lint`) - 9 automated health checks with `--fix` auto-repair
- The status verb (now `/wiki-maintain`) - wiki metrics and health dashboard
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
