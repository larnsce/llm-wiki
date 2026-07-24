# paper-site — minimal public paper wiki example

A working fixture of the Karpathy-style static wiki site described in
issues #145–#148: raw markdown files plus one self-contained
`index.html` viewer. No build step, no dependencies, no framework.

## Preview

```
cd examples/paper-site
python3 -m http.server 8123
# open http://localhost:8123/#/index.md
```

Everything after `#/` names a real markdown file; the viewer fetches and
renders it client-side. The raw file behind any page is served at the same
path (`/agent-log.md`), so the site is human-readable and agent-readable
from identical URLs. Deploying is copying the directory to any static host
(GitHub Pages serves it as-is).

## What it demonstrates

- **Paper hub as homepage** (`index.md`) — the #146 hub page doubles as
  the published site's navigation root
- **Agent-use log** (`agent-log.md`) — the #147 AI-transparency log with a
  generated disclosure statement
- **Export-shaped content** — literature notes (`notes/literature/@citekey`),
  concept pages, and a data page: the subgraph a #148 export walk would
  collect, with private tiers absent
- **Both serializations, one viewer** — pages are Obsidian-flavor
  (frontmatter + flat markdown); `pages/wiki___papers___cbs-adoption.md`
  is the same hub in Logseq flavor (`property::` lines + outline blocks),
  converted on the fly
- **Graceful exclusion** — routes outside the published set render a
  "not part of the published set" page (#148's boundary made visible)

## Scope

Fixture-grade: all content is fictional, and the embedded markdown
renderer covers the subset the wiki schema uses (headings, lists, tables,
blockquotes, code, wikilinks, frontmatter/properties) — it is a
demonstration for #145, not the production viewer.
