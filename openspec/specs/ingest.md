# Spec: /wiki-ingest - Source Processing Pipeline

## Description

The ingest command processes external sources (URLs, files, text) and distributes
extracted knowledge across wiki pages. It is the primary write path into the wiki.
A single ingest run targets 5-15 page touches (creates + updates + hub updates).

---

## Requirements

### Phase 1: Source Analysis

- REQ-010: The system SHALL accept three source types: URL (fetched via WebFetch),
  file path (read from disk), and inline text (parsed directly).
- REQ-011: The system SHALL extract entities, facts, relationships, dates, and
- REQ-011a (author extraction, #73): The system SHALL extract the source's
  author(s) where identifiable: clip frontmatter, byline, paper author
  list, or Semantic Scholar metadata (REQ-073a). Absence of an
  identifiable author is normal and never blocks; nothing is guessed.
  decisions from the source material.
- REQ-012: The system SHALL classify extracted knowledge into exactly one of six
  categories: business, technical, content, project, learning, reference.
- REQ-013: The system SHALL evaluate each extracted fact against the L1/L2 routing
  rule (see specs/l1-l2-routing.md) and recommend Memory for L1 candidates.
- REQ-014: The system SHOULD identify when a source contains credentials or secrets
  and MUST NOT write them to wiki pages.

### Phase 2: Wiki Scan

- REQ-020: The system SHALL read `llm-wiki.yml` before any wiki operations to
  determine tool mode (logseq/obsidian), paths, and namespace configuration.
- REQ-021: The system SHALL read the Schema page to load current conventions and
  property requirements.
- REQ-022: The system SHALL glob for existing wiki pages matching extracted entities
  and topics to identify update targets.
- REQ-023: The system SHALL read existing target pages before modifying them.
  Maximum 3 pages loaded simultaneously (JIT retrieval).
- REQ-024a (author recurrence, #74): When a source's extracted author
  already appears in the `author::` values (or `ingested/` provenance) of
  existing pages - the SECOND source by the same person - the plan SHALL
  include a `wiki/people/<name>` page (proper-noun leaf): `type:: entity`,
  `entity-type:: person`, a one-line who-this-is, links to the pages built
  on their work, and a routing line in the people hub. The page is born
  cited: its who-this-is claim cites the `ingested/` files of the works
  themselves, so `source-file::` is their union and the citation invariants
  (REQ-033b, citations REQ-904) hold with no exemption. Below the
  threshold `author::` alone suffices; the user MAY request a person page
  for any author at the checkpoint, and the proposed create appears in the
  plan table like any other create (overridable per run).
- REQ-024: The system SHALL produce a page operation plan: pages to create,
  pages to update, cross-references to add, hub pages to update.
- REQ-025 (interactive checkpoint): After the page operation plan and BEFORE any
  write, the system SHALL pause and present: the planned page touches, the
  per-source `reliability::` rating with a one-line rationale, any contradictions
  detected against existing pages, and the question "what should I emphasize,
  skip, or route to L1 Memory?". The system SHALL apply the user's guidance to the
  plan and only then proceed to Phase 3. This is the default mode.
- REQ-026 (--auto): With the `--auto` flag the system SHALL skip the REQ-025
  checkpoint (batch queue-draining). The plan and ratings SHALL still be included
  in the Phase 5 report, and the Quality Gate (REQ-040/042/045) still blocks on
  failures. `--auto` never bypasses a blocking gate.

### Phase 3: Page Operations

- REQ-030: The system SHALL create new pages with ALL required properties for the
  declared page type (per Schema). Missing required properties are a spec violation.
- REQ-031: The system SHALL use the correct format for the configured tool:
  Logseq (outliner with `- ` body prefix, unbulleted `property:: value` page
  properties per specs/schema.md REQ-591) or Obsidian (flat markdown, YAML
  frontmatter).
- REQ-032: The system MUST NOT overwrite existing content blocks when updating pages.
  New facts SHALL be appended as new blocks below existing content.
- REQ-033: The system SHALL update hub pages to list any newly created child pages
  in their namespace.
- REQ-033a: For every page created or updated, the system SHALL set or refresh its
  routing line in the namespace hub's `### Index` section, formatted
  `[[Wiki/NS/Page]] -- <one-sentence description, <=120 chars> #tags` (see specs/schema.md
  and specs/query.md Phase 0). The description is the routing key consumed by two-stage
  query and MUST be terse and distinctive, not filler. A page without a routing line is
  unroutable.
- REQ-033c (author emission, #73): The system SHALL set `author::` on
  created ingested pages when Phase 1 identified author(s) (schema
  REQ-585a), and SHALL append missing authors (union, deduplicated) when a
  corroborating update touches the page. Never backfilled outside an
  ingest that touches the page.
- REQ-033b: On ingested pages, the system SHALL attach a `cite::` reference to every
  non-common-knowledge factual claim block it writes, per specs/citations.md
  (REQ-900..905). Pages are born auditable. STAGING: this requirement takes effect
  with the citations implementation (v2.1, #17); v2.0.0 ingest is exempt.
- REQ-034: The system SHALL add `[[Wiki/Namespace/Page]]` cross-references between
  all affected pages. Every page touched MUST have at least 1 outgoing wiki link.
  Navigation cross-links SHALL be written under a `## Cross-References` section
  with that exact heading (specs/schema.md REQ-573): the citation checker exempts
  it from claim coverage, while synonym headings (Related, See also) drift out of
  the exemption on other tooling.
- REQ-035: The system SHALL set the `updated::` property (or YAML `updated` field)
  to today's date on every modified page.
- REQ-036: When a page mentions an entity that has its own wiki page, the system
  SHALL use `[[Wiki/...]]` link syntax instead of plain text.
- REQ-036a (person names are always linked, #99): When the system writes a
  PERSON's name into content (page claims, the journal seam's Ingested
  bullets), it SHALL write it as a `[[wiki/people/<First> <Last>]]` link,
  in First-name Surname order (normalize sources that deliver
  "Last, First"). This holds even when the person page does not exist
  yet: person pages are created at the second-source threshold
  (REQ-024a), and lint reports the interim link as info-level pending
  (lint REQ-141a), not broken. The `author::` property stays PLAIN text
  (schema REQ-585a); only prose gets links.
- REQ-037: The system SHOULD target 5-15 page touches per ingest. Fewer than 5
  suggests insufficient cross-referencing. More than 20 suggests the ingest should
  be split.
- REQ-038: File names MUST follow tool conventions: Logseq uses triple-underscore
  separators (`Wiki___Tech___Strapi.md`), Obsidian uses directory hierarchy
  (`Wiki/Tech/Strapi.md`).
- REQ-039: Namespace depth MUST NOT exceed 3 levels
  (e.g., `Wiki/Business/Clients/Acme` is the maximum depth).

### Phase 4: Quality Gate

- REQ-040: The system SHALL verify that all new pages have ALL required properties
  for their declared type before completing the ingest.
- REQ-041: The system SHALL verify that every touched page has at least 1 outgoing
  `[[Wiki/...]]` cross-reference.
- REQ-041a: The system SHALL verify that every new or updated active page has a
  routing line in its namespace hub `### Index` (REQ-033a). A missing routing line is
  a warning (the page is unroutable until `lint --fix` backfills it).
- REQ-042: The system SHALL scan all created/updated content for credential patterns
  (`token::`, `password::`, `secret::`, `api-key::`, base64 strings of 40+ chars).
  Any match MUST block the ingest and warn the user.
- REQ-043: The system SHALL count page touches and emit a warning if the count is
  below 5 or above 20.
- REQ-044: The quality gate SHALL NOT block the ingest on page-touch count warnings
  (REQ-043). It SHALL block on credential detection (REQ-042), pre-archive secret
  detection (REQ-045), and missing required properties (REQ-040).
- REQ-045 (pre-archive secret gate): Before any source file is MOVED into the
  git-tracked `ingested/` tree (REQ-075), the system SHALL scan the source file's
  BYTES for credential patterns (the REQ-042 pattern set, applied to the source
  itself, including a strings-style pass over binary formats). On a match the
  system MUST NOT archive or commit the file: it stays in `raw_dir` with a warning
  naming the match location and requiring redaction (or an explicit
  `--allow-secret` override) before re-ingest. Rationale: `ingested/` is committed
  git history; exposure there is sticky.
- REQ-046 (sensitive source types): When a source's type is listed in the config
  key `sensitive_source_types` (specs/config.md REQ-624), the system SHALL write
  the wiki pages as normal but MUST keep the source file's bytes out of git: the
  file is moved to `ingested/<type>/` but that path is gitignored (managed by the
  system), and `source-file::` still records it. The provenance path stays valid
  locally; only the bytes are excluded from history.

### Phase 5: Report

- REQ-050: The system SHALL output a summary listing: pages created (with types),
  pages updated, cross-references added, hub pages updated.
- REQ-051: The system SHALL list any warnings (low page-touch count, L1 candidates
  found, skipped items) and their reasons.
- REQ-052: The system SHOULD recommend a git commit after structural changes.
- REQ-053 (run log): The system SHALL append a run-log entry to the Dashboard
  page:
  `## [YYYY-MM-DD] ingest | <filename or n sources> -> <n> pages | reliability <level> | mode <interactive|auto> | agents <names|none>`.
  The `agents` field records which installed agent definitions
  (specs/setup.md REQ-807) were actually DISPATCHED during the run
  (comma-separated names, e.g. `wiki-triage, wiki-synthesize`), or `none`.
  It is an observable dispatch record, NEVER a self-reported model id: the
  executing model cannot introspect its own id, and a silent fallback
  (agents not installed, allowlist, inherit) would log the plan instead of
  the execution (issue #108). The field is additive; legacy entries without
  it stay valid.

### Cross-Cutting

- REQ-060: The system MUST NOT modify any non-wiki pages (personal notes,
  other vault content). Journal pages admit EXACTLY ONE machine write path:
  the journal seam (REQ-090..095), which is append-only and never modifies
  existing journal content. The voice journal summary (REQ-082) writes
  through the same seam discipline. No other journal write is sanctioned.
- REQ-061: The system SHALL use ISO 8601 date format (YYYY-MM-DD) for all date
  properties.
- REQ-062: When the configured tool is Logseq, every line of wiki content MUST start
  with `- ` (outliner block prefix). Properties MUST use `property:: value` syntax.
- REQ-063: When the configured tool is Obsidian, properties MUST be in YAML
  frontmatter. Content uses standard markdown without block prefixes.

### Source Pipeline

This extends Phases 1-5 above. It applies when `llm-wiki.yml`
configures a source pipeline (`raw_dir`, `ingested_dir`, `source_types`,
`default_source_type`). It is the path for NEW external sources (e.g. a Zotero export).
Pulling notes ALREADY written in the graph uses `/wiki-ingest --import`, which does NOT move files
or assign `source-file::`.

- REQ-070 (Phase 0, queue intake): When `/wiki-ingest` is given NO argument, the system
  SHALL scan `raw_dir` and process every file there oldest-first (drain the queue). When
  given a path/URL argument, that single source is the input; a local file outside
  `raw_dir` SHALL be copied into `raw_dir` first so the lifecycle is consistent.
- REQ-070a (intake slugging): When a file entering processing from `raw_dir` has a
  filename containing whitespace, commas, `#`, or other non-kebab characters, the
  system SHALL rename it (and any companion asset folder) to a kebab-case slug
  BEFORE planning, so `source-file::` and `cite::` refs are born valid: the
  citation checker rejects refs containing whitespace (specs/citations.md REQ-901),
  and refs are comma-separated, so a comma in a filename breaks ref parsing.
- REQ-071: For each source the system SHALL infer its type (one of `source_types`),
  falling back to `default_source_type`, asking the user only if genuinely ambiguous.
- REQ-072: If processing fails partway, the system SHALL LEAVE the source in `raw_dir`
  (the queue is resumable) and SHALL NOT move a half-processed source.
- REQ-073 (Phase 3 addition): On every created/updated ingested page the system SHALL set
  `source-file::` (the path the source will live at, `ingested/<type>/<filename>`; append
  comma-separated when corroborating) and `reliability::` (per schema REQ-586:
  corroboration is judged per claim, the page value is the minimum across claims).
  These do NOT alter `confidence::` (schema REQ-587).
- REQ-073a (Phase 1, optional enrichment): When a Semantic Scholar MCP is configured, the
  system MAY resolve the source (by DOI, else title + first author + year) and record its
  metrics verbatim as `s2-metrics::` (per schema REQ-586a). These metrics INFORM the
  qualitative `reliability::` judgment but MUST NOT determine it by formula or citation-count
  threshold. The enrichment is OPTIONAL: when no S2 MCP is present the system SHALL skip it
  and judge `reliability::` from the source alone. Absence of the MCP MUST NOT block ingest.
- REQ-074: If a page rests on a SINGLE source and `reliability::` is not `high`, the system
  SHALL append a `## Pending Review` section listing the specific claims needing
  corroboration. If this ingest corroborates an existing flagged page, the system SHALL
  re-check each flagged claim, remove resolved ones, delete the section if all resolve, and
  raise `reliability::`.
- REQ-075 (Phase 5 addition): Only after the Quality Gate passes, the system SHALL MOVE
  each processed source from `raw_dir` to `ingested_dir/<type>/<filename>`. The new location
  MUST match what `source-file::` records. The page edits AND the file move SHALL be staged
  and committed as ONE atomic commit.
- REQ-076 (Phase 0, queue triage delegation): When draining a MULTI-file queue
  AND the `wiki-triage` agent definition is installed (specs/setup.md
  REQ-807), the system SHOULD delegate per-file classification to it: the
  proposed intake slug (REQ-070a), the inferred type (REQ-071), and a
  COMPLEXITY FLAG with a one-line reason. The caller SHALL hand the agent the
  hub-index routing lines and the Schema page list as context; the flag
  SHALL rest only on QUEUE-DECIDABLE triggers (source length, source type,
  another queue item or `ingested/` source on the same topic, the topic
  mapping to a hub or Schema page itself, or the agent's own low
  confidence). Wiki-state judgments (supersedes existing content, conflicts
  with existing claims) stay at the checkpoint, which reads the wiki
  (issue #108 premortem). Flagged items SHOULD route their Phase 1-2
  analysis to the `wiki-synthesize` agent when installed. Single-source
  runs are unchanged, and a missing agent definition degrades to inline
  classification; the triage pass never writes.

### Journal Seam

The journal is the daily working surface; the wiki is the knowledge store.
The seam connects them in both directions on every ingest run: the day's
journal page records what was ingested (with room for the human's own
notes), and every touched wiki page links back to the journal day. This
section extends Phases 3 and 5 when the source pipeline is configured;
without the pipeline the seam is inert. The journal directory resolves from
the config key `journals_dir` (specs/config.md REQ-629).

- REQ-090 (daily Ingested block): After the Quality Gate passes, the system
  SHALL append to TODAY's journal page a block under the heading `Ingested`:
  one bullet per source processed in the run, carrying the source title, its
  type, and `[[wiki/...]]` links to every page the source created or
  updated, plus one EMPTY child bullet reserved for the user's own notes.
  One block per day, not per resource: when the day's journal page already
  has an `Ingested` block (an earlier run today), the system SHALL append
  bullets to that block instead of creating a second one.
- REQ-091 (journal page resolution): The journal page name and file path
  SHALL be resolved per tool flavor: derive the naming pattern from
  existing files in `journals_dir` when any exist; otherwise use the tool
  default (Logseq `journals/YYYY_MM_DD.md` with the graph's date-format
  page reference; Obsidian `<journals_dir>/YYYY-MM-DD.md`). When today's
  journal page does not exist, the system SHALL create it with the
  Ingested block as its only machine-written content.
- REQ-092 (checkpoint visibility): The planned journal append SHALL be
  visible at the REQ-025 checkpoint (a summary line naming the journal page
  and the bullet count is sufficient), and SHALL be included in the Phase 5
  report. `--auto` runs carry it into the report like the rest of the plan.
- REQ-093 (wiki-to-journal back-link): On every page created or updated in
  the run, the system SHALL set or refresh the `journal::` property to
  today's journal page link, tool-native format, per schema REQ-585c. The
  refresh mirrors `updated::`: metadata, not content; the append-only rule
  for content blocks (REQ-032) is untouched.
- REQ-094 (append-only inside the journal): The system MUST NOT modify or
  delete ANY existing journal content: earlier bullets, the user's notes
  under them, or anything else on the page. The seam only appends bullets
  to today's Ingested block (or creates the block, or the page). Child
  bullets written by the user under earlier entries are never touched.
- REQ-095 (atomicity): The journal edit SHALL ride the same atomic commit
  as the page edits and the file move (REQ-075). A quality-gate failure
  that blocks a source also drops that source's journal bullet.

### Data-Package Seam

An R data package is a self-describing, versioned dataset bundle:
DESCRIPTION (name, version, license, URL), `data/*.rda` (canonical data
objects), `inst/extdata/*.csv` (portable copies), `man/*.Rd` (the data
documentation: description, per-variable dictionary, source). The seam
ingests the WHOLE bundle, not just the CSVs, and keeps the vault current
when the package updates on GitHub. Registered packages come from the
config key `data_packages` (specs/config.md REQ-660); the seam runs
through `scripts/data_pkg_sync.R` and the `/data-sync` command. When the
key is absent the seam is inert.

- REQ-100 (versioned snapshot): A sync SHALL write one snapshot directory
  per package version, `ingested/data/<pkg>-<version>/`, containing: the
  package's data frames materialized to CSV (from `data/*.rda`) and any
  `inst/extdata` CSVs; one extracted markdown doc per dataset (title,
  description, variable dictionary, source, pulled from the Rd
  documentation); and a provenance record (package, version, GitHub slug,
  license, sync date). Snapshot paths are cite targets exactly like any
  other `ingested/` path.
- REQ-101 (dataset pages): Each dataset SHALL get a page
  `wiki/data/<pkg>/<dataset>` (`type:: entity`,
  `entity-type:: dataset`) carrying the managed properties `package::`,
  `version::`, `license::`, `url::`, `source-file::` (the snapshot
  paths), and `data-last-sync::` (the synced package version), plus the
  standard required entity properties. A `wiki/data` hub routes the
  packages; a package page routes its datasets.
- REQ-102 (managed sections): The dataset page's `## description` and
  `## data dictionary` sections are MACHINE-MANAGED: regenerated from the
  Rd documentation on every sync. This is the single sanctioned
  regeneration path on these pages (the dataset-page counterpart of the
  journal seam's REQ-094 carve-out); everything else on the page is
  append-only and the human's own sections are NEVER touched.
- REQ-103 (version updates): A new package version SHALL produce a NEW
  snapshot directory; existing `cite::`/`source-file::` references to
  older snapshots remain valid (claims stay pinned to the version they
  were made against). The sync SHALL surface the package's NEWS changes
  between the vault version and the new version at the checkpoint.
- REQ-104 (checkpoint): A sync with writes SHALL run through the REQ-025
  checkpoint discipline (dry-run plan shown, user confirms before
  writes). Update DETECTION is automated; update WRITES are always
  human-confirmed.
- REQ-105 (retention): The seam SHALL keep the last N snapshots per
  package (`data_snapshots_keep`, config REQ-661, default 3) and MUST NOT
  delete a snapshot that any page references via `cite::` or
  `source-file::`, regardless of N.
- REQ-106 (staleness check): `data_pkg_sync.R --check` SHALL compare each
  registered package's GitHub DESCRIPTION `Version:` against the newest
  local snapshot and report stale packages. The check is surfaced through
  `/wiki-maintain` status and MAY be run on a schedule; it never writes
  to the vault.

### Voice Sources

This extends Phases 1-5 for sources that are unprocessed `voice_notes` rows in
archive.db (specs/storage.md) instead of files in `raw_dir`. The base contract
applies unchanged: the checkpoint (REQ-025), the quality gate (REQ-040/042/044),
the secret gate over promoted text (REQ-042), and the namespace scope rule
(specs/namespaces.md REQ-965..967). The file lifecycle (REQ-070/072/075) does
NOT apply: the row's `processed` flag is the lifecycle. STAGING: this section
takes effect with the voice pipeline implementation (v3.0, P-3); until then no
voice source exists.

- REQ-080 (source and lifecycle): A voice source is ONE unprocessed
  `voice_notes` row; the system starts from the stored transcript (transcription
  itself is outside this workflow: deterministic and re-runnable). The row SHALL
  be marked `processed` only after the run's writes are committed. A failed or
  aborted run leaves the row unprocessed; the queue is resumable (mirroring
  REQ-072).
- REQ-081 (interactive only): Voice ingestion SHALL always run the REQ-025
  checkpoint. There is NO `--auto` path for voice sources: REQ-026 does not
  apply to them, and when `--auto` is passed the system SHALL state that voice
  sources are interactive-only and run the checkpoint anyway.
- REQ-082 (default routing: the journal): The default destination for a voice
  note is a 2-4 line summary on today's journal page with `[[links]]` and the
  provenance id. Journal summaries MAY be batch-confirmed at the checkpoint.
  The daily journal summary opens with the pipeline status line per
  specs/storage.md REQ-1140. The write follows the journal-seam discipline
  (REQ-091 page resolution, REQ-094 append-only): it never modifies
  existing journal content.
- REQ-083 (wiki writes are per-row opt-in): Any update touching a wiki page is
  OPT-IN per row at the checkpoint: the system SHALL show the full sentence(s)
  it would write (no truncation) and write nothing to a wiki page without an
  explicit yes for that specific row. Declined rows stay in the journal summary
  or the transcript.
- REQ-084 (people rows confirmed individually): Any row that touches a people
  page or that names a person SHALL require INDIVIDUAL confirmation, with the
  full sentence shown. Such rows MUST NOT ride a batch confirmation, regardless
  of batch size or how the rest of the plan is confirmed.
- REQ-085 (sensitive content is never promoted): Assessments of people (their
  health, family, grades, conflicts, or performance) SHALL NOT be promoted out
  of the checkpoint onto any wiki page, REGARDLESS of confirmation. They remain
  in the transcript (archive.db) only. This is a standing content rule, not a
  pattern gate: it binds the system even when no credential-style pattern
  matches and even when the user confirms the row.
- REQ-086 (provenance shape): A wiki page or claim written from a voice source
  SHALL carry the capture ref `archive.db:voice_notes/<id>`: at page level in
  `source-file::` (comma-separated alongside any other origins) and at block
  level as the `cite::` ref on the claims it supports (block-native per
  specs/citations.md REQ-900). For the citations union invariant (REQ-904),
  capture refs count as cite targets exactly like `ingested/` paths: a page's
  `source-file::` includes an `archive.db:` ref precisely when a block cites it.
  Capture refs are capture-backed provenance: `reliability::` defaults per
  schema REQ-586b and audit reports such claims per audit REQ-927.
- REQ-087 (TODO extraction): TODOs found in the transcript SHALL be OFFERED at
  the checkpoint for the human to place (today's journal, or a `para/` page the
  human edits themself). The system SHALL NOT write to `para/` or `notes/`
  (specs/namespaces.md REQ-966); voice sources do not change the scope rule.

### Voice Conversation Sessions

This extends the Voice Sources section for `/wiki-chat-voice` (issue #117):
a conversational session over STORED voice notes - browse the archive, talk
about selected notes in the session, and close with one ingest. Where Voice
Sources (REQ-080..087) drains the unprocessed queue note by note, this
section covers REVISITING notes (processed or not) as conversation material.
The Voice Sources rules apply unchanged wherever this section is silent.
STAGING: this section takes effect with the wiki-chat-voice skill
(issue #117).

- REQ-1200 (browse is read-only): The session SHALL open with a picker over
  `voice_notes` rows - processed AND unprocessed, marked which is which -
  read via python3's stdlib sqlite3 (storage REQ-1104) in read-only mode,
  newest first, bounded by default (last ~20 rows, paginated on request) and
  filterable by date (`--since`), transcript substring (`--grep`, SQL LIKE),
  and `--unprocessed`. Each picker row carries: id, recorded date, duration,
  the original filename (the basename of `audio_path`, derived at display
  time - a human-recognizable handle and a cross-check when a `recorded_at`
  looks wrong, issue #121), a one-line description, and 3-5 keywords.
  Descriptions and keywords are
  generated AT RUN TIME for the rows shown, and only those; they MUST NOT be
  persisted anywhere: `voice_notes` is frozen at six columns (storage
  REQ-1111), archive.db holds raw capture only (REQ-1110), and index.db
  admits nothing without a markdown source (REQ-1132). Digest generation
  SHOULD dispatch to the haiku-tier triage agent when installed (setup
  REQ-807) and degrades to inline generation without it.
- REQ-1201 (interactive only): A conversation session is interactive by
  nature; there is NO `--auto` path (mirroring REQ-081). When `--auto` is
  passed the system SHALL state that and continue interactively.
- REQ-1202 (the conversation writes nothing): Between note selection and the
  closing checkpoint the system MUST NOT write: no journal edits, no page
  edits, no `processed` flips, no archive.db mutation of any kind. Candidate
  insights (journal lines, wiki claims, TODOs, contradictions with existing
  pages) are tracked in-session only. The conversation ends only on the
  user's explicit signal, never on the system's initiative.
- REQ-1203 (one closing checkpoint): On the end signal the system SHALL run
  ONE consolidated checkpoint (REQ-025 discipline) presenting: the journal
  synthesis (the default destination, REQ-082 discipline; the block opens
  with the pipeline status line per storage REQ-1140), each wiki offer with
  the full sentence(s) (REQ-083), retained sensitive items (REQ-085, listed
  by category only), the TODO hand-over (REQ-087), and the processed-flip
  offers (REQ-1205). All writes happen after this checkpoint or not at all.
- REQ-1204 (the conversation is not a source): Every claim promoted from the
  session SHALL cite the underlying voice note id(s),
  `archive.db:voice_notes/<id>` (the REQ-086 shape). The conversation itself
  is NEVER a cite target and adds no evidence: reliability stays
  capture-backed `low` (schema REQ-586b) no matter how thoroughly the claim
  was discussed, and one memo cannot corroborate another by the same speaker
  (schema REQ-586 independence). A conclusion not grounded in at least one
  specific note is journal-only; it MUST NOT be promoted to a wiki page.
- REQ-1205 (processed-flip is per-note opt-in, post-commit): For each
  UNPROCESSED note whose content the closing journal synthesis substantively
  covers, the checkpoint SHALL offer to mark it processed - suggested yes,
  individually declinable - so the queue drain (REQ-080/082) does not write
  a duplicate journal summary later. Flips happen only AFTER the run's
  atomic commit succeeds, reusing the REQ-080 lifecycle. Notes merely listed
  or partially discussed, and already-processed notes, are never touched.
- REQ-1206 (people and sensitive-content rules bind at write time): REQ-084
  (individual confirmation for rows naming people) and REQ-085 (assessments
  of people are never promoted, regardless of confirmation) apply to the
  closing checkpoint exactly as to voice ingest. Discussing people DURING
  the conversation is unrestricted - the session is private; the rules gate
  what leaves the checkpoint, not what is talked about.
- REQ-1207 (context budget): At selection time the system SHALL sum the
  selected transcripts' word counts and, above a threshold (default 15000
  words), push back: offer to narrow the selection or split into more than
  one session rather than degrade synthesis quality by loading everything.

### Transcript Sources

AI conversation transcripts (claude.ai chats, cross-project design
discussions) as ingest sources. The route was designed in issue #107,
descoped to a manual protocol by the 2026-07-07 premortem, validated by the
Phase-0 hand ingests (2026-07-08), and spec'd when the maintainer waived the
five-ingest gate (2026-07-16). It stays file-based on purpose: transcripts
ride the standard `raw/` to `ingested/` lifecycle; there is NO archive.db
transcript table (the shape for automated bulk capture - revisit only if
volume demands it). Where this section is silent, the Source Pipeline rules
apply unchanged.

- REQ-1300 (file route and type inference): A transcript enters the pipeline
  as a curated markdown export in `raw_dir`, with source type `transcripts`
  (specs/config.md REQ-623). A filename with the `chat-` prefix
  (`raw/chat-*.md`; convention `chat-YYYY-MM-DD-<topic-slug>.md`) SHALL
  infer type `transcripts`, extending the REQ-071 inference set consistently
  with the `para-`/`note-` promotion prefixes; non-prefixed exports fall
  back per REQ-071 as before.
- REQ-1301 (sensitive by default): `transcripts` is in
  `sensitive_source_types` by default (specs/config.md REQ-624): chats mix
  project detail, personal context, and half-formed ideas, and their bytes
  MUST NOT enter git history. The REQ-046 machinery (gitignored
  `ingested/transcripts/` path, the gitignore check of the secret gate)
  carries the mechanics unchanged. Because gitignored bytes fall outside
  git-as-backup, an off-machine copy of the gitignored `ingested/` subtrees
  SHALL exist before the first sensitive transcript ingest (mirroring the
  archive.db durability discipline, specs/storage.md REQ-1120); the
  audit-side tripwire distinguishing lost bytes from weak sources is the
  `source-missing` verdict (specs/audit.md REQ-923/927), which is never
  conflated with `reliability:: low`.
- REQ-1302 (capture-backed, decisions excepted): A transcript is
  capture-backed (schema REQ-586b): claims resting only on it default to
  `reliability:: low`, a transcript can never corroborate itself, and
  multiple transcripts of the same speaker's conversations count as ONE
  source for REQ-586 corroboration. The exception is the route's point:
  DECISIONS - the user's own recorded conclusions ("we chose X because Y") -
  route like promoted personal notes and rate `medium` once the user
  confirms them INDIVIDUALLY at the checkpoint (the REQ-586
  personal-synthesis case): the confirmation makes the user the source; the
  transcript is merely where the decision was written down. Model-asserted
  analysis in the same transcript stays `low` with a `## Pending Review`
  entry per REQ-074.
- REQ-1303 (interactive only, decision-log default): There is NO `--auto`
  path for transcript sources (mirroring REQ-081): when `--auto` is passed
  the system SHALL state that transcripts are interactive-only and run the
  REQ-025 checkpoint anyway. The default destination is a 2-4 line
  journal/decision-log entry with `[[links]]` (REQ-082 discipline); wiki
  writes are offered PER EXTRACTED DECISION, individually opt-in with the
  full sentence(s) shown (REQ-083). The people rules bind unchanged: rows
  naming a person are confirmed individually (REQ-084) and assessments of
  people never leave the checkpoint (REQ-085).
- REQ-1304 (skip what another system records): The system SHOULD NOT extract
  content a better system of record already holds: decisions from a session
  on a repository (its issues, CHANGELOG, and commits absorb them),
  ecosystem trivia, install mechanics. An ingest whose checkpoint proposes
  no wiki writes is a VALID outcome; the source still completes the
  lifecycle move so the queue drains.
- REQ-1305 (curation precedes ingest): The expected input is an export
  curated at capture time - decisions, the questions that drove them, enough
  surrounding text to stay honest (Phase-0 evidence: a raw one-day session
  export measured 4,637 lines and 254 tool calls and yielded zero net-new
  content). When a queued transcript is visibly uncurated (dominated by tool
  output or transcript noise), the system SHOULD recommend re-export with
  curation at the checkpoint instead of attempting extraction over the
  noise. Capture-at-source (ending a session by asking for a decision log)
  is the recommended capture mechanism (docs/source-routes.md).

---

## Scenarios

### Scenario 1: Ingest a URL source (happy path)

```
GIVEN llm-wiki.yml is configured with tool: logseq and wiki_path: /tmp/test-wiki
AND the wiki has a Schema page and a Wiki/Tech hub page
AND no page exists for "Redis"
WHEN the user runs /wiki-ingest "https://redis.io/docs/about/"
THEN the system SHALL create a new page Wiki___Tech___Redis.md
AND the page SHALL have properties: type:: entity, entity-type:: technology,
    created:: [today], updated:: [today], status:: active, source:: ingest
AND the page SHALL contain extracted facts about Redis from the URL
AND the page SHALL have at least 1 [[Wiki/Tech]] cross-reference
AND the Wiki___Tech.md hub `### Index` SHALL gain a routing line:
    "[[Wiki/Tech/Redis]] -- In-memory data store, cache + pub/sub #redis"
AND the report SHALL show: 1 page created, 1 hub updated, N cross-refs added
```

### Scenario 2: Ingest updates existing page (append-only)

```
GIVEN a page Wiki___Tech___Strapi.md exists with content "Headless CMS for Node.js"
AND the page has updated:: 2026-03-01
WHEN the user runs /wiki-ingest "Strapi 5 uses documentId for PUT, not numeric id"
THEN the system SHALL append a new block to the existing page
AND the original content "Headless CMS for Node.js" SHALL still be present unchanged
AND updated:: SHALL be changed to [today]
AND the report SHALL show: 1 page updated
```

### Scenario 3: Credential detected in source - ingest blocked

```
GIVEN the user provides source text containing "api-key:: sk-abc123def456ghi789"
WHEN the system reaches Phase 4 (Quality Gate)
THEN the ingest SHALL be blocked
AND the system SHALL warn: "Credential pattern detected. Move to L1 memory, not wiki."
AND no wiki pages SHALL be created or modified
```

### Scenario 4: L1 candidate detected - recommend memory

```
GIVEN the user provides source text "PM2 reload does not work with npm start"
WHEN the system evaluates L1/L2 routing in Phase 1
THEN the system SHALL identify this as an L1 candidate (operational gotcha)
AND the system SHALL recommend: "This looks like an L1 rule. Consider saving to
    Memory instead of Wiki."
AND the system SHALL still proceed with wiki ingest if the user confirms
```

### Scenario 5: Page touch count below minimum

```
GIVEN a small source with one fact about an existing page
WHEN the ingest completes with only 2 page touches
THEN the system SHALL emit a warning: "Only 2 page touches (target: 5-15).
    Consider adding cross-references to related pages."
AND the ingest SHALL complete successfully (warning, not blocking)
```

### Scenario 6: Page touch count above maximum

```
GIVEN a complex source spanning 25 different topics
WHEN the ingest plan identifies 25 page operations
THEN the system SHALL emit a warning: "25 page touches exceeds target (5-15).
    Consider splitting this ingest into multiple runs."
AND the ingest SHALL complete successfully (warning, not blocking)
```

### Scenario 7: Hub page missing for new namespace child

```
GIVEN a hub page Wiki___Projects.md exists
AND no page Wiki___Projects___NewProject.md exists
WHEN the user ingests information about "NewProject"
THEN the system SHALL create Wiki___Projects___NewProject.md with required properties
AND the system SHALL append [[Wiki/Projects/NewProject]] to Wiki___Projects.md
```

### Scenario 8: Obsidian mode - YAML frontmatter format

```
GIVEN llm-wiki.yml is configured with tool: obsidian and wiki_path: /tmp/test-wiki
WHEN the user ingests a new technology "Milvus"
THEN the system SHALL create Wiki/Tech/Milvus.md
AND the file SHALL start with YAML frontmatter:
    ---
    type: entity
    entity-type: technology
    created: [today]
    updated: [today]
    status: active
    source: ingest
    ---
AND the content SHALL use standard markdown without "- " block prefixes
```

### Scenario 9: Max 3 pages loaded simultaneously

```
GIVEN an ingest source references 8 existing wiki pages
WHEN Phase 2 identifies all 8 as update targets
THEN the system SHALL read at most 3 pages at a time
AND process them in batches: read 3, update 3, read next 3, update next 2
AND all 8 pages SHALL be correctly updated after the ingest completes
```

### Scenario 10: Namespace depth violation

```
GIVEN a source describes an entity "Contact" under Wiki/Business/Clients/Acme
WHEN the ingest would create Wiki/Business/Clients/Acme/Contact (depth 4)
THEN the system SHALL NOT create the 4-level page
AND the system SHALL instead add "Contact" as a section within the
    Wiki/Business/Clients/Acme page
AND the report SHALL note: "Namespace depth limit (3) reached, content merged
    into parent page"
```

### Scenario 11: Interactive checkpoint (default mode)

```
GIVEN a source in raw/ and no --auto flag
WHEN ingest completes the page operation plan (Phase 2)
THEN the system pauses BEFORE any write and presents: planned page touches,
    the source's reliability rating with rationale, detected contradictions,
    and asks "what should I emphasize, skip, or route to L1?"
AND the user answers "skip the pricing details, emphasize the method"
THEN Phase 3 writes reflect that guidance
```

### Scenario 12: --auto drains the queue without prompts

```
GIVEN three sources in raw/ and the --auto flag
WHEN ingest runs
THEN no checkpoint prompt appears and all three sources are processed oldest-first
AND the report includes each source's plan and reliability rating
AND a quality-gate failure on source 2 still blocks source 2 (left in raw/)
```

### Scenario 13: Secret in source bytes blocks the archive

```
GIVEN a raw source file containing an API key string
AND the synthesized pages contain no credential
WHEN ingest reaches the pre-archive gate (REQ-045)
THEN the file is NOT moved into ingested/ and NOT committed
AND the warning names the match location and asks for redaction
AND the wiki pages written from the source are reported as pending re-ingest
```

### Scenario 14: Sensitive source type stays out of git

```
GIVEN sensitive_source_types: [notes] in llm-wiki.yml
AND a personal note in raw/ inferred as type notes
WHEN ingest completes
THEN wiki pages are written and source-file:: records ingested/notes/<file>
AND the moved file's path is gitignored; its bytes never enter git history
```

### Scenario 15: Daily Ingested block, second run same day

```
GIVEN journals_dir resolves to journals/ and today is 2026-07-06
AND journals/2026_07_06.md already has an Ingested block from a morning run:
    - Ingested
      - smith-2024 (papers) -> [[wiki/learning/spaced-repetition]]
        -
      - (user's own note written under the bullet)
WHEN /wiki-ingest processes clip-sanitation.md touching wiki/tech/sanitation
THEN the system SHALL append ONE bullet to the EXISTING Ingested block:
    "clip-sanitation (clippings) -> [[wiki/tech/sanitation]]" plus an empty
    child bullet for notes
AND SHALL NOT create a second Ingested block
AND SHALL NOT modify the morning bullets or the user's note (REQ-094)
AND wiki/tech/sanitation SHALL carry journal:: linking today's journal page
    (REQ-093, schema REQ-585c)
AND the journal edit SHALL be in the same commit as the page edits and the
    file move (REQ-095)
```

### Scenario 16: Voice note routes to the journal by default

```
GIVEN an unprocessed voice_notes row with a rambling 4-minute transcript
WHEN /wiki-ingest processes it as a voice source (a --auto flag is declined
    with a notice; the checkpoint always runs)
THEN the default plan is a 2-4 line summary on today's journal page with
    [[links]] and the provenance id archive.db:voice_notes/17
AND no wiki page is touched unless the user opts in per row
AND the row is marked processed only after the commit
```

### Scenario 17: People row requires individual confirmation

```
GIVEN the checkpoint plan contains a row updating a people page
WHEN the checkpoint presents the plan
THEN that row is shown with the FULL sentence to be written (no truncation)
AND it is confirmed individually - it can never ride a batch confirmation
AND declining it leaves the sentence in the journal summary or the transcript
```

### Scenario 18: Sensitive assessment is never promoted

```
GIVEN a transcript sentence assessing a named student's family situation
WHEN the user confirms that row at the checkpoint anyway
THEN the system SHALL NOT write it to any wiki page (REQ-085 overrides
    confirmation)
AND the content remains only in the transcript (archive.db)
AND the checkpoint states why the row was withheld
```

### Scenario 19: Data-package version update keeps old claims citable

```
GIVEN data_packages lists larnsce/sanitationdata and the vault holds
    ingested/data/sanitationdata-1.1.0/ with dataset pages stamped
    data-last-sync:: 1.1.0
AND a wiki page cites ingested/data/sanitationdata-1.1.0/toilets.csv
WHEN data_pkg_sync.R --check reports 1.2.0 on GitHub
AND the user runs /data-sync (dry-run reviewed, NEWS diff shown, confirmed)
THEN a NEW snapshot ingested/data/sanitationdata-1.2.0/ is written
AND the dataset pages' managed properties and description/data dictionary
    sections regenerate; the user's own note blocks are untouched (REQ-102)
AND the citing wiki page still points at the 1.1.0 path, which still exists
AND with data_snapshots_keep: 3 the oldest unreferenced snapshot beyond
    three is deleted; the cited 1.1.0 snapshot is NEVER deleted (REQ-105)
```

### Scenario 20: Chat-voice browse and conversation write nothing

```
GIVEN archive.db holds voice_notes rows 1 (processed) and 2 (unprocessed)
WHEN the user runs /wiki-chat-voice
THEN a picker lists both rows newest first, marked processed/unprocessed,
    each with its original filename (basename of audio_path), a runtime
    one-line description and 3-5 keywords
AND the browse persists nothing (archive.db bytes are unchanged)
AND after the user selects both and converses at length, no journal, page,
    or archive.db write happens before the closing checkpoint is confirmed
```

### Scenario 21: Chat-voice closing ingest cites notes, offers the flip

```
GIVEN the conversation covered rows 1 and 2 and surfaced one wiki-worthy
    claim grounded in row 2, plus one idea born purely in the discussion
WHEN the user says "wrap up"
THEN one checkpoint presents: the journal synthesis opening with the
    pipeline status line, the claim offered with
    cite:: archive.db:voice_notes/2 at reliability:: low, and a
    processed-flip offer for row 2 only (row 1 is already processed)
AND the discussion-born idea appears in the journal synthesis only; it is
    not offered as a wiki claim (REQ-1204)
AND row 2 is flipped only after the atomic commit succeeds
```

### Scenario 22: Transcript ingest - decisions medium, analysis low, bytes out of git

```
GIVEN raw/chat-2026-06-25-vault-design.md is a curated claude.ai chat export
AND llm-wiki.yml lists transcripts in source_types and sensitive_source_types
WHEN the user runs /wiki-ingest --auto
THEN the system states that transcript sources are interactive-only and runs
    the checkpoint anyway (REQ-1303)
AND the source's type infers as transcripts from the chat- prefix (REQ-1300)
AND the checkpoint offers each extracted decision individually with the full
    sentence(s); a decision the user confirms is written at
    reliability:: medium, while model-only analysis from the same chat rates
    low with a ## Pending Review entry (REQ-1302)
AND after confirmation the file moves to ingested/transcripts/, which is
    gitignored: the wiki pages and journal entry enter the atomic commit,
    the transcript bytes do not (REQ-1301, REQ-046)
```

---

## Acceptance Criteria

- [ ] All 5 phases execute in order (Analysis, Scan, Operations, Quality Gate, Report)
- [ ] URL, file path, and inline text sources all work
- [ ] New pages have ALL required properties per Schema
- [ ] Existing pages are never overwritten - only appended to
- [ ] Hub pages list all child pages after ingest
- [ ] Every created/updated active page has a routing line in its hub `### Index`
- [ ] Every touched page has at least 1 cross-reference
- [ ] Credential patterns block the ingest
- [ ] Source bytes are scanned pre-archive; a match leaves the file in raw/
- [ ] Default mode pauses at the checkpoint before any write; --auto does not
- [ ] Ingested claim blocks carry cite:: per specs/citations.md (v2.1, with #17)
- [ ] Page touch warnings are emitted but do not block
- [ ] Works correctly in both Logseq and Obsidian modes
- [ ] Max 3 pages loaded simultaneously during processing
- [ ] Namespace depth never exceeds 3 levels
- [ ] All dates use ISO 8601 format
- [ ] Each run appends to the day's single Ingested journal block; a second
      block is never created (REQ-090)
- [ ] Existing journal content, including the user's notes under earlier
      bullets, is never modified (REQ-094)
- [ ] Every touched page carries journal:: linking today's journal page
      (REQ-093)
- [ ] The journal edit rides the run's atomic commit (REQ-095)
- [ ] Data-package sync writes a versioned snapshot; old snapshots stay
      citable; managed sections regenerate while human sections survive
      (REQ-100..103)
- [ ] Snapshot retention never deletes a referenced snapshot (REQ-105)
- [ ] --check detects staleness without writing (REQ-106)
- [ ] Voice sources always run the checkpoint; --auto never applies to them (v3.0)
- [ ] Voice wiki writes are per-row opt-in; people rows are confirmed
      individually with the full sentence shown
- [ ] Assessments of people are never promoted out of the checkpoint (v3.0)
- [ ] Voice provenance uses archive.db:voice_notes/<id> and is capture-backed
      (schema REQ-586b, audit REQ-927)
- [ ] Chat-voice browse is read-only; runtime digests are never persisted
      (REQ-1200)
- [ ] The conversation phase writes nothing; every write goes through the
      single closing checkpoint (REQ-1202/1203)
- [ ] Promoted claims cite voice note ids only; the conversation is never a
      cite target and never raises reliability (REQ-1204)
- [ ] Processed flips are per-note opt-in and happen only post-commit
      (REQ-1205)

---

## Dependencies

- `llm-wiki.yml` must exist and be valid
- Schema page must exist in the wiki
- specs/l1-l2-routing.md defines the L1/L2 routing decision logic used in Phase 1
- specs/storage.md defines archive.db and the `voice_notes` table consumed by
  the Voice Sources section (v3.0)
