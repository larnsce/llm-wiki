# Formats: Logseq vs Obsidian, Hub Index, Access-Log

Spec: openspec/specs/schema.md REQ-500..595 (page types, properties, hub structure,
Access-Log, format rules)

The configured `tool` (see [config.md](config.md)) selects one of two format modes.
Always use the correct format for the configured tool.

## Logseq mode

- Every line of wiki content starts with `- ` (outliner format; REQ-590).
- Properties: inline `property:: value` syntax on the first lines; NO YAML
  frontmatter (REQ-591).
- File naming: triple-underscore for namespaces (`wiki___tech___Strapi.md`), all
  files flat in the `pages/` directory (REQ-583).
- Hub file naming: `wiki___<namespace>.md`.
- Sub-items indented with tab + `- `.
- Headings go inside blocks: `- ## Heading` (REQ-594).

## Obsidian mode

- Standard flat markdown; no `- ` prefix required (REQ-593).
- Properties: YAML frontmatter between `---` fences (REQ-592).
- File naming: folder hierarchy (`wiki/tech/Strapi.md`); namespaces map to
  directories on disk (REQ-583).
- Hub file naming: `wiki/<namespace>/_index.md`.
- Headings: standard `## Heading` syntax (REQ-594).

## Both tools

- Cross-references: `[[wiki/<namespace>/Page]]` syntax (REQ-574); links are
  bidirectional (backlinks panel in both tools).
- Schema page: read `wiki/schema` (`wiki___schema.md` / `wiki/schema.md`) for the
  current conventions.
- Dates: ISO 8601 (`YYYY-MM-DD`), zero-padded (REQ-560..561).
- Page and namespace naming: lowercase structural segments, hyphen (U+002D) for
  multi-word names (no spaces, underscores, or en/em dashes), maximum namespace
  depth 3; proper-noun leaf segments (people, tools, papers, `@citekey`s) keep
  natural casing (REQ-580..582). Pre-migration `Wiki/` corpora are grandfathered
  until the lowercase migration runs (`migrate_wiki.py --lowercase`, REQ-580c).
- Write discipline: NEVER overwrite existing content blocks; only append new blocks
  (openspec/specs/ingest.md REQ-032). Set the `updated::` property (or YAML
  `updated` field) on every modified page.
- Page properties per type (entity, project, knowledge, feedback, hub): see the
  Schema page and openspec/specs/schema.md REQ-510..557. Do not mix tool formats
  (REQ-595).
- `schema-spec-version:: 2.0.0` (Logseq) / `schema-spec-version: "2.0.0"`
  (Obsidian YAML): a stamp written on every page that init_wiki.py scaffolds
  and every page ingest creates. It marks the page as conforming to the
  current schema contract; pages WITHOUT it are grandfathered by lint
  (findings one severity tier lower). It is a stamp set at creation, not a
  property lint requires.

## Hub-Index-Routing (format)

Every hub page (`type:: hub`) carries two sections that query Phase 0 reads and
ingest/prune maintain (REQ-555..557). A routing line is
`[[link]] -- description #tags`, one per child page.

Logseq (outliner):

```
- ## Tech
  - ### Index
    - [[wiki/tech/Strapi]] -- Strapi 5 CMS, ports, deploy + migration gotchas #strapi #deploy
    - [[wiki/tech/PM2]] -- PM2 process management on the VPS, cwd/reload bug #pm2 #deploy
  - ### Archive
    - [[wiki/tech/legacy-foo]] -- (demoted 2026-06-07) old Foo stack, replaced by Bar #archived
```

Obsidian (flat markdown):

```
## Tech

### Index
- [[wiki/tech/Strapi]] -- Strapi 5 CMS, ports, deploy + migration gotchas #strapi #deploy
- [[wiki/tech/PM2]] -- PM2 process management on the VPS, cwd/reload bug #pm2 #deploy

### Archive
- [[wiki/tech/legacy-foo]] -- (demoted 2026-06-07) old Foo stack, replaced by Bar #archived
```

Rules:

- Description <= 120 chars, distinctive (it is the routing key), no filler
  ("Info about ...").
- Tags mirror the page's own #tags; multi-match across tags is fine.
- `### Index` = live (routable). `### Archive` = evicted (only L3 grep finds the
  page).
- The hub child list IS the routing index; there is no separate index file
  (REQ-557).
- Every active page belongs in exactly one hub `### Index`: ingest sets the routing
  line, else the page is unroutable (only findable via L3 grep). lint --fix
  backfills missing lines.

## Access-Log (format)

Page: `wiki/reference/access-log` (`wiki___reference___access-log.md` /
`wiki/reference/access-log.md`); an append-only LRU signal plus routing
transparency, one line per page read (REQ-569).

Logseq:

```
- access-log:: true
- type:: reference
- ## Log (append-only, newest at bottom)
  - 2026-06-07 -- [[wiki/tech/Strapi]] -- query -- matched: "Strapi 5 -- ports, deploy, migration"
  - 2026-06-07 -- [[wiki/projects/GEO]] -- query -- matched: "L3-grep: geo strategy"
```

Obsidian:

```
---
access-log: true
type: reference
---
## Log (append-only, newest at bottom)
- 2026-06-07 -- [[wiki/tech/Strapi]] -- query -- matched: "Strapi 5 -- ports, deploy, migration"
- 2026-06-07 -- [[wiki/projects/GEO]] -- query -- matched: "L3-grep: geo strategy"
```

Rules:

- One line per page read; the wiki-query workflow (Phase 1b) defines WHICH reads
  are logged and WHAT the `matched:` routing reason records.
- `matched:` field: <= 60 chars, in quotes. It makes loading auditable; not just
  WHAT loaded but WHY. Legacy lines without `matched:` stay valid (the field is
  additive, optional-backward).
- Append-only, NO per-query git commit (non-structural; rides along with the next
  prune/lint/ingest commit).
- prune/status parse the date + `[[page]]` from fixed positions (split on ` -- `);
  the `matched:` suffix is irrelevant to LRU aggregation and does not affect
  parsing.
- This page is exempt from orphan / stale / demote rules.
