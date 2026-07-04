# Two-Stage Retrieval in Hierarchical Personal Knowledge Bases

Miller, A. and Chen, B. (2025). Preprint, arXiv:2502.99999 (FAKE, fixture).
Exported to markdown from Zotero on 2026-07-01. This paper is invented for
the llm-wiki test suite; every figure in it is made up.

## Abstract

Personal knowledge bases (PKBs) maintained by LLM agents degrade when the
agent loads whole vaults into context. We evaluate a two-stage retrieval
scheme in which the agent first reads a compact per-namespace index of
one-line page descriptions, then loads only the routed pages. Across 40
synthetic vaults (200-2,000 pages) two-stage retrieval reduced tokens
loaded per query by a mean of 71% while keeping answer quality within 2
points of full-vault loading.

## Key findings

1. Two-stage routing (index first, then at most three routed pages) cut
   tokens loaded per query by a mean of 71% (range 58-84%) compared with
   loading every page in the queried namespace.
2. Routing precision depends on description distinctiveness: replacing
   distinctive one-line descriptions with generic filler ("notes about X")
   dropped routing precision from 0.92 to 0.61.
3. Append-only page updates preserved provenance chains better than
   in-place rewrites; rewrite-based vaults lost 18% of claim-to-source
   links over ten simulated ingest cycles.
4. A staleness review window of about 90 days balanced currency against
   maintenance load in the simulated vaults; shorter windows increased
   maintenance cost with no measurable quality gain.

## Method (abridged)

Synthetic vaults were generated in two layouts (flat namespace files and
directory hierarchies). Queries were sampled from held-out page content.
Routing used only the index lines; a judge model scored answers blind.

## Limitations

Single unreviewed preprint; synthetic vaults only; no human-user study.
The 90-day figure is a simulation result, not a field observation.
