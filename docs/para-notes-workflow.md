# PARA + Zettelkasten in the same graph as `/wiki`

How to run a PARA task/project layer (`para/`) and a Zettelkasten note layer (`notes/`) in the
same graph as your machine-written `wiki/`, without the two ever colliding.

> **Scope.** This is a **vault-side workflow guide**, not a `/wiki` command reference. The `/wiki`
> tool does not manage `para/` or `notes/` — by design (see
> [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md)) it never writes to them. The
> pages, queries, and task markers below are things **you** create and maintain in Logseq/Obsidian.
> The tool's only involvement is the promotion seam at the end: durable content you deliberately
> copy into `raw/` and run through `/wiki ingest`.

## The three-namespace contract

| Namespace | Owner | What lives there | Tool touches it? |
|---|---|---|---|
| `wiki/` | machine (via `/wiki`) | source-backed, synthesized knowledge | writes, lints, audits |
| `para/` | you | tasks, projects, areas, resources | **never** (may read for context) |
| `notes/` | you | fleeting / literature / permanent notes | **never** (may read for context) |

The only path from `para/`/`notes/` into `wiki/` is through `raw/` — the same door every external
source uses, so promoted content gets the same provenance (`source-file::`, `reliability::`). The
wiki never silently absorbs your claims.

## Naming

Structure is **lowercase-hyphenated**; proper nouns keep their natural casing.

- **Structural segments** (namespaces, note types, workflow pages, properties): all lowercase,
  hyphen `-` (U+002D) between words, no spaces. `para/`, `notes/`, `live-list`, `fleeting-inbox`,
  `type::`.
- **Proper-noun leaves** (people, tools, papers, citekeys): written as the world writes them.
  `[[Claude Code]]`, `notes/literature/@Forte2022`.
- Hyphen `-` only — never en dash `–` (U+2013) or em dash `—` (U+2014) in page names; they are
  invisible grep traps. No underscores in structural names.

---

## `para/` — the PARA layer

### Layout

```
para/projects/<project-name>     one page per active project, tasks as blocks
para/areas/<area-name>           ongoing responsibilities
para/resources/<topic>           reference material by interest
para/archives/<project-name>     completed/inactive projects
```

### Conventions

Create a `para/schema` page recording these (for your own reference; the tool does not read it):

- Human-authored. No `source-file::`, no citations, no `reliability::`.
- Tasks are native Logseq markers — `TODO` / `DOING` / `NOW` / `DONE` / `CANCELED` — on blocks
  inside the owning project or area page.
- Every project page starts with:
  - `type:: project`
  - `status:: active | paused | archived`
  - `outcome::` — one line: what "done" looks like.
- Link freely into `[[wiki/...]]` and `[[notes/...]]`. That is the whole point of one graph.

`para/resources/` is a waiting room, not a destination: anything source-backed and stable belongs
in `wiki/` (as a proper page, or a `canonical-url::` stub if it lives elsewhere — see
[`docs/literature-research.md`](literature-research.md)); anything that is your own thinking belongs
in `notes/`.

### Roam → Logseq task conversion (one-time, on import)

If you are importing PARA pages from a Roam export, the task markers arrive as `{{[[TODO]]}}` /
`{{[[DONE]]}}` and need converting to Logseq's bare markers. **Do this through the tool's import
path** (`init_wiki.py` / the documented import step), not a hand-run `sed` — the v2 tooling
deliberately carries no `sed`. The converter normalizes `{{[[TODO]]}}` → `TODO` and
`{{[[DONE]]}}` → `DONE`. After import, spot-check for:

- `{{[[NOW]]}}` / `{{[[DOING]]}}` variants that need the same treatment.
- Stray block references `((...))` — resolve them to plain text or real `[[links]]`.

### The Live List (a query page you own)

Create `para/live-list` as a **view** — never edit tasks here; edit them on their project page.

**Logseq** (`para___live-list.md`):

```
type:: query-page

- ## live list
	- All NOW/DOING tasks across active projects. This page is a VIEW.
	- #+BEGIN_QUERY
	  {:title "now / doing"
	   :query [:find (pull ?b [*])
	           :where
	           [?b :block/marker ?m]
	           [(contains? #{"NOW" "DOING"} ?m)]
	           [?b :block/page ?p]
	           [?p :block/name ?name]
	           [(clojure.string/starts-with? ?name "para/projects/")]]
	   :group-by-page? true
	   :breadcrumb-show? true}
	  #+END_QUERY
	- #+BEGIN_QUERY
	  {:title "next up (TODO)"
	   :query [:find (pull ?b [*])
	           :where
	           [?b :block/marker "TODO"]
	           [?b :block/page ?p]
	           [?p :block/name ?name]
	           [(clojure.string/starts-with? ?name "para/projects/")]]
	   :group-by-page? true}
	  #+END_QUERY
```

**Obsidian** — Logseq's `#+BEGIN_QUERY` Datalog is Logseq-only. This page (and the fleeting inbox
below) are **Logseq tier-1**. On Obsidian, reproduce them with the community **Dataview** plugin
(a `dataview` task query filtering on the `para/projects/` folder). It is not part of core and is
not maintained by this project — treat it as experimental.

### Archiving a project (a manual procedure)

There is no `/para archive` command — this is a deliberate choice (the tool stays a wiki tool). Run
it by hand:

1. **Gate.** Confirm every task block on `para/projects/<project>` is `DONE` or `CANCELED`. If not,
   finish or cancel the open ones first.
2. **Distill.** Write a ≤10-line outcome summary (what was done, what was learned, links touched)
   under a `## outcome` heading on the page.
3. **Harvest (optional).** Ask yourself: does this project hold knowledge the `wiki/` should keep?
   If yes, copy the durable blocks + the outcome summary verbatim into `raw/para-<project>.md` and
   run `/wiki ingest`. It enters at `reliability:: medium` ("personal synthesis") unless it carries
   external citations that justify higher.
4. **Move.** Rename `para/projects/<project>` → `para/archives/<project>`; set `status:: archived`
   and `archived:: <date>`.

---

## `notes/` — the Zettelkasten layer

### Conventions

Create a `notes/schema` page recording these:

- Human-written, always. If Claude drafts it, it is not a note — it is a `wiki/` page. The writing
  IS the thinking; do not delegate it.
- One `type::` property per page: `fleeting | literature | permanent`. Properties, not tags, carry
  the note type — queries filter on them.
- Layout:
  - **fleeting** → NOT pages. Journal blocks tagged `#fleeting`.
  - **literature** → `notes/literature/@<citekey>` (born from Zotero — see
    [`docs/zotero-setup.md`](zotero-setup.md)). Carries `source-file::` pointing at the SAME
    `ingested/...` path the wiki pages cite. One archived source, two readings.
  - **permanent** → `notes/permanent/<idea-in-a-few-words>`. Atomic: one idea, your own words,
    densely linked to other `[[notes/...]]` and `[[wiki/...]]` pages.
- **Promotion is an act of writing, not a rename:**
  - fleeting → permanent: write the permanent note fresh, link the journal block to it, remove
    `#fleeting` (or mark the block `DONE`).
  - fleeting → task: move it to the owning `para/` page as a `TODO`.
  - Anything not promoted within ~2 weeks: delete without guilt.
- **notes → wiki (deliberate only):** copy the note into `raw/note-<name>.md` and run
  `/wiki ingest`. It arrives at `reliability:: medium`.

### The fleeting inbox (a query page you own)

Create `notes/fleeting-inbox` (Logseq tier-1; Dataview on Obsidian as above):

```
type:: query-page

- ## fleeting inbox
	- Unprocessed #fleeting blocks from the journal. Process = promote or delete. Aim for empty.
	- #+BEGIN_QUERY
	  {:title "unprocessed fleeting notes"
	   :query [:find (pull ?b [*])
	           :where
	           [?b :block/refs ?r]
	           [?r :block/name "fleeting"]
	           [?b :block/page ?p]
	           [?p :block/journal? true]
	           (not [?b :block/marker "DONE"])]
	   :breadcrumb-show? true}
	  #+END_QUERY
```

A processed fleeting block is either deleted or marked `DONE` with a link to where it went.

---

## A note on personal data

Promoted `para/`/`notes/` sources go through `raw/` and are committed verbatim into `ingested/`
(git history). If your notes can carry governed personal data, list `notes` (and/or `para`) under
`sensitive_source_types` in `llm-wiki.yml` so the pre-archive secret gate scans the bytes before
they enter git. See the schema/ingest specs for the "`ingested/` is committed history — keep it
secret-free" invariant.

## Related

- [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) — the normative contract
- [Zotero setup](zotero-setup.md) — how literature notes are born as `notes/literature/@citekey`
- [Literature Research](literature-research.md) — the discovery→Zotero→ingest funnel
- [Schema Reference](schema-reference.md) — naming, reliability, provenance
