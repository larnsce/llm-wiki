# Zotero → `notes/literature/@citekey`

How to wire Zotero into the graph so literature notes are born in the right namespace with the
right properties, and stay auditable against the same archived source the `wiki/` pages cite.

> **Status (2026-07-07).** The logseq-zoterolocal-plugin recommended by earlier versions of
> this guide **did not work in practice; the plugin approach is abandoned** (issue
> [#90](https://github.com/larnsce/llm-wiki/issues/90)). Replacement: `scripts/lit_sync.py`
> against Zotero's local HTTP API, driven by the `/lit-sync` command. The schema side is
> unchanged from v2.2 (the `@citekey` proper-noun leaf, namespaces REQ-976, the
> literature-variant seam in `/wiki-ingest`, REQ-973/974). The end-to-end loop run with the
> script is the remaining maintainer-verified item, tracked in
> [#28](https://github.com/larnsce/llm-wiki/issues/28).

> **Verify before you trust this.** The local API endpoint and behavior below are written
> against **Zotero 9** (the local API arrived in Zotero 7 and is unchanged through current
> releases: API v3 only, same endpoint, same enable switch). After each end-to-end loop run,
> stamp this doc with the Zotero version it was verified on, so the metadata your provenance
> rests on does not shift under you. Not yet verified end-to-end; #28 tracks the first run.

## Where this fits

Zotero is your **citation source of truth** (see [Literature Research](literature-research.md)).
This guide covers the last mile: getting a Zotero item into Logseq as a
`notes/literature/@<citekey>` page that (1) holds your reading in your own words and (2) points at
the same `ingested/...` source the wiki cites. The `## literature` block is a **`notes/` page**:
human-written, machine-exempt (see [`namespaces.md`](../openspec/specs/namespaces.md)). It is not a
`wiki/` page and the wiki skills never edit it.

## The sync script

**`scripts/lit_sync.py`**, run via the **`/lit-sync`** command. It talks to Zotero's **local
HTTP API** (`http://localhost:23119/api/users/0`, Zotero 7+, API v3): no Logseq plugin, no
Zotero cloud API, no BBT export file.

- **Idempotent metadata:** each run rewrites only the managed properties (`type`, `citekey`,
  `authors`, `year`, `item-type`, `doi`, `zotero`); `source-file::` and any user-added
  properties are preserved.
- **Incremental annotation sync:** annotations are read as children of the PDF attachments,
  sorted by position in the PDF, and only annotations with a Zotero version newer than the
  page's `zotero-last-sync::` stamp are appended; the stamp is then updated from the library
  version. Re-syncing never clobbers your prose; the reading section (`## literature`; `## my reading` on pages created before the #101 rename) is never touched.
- **Skips unpinned items with a warning:** the citekey is read from the item's `extra` field
  (`Citation Key: xxx`, written by Better BibTeX pinning). Nothing is guessed.

(Obsidian users: the **Zotero Integration** plugin remains the equivalent there. This guide is
written for the Logseq script; the property template idea transfers.)

### One-time setup

1. Zotero → **Settings → Advanced** → check *Allow other applications on this computer to
   communicate with Zotero* (the local API returns 403 without it).
2. Install **Better BibTeX**; set *Automatically pin citation key after* to `1` second (citekeys
   must be pinned to reach Logseq).

### Running it

```
python3 scripts/lit_sync.py --vault <logseq-graph-root> --dry-run   # review first
python3 scripts/lit_sync.py --vault <logseq-graph-root>            # then for real
```

Or run `/lit-sync`, which wraps exactly this (dry-run, review, real run, commit). If the local
connection fails, **stop**: fix the Zotero side; do not work around it with the cloud API.

## Page name and file

Every synced item gets the page `notes/literature/@<citekey>`, e.g.
`notes/literature/@Forte2022` - the zoteroRoam-style proper-noun leaf (lint recognizes it; see
[`namespaces.md`](../openspec/specs/namespaces.md) REQ-976). On disk the script matches the
vault's existing namespace-filename encoding (`___` by default, `%2F` if the vault already uses
it), so e.g. `pages/notes___literature___@Forte2022.md`.

## Page template

The script writes this template on creation - full metadata is noise; the raw source lives in
`ingested/` anyway:

```markdown
type:: literature
citekey:: Forte2022
authors:: Tiago Forte
year:: 2022
item-type:: book
doi::
zotero:: zotero://select/library/items/<KEY>
source-file::
zotero-last-sync:: <library version>

- ## literature
	-
- ## annotations
	- (synced from Zotero below this line)
```

- `source-file::` is left blank by the template. It gets filled **when the paper goes through the
  pipeline**, pointing at `ingested/papers/<file>.md` - the same path the machine-written `wiki/`
  page cites. That shared path is the seam that makes your interpretation auditable against the
  same source as the wiki's ("one archived source, two readings", namespaces REQ-973). When
  `/wiki-ingest` recognizes a promoted literature note (a `raw/note-@<citekey>.md` filename, or
  `citekey::` / `type:: literature` metadata) and this page exists with the property still blank,
  it offers at the checkpoint to set it to the `ingested/` path it produced - you confirm, the
  tool types (REQ-974, issue #133). This is the one sanctioned tool write into `notes/`; it never
  creates the page, never overwrites a value you set, and in `--auto` runs it only reminds.
- `## literature` is yours: your literature note in the Zettelkasten sense (add the `#literature` tag by hand when you write it; the tooling never writes tags). Annotation sync appends under its own blocks and never touches your
  prose.

## The working loop

1. Read + annotate the PDF in Zotero.
2. Run `/lit-sync` (dry-run first, then real): new items get their `@citekey` page, new
   annotations append under `## annotations`.
3. Write `## literature` in your own words - this is the literature note (tag it `#literature` yourself).
4. When the paper feeds the wiki: export/flatten to markdown into `raw/`, run `/wiki-ingest`, and
   confirm at the checkpoint when it offers to set `source-file::` here to the `ingested/` path it
   produced (REQ-973/974) - the tool writes the path for you.
5. Ideas that outgrow the paper get their own `notes/permanent/` page, linking back to
   `[[notes/literature/@citekey]]`.

## Citation-graph gap

No Logseq plugin replicates zoteroRoam's citation-network browsing (Scite / Connected Papers).
Cover it with the Semantic Scholar MCP already documented in
[Literature Research](literature-research.md): citation-walk on demand, results entering through
`raw/` like everything else.

## Related

- [Literature Research](literature-research.md) - the full discovery→Zotero→ingest funnel and the
  Semantic Scholar MCP setup
- [PARA + Zettelkasten workflow](para-notes-workflow.md) - the `notes/` layer this feeds
- [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) - the namespace contract
