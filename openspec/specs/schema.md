# Spec: Schema - Page Types, Properties & Validation

## Description

The schema defines the structural contract for all wiki pages. Every page has a type,
every type has required properties with allowed values, and every page must follow
tool-specific formatting rules. The schema is enforced during ingest (creation) and
lint (validation).

---

## Requirements

### Page Types (Mutually Exclusive)

- REQ-500: Every wiki page MUST declare exactly one `type` property. Valid values:
  `entity`, `project`, `knowledge`, `feedback`, `hub`.
- REQ-501: A page MUST NOT have multiple types. The type is immutable after creation.
- REQ-502: A page with an unrecognized type value SHALL be flagged by lint as
  "unknown type".

### Entity Type

- REQ-510: Entity pages MUST have ALL of these properties:
  - `type` = `entity`
  - `entity-type` = one of: `person`, `client`, `tool`, `service`, `technology`
  - `created` = date (YYYY-MM-DD)
  - `updated` = date (YYYY-MM-DD)
  - `status` = one of: `active`, `inactive`, `archived`
  - `source` = one of: `memory-migration`, `ingest`, `manual`
- REQ-511: An `entity-type` value not in the allowed list SHALL be flagged by lint.
- REQ-512: A `status` value not in the allowed list SHALL be flagged by lint.
- REQ-513: When an entity represents both a person and a client, `entity-type`
  SHALL be set to the primary role (`person` if individual, `client` if business
  relationship is primary).

### Project Type

- REQ-520: Project pages MUST have ALL of these properties:
  - `type` = `project`
  - `status` = one of: `active`, `completed`, `on-hold`, `cancelled`
  - `created` = date (YYYY-MM-DD)
  - `updated` = date (YYYY-MM-DD)
  - `started` = date (YYYY-MM-DD)
- REQ-521: Project pages MAY have an optional `completed` date property.
- REQ-522: If `status` is `completed`, the page SHOULD have a `completed` date.
  Lint MAY flag a completed project without a `completed` date as info-level.

### Knowledge Type

- REQ-530: Knowledge pages MUST have ALL of these properties:
  - `type` = `knowledge`
  - `domain` = one of: `tech`, `business`, `content`, `ops`
  - `created` = date (YYYY-MM-DD)
  - `updated` = date (YYYY-MM-DD)
  - `confidence` = one of: `high`, `medium`, `low`, `stale`
- REQ-531: A `domain` value not in the allowed list SHALL be flagged by lint.
- REQ-532: When knowledge spans multiple domains, `domain` SHALL be set to the
  primary domain. There is no multi-domain value.
- REQ-533: The `confidence` property follows this lifecycle:
  - `high` → verified, reliable, up-to-date
  - `medium` → probably correct, verify on next ingest
  - `low` → uncertain, incomplete, or limited sources
  - `stale` → was high/medium but `updated` is 90+ days old

### Feedback Type

- REQ-540: Feedback pages MUST have ALL of these properties:
  - `type` = `feedback`
  - `severity` = one of: `critical`, `important`, `nice-to-know`
  - `created` = date (YYYY-MM-DD)
  - `verified` = date (YYYY-MM-DD)
  - `applies-to` = one or more page references
- REQ-541: `severity` determines L1 candidacy:
  - `critical` → almost always belongs in L1 Memory
  - `important` → sometimes belongs in L1 Memory
  - `nice-to-know` → rarely belongs in L1 Memory
- REQ-542: `verified` tracks the last date this feedback was confirmed still valid.
  It is distinct from `updated` (content change) - a page can be verified without
  changing content.

### Hub Type

- REQ-550: Hub pages MUST have ALL of these properties:
  - `type` = `hub`
  - `namespace` = the namespace path (e.g., `Wiki/Tech`)
- REQ-551: Hub pages are structural (navigation), not knowledge-bearing. They
  list child pages in their namespace.
- REQ-552: Hub pages are exempt from orphan detection (they are entry points).
- REQ-553: Hub pages MUST still have at least 1 outgoing `[[Wiki/...]]` link
  (typically links to their child pages).
- REQ-554: Every namespace MUST have exactly one hub page.
- REQ-555: Each hub page MUST carry an `### Index` section: one **routing line** per
  active child page, formatted `[[Wiki/NS/Page]] -- <description, <=120 chars> #tags`.
  This index is the retrieval entry point read by `/wiki-query` Phase 0 (two-stage routing).
- REQ-556: Each hub page MAY carry an `### Archive` section holding the routing lines of
  demoted (cold) child pages. Lint flags an active page in `### Archive`, or a demoted
  page (see Archived Pages) still in `### Index`.
- REQ-557: The hub's child list under `### Index` IS the routing index - there is no
  separate index file. A description after the `--` separator is REQUIRED (it is the
  routing key); an empty description SHALL be flagged by lint.

### Archived / Demoted Pages

- REQ-565: A page demoted by `/wiki-maintain prune` SHALL be marked with the optional property
  `archived:: <date>` (the date it was evicted from the live index). The presence of
  `archived::` is the canonical "demoted" marker, valid on ANY page type.
- REQ-566: For pages whose `status` enum allows it (Entity: `active|inactive|archived`),
  `status::` SHOULD additionally be set to `archived`. For types whose `status` enum does
  NOT include `archived` (Project, Knowledge), ONLY the `archived::` property is added -
  the type's `status` value MUST NOT be set to an out-of-enum value.
- REQ-567: Demotion SHALL NOT rename or move the page file. The tool links by page name,
  so a move would break incoming `[[links]]`. A demoted page keeps its filename and
  location; only its routing line moves from the hub `### Index` to `### Archive`.
- REQ-568: A demoted page remains greppable as an L3 fallback. If `/wiki-query` reads it
  again, the system SHOULD offer to re-promote it (routing line back to `### Index`,
  `archived::` removed).

### Access-Log Page

- REQ-569: The wiki SHALL contain a system page `Wiki/Reference/Access-Log` with
  properties `access-log:: true` and `type:: reference`, holding an append-only `## Log`
  block. `/wiki-query` appends one line per full-page read; `/wiki-maintain prune` reads it to
  compute last-access per page. This page is EXEMPT from orphan, stale, and demote rules.

### Date Validation

- REQ-560: All date properties MUST use ISO 8601 format: `YYYY-MM-DD`.
- REQ-561: Dates MUST be zero-padded: `2026-04-01`, not `2026-4-1`.
- REQ-562: Dates with slashes (`2026/04/01`), dots (`2026.04.01`), or other
  separators SHALL be flagged as invalid.
- REQ-563: The system SHOULD validate that dates are real calendar dates
  (e.g., `2026-02-30` is invalid).

### Cross-Reference Rules

- REQ-570: Every non-hub page MUST have at least 1 outgoing `[[Wiki/...]]` link.
- REQ-571: Hub pages MUST list ALL child pages that exist in their namespace.
- REQ-572: When a page mentions an entity that has its own wiki page, it SHOULD
  use `[[Wiki/...]]` link syntax instead of plain text.
- REQ-573: Every non-hub page SHOULD end with a `## Cross-References` section
  (Obsidian) or `- ## Cross-References` section (Logseq) listing key outgoing links.
- REQ-574: Link syntax is `[[Wiki/Namespace/Page]]` in both Logseq and Obsidian.
  Backlinks are automatic in both tools.

### Namespace Conventions

- REQ-580: Structural namespace names MUST be lowercase: `wiki/tech`, not `Wiki/Tech`
  or `wiki/Tech`. This applies to every structural segment of a page name (the
  namespace levels and any non-proper-noun leaf).
- REQ-580a: The word separator inside a structural segment is the ASCII hyphen
  `U+002D` ONLY. Structural segments MUST NOT contain spaces, underscores, en dashes
  (`U+2013`), or em dashes (`U+2014`); lookalike dashes are invisible grep traps.
- REQ-580b: Proper-noun-leaf exemption: a LEAF segment that names a person, tool,
  paper, or `@citekey` keeps its natural casing and spelling, written as the world
  writes it: `wiki/tools/Claude Code`, `notes/literature/@Forte2022`. The exemption
  applies to the leaf only; the structural segments before it stay lowercase.
- REQ-580c: The corpus rename `Wiki/` → `wiki/` is executed by the migration
  converter (`migrate_wiki.py`, issue #25), not by hand. Pre-migration corpora that
  still use Title Case names are covered by the grandfather floor (pages without the
  current `schema-spec-version` are reported one severity tier lower); their names
  are not a blocking failure.
- REQ-581: Multi-word structural names MUST use hyphens: `wiki/projects/blog-series`,
  not `wiki/projects/blog_series` or `wiki/projects/blog series`.
- REQ-582: Namespace depth MUST NOT exceed 3 levels. `wiki/business/clients/Acme`
  (3 levels) is the maximum. A 4th level is not allowed.
- REQ-583: File names MUST follow tool conventions:
  - Logseq: `wiki___<namespace>___<page>.md` (triple-underscore, flat directory)
  - Obsidian: `wiki/<namespace>/<page>.md` (directory hierarchy)

### Stub Pages (external source of truth)

- REQ-584: A `reference` or `knowledge` page whose source of truth is an external
  URL the user maintains (e.g. their own Quarto site or blog series) MAY carry a
  `canonical-url::` property with that URL ("stub, don't ingest"). A page with
  `canonical-url::` is a deliberate stub: it SHALL NOT carry `source-file::` and is
  exempt from ingested-page requirements (REQ-585/586). Lint SHALL check that
  `canonical-url::` targets still resolve (specs/lint.md Rule 12).

### Provenance & Trust (source pipeline)

- REQ-585: An ingested page (one written from a source in the `raw/`/`ingested/`
  pipeline) SHALL carry a `source-file::` property: comma-separated relative path(s)
  into `ingested/` (e.g. `ingested/papers/smith-2024.md`). It is plain text, NOT a
  `[[link]]`. Hand-written pages omit it. `source-file::` is distinct from the existing
  `source::` property: `source::` records the METHOD (memory-migration | ingest | manual),
  `source-file::` records WHICH origin file.
- REQ-585a (author provenance, v3.x #73): An ingested page MAY carry an
  OPTIONAL `author::` property: comma-separated person names, plain text,
  recording the source's author(s) as structured metadata. Optional because
  not every source has a meaningful author (datasets, organization pages).
  On corroborating updates the value is a UNION (append new authors,
  deduplicated), like `source-file::`. Lint recognizes it and never
  requires it; ingest never backfills it onto existing pages (same rule as
  the schema-spec-version stamp).
- REQ-586: An ingested page SHALL carry a `reliability::` property, one of
  `high | medium | low`, rating the QUALITY of its sources. Hand-written pages
  (no `source-file::`) omit it. Reliability is assessed per CLAIM and rolled up
  to the page:
  - Per-source rubric: `high` = peer-reviewed primary / official standard;
    `medium` = single secondary / preprint / expert post; `low` = speculative /
    anecdotal / forum / model-only.
  - Personal synthesis = `medium`: a source promoted from the human-owned `para/`
    or `notes/` namespaces (specs/namespaces.md, promotion seam) rates `medium`
    by default, UNLESS its claims carry external citations that justify a higher
    rating under this rubric. This is the single normative statement of that
    default; other specs cite it rather than restate it.
  - Claim level: a claim supported by 2+ INDEPENDENT sources rated `medium` or
    better is `high` (corroboration). Otherwise the claim takes its source's
    rubric rating; partial corroboration does not raise it.
  - Page level: `reliability::` is the MINIMUM across the page's claims (most
    conservative roll-up).
  Worked example: two independent `medium` sources corroborating the SAME claim
  make that claim `high`; if the page's only other claim rests on a single `low`
  source, the page is `reliability:: low`.
- REQ-586a: An ingested page MAY carry an OPTIONAL `s2-metrics::` property recording raw
  Semantic Scholar figures verbatim (e.g. `cites=<n> influential=<n> venue=<...> type=<...>
  year=<...>`), or the value `none`. It is present only when a Semantic Scholar MCP enriched
  the ingest. `s2-metrics::` is ADVISORY: it informs the qualitative `reliability::` judgment
  (REQ-586) but MUST NOT be used to derive `reliability::` by formula or citation-count
  threshold. The qualitative rubric remains the decision.
- REQ-586b (capture-backed provenance): A claim whose provenance is an archive.db
  row (a `source-file::`/`cite::` ref of shape `archive.db:voice_notes/<id>`,
  specs/ingest.md Voice Sources) is CAPTURE-BACKED: raw capture, not a vetted
  source. A transcript is what was said, not a source for what is true.
  Capture-backed claims default to `reliability:: low` (they rate with the
  speculative/anecdotal tier of the REQ-586 rubric), and the page roll-up applies
  as usual. Raising a capture-backed claim above `low` SHALL require a real
  source ingested through the normal pipeline (`raw/` to `ingested/`) that
  supports the claim: a transcript cannot corroborate itself, and multiple voice
  notes from the same speaker count as ONE source for REQ-586 corroboration.
  This is the single normative statement of the capture-backed default; other
  specs (ingest, audit, storage) cite it rather than restate it.
- REQ-587: `confidence::` (REQ-530/533) and `reliability::` (REQ-586) are TWO SEPARATE
  axes and MUST NOT be cross-derived. `confidence::` answers "is this content current and
  verified" (and follows the 90-day staleness lifecycle); `reliability::` answers "how good
  were the sources". A page MAY be `confidence:: high` with `reliability:: low` or the
  reverse. Lint SHALL NOT auto-convert one into the other.
- REQ-588: When a page rests on a SINGLE source AND `reliability::` is not `high`, the
  page SHALL carry a `## Pending Review` section listing the SPECIFIC claims that need
  corroboration. When a corroborating source is later ingested, resolved claims SHALL be
  removed; when all are resolved the section SHALL be removed and `reliability::`
  recomputed per REQ-586 (newly corroborated claims rate `high`; the page takes the
  minimum across its claims).
- REQ-589: A source file SHALL live in `raw/` while pending and be MOVED to
  `ingested/<type>/` once its knowledge is written into wiki pages. Presence in
  `ingested/` means processed; the move is the atomic provenance commit. Source files are
  immutable (read and linked by path, never edited). `raw/` and `ingested/` live BESIDE
  the pages directory, keeping sources out of the pages tree; keeping them out of the
  tool's index additionally requires the tool-side exclusion (Logseq `:hidden`,
  specs/setup.md REQ-787; Obsidian Excluded files).

### Tool-Specific Format Rules

- REQ-590: In Logseq mode, every line of wiki BODY content MUST start with `- `
  (outliner block prefix). The page-property block at the top of the file is the
  one exception (REQ-591).
- REQ-591: In Logseq mode, properties MUST use inline syntax: `property:: value`.
  YAML frontmatter is NOT allowed. PAGE properties SHALL be written as unbulleted
  `property:: value` lines at the top of the file followed by one blank line,
  matching what the Logseq app itself writes (a bulleted page-property block is
  normalized by the app on first open, producing spurious diffs). BLOCK
  properties (e.g. `cite::`) remain continuation lines under their block.
  Readers SHALL accept both the bulleted and unbulleted page-property shapes
  (pre-v2.3 pages are bulleted).
- REQ-592: In Obsidian mode, properties MUST be in YAML frontmatter
  (between `---` fences at the top of the file).
- REQ-593: In Obsidian mode, content uses standard markdown. The `- ` block
  prefix is NOT required.
- REQ-594: In Logseq mode, headings go inside blocks: `- ## Section Name`.
  In Obsidian mode, headings use standard markdown: `## Section Name`.
- REQ-595: Mixing tool formats (e.g., Logseq outliner syntax in an Obsidian wiki)
  SHALL be flagged by lint.

---

## Scenarios

### Scenario 1: Valid entity page - all properties correct

```
GIVEN the configured tool is logseq
WHEN a page is created with:
    - type:: entity
    - entity-type:: technology
    - created:: 2026-04-10
    - updated:: 2026-04-10
    - status:: active
    - source:: ingest
AND the page has content blocks and at least 1 [[Wiki/...]] link
THEN lint SHALL report no issues for this page
```

### Scenario 2: Missing required property

```
GIVEN an entity page Wiki/Tech/Redis exists with:
    - type:: entity
    - entity-type:: technology
    - created:: 2026-04-10
    (missing: updated, status, source)
WHEN lint runs
THEN the system SHALL flag 3 missing properties: updated, status, source
AND report severity: warning
```

### Scenario 3: Invalid entity-type value

```
GIVEN a page has entity-type:: framework
WHEN lint runs
THEN the system SHALL flag: "Invalid entity-type 'framework'.
    Allowed: person, client, tool, service, technology"
```

### Scenario 4: Invalid date format

```
GIVEN a page has created:: 2026-4-1
WHEN lint runs
THEN the system SHALL flag: "Invalid date format '2026-4-1'.
    Required: YYYY-MM-DD (zero-padded)"
```

### Scenario 5: Logseq syntax in Obsidian wiki

```
GIVEN the configured tool is obsidian
AND a page starts with "- type:: knowledge" (Logseq outliner syntax)
    instead of YAML frontmatter
WHEN lint runs
THEN the system SHALL flag: "Page uses Logseq outliner format but wiki
    is configured for Obsidian. Properties should be in YAML frontmatter."
```

### Scenario 6: Namespace depth exceeded

```
GIVEN someone attempts to create Wiki/Business/Clients/Acme/Contact
    (4 levels deep)
WHEN the system validates the namespace
THEN it SHALL reject the page: "Namespace depth 4 exceeds maximum of 3.
    Add 'Contact' as a section within Wiki/Business/Clients/Acme instead."
```

### Scenario 7: Hub page missing namespace property

```
GIVEN a page has type:: hub but no namespace:: property
WHEN lint runs
THEN the system SHALL flag: "Hub page missing required property: namespace"
```

### Scenario 8: Completed project without completed date

```
GIVEN a project page has status:: completed but no completed:: property
WHEN lint runs
THEN the system SHALL flag at info level: "Project is completed but has
    no completed:: date. Consider adding one."
AND this SHALL NOT be treated as a warning or error
```

### Scenario 9: Cross-reference section missing

```
GIVEN a knowledge page has 2 outgoing [[Wiki/...]] links in the body
BUT does not have a ## Cross-References section at the end
WHEN lint runs
THEN the system SHOULD flag at info level: "Page has no Cross-References
    section. Consider adding one for clarity."
AND this SHALL NOT be treated as a warning (outgoing links exist)
```

### Scenario 10: Multi-domain knowledge - primary domain chosen

```
GIVEN a page covers both Strapi configuration (tech) and content publishing (content)
WHEN the user creates the page during ingest
THEN domain:: SHALL be set to the PRIMARY domain (e.g., tech if the page
    is mostly about Strapi configuration)
AND the system SHALL NOT create two pages or use a multi-domain value
```

---

## Acceptance Criteria

- [ ] All 5 page types have clearly defined required properties
- [ ] All property values have explicit allowed-value lists
- [ ] Date format strictly enforced (YYYY-MM-DD, zero-padded)
- [ ] Entity-type, status, domain, confidence, severity validated against enums
- [ ] Cross-reference minimum (1 outgoing link) enforced
- [ ] Hub completeness (all children listed) enforced
- [ ] Namespace depth (max 3) enforced
- [ ] Tool-specific format rules enforced (Logseq outliner vs Obsidian flat)
- [ ] Format mixing flagged (Logseq syntax in Obsidian wiki or vice versa)
- [ ] Works with both Logseq and Obsidian property syntax

---

## Dependencies

- specs/lint.md rules 1-9 enforce these schema constraints
- specs/ingest.md Phase 3 creates pages according to these rules
- specs/config.md determines tool mode (Logseq vs Obsidian)
- specs/namespaces.md (v2.2) binds the promotion seam to the personal-synthesis
  rubric case (REQ-586) and consumes the naming rules (REQ-580..583)
- specs/storage.md and specs/ingest.md (Voice Sources, v3.0) define the
  archive.db capture ref whose reliability default is REQ-586b; specs/audit.md
  REQ-927 reports such claims as capture-backed
