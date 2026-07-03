---
wiki-version: "1.0"
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

<!-- larnsce:provenance start -->
## Provenance Properties (ingested pages)

Added by the source pipeline. YAML frontmatter on ingested pages (`source-file` and `reliability` are required on ingested pages; hand-written pages omit all of these):

```yaml
source-file: ingested/papers/smith-2024.md   # comma-separated path(s) into ingested/, plain text not a [[link]]
reliability: high | medium | low             # source QUALITY; page value = MINIMUM across its claims
last-reviewed: YYYY-MM-DD                     # optional: date a human last verified the page
s2-metrics: cites=120 influential=8 venue=... type=... year=2024  # optional: raw Semantic Scholar figures (or "none")
```

`s2-metrics` is OPTIONAL and present only when a Semantic Scholar MCP enriched the ingest. It is EVIDENCE that INFORMS the qualitative `reliability` decision; it does NOT set `reliability` by formula (no citation-count thresholds).

NOTE: `source-file` is separate from the existing `source` property. `source` records the METHOD (memory-migration | ingest | manual); `source-file` records WHICH origin file. Both may appear.

### Reliability Rubric (per source)

- **high**: peer-reviewed primary source or official standard/spec.
- **medium**: single secondary source, preprint, or expert blog post.
- **low**: speculative, anecdotal, forum/unverified, or model-generated without a source.

Corroboration works at CLAIM level: a claim supported by 2+ INDEPENDENT sources rated medium or better is high. Partial corroboration does not raise a claim. The page's `reliability` is the MINIMUM across its claims.

### Trust Axes: confidence vs reliability (do NOT conflate)

These are TWO SEPARATE, independently-set axes. Neither is derived from the other; lint NEVER auto-converts between them.

- `confidence` (existing — high | medium | low | stale) answers "is this content CURRENT and VERIFIED?" It follows the staleness lifecycle (goes `stale` when `updated` is 90+ days old).
- `reliability` (new — high | medium | low) answers "how GOOD were the SOURCES this rests on?"
- A page can be `confidence: high` (recently verified by a human) yet `reliability: low` (rests on a single weak source), and vice-versa. Set each on its own merits.

### Pending Review Convention

- Trigger: a page rests on a SINGLE source AND `reliability` is not `high`.
- Action: append a `## Pending Review` section listing the SPECIFIC claims that need corroboration (not the whole page).
- Resolution: when a corroborating source is later ingested, re-check each flagged claim, delete resolved ones, and if all clear, remove the section and recompute `reliability` (newly corroborated claims rate high; the page takes the minimum across its claims). Log the change.

### Source Lifecycle

- A source file lives in `raw/` while pending and is MOVED to `ingested/<type>/` once its knowledge has been written into wiki pages. Presence in `ingested/` = processed. The move is the atomic provenance commit.
- Source files are immutable: the wiki reads from them and links to them by path, but never edits them.
- `raw/` and `ingested/` live BESIDE the vault pages, so Obsidian does not render sources as wiki pages.
<!-- larnsce:provenance end -->

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

### L2 = Wiki (on-demand via `/wiki query`)

- Projects and their details
- Workflows and processes
- Research and learning notes
- Deep technical knowledge
- Business intelligence and strategy

### Boundary Rules

- New quick rule or gotcha discovered? --> Save to Claude Memory (L1)
- New project, workflow, or research? --> Save to Wiki (L2)
- Same info in L1 AND L2? --> Warning on `/wiki lint`

## Ingest Workflow

1. Analyze new source --> extract entities, facts, relationships
2. Identify affected wiki pages (existing + new)
3. Target: 5-15 page touches per ingest
4. Create new pages with all required properties
5. Existing pages: APPEND, never overwrite
6. Update hub pages
7. Add cross-references
8. Set `updated` property on all changed pages

## Lint Rules

- **Orphan Detection**: Pages with 0 incoming [[links]] (hub pages excluded)
- **Stale Detection**: `updated` > 90 days old AND `confidence: high`
- **Missing Properties**: Pages missing type-specific required properties
- **Broken References**: [[links]] to non-existent pages
- **Hub Completeness**: Hub pages missing children in their namespace
- **Credential Leak**: Scan for token/password/secret patterns
- **Empty Pages**: Only properties, no content
- **Cross-Ref Minimum**: Pages with fewer than 1 outgoing [[link]]
- **L1/L2 Duplicates**: Same info in Memory AND Wiki

## Conventions

- Language: English (customize per project)
- Dates: ISO 8601 (YYYY-MM-DD)
