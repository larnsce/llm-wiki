# Index Maintenance and Staleness in Agent-Maintained Knowledge Bases

Chen, B. and Okafor, D. (2026). In Proceedings of the 3rd Conference on
Agentic Knowledge Systems (AKS '26), pp. 141-155 (FAKE venue, fixture).
Peer-reviewed. Exported to markdown from Zotero on 2026-07-07. This paper
is invented for the llm-wiki test suite; every figure in it is made up.
Never edit it; baseline outputs are only comparable while the input is
frozen.

DENSE-PAPER FIXTURE. Unlike the other fixture sources, this one is
designed to be ingested into a vault that ALREADY holds the Miller and
Chen (2025) ingest (see `tests/golden/README.md` for the exact vault
conditions). It deliberately packs the judgment calls a cheap model is
most likely to get wrong: a same-team replication that looks like
corroboration, a scoped contradiction, a conditional partial
contradiction, and a discussion-section conjecture inside a peer-reviewed
source.

## Abstract

Agent-maintained personal knowledge bases rely on per-namespace index
descriptions for retrieval routing, but the literature has not examined
how those indexes degrade as the vault changes. We extend the synthetic
vault framework of Miller and Chen (2025) to 400 vaults simulated over
26 weeks of ingest activity and evaluate index maintenance policies and
staleness review windows longitudinally. Eager routing-line regeneration
preserved routing precision (0.94 vs 0.79 for nightly batch), and index
entries older than the median page age predicted 74% of misroutes. At
ingest rates above five sources per week, a 30-day staleness review
window outperformed the 90-day window recommended in prior work; at low
ingest rates the 90-day recommendation held. We could not reproduce the
earlier 18% provenance link-loss figure for rewrite-based vaults; link
loss depended on whether rewrites preserved block identifiers (4% with,
22% without).

## Key findings

1. Replication of two-stage routing savings: across the enlarged
   400-vault sweep, index-first routing cut tokens loaded per query by a
   mean of 68% (range 55-82%), consistent with the 71% we reported in
   Miller and Chen (2025). The sweep reuses our earlier vault generator
   and query sampler unchanged.
2. Eager routing-line maintenance (regenerate the hub routing line on
   every page write) held routing precision at 0.94 over the 26-week
   simulation, against 0.79 for a nightly batch regeneration policy and
   0.58 for write-once-never-update.
3. Index-entry age predicts misrouting: entries older than the median
   page age of their namespace accounted for 74% of observed misroutes,
   making entry age a usable maintenance trigger.
4. Staleness review windows interact with ingest rate: above roughly
   five ingested sources per week, a 30-day review window improved
   answer quality by 6 points over a 90-day window at 2.1 times the
   maintenance cost; at or below that rate, the 90-day window of Miller
   and Chen (2025) remained the better trade-off.
5. The 18% link-loss figure for rewrite-based vaults reported in Miller
   and Chen (2025) did not reproduce as stated: in our sweep, rewrite
   pipelines that preserved stable block identifiers lost 4% of
   claim-to-source links over ten ingest cycles, while pipelines that
   regenerated identifiers lost 22%. The earlier figure appears to
   average over the two regimes.

## Method (abridged)

Vault generation, query sampling, and blind judge scoring follow Miller
and Chen (2025) exactly; the simulation codebase is shared with that
work and extended with a longitudinal ingest-activity model (26 weeks,
Poisson-distributed ingest events). Maintenance policies were varied
per-vault. All results are simulation results.

## Discussion (excerpt)

We conjecture that the description-distinctiveness effect reported in
Miller and Chen (2025) would largely disappear under embedding-based
routing, since dense retrieval does not depend on surface wording; we
have not tested this.

## Limitations

Synthetic vaults only; no human-user study. The simulation codebase is
shared with Miller and Chen (2025), so findings 1 and 5 are not
independent replications by a different group. The 30-day window result
(finding 4) is sensitive to the simulated maintenance-cost model.
