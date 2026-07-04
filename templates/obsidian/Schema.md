---
wiki-version: "1.0"
schema-spec-version: "2.0.0"
last-updated: "{{DATE}}"
maintained-by: llm-wiki
type: schema
---

# Wiki Schema

## Namespace Conventions

- Top-Level: {{NAMESPACES}}
- Page Naming: Title Case, hyphens for multi-word (`Wiki/Projects/My-Project`)
- Max Depth: 3 levels (e.g., `Wiki/Business/Clients/ClientName`)
- Hub Pages: Every namespace level has a hub page listing its children
- Folder Hierarchy: Namespaces map to folders (e.g., `Wiki/Tech/Docker.md`)

## Page Types and Required Properties

Every page declares exactly one type; the valid values are:

```yaml
type: entity | project | knowledge | feedback | hub
```

Pages that conform to this schema carry the contract version in their frontmatter:

```yaml
schema-spec-version: "2.0.0"
```

Pages WITHOUT the current schema-spec-version are treated as pre-2.0.0 by lint (grandfather mode): findings on them are reported one severity tier lower, except credential leaks, which always stay critical. `lint.py --strict` disables the floor.

### Entity (Person, Client, Tool, Service, Technology)

Required YAML frontmatter:

```yaml
type: entity
entity-type: person | client | tool | service | technology
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active | inactive | archived
source: memory-migration | ingest | manual
```

### Project

```yaml
type: project
status: active | completed | on-hold | cancelled
created: YYYY-MM-DD
updated: YYYY-MM-DD
started: YYYY-MM-DD
completed: YYYY-MM-DD  # if applicable
```

### Knowledge (Learning, Reference)

```yaml
type: knowledge
domain: tech | business | content | ops
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high | medium | low | stale
```

### Feedback (Lessons Learned, Gotchas)

```yaml
type: feedback
severity: critical | important | nice-to-know
created: YYYY-MM-DD
verified: YYYY-MM-DD
applies-to: []  # page references to affected systems
```

### Hub (Namespace Index)

```yaml
type: hub
namespace: Wiki/NamespaceName
```

## Provenance Properties (ingested pages)

Added by the source pipeline. YAML frontmatter on ingested pages (`source-file` and `reliability` are required on ingested pages; hand-written pages omit all of these):

```yaml
source-file: ingested/papers/smith-2024.md   # comma-separated path(s) into ingested/, plain text not a [[link]]
reliability: high | medium | low             # source QUALITY; page value = MINIMUM across its claims
last-reviewed: YYYY-MM-DD                    # optional: date a human last verified the page
s2-metrics: cites=120 influential=8 venue=... type=... year=2024  # optional: raw Semantic Scholar figures (or "none")
canonical-url: https://example.org/my-course # marks a deliberate stub whose source of truth is external
```

`s2-metrics` is OPTIONAL and present only when a Semantic Scholar MCP enriched the ingest. It is EVIDENCE that INFORMS the qualitative `reliability` decision; it does NOT set `reliability` by formula (no citation-count thresholds).

`canonical-url` marks a deliberate stub ("stub, don't ingest"): the page's source of truth is an external URL the user maintains. A stub with `canonical-url` carries NO `source-file` and is exempt from the ingested-page requirements above; lint rule 12 checks the URL still resolves.

NOTE: `source-file` is separate from the existing `source` property. `source` records the METHOD (memory-migration, ingest, or manual); `source-file` records WHICH origin file. Both may appear.

### Claim Citations (cite::)

Every non-common-knowledge factual claim block on an ingested page carries a `cite::` reference attached to the claim block itself, as an indented child bullet directly under the claim:

```markdown
- Solar capacity grew 24% in 2024.
  - cite:: ingested/papers/iea-2024.md#p12
```

- Value: one or more comma-separated refs. Each ref is a relative path into `ingested/` with an optional `#locator` (free-text page/section/table pointer, e.g. `#p12` or `#sec-3.2`), or a live-web ref `url:<https://...>`.
- Refs are plain text, NOT `[[links]]`: they point at source files, not wiki pages, and must not create graph nodes.
- Union invariant: the page's `source-file` equals the union of the page's ingested/ cite targets (paths only, locators stripped, deduplicated). Mechanically enforced by the ingest quality gate (`check_citations.py`).
- Exempt: common knowledge (field-standard definitions, widely-taught facts) and clearly-marked synthesis/opinion blocks. When unsure, cite; exemption is an audit-time judgment call, not a lint failure.
- Corroboration: refs on the same claim count as independent only when they originate from different sources (different authors, publishers, or datasets); two exports of one work are ONE source.
- Born cited: pages written by ingest carry `cite::` from creation (ingest REQ-033b, v2.1+). Pre-v2.1 pages without `cite::` are reported as coverage gaps, not blocking failures.

### Reliability Rubric (per source)

- **high**: peer-reviewed primary source or official standard/spec.
- **medium**: single secondary source, preprint, or expert blog post.
- **low**: speculative, anecdotal, forum/unverified, or model-generated without a source.

Corroboration works at CLAIM level: a claim supported by 2+ INDEPENDENT sources rated medium or better is high. Partial corroboration does not raise a claim. The page's `reliability` is the MINIMUM across its claims.

### Trust Axes: confidence vs reliability (do NOT conflate)

These are TWO SEPARATE, independently-set axes. Neither is derived from the other; lint NEVER auto-converts between them.

- The `confidence` property (existing) answers "is this content CURRENT and VERIFIED?" It follows the staleness lifecycle (goes stale when the `updated` date is 90+ days old).
- The `reliability` property answers "how GOOD were the SOURCES this rests on?"
- A page can be high confidence (recently verified by a human) yet low reliability (rests on a single weak source), and vice-versa. Set each on its own merits.

### Pending Review Convention

- Trigger: a page rests on a SINGLE source AND `reliability` is not `high`.
- Action: append a `## Pending Review` section listing the SPECIFIC claims that need corroboration (not the whole page).
- Resolution: when a corroborating source is later ingested, re-check each flagged claim, delete resolved ones, and if all clear, remove the section and recompute `reliability` (newly corroborated claims rate high; the page takes the minimum across its claims). Log the change.

### Source Lifecycle

- A source file lives in `raw/` while pending and is MOVED to `ingested/<type>/` once its knowledge has been written into wiki pages. Presence in `ingested/` = processed. The move is the atomic provenance commit.
- Source files are immutable: the wiki reads from them and links to them by path, but never edits them.
- `raw/` and `ingested/` live BESIDE the vault pages, so Obsidian does not render sources as wiki pages.

## Cross-Reference Rules

- Every wiki page MUST have at least one `[[Wiki/...]]` link to another wiki page
- Hub pages MUST list ALL child pages in their namespace
- When a page mentions an entity that has its own page, use `[[Wiki/Entity/Name]]` link syntax
- Tags: use `#tag` for lightweight categorization (e.g., `#docker`, `#deploy`, `#critical`)
- External links: `[Text](URL)` for URLs outside the wiki

## Content Format Rules

- Flat Markdown (no outliner `- ` prefix required on every line)
- Properties: YAML frontmatter between `---` fences at the top of the file
- Sections: standard `## Heading` syntax
- Code blocks: fenced with triple backticks
- NEVER store credentials, passwords, or API tokens in wiki pages

## L1/L2 Architecture

### L1 = Claude Memory (auto-loaded every session)

- Feedback rules and quick gotchas
- User identity (name, preferences)
- Credentials (MUST NEVER go into the wiki)
- Everything Claude needs to know at the START of every session

### L2 = Wiki (on-demand via `/wiki-query`)

- Projects and their details
- Workflows and processes
- Research and learning notes
- Deep technical knowledge
- Business intelligence and strategy

### Boundary Rules

- New quick rule or gotcha discovered? --> Save to Claude Memory (L1)
- New project, workflow, or research? --> Save to Wiki (L2)
- Same info in L1 AND L2? --> Warning on `/wiki-lint`

## Ingest Workflow

1. Analyze new source --> extract entities, facts, relationships
2. Identify affected wiki pages (existing + new)
3. Target: 5-15 page touches per ingest
4. Create new pages with all required properties
5. Existing pages: APPEND, never overwrite
6. Update hub pages
7. Add cross-references
8. Set `updated` property on all changed pages

<!-- canon:lint-rules start -->
## Lint Rules

12 rules (openspec/specs/lint.md). The mechanical subset runs via `lint.py`; rules 2 and 9 plus all quality judgments run agent-side in the wiki-lint skill. Fixes are only ever applied agent-side after confirmation.

- **Rule 1 Orphan Detection** (REQ-110): pages with 0 incoming `[[links]]`; hub and system pages exempt
- **Rule 2 Stale Detection** (REQ-120): updated date more than 90 days old AND high confidence
- **Rule 3 Missing Properties** (REQ-130): pages missing type-specific required properties, or property values outside the allowed lists
- **Rule 4 Broken References** (REQ-140): `[[links]]` to non-existent pages
- **Rule 5 Hub Completeness** (REQ-150): hub pages missing children in their namespace
- **Rule 6 Credential Leak** (REQ-160): credential-shaped property patterns (token, password, secret, api-key) and long base64 runs; CRITICAL, never auto-fixed
- **Rule 7 Empty Pages** (REQ-170): pages with only properties, no content
- **Rule 8 Cross-Ref Minimum** (REQ-180): pages with fewer than 1 outgoing `[[link]]`
- **Rule 9 L1/L2 Duplicates** (REQ-190): same info in Memory AND Wiki
- **Rule 10 Index Drift** (REQ-193): orphaned routing lines, unroutable active pages, empty routing descriptions
- **Rule 11 Archived-in-Live-Index** (REQ-197): archived pages whose routing line still sits in the hub `### Index`
- **Rule 12 External Link Rot** (REQ-220): canonical-url targets that no longer resolve; URL-shape check by default, real HTTP check with `--check-urls`
<!-- canon:lint-rules end -->

## Conventions

- Language: English (customize per project)
- Dates: ISO 8601 (YYYY-MM-DD)
