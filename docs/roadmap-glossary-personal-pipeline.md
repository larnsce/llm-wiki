# Roadmap: Glossary (v2.3) + Personal Pipeline (v3.0)

Implementation plan for the two concepts in `prompts/glossary-concept.md` (EN-DE
terminology system) and `prompts/llm-wiki-setup-plan.md` (voice pipeline plus
SQLite archive/index layers). Issue-based, following the v2.0.0/v2.2 pattern:
canon first, one PR per issue, mechanical verification per PR.

Status: premortem applied (2026-07-04, ten failure modes; report at
`docs/premortem-report-20260704.html`, transcript at
`prompts/2026-07-04-001-premortem-glossary-personal-pipeline.md`). The
"Premortem revisions" section at the end overrides anything above it that it
contradicts. Awaiting maintainer go before issues are filed.

## Context

- The maintainer starts a fresh, empty Logseq graph: no migration or
  existing-corpus machinery is needed anywhere in this plan.
- v2.0.0 (multi-skill suite), v2.1.0 (citations, audit/update), and v2.2
  (namespaces contract, naming canon, promotion seams, para/notes scaffold)
  are shipped. The three-namespace contract (`wiki/` machine-written, `para/`
  and `notes/` human-owned) is normative in `openspec/specs/namespaces.md`
  REQ-960..981.
- Repo ground rules that bind this plan: canon-first (specs are the single
  source of truth), zero external dependencies (bash, python3 stdlib, git),
  interactive-by-default writes, "do not formalize a verb until it has been
  done by hand enough to know the ceremony pays off".

---

## Idea A: Glossary system (milestone v2.3)

### Design decisions

1. **Placement: a fourth recognized namespace `glossary/`.** The concept wants
   a curated, permanently maintained evergreen reference layer. It fits none of
   the three existing namespaces cleanly: `wiki/` is machine-written and
   source-backed (a terminology *decision* is not a sourced claim and carries
   no `reliability::`); `para/` is tasks; `notes/` is thinking. Proposal:
   `glossary/` becomes a fourth namespace with a distinct ownership model:
   human-DECIDED, tool-READABLE, structure-LINTED. The tool never invents or
   edits a Rule value; it may scaffold staging pages (imports) and check
   structure. This amends namespaces.md REQ-960 ("exactly three") and the
   rule-14 allowlist: deliberate spec churn, done once, canon-first.
2. **Domain pages, not language-pair pages**: `glossary/tech`,
   `glossary/teaching`, `glossary/marketing` (lowercase structural names per
   REQ-580). The parent `glossary` page is the index (hub-style routing lines,
   so Stage-1 query routing can load the right domain glossary as context).
3. **Term pages under the domain**: `glossary/tech/repository`, with
   `alias:: Repository, Repositorium` so both language forms resolve via
   Logseq aliases. No root-level term pages (would trip namespace-hygiene and
   pollute the root). Properties: `alias::`, `domain::`, `rule::`
   (enum: `keep-en | translate | context`), `conflicts::` (free text, the
   recorded why). Promote selectively: table rows are the default, term pages
   only for load-bearing terms.
4. **Table format is canon**: `| EN | DE | Rule | Note |` with the Rule column
   restricted to the enum. Lint checks structure mechanically; the decision
   content stays human.
5. **Import = staging + promote, never merge**: imported termbases land on
   `glossary/imported/<source>` staging pages with `source::` (attribution,
   e.g. CC-BY for Glosario) and `status:: unreviewed`. Rule column arrives
   EMPTY: filling it is the human decision. The importer is a script that
   takes a LOCAL file (no network in validators); Glosario's `glossary.yml`
   needs a minimal purpose-built parser for its specific flat shape (PyYAML is
   not stdlib and stays banned); TBX/CSV variants are follow-ups.
6. **Capture loop**: `#glossary-todo` inline tag while writing; curation is a
   periodic human pass. The wiki-glossary skill automates the mechanical part
   (collect all `#glossary-todo` blocks, present a curation checkpoint, write
   the decided rows to the chosen domain page, mark the blocks done).
7. **Use loop**: drafting with Claude references the relevant domain glossary
   ("use the conventions from glossary/teaching"). wiki-query's Stage-1
   routing recognizes the glossary index so this costs one hub read.

### Issues (v2.3, in dependency order)

| # | Issue | Contents | Deps |
|---|---|---|---|
| G-1 | spec: glossary namespace + term canon | New `openspec/specs/glossary.md` (REQ-1000..1020 range): namespace ownership model, domain/term page format, rule enum, staging/import contract, capture tag. Amend namespaces.md REQ-960/962 and lint.md rule 14 allowlist. | - |
| G-2 | templates + scaffold | `templates/*/glossary*.md` (domain page, term page, staging page); `init_wiki.py --with-glossary` opt-in (index + one seed domain page); config key `glossary_dir` (default `glossary/`). | G-1 |
| G-3 | lint rule 15: glossary-hygiene | Table shape, rule-enum values, staging pages carry source/status, term pages carry rule::; glossary pages exempt from wiki-only rules (source-file, reliability, cite). check_canon surfaces updated (rule count 15). | G-1 |
| G-4 | glossary_import.py | Stdlib importer: Glosario glossary.yml (local file) to staging page rows, EN+DE filter, attribution line, slug links; `--json`, exit codes per repo contract. | G-1, G-2 |
| G-5 | wiki-glossary skill + docs | Skill: capture-review checkpoint (drain #glossary-todo), promote flow (staging row to domain page to optional term page), drafting-context loader. `docs/glossary-workflow.md` narrative guide. | G-2, G-3 |
| G-6 | v2.3 rollup | Harness fixtures (clean glossary passes, bad rule enum flagged, staging without status flagged), CHANGELOG 2.3.0, tag v2.3.0. | all |

Estimated size: comparable to the v2.2 milestone (one spec PR, four small
implementation PRs, one rollup).

---

## Idea B: Personal pipeline (milestone v3.0)

### The split that shapes everything

The setup plan mixes two kinds of work:

- **Tool features** (belong in this public repo): the storage-plane contract,
  the voice-ingest skill, the index rebuild script, SQL-aware query routing.
  Generic: any user with a voice recorder and a laptop could run them.
- **Personal infrastructure** (belongs to the maintainer's machine and vault):
  whisper.cpp install, phone sync, launchd watcher, archive.db content,
  Google Takeout, alias resolution. The repo DOCUMENTS these (docs/ guides
  with copy-paste snippets) but does not ship or test them.

The maintainer's own phased adoption plan (Phase 0 exit test, daily review
habit, three weeks of habit before expanding scope) is the pacing authority.
Repo issues below only build what a phase needs, just before it needs it.

### Design decisions

1. **Storage-plane contract as canon**: new `openspec/specs/storage.md`.
   Markdown is what a human writes (or the tool writes as curated synthesis);
   SQLite is what a machine accumulates. `index.db` (derived, disposable,
   rebuilt from the vault, gitignored) and `archive.db` (source data,
   irreplaceable, never in git, backed up) are NEVER merged. python3's
   stdlib `sqlite3` keeps the zero-dependency rule intact.
2. **Voice ingest is a variant of the existing ingest contract**: the
   checkpoint, provenance, secret gate, and namespace scope rules all apply
   unchanged. Source = an unprocessed `voice_notes` row instead of a `raw/`
   file; provenance = `source-file:: archive.db:voice_notes/<id>` (a new
   provenance shape REQ, since the transcript is not an `ingested/` file);
   output = 2-4 line journal summary with `[[links]]` plus routed wiki page
   updates plus extracted TODOs (to the journal or a para/ page the human
   confirms, never auto-written to `para/` per REQ-966: the checkpoint offers
   the TODO list for the human to place).
3. **Third-party PII stance**: transcripts and emails mention other people.
   archive.db never enters git by construction; the gate that matters is at
   PROMOTION (voice summary to wiki page). The ingest checkpoint for voice
   sources always runs interactively (no `--auto` for voice) and the secret
   gate scans the summary text; PII advisories are surfaced at the checkpoint.
4. **Query routing stays two-plane and honest**: entity questions route to
   wiki pages (existing Stage-1/2); aggregate, temporal, and full-text
   questions route to `index.db` SQL (FTS5). The query report always states
   which plane answered. index.db staleness is handled by checking the
   rebuild timestamp against the vault's latest commit and warning.
5. **Dogsheep, not hand-written importers**: the archive layer guide
   documents google-takeout-to-sqlite and an .ics-to-meetings snippet; the
   repo ships no email/calendar importer code.
6. **Provenance-to-SQLite (the setup plan's Phase 5) is explicitly parked**:
   `sources`/`page_updates` tables replacing `source-file::` would be a
   second provenance system fighting the shipped one. Revisit only after the
   voice loop has survived contact with reality for a quarter.

### Issues (v3.0, in dependency order)

| # | Issue | Contents | Deps | Serves phase |
|---|---|---|---|---|
| P-1 | spec: storage planes + voice provenance | `openspec/specs/storage.md` (REQ-1100.. range): two-plane contract, db placement/gitignore, archive.db schema for `voice_notes`, provenance shape `archive.db:voice_notes/<id>`, staleness rule. Amend ingest.md: voice source variant, interactive-only. | - | 0 |
| P-2 | docs: voice capture + transcription guide | `docs/voice-pipeline.md`: whisper.cpp + large-v3-turbo setup, phone sync options (iCloud/Shortcuts, Syncthing), context-prompt trick for proper nouns, archive.db DDL + insert snippet, launchd watcher (pull-based, idempotent, drain-the-backlog), cold-storage move. All copy-paste, maintainer-run. | P-1 | 0-1 |
| P-3 | wiki-ingest-voice skill | Consumes unprocessed `voice_notes` rows (sqlite3 stdlib); per note: summary to today's journal with links + provenance id, substantive content routed to wiki pages through the NORMAL ingest write path (checkpoint, quality gate, secret gate), TODO extraction offered at the checkpoint, row marked processed only after the commit. Transcription stays outside (deterministic, re-runnable); this skill starts at the transcript. | P-1 | 1-2 |
| P-4 | rebuild_index.py | Vault to index.db: `people`, `meetings`, `page_properties` tables + FTS5 over page text; idempotent full rebuild (no incremental complexity); `--json`; staleness stamp. Fixture round-trip test in the harness. | P-1 | 4 |
| P-5 | wiki-query: two-plane routing | Query skill extension + query.md REQs: routing decision (entity vs aggregate/temporal/full-text), SQL templates for the three index tables, staleness warning, plane attribution in the answer. | P-4 | 4 |
| P-6 | docs: archive layer guide | `docs/archive-layer.md`: Takeout via google-takeout-to-sqlite, .ics to meetings, contacts seed, lazy per-person alias resolution (explicitly months-long, never front-loaded), backup discipline (nightly off-machine for archive.db, quarterly restore check). | P-1 | 3 |
| P-7 | v3.0 rollup | Harness: voice_notes fixture db, ingest-voice golden transcript (summary + routing for a fixed rambling transcript), rebuild round-trip, CHANGELOG 3.0.0, tag. | all | - |

Parked (not issues): provenance-to-SQLite refactor (Phase 5 of the setup
plan); server hardware; OpenClaw/Datasette-agent integration.

---

## Sequencing across both ideas

1. v2.3 glossary first: small, self-contained, exercises the fresh graph
   immediately (the glossary is useful from day one of writing).
2. v3.0 pipeline second, paced by the maintainer's Phase 0-4 adoption plan:
   P-1/P-2 land before weekend 1; P-3 lands during week 2 (Phase 1); P-4/P-5
   land around week 5 (Phase 4); P-6 alongside Phase 3.
3. Nothing in v3.0 blocks v2.3 or vice versa; if the premortem or the
   maintainer reprioritizes, the milestones swap cleanly.

## Verification pattern (every PR)

- Harness assertions green (fixtures for each mechanical behavior)
- check_canon.py green (new spec surfaces registered)
- Fresh scaffold in both tool modes lints clean under --strict
- Skills verified by a condensed end-to-end transcript in the PR body
- Zero external dependencies (sqlite3 is stdlib)

---

## Premortem revisions (2026-07-04, normative)

Ten failure modes were investigated (report:
`docs/premortem-report-20260704.html`). Most likely: tooling outruns
behavior. Most dangerous: third-party privacy leak through the promotion
seam. Most irreversible: archive.db loss. Hidden assumption: because
implementation is free, shipping the tool is progress; the system's real
products are habits and decisions, and raw capture (transcripts, imported
termbases) is not a curated source. The following changes are binding.

### Re-gating: behavior before code

1. **The base loop goes first.** No v2.3 or v3.0 issue is filed until the
   fresh graph has survived two weeks of REAL use of the existing suite
   (ingest papers, query, lint, daily journal). The v2.0-v2.2 machinery has
   never been used in anger; building on top of an unused base is how the
   whole system dies at week two.
2. **Glossary starts by hand (new G-0, replaces G-1..G-6 initially).** A
   glossary is two markdown pages and a convention; per the repo's own rule,
   no verb is formalized until it has been done by hand enough to know the
   ceremony pays off. G-0 ships ONLY: the two templates (domain page, term
   page) and `docs/glossary-workflow.md`. Capture (#glossary-todo), curation,
   and promotion run manually for at least 4 weeks. G-1..G-6 (spec, lint
   rule 15, scaffold flag, skill) are filed only after 20+ hand-decided Rule
   rows exist; if the hand-run loop does not produce them, the tooling would
   not have saved it.
3. **v3.0 phase gates become merge gates.** P-3 (voice skill) does not merge
   until the Phase 0 exit test (speak a memo, read the summary in tomorrow's
   journal, run manually) is recorded on the issue. P-4/P-5 (index + query
   plane) do not merge until P-3 has run for three weeks with the daily
   review alive. The maintainer's adoption pacing is enforced by the issue
   dependencies, not by restraint.

### Design changes (remove the risk, do not mitigate it)

4. **No hand-rolled YAML parser; G-4 is deleted as a script.** Import IS an
   agent workflow: the glossary import step (in G-0 as a documented prompt,
   later optionally in the skill) has Claude read the downloaded
   glossary.yml and write the staging rows, verifying the parsed count
   against `grep -c` of the source. A deterministic importer script is
   written only for CSV/TSV inputs if ever needed. The zero-dependency rule
   stays intact with nothing to rot.
5. **Import is pull, not bulk.** The staging import brings in ONLY terms
   matching open #glossary-todo captures (plus explicitly requested ones),
   not the full termbase. Drafting context loads domain pages only, never
   staging pages; the workflow doc states this as a rule. A 400-row
   unreviewed staging page next to a 12-row curated page is how the Rule
   column dies.
6. **Voice routes to the journal by default; wiki writes are per-row opt-in.**
   The voice checkpoint confirms journal summaries in batch, but any update
   touching a wiki page, and ESPECIALLY any people page or any row containing
   a person's name, requires individual per-row confirmation with the full
   sentence shown (no 80-char truncation, no batch-confirm). A standing
   content rule in the skill: assessments of people (health, family, grades,
   conflicts, performance) are never promoted out of the checkpoint,
   regardless of confirmation; they stay in the transcript.
7. **Voice provenance is capture-backed, not source-backed.** Claims with
   `archive.db:voice_notes/<id>` provenance carry `reliability:: low` by
   default and wiki-audit reports them as capture-backed (a distinct verdict
   class), so the audit layer never launders spoken speculation into
   green-checked fact. Upgrading such a claim requires a real source through
   normal ingest.
8. **The namespace contract becomes a parsed canon surface.** G-1 (when it
   happens) adds the namespace count + ownership table to check_canon's
   parsed surfaces and includes a grep gate (`three namespaces`,
   `exactly three`) across specs, references, templates, and docs in the PR
   checklist. Prose narration of the contract is what drifts; make it
   mechanical before amending it.

### Tripwires for the silent failures

9. **Dead-man status line.** The daily journal summary always begins with a
   pipeline status line: newest voice-inbox file age, unprocessed voice_notes
   count, last index rebuild age. Silence becomes visible in the one place
   the maintainer already looks. A documented weekly canary memo (speak one
   test memo, expect it in tomorrow's journal) closes the phone-side gap that
   Mac-side monitoring cannot see.
10. **archive.db durability is a spec REQ, not a docs footnote.** P-1 gains:
    nightly off-machine copy requirement, quarterly restore drill, and a
    wiki-audit check that voice provenance ids resolve against archive.db
    (dangling id = warning). The vault's agent guidance (CLAUDE.md) forbids
    `git clean -xfd` and equivalents inside the vault; agents are the most
    likely executor of the deletion.
11. **index.db stays provably derived.** No rebuild hooks in pre-commit; the
    query skill triggers a rebuild when the staleness stamp lags the vault
    head. Schema is frozen to the three spec tables; any addition requires a
    spec amendment. The harness asserts rebuild reproducibility (two rebuilds
    from the same vault produce identical dumps); data with no markdown
    source never enters index.db (importers write to archive.db or the vault,
    never to index.db).
12. **Personal tier stays out of the default install.** wiki-ingest-voice
    and the storage plane ship behind an explicit opt-in (`setup.sh
    --with-personal`), the README labels the personal tier (macOS,
    whisper.cpp) separately from the generic tool, and harness fixtures for
    it are clearly synthetic. The public tool and the personal system share
    a repo but not a default surface.

### Kill criteria

- Phase 0 exit test not passed within two weekends of P-2 landing: stop
  filing v3.0 issues; the plumbing does not deserve a skill yet.
- Fewer than 20 hand-decided Rule rows after 4 weeks of G-0: do not build
  G-1..G-6; the glossary stays a manual convention.
- Daily review skipped 5 consecutive days inside the first three weeks:
  pause all expansion, shrink ceremony (voice drops to journal-only), do not
  add tooling to fix a habit problem.
- Two voice-sourced wiki claims found wrong within one month: voice routing
  drops to journal-only until the per-row checkpoint has been redesigned and
  re-validated.

### Pre-launch checklist

- [ ] Two weeks of real base-loop use on the fresh graph recorded (gate for
      filing any new issue)
- [ ] archive.db backup + restore drill documented and executed once before
      the first real voice note enters it
- [ ] Dead-man status line and canary-memo procedure in place when P-3 merges
- [ ] Per-row people-page confirmation and the sensitive-content rule
      implemented in the P-3 checkpoint before first daily use
- [ ] check_canon namespace surface + grep gate merged in the same PR that
      amends REQ-960
- [ ] Import-is-pull rule and staging-never-as-context rule stated in
      docs/glossary-workflow.md from day one
