# Zotero → `notes/literature/@citekey`

How to wire Zotero into the graph so literature notes are born in the right namespace with the
right properties, and stay auditable against the same archived source the `wiki/` pages cite.

> **Verify before you trust this.** The plugin and settings below are **known-good as of
> 2026-07** but community plugins move. Before relying on this guide, confirm the plugin still
> exists in the marketplace and its settings match what is described here, and **pin the plugin
> version** rather than tracking its latest — so the metadata your provenance rests on does not
> shift under you.

## Where this fits

Zotero is your **citation source of truth** (see [Literature Research](literature-research.md)).
This guide covers the last mile: getting a Zotero item into Logseq as a
`notes/literature/@<citekey>` page that (1) holds your reading in your own words and (2) points at
the same `ingested/...` source the wiki cites. The `## my reading` block is a **`notes/` page** —
human-written, machine-exempt (see [`namespaces.md`](../openspec/specs/namespaces.md)). It is not a
`wiki/` page and the wiki skills never edit it.

## Recommended plugin

**logseq-zoterolocal-plugin** (benjypng), from the Logseq marketplace. Why this one:

- Connects to Zotero **locally** — no cloud sync required.
- Fully **templated** properties.
- **Incremental annotation sync** — only annotations added since the last sync are appended,
  tracked via a `zotero-last-sync` property per page, so re-syncing never clobbers your prose.

(Obsidian users: the equivalent is the **Zotero Integration** plugin. This guide is written for the
Logseq plugin; the property template idea transfers.)

### One-time setup

1. Zotero → **Settings → Advanced** → check *Allow other applications on this computer to
   communicate with Zotero*.
2. Install **Better BibTeX**; set *Automatically pin citation key after* to `1` second (citekeys
   must be pinned to reach Logseq).
3. In the plugin settings, confirm *Connection to Zotero is working*.

## Page-name template

In the plugin's page-name setting:

```
notes/literature/@<% citeKey %>
```

Every imported item is born in the right namespace with a zoteroRoam-style `@citekey` name, e.g.
`notes/literature/@Forte2022`. (Lint recognizes the `@citekey` leaf as a proper noun — it is not a
naming violation; see [`namespaces.md`](../openspec/specs/namespaces.md) REQ-631.)

## Page template

Run *Insert Zotero template* and replace the generated block with this trimmed version — full
metadata is noise; the raw source lives in `ingested/` anyway:

```markdown
type:: literature
citekey:: <% citeKey %>
authors:: <% creators %>
year:: <% date %>
item-type:: <% itemType %>
doi:: <% DOI %>
zotero:: <% libraryLink %>
source-file::

- ## my reading
	-
- ## annotations
	- (synced from Zotero below this line)
```

- `source-file::` is left blank by the template. Fill it **when the paper goes through the
  pipeline**, pointing at `ingested/papers/<file>.md` — the same path the machine-written `wiki/`
  page cites. That shared path is the seam that makes your interpretation auditable against the
  same source as the wiki's ("one archived source, two readings").
- `## my reading` is yours; annotation sync appends under its own blocks and never touches your
  prose.

## The working loop

1. Read + annotate the PDF in Zotero.
2. In Logseq: right-click the item page title → *Zotero: Sync annotations* (or command palette →
   *Sync all annotations*).
3. Write `## my reading` in your own words — this is the literature note.
4. When the paper feeds the wiki: export/flatten to markdown into `raw/`, run `/wiki-ingest`, then
   set `source-file::` here to the `ingested/` path the ingest produced.
5. Ideas that outgrow the paper get their own `notes/permanent/` page, linking back to
   `[[notes/literature/@citekey]]`.

## Citation-graph gap

No Logseq plugin replicates zoteroRoam's citation-network browsing (Scite / Connected Papers).
Cover it with the Semantic Scholar MCP already documented in
[Literature Research](literature-research.md): citation-walk on demand, results entering through
`raw/` like everything else.

## Related

- [Literature Research](literature-research.md) — the full discovery→Zotero→ingest funnel and the
  Semantic Scholar MCP setup
- [PARA + Zettelkasten workflow](para-notes-workflow.md) — the `notes/` layer this feeds
- [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) — the namespace contract
