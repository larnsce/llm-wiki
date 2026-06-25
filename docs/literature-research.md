# Literature Research with /wiki

How to combine four literature tools (Connected Papers, Semantic Scholar, Elicit, Zotero) with Claude Code and the `/wiki` knowledge base, so that discovery stays fast and the wiki stays a durable, trustworthy artifact.

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

Claude Code ties the stages together and is the bridge to your `/wiki`. With the Semantic Scholar MCP connected, citation chasing and metadata lookup happen in the same session that ingests into the wiki.

## Where /wiki fits

The `/wiki` system is not a stage in the pipeline. It is the persistent layer the pipeline feeds into. Two commands attach at the two ends of the funnel.

**`/wiki query` at the front, before discovery.**

Ask the wiki "what do I already know about X?" first. This stops you re-discovering papers you already synthesized, and it tells you the exact gap, so your Connected Papers seeds and Semantic Scholar queries target only new territory.

**`/wiki ingest` at the back, after you have read a paper.**

Not at discovery, not at screening. The bar is: a paper you have read and intend to cite, build on, or remember. That is a small fraction of what enters the funnel.

## The funnel rule

This is the single most important habit for keeping the wiki useful:

> Discovery feeds Zotero. Zotero feeds ingest. Only read papers cross the line.

Ingesting everything floods the wiki and destroys the reliability discipline. The `reliability::` rating and the `## Pending Review` flag (see the [Schema Reference](schema-reference.md)) only mean something if the wiki holds papers you have actually read and judged, not the raw output of a search.

## The full loop

1. **`/wiki query`** asks your wiki what you already know, and finds the gap.
2. **Connected Papers** maps the unfamiliar cluster from your seed papers.
3. **Claude Code + Semantic Scholar MCP** chase citations and build the candidate list.
4. **Screen.** The keepers go into Zotero.
5. **Read and annotate.** Export the highlights to markdown (Better BibTeX, a Zotero-to-markdown export, or a Logseq-Zotero plugin), and drop the result into `raw/`.
6. **`/wiki ingest`** synthesizes the page, stamps `reliability::`, and moves the source into `ingested/papers/`.

## Semantic Scholar MCP setup

This is session or user configuration, not a change to this repository. You wire the MCP server into Claude Code once.

```
claude mcp add semantic-scholar -s user -- uvx --from git+https://github.com/akapet00/semantic-scholar-mcp semantic-scholar-mcp
```

Get a free API key at semanticscholar.org/product/api before anything serious. The key gives you a dedicated rate limit (around 1 request per second) instead of a shared anonymous pool, which makes the difference between a smooth session and constant throttling.

There is also a purpose-built `semantic-scholar-skills` package that bundles the MCP server with Claude Code skills such as `/expand-references`, `/trace-citations`, and `/paper-triage`.

Reproducibility caveat: most of these MCP servers are community projects, not official. If a review must be auditable, pin to a known version of the server rather than tracking its main branch, so the metadata your provenance rests on does not shift under you.

## Reliability from Semantic Scholar metrics

When the Semantic Scholar MCP is connected, `/wiki ingest` can record a paper's bibliometric figures on the page as an optional `s2-metrics::` property: citation count, influential-citation count, venue, publication type, and year, recorded verbatim.

These metrics are evidence, not a verdict. The qualitative reliability rubric in your Schema page (peer-reviewed primary source, official standard, or corroborated by independent sources) stays the decision-maker. Citation count measures influence and age, not correctness or currency. A three-citation preprint defining a FAIR data standard can be authoritative; a heavily-cited method paper can be superseded. Recording the raw figures keeps the reliability judgment auditable without turning it into a citation-count formula. Currency is tracked separately by `confidence::`.

This step is optional. When no Semantic Scholar MCP is configured, ingest skips it and judges reliability from the source alone.

## Ingesting an Elicit synthesis

You can feed `/wiki ingest` an Elicit review output. This needs no new command. It is three sentences you say at ingest time:

1. Feed the narrative report as markdown, not the raw CSV. Export the Elicit report to markdown into `raw/`, and keep the CSV alongside it as the data artifact. The synthesis workflow reads prose far better than a bare table.
2. Tell ingest: "ingest this as a `knowledge` page; link to the existing `[[Wiki/...]]` paper pages it summarizes; do not create new paper pages." The synthesis then sits above its sources in the graph rather than duplicating them.
3. Set reliability from the review's rigor, not per-source. A synthesis inherits reliability from its constituents. For a PRISMA-followed Elicit review, stamp it `high` and note the method on the page.

Semantic Scholar (via Zotero) feeds per-paper ingests; Elicit feeds review-level synthesis pages that link down to them.

If you find yourself ingesting review syntheses regularly, a dedicated `/wiki synthesize` path would be cleaner. Wait until you have done it manually a few times before formalizing it, so the verb matches how you actually work.

## Related

- [Schema Reference](schema-reference.md) for `reliability::`, `source-file::`, `s2-metrics::`, and the Trust Axes (confidence vs reliability).
- The provenance pipeline (`raw/` to `ingested/`) is documented in the main [README](../README.md) under Source Provenance & Trust.
