# Literature Research with /wiki

How to combine four literature tools (Connected Papers, Semantic Scholar, Elicit, Zotero) with Claude Code and the wiki knowledge base, so that discovery stays fast and the wiki stays a durable, trustworthy artifact.

The short version: the four discovery tools are transient and question-scoped. The wiki is durable and cross-project. Each discovery tool does the one stage it is best at, Claude Code orchestrates, and only a small, deliberate fraction of what you discover ever crosses into the wiki.

## The pipeline

The four tools overlap less than they appear. The efficient setup is a pipeline where each does one stage.

**Stage 1: Map the field (Connected Papers).**

Feed it one or two seed papers; it builds a similarity graph from co-citation and bibliographic coupling, surfacing topically adjacent work even when papers do not cite each other. Use it to spot seminal nodes and sub-clusters, then export the handful that matter as seeds. It is visual orientation, not exhaustive collection. Do not overload it with dozens of seeds; its value is the focused map.

**Stage 2: Systematic citation chasing (Semantic Scholar).**

The backbone for forward and backward citation work: 200M+ papers, billions of citation edges, TLDR summaries, open-access PDF links, and a free API. This is where the Claude Code integration pays off, since citation expansion is repetitive and scriptable. See the MCP setup below.

**Stage 3: Extraction and synthesis (Elicit).**

Strongest at pulling structured data into comparison tables across dozens of papers, and built for formal systematic review (PRISMA, reproducible and auditable). Do not use Elicit for discovery; its strength is extraction. Let Semantic Scholar plus Claude Code own discovery and screening.

**The orchestration layer (Claude Code).**

Claude Code ties the stages together and is the bridge to your wiki. With the Semantic Scholar MCP connected, citation chasing and metadata lookup happen in the same session that ingests into the wiki.

## Where the wiki fits

The wiki is not a stage in the pipeline. It is the persistent layer the pipeline feeds into. Two commands attach at the two ends of the funnel.

**`/wiki-query` at the front, before discovery.**

Ask the wiki "what do I already know about X?" first. This stops you re-discovering papers you already synthesized, and it tells you the exact gap, so your Connected Papers seeds and Semantic Scholar queries target only new territory.

**`/wiki-ingest` at the back, after you have read a paper.**

Not at discovery, not at screening. The bar is: a paper you have read and intend to cite, build on, or remember. That is a small fraction of what enters the funnel.

## The funnel rule

This is the single most important habit for keeping the wiki useful:

> Discovery feeds Zotero. Zotero feeds ingest. Only read papers cross the line.

Ingesting everything floods the wiki and destroys the reliability discipline. The `reliability::` rating and the `## Pending Review` flag (see the [Schema Reference](schema-reference.md)) only mean something if the wiki holds papers you have actually read and judged, not the raw output of a search.

## What to ingest (and what not to)

The wiki is for synthesis you will reuse, not for storage. The test is not "is this relevant?" (almost everything is), it is "will future-me query for this and want a synthesized answer rather than the original?" That is a much smaller set, and applying the test is what keeps the wiki from crowding. Four cases come up constantly.

### Your own published material (Quarto teaching sites, blog posts)

Do not ingest these as sources. They are already authored, version-controlled, and published by you. The wiki's job is to point at them, not duplicate them. A copy goes stale the moment you edit the Quarto source, and you end up with two homes for the same knowledge (which `/wiki-lint` flags as an L1/L2 duplicate).

Instead, write a thin stub page: one `knowledge` or `reference` page per course or blog series that links out to the live URL and records the durable metadata (what it covers, where it lives, when last revised). The Quarto site stays the source of truth; the wiki becomes the map.

```
- type:: reference
- source-file:: (omit - this is a stub, not an ingested source)
- ## Wiki/Teaching/Data-Science-with-R
  - Course site: https://your-quarto-site.example/course
  - Covers: tidyverse, reproducible workflows, RStudio projects, Quarto authoring.
  - Last major revision: 2026-05. Source of truth is the Quarto repo, not this page.
  - [[Wiki/Methods/Reproducible-Pipelines]] [[Wiki/Tech/Quarto]]
```

### Other people's web articles and blog posts

Apply the funnel. Most are read-and-discard: relevant in the moment, not worth durable synthesis. A few cross the line, the ones you will cite, build on, or return to. For those, ingest. For the rest, a bookmark or a Zotero web-clip is enough. The honest filter: if you cannot already imagine the future `/wiki-query` that would surface this page, it is crowding, not knowledge.

### Reference material you consult repeatedly (a standard, a canonical method post)

These belong in the wiki as proper `reference` or `knowledge` pages, with `source-file::` and a `reliability::` rating. The value is your synthesis of them, consulted often, not the original document.

### Papers and preprints

The scholarly path, covered by the funnel and the full loop below: Zotero first, annotate, export, ingest.

## Zotero first, or straight to /wiki-ingest?

Decide by whether the thing is a scholarly object or just a web page.

- **Papers, preprints, anything with a DOI or formal citation:** Zotero first, always. Zotero is your citation source of truth and where stable keys and `s2-metrics::` enrichment come from. Then ingest from there.
- **A plain web article or blog post:** pick by durability. If you might cite it formally, put it in Zotero (it has a web-page item type; Better BibTeX gives it a stable key), then ingest. If you only want the idea captured, run `/wiki-ingest <url>` directly. The ingest workflow fetches the URL for you.

Rule of thumb: Zotero owns anything you might put in a bibliography; the wiki owns your synthesis of it. A web article that will never appear in a reference list does not need Zotero ceremony.

## Notes in the wiki, or notes in Zotero?

These are two different kinds of note.

| Note type | Lives in | Why |
|---|---|---|
| Per-source annotation (highlights, marginalia, "this passage says X") | Zotero | Anchored to the document, travels with the citation, is the raw input you later export |
| Cross-source synthesis ("X and Y disagree on Z; my position is...") | Wiki | The durable, reusable knowledge, the whole reason the wiki exists |

Zotero notes are about one document. Wiki notes are about your understanding across documents. If a note only makes sense next to the paper it is attached to, it is a Zotero note. If it would still be useful to a future-you who never re-opens that paper, it is a wiki page. The Zotero annotation is the input; the wiki synthesis is the output. Do not put synthesis in Zotero (it gets buried per-document) and do not put per-passage highlights in the wiki (they crowd it with detail you will never query).

## The full loop

1. **`/wiki-query`** asks your wiki what you already know, and finds the gap.
2. **Connected Papers** maps the unfamiliar cluster from your seed papers.
3. **Claude Code + Semantic Scholar MCP** chase citations and build the candidate list.
4. **Screen.** The keepers go into Zotero.
5. **Read and annotate.** Export the highlights to markdown (Better BibTeX, a Zotero-to-markdown export, or a Logseq-Zotero plugin), and drop the result into `raw/`.
6. **`/wiki-ingest`** synthesizes the page, stamps `reliability::`, and moves the source into `ingested/papers/`.

## Semantic Scholar MCP setup

This is session or user configuration, not a change to this repository. You wire the MCP server into Claude Code once.

```
claude mcp add semantic-scholar -s user -- uvx --from git+https://github.com/akapet00/semantic-scholar-mcp semantic-scholar-mcp
```

Get a free API key at semanticscholar.org/product/api before anything serious. The key gives you a dedicated rate limit (around 1 request per second) instead of a shared anonymous pool, which makes the difference between a smooth session and constant throttling.

There is also a purpose-built `semantic-scholar-skills` package that bundles the MCP server with Claude Code skills such as `/expand-references`, `/trace-citations`, and `/paper-triage`.

Reproducibility caveat: most of these MCP servers are community projects, not official. If a review must be auditable, pin to a known version of the server rather than tracking its main branch, so the metadata your provenance rests on does not shift under you.

## Reliability from Semantic Scholar metrics

When the Semantic Scholar MCP is connected, `/wiki-ingest` can record a paper's bibliometric figures on the page as an optional `s2-metrics::` property: citation count, influential-citation count, venue, publication type, and year, recorded verbatim.

These metrics are evidence, not a verdict. The qualitative reliability rubric in your Schema page (peer-reviewed primary source, official standard, or corroborated by independent sources) stays the decision-maker. Citation count measures influence and age, not correctness or currency. A three-citation preprint defining a FAIR data standard can be authoritative; a heavily-cited method paper can be superseded. Recording the raw figures keeps the reliability judgment auditable without turning it into a citation-count formula. Currency is tracked separately by `confidence::`.

This step is optional. When no Semantic Scholar MCP is configured, ingest skips it and judges reliability from the source alone.

## Ingesting an Elicit synthesis

You can feed `/wiki-ingest` an Elicit review output. This needs no new command. It is three sentences you say at ingest time:

1. Feed the narrative report as markdown, not the raw CSV. Export the Elicit report to markdown into `raw/`, and keep the CSV alongside it as the data artifact. The synthesis workflow reads prose far better than a bare table.
2. Tell ingest: "ingest this as a `knowledge` page; link to the existing `[[Wiki/...]]` paper pages it summarizes; do not create new paper pages." The synthesis then sits above its sources in the graph rather than duplicating them.
3. Set reliability from the review's rigor, not per-source. A synthesis inherits reliability from its constituents. For a PRISMA-followed Elicit review, stamp it `high` and note the method on the page.

Semantic Scholar (via Zotero) feeds per-paper ingests; Elicit feeds review-level synthesis pages that link down to them.

If you find yourself ingesting review syntheses regularly, a dedicated synthesize skill would be cleaner. Wait until you have done it manually a few times before formalizing it, so the verb matches how you actually work.

## Related

- [Schema Reference](schema-reference.md) for `reliability::`, `source-file::`, `s2-metrics::`, and the Trust Axes (confidence vs reliability).
- The provenance pipeline (`raw/` to `ingested/`) is documented in the main [README](../README.md) under Source Provenance & Trust.
