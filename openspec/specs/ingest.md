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
  Logseq (outliner with `- ` prefix, `property:: value`) or Obsidian (flat markdown,
  YAML frontmatter).
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

### Cross-Cutting

- REQ-060: The system MUST NOT modify any non-wiki pages (existing Logseq journals,
  personal notes, other vault content).
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
  specs/storage.md REQ-1140.
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

### Scenario 15: Voice note routes to the journal by default

```
GIVEN an unprocessed voice_notes row with a rambling 4-minute transcript
WHEN /wiki-ingest processes it as a voice source (a --auto flag is declined
    with a notice; the checkpoint always runs)
THEN the default plan is a 2-4 line summary on today's journal page with
    [[links]] and the provenance id archive.db:voice_notes/17
AND no wiki page is touched unless the user opts in per row
AND the row is marked processed only after the commit
```

### Scenario 16: People row requires individual confirmation

```
GIVEN the checkpoint plan contains a row updating a people page
WHEN the checkpoint presents the plan
THEN that row is shown with the FULL sentence to be written (no truncation)
AND it is confirmed individually - it can never ride a batch confirmation
AND declining it leaves the sentence in the journal summary or the transcript
```

### Scenario 17: Sensitive assessment is never promoted

```
GIVEN a transcript sentence assessing a named student's family situation
WHEN the user confirms that row at the checkpoint anyway
THEN the system SHALL NOT write it to any wiki page (REQ-085 overrides
    confirmation)
AND the content remains only in the transcript (archive.db)
AND the checkpoint states why the row was withheld
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
- [ ] Voice sources always run the checkpoint; --auto never applies to them (v3.0)
- [ ] Voice wiki writes are per-row opt-in; people rows are confirmed
      individually with the full sentence shown
- [ ] Assessments of people are never promoted out of the checkpoint (v3.0)
- [ ] Voice provenance uses archive.db:voice_notes/<id> and is capture-backed
      (schema REQ-586b, audit REQ-927)

---

## Dependencies

- `llm-wiki.yml` must exist and be valid
- Schema page must exist in the wiki
- specs/l1-l2-routing.md defines the L1/L2 routing decision logic used in Phase 1
- specs/storage.md defines archive.db and the `voice_notes` table consumed by
  the Voice Sources section (v3.0)
