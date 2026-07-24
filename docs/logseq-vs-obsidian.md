# Logseq vs. Obsidian

llm-wiki supports both Logseq and Obsidian as the wiki UI layer. This document explains the differences, helps you choose, and provides migration paths if you switch later.

## Why Both?

The LLM wiki pattern is fundamentally about structured markdown files with cross-references. Both Logseq and Obsidian operate on local markdown files, render `[[wikilinks]]`, and provide graph views. The *pattern* is the same -- the *format* differs.

Supporting both means you can use whichever tool fits your workflow. If you prefer outliner-style editing and block-level granularity, use Logseq. If you prefer flat markdown and a rich plugin ecosystem, use Obsidian. The wiki's value is in the knowledge, not the renderer.

## Feature Comparison

| Feature | Logseq | Obsidian |
|---------|--------|----------|
| **Data format** | Outliner (every line is `- ` prefixed) | Flat markdown |
| **Properties** | `property:: value` (inline) | YAML frontmatter |
| **File structure** | Flat directory, namespaces in filename (`wiki___tech___Strapi.md`) | Nested directories (`wiki/tech/Strapi.md`) |
| **Links** | `[[wiki/tech/Strapi]]` | `[[wiki/tech/Strapi]]` |
| **Backlinks** | Built-in, automatic | Built-in, automatic |
| **Graph view** | Yes | Yes |
| **Block references** | Native (every block has a UUID) | Via plugin or block-id |
| **Plugin ecosystem** | Growing, smaller | Massive, 1000+ plugins |
| **Mobile app** | Yes (beta quality) | Yes (solid) |
| **Sync** | Logseq Sync or git | Obsidian Sync, git, or any file sync |
| **License** | AGPL-3.0 (open source) | Proprietary (free for personal use) |
| **Local-first** | Yes, always | Yes, always |
| **Pricing** | Free (Sync is paid) | Free for personal, paid for commercial |

## When to Choose Logseq

Logseq is the better choice when:

**The LLM does most of the writing.** Logseq's outliner format means every block (line) is independently addressable. When the LLM appends new content to a page, it adds new blocks without touching existing ones. In flat markdown, appending content requires understanding the document structure -- where does the new paragraph go? After which heading? The outliner format makes this unambiguous.

**You want block-level granularity.** In Logseq, you can reference, embed, and link to individual blocks. This is powerful for a wiki where specific facts need to be cited across multiple pages.

**You value open source.** Logseq is AGPL-3.0 licensed. You can audit the code, contribute, and know that your tool will not disappear behind a paywall. For a knowledge base that might contain sensitive information, the ability to verify what the software does matters.

**You prefer a daily journal workflow.** Logseq's journal pages are first-class. If you like capturing thoughts in a daily log and then extracting wiki-worthy knowledge via `/wiki-ingest`, Logseq's journal integration makes this natural.

## When to Choose Obsidian

Obsidian is the better choice when:

**You do a lot of manual editing.** Flat markdown is more natural to write by hand. No `- ` prefix on every line, standard heading syntax, and YAML frontmatter that most developers already know. If you split your time between LLM-generated and hand-written content, Obsidian's format is less friction.

**You need specific plugins.** Obsidian's plugin ecosystem is massive. Dataview for database-like queries, Kanban for project boards, Calendar for timeline views, Templater for advanced templates. If your workflow depends on specific functionality, Obsidian probably has a plugin for it.

**You want polished mobile editing.** Obsidian's mobile app is more mature. If you frequently edit wiki pages from your phone, this matters.

**You prefer nested directories.** Obsidian stores files in a directory hierarchy that mirrors the namespace structure: `wiki/tech/Strapi.md`. This makes browsing the wiki in any file manager intuitive. Logseq's flat directory with triple-underscore filenames (`wiki___tech___Strapi.md`) is less readable at the filesystem level.

**Your team uses Obsidian.** If you are introducing the wiki pattern to a team and they already use Obsidian, the lower switching cost wins.

## Format Differences in Detail

### Properties

**Logseq** uses inline property syntax: unbulleted `property:: value` lines at the top of the page, followed by one blank line (this is the shape the Logseq app itself writes; pre-v2.3 pages with `- `-bulleted properties still parse):

```markdown
type:: knowledge
domain:: tech
confidence:: high
created:: 2026-03-15
updated:: 2026-04-07

- ## Topic Title
  - Content goes here as indented blocks.
```

**Obsidian** uses YAML frontmatter:

```markdown
---
type: knowledge
domain: tech
confidence: high
created: 2026-03-15
updated: 2026-04-07
---

## Topic Title

Content goes here as regular markdown.
```

### Content Structure

**Logseq** -- every line is a block, hierarchy via indentation:

```markdown
- ## Deployment Pipeline
  - CI/CD workflow for production.
  - ### Steps
    - 1. Run test suite
    - 2. Build production bundle
    - 3. Upload to server
    - 4. Restart process manager
  - ### Known Issues
    - Process manager reload does not work for npm-started processes.
    - Must delete and re-start instead.
  - ### Cross-References
    - [[wiki/tech/PM2]] -- Process manager
    - [[wiki/tech/Nginx]] -- Reverse proxy
```

**Obsidian** -- standard markdown:

```markdown
## Deployment Pipeline

CI/CD workflow for production.

### Steps

1. Run test suite
2. Build production bundle
3. Upload to server
4. Restart process manager

### Known Issues

- Process manager reload does not work for npm-started processes.
- Must delete and re-start instead.

### Cross-References

- [[wiki/tech/PM2]] -- Process manager
- [[wiki/tech/Nginx]] -- Reverse proxy
```

### Tables

**Logseq** -- tables are inside blocks:

```markdown
- ### Metrics
  - | Metric | Value | As of |
    |--------|-------|-------|
    | Users | 240 | 2026-04-01 |
    | Growth | 12% MoM | 2026-04-01 |
```

**Obsidian** -- standard markdown tables:

```markdown
### Metrics

| Metric | Value | As of |
|--------|-------|-------|
| Users | 240 | 2026-04-01 |
| Growth | 12% MoM | 2026-04-01 |
```

### File Names and Namespaces

**Logseq** uses a flat pages directory with triple-underscore separators:

```
pages/
  wiki___schema.md
  wiki___tech.md               (hub)
  wiki___tech___Strapi.md
  wiki___tech___Next-js.md
  wiki___tech___PM2.md
  wiki___projects.md            (hub)
  wiki___projects___blog-series.md
```

**Obsidian** uses nested directories:

```
wiki/
  Schema.md
  Tech/
    Tech.md                     (hub, or _index.md)
    Strapi.md
    Next-js.md
    PM2.md
  Projects/
    Projects.md                 (hub)
    Blog-Series.md
```

## Migration Paths

### Logseq to Obsidian

If you started with Logseq and want to switch to Obsidian:

**Step 1 -- Convert properties.** Replace inline `property:: value` with YAML frontmatter.

```
Before (Logseq, page properties unbulleted; older pages may carry a "- " prefix on them):
type:: knowledge
domain:: tech

After (Obsidian):
---
type: knowledge
domain: tech
---
```

**Step 2 -- Remove outliner prefixes.** Strip the `- ` prefix from content lines. Keep it for actual bullet points.

**Step 3 -- Restructure files.** Move from flat directory with triple-underscore names to nested directories.

```
Before: pages/wiki___tech___Strapi.md
After:  wiki/tech/Strapi.md
```

**Step 4 -- Update links.** Links stay the same (`[[wiki/tech/Strapi]]`) -- both apps use identical syntax.

**Step 5 -- Validate.** Run `/wiki-lint` to catch any broken references or missing properties.

**Automation:** The `./migrate.sh logseq-to-obsidian` script handles steps 1-3 automatically. Review the output and run lint to verify.

### Obsidian to Logseq

If you started with Obsidian and want to switch to Logseq:

**Step 1 -- Convert properties.** Replace YAML frontmatter with inline `property:: value` syntax: unbulleted lines at the top of the file, followed by one blank line.

**Step 2 -- Add outliner prefixes.** Every BODY line must start with `- ` (the page-property block stays unbulleted). Indentation creates hierarchy.

**Step 3 -- Flatten files.** Move from nested directories to flat directory with triple-underscore names.

```
Before: wiki/tech/Strapi.md
After:  pages/wiki___tech___Strapi.md
```

**Step 4 -- Update links.** Links stay the same.

**Step 5 -- Validate.** Run `/wiki-lint`.

**Automation:** The `./migrate.sh obsidian-to-logseq` script handles steps 1-3 automatically.

## Dual-Format Support in the Schema

The schema itself is wiki-app-agnostic at the conceptual level. The same 6 page types, the configured namespaces, and 16 lint rules apply regardless of whether you use Logseq or Obsidian. The hub-index routing and LRU-demote mechanisms are likewise tool-agnostic. The only differences are in serialization:

| Schema Concept | Logseq Serialization | Obsidian Serialization |
|----------------|---------------------|----------------------|
| Page type declaration | `- type:: knowledge` | `type: knowledge` (frontmatter) |
| Date property | `- updated:: 2026-04-07` | `updated: 2026-04-07` (frontmatter) |
| Section heading | `- ## Section` | `## Section` |
| Cross-reference | `- [[wiki/tech/Strapi]]` | `[[wiki/tech/Strapi]]` |
| Content block | `- Some text here` | `Some text here` |

The wiki skills read `llm-wiki.yml` to determine which format to use and adjusts its output accordingly. The schema rules (required properties, lint checks, L1/L2 boundary) are enforced identically in both formats.

## Recommendation

If you are starting fresh and have no preference:

- **Solo use, LLM does most writing** --> Logseq
- **Solo use, you write as much as the LLM** --> Obsidian
- **Team use** --> Obsidian (lower learning curve, bigger ecosystem)
- **Privacy-critical** --> Logseq (fully open source, auditable)
- **Mobile-heavy** --> Obsidian (more mature mobile app)

Either way, you can migrate later. The knowledge is in the content and the cross-references, not in the file format.
