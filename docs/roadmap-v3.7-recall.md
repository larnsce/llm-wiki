# Roadmap: Recall (v3.7) - one-hop neighbors + context priming

Implementation plan for the two recall features adapted from
[daniloc/mnemion](https://github.com/daniloc/mnemion) (comparison session,
2026-07-21). Issue-based, following the v2.0.0/v2.2/v2.3 pattern: canon first,
one PR per issue, mechanical verification per PR.

Status: canon drafted and merged with this roadmap (`openspec/specs/prime.md`,
`openspec/specs/query.md` REQ-480..485, both marked "v3.7, not yet
implemented"). The implementation issues (#142, #143) are filed but NOT
implemented; this document is the cycle plan.

## Context

mnemion solves the same problem as llm-wiki (persistent, agent-maintained
memory) as a hosted service: Cloudflare Worker, SQLite, vector embeddings, MCP
tools. Two of its mechanisms have no llm-wiki equivalent and transfer cleanly
to the local, lexical, plain-text architecture:

1. **Auto-associative recall** (mnemion's `prime` tool): the agent describes
   the conversational context; the system surfaces relevant entries without a
   formulated question. llm-wiki's query path is question-driven only; a prime
   mode moves the wiki from "answers when asked" toward "surfaces what is
   relevant unprompted" - the heart of the original Karpathy pitch.
2. **One-hop link expansion**: recall results return with their one-hop
   neighbors. llm-wiki reads targeted pages but never surfaces the graph
   context around them; a mechanical neighbor list costs no extra page reads.

Several other mnemion mechanisms already have llm-wiki equivalents (read-time
supersession legibility = wiki-update; access-refreshed decay = Access-Log +
LRU-Demote; stale surfacing = wiki-maintain status; write-time contradiction
checks = the ingest checkpoint). Those need nothing this cycle.

Repo ground rules that bind this plan: canon-first (specs are the single
source of truth), zero external dependencies (bash, python3 stdlib, git),
interactive-by-default, JIT page budget (max 3 full reads), append-only wiki,
both tool modes (Logseq and Obsidian) for every change.

---

## Design decisions

1. **Lexical, not embeddings.** mnemion primes via embedding KNN
   (Workers AI + Vectorize). That infrastructure is excluded here by the
   zero-dependency rule, deliberately. Prime reuses the surfaces built for
   cheap recall: hub `### Index` routing lines (read breadth-first, all hubs),
   the optional index.db FTS plane (SELECT-only, stale-checked), and a bounded
   grep fallback. If lexical recall proves too weak in practice, that is
   evidence for a future cycle, not a reason to smuggle in a vector store now.
2. **Pointers, not reads.** Both features respect the JIT budget: prime fully
   reads at most 3 pages; everything else (further candidates, one-hop
   neighbors) is presented as link + routing description. The hub routing
   line is the unit of cheap context; nothing new is invented for this.
3. **Prime is read-only.** No write-back offers, no page writes; the only
   write is the Access-Log append for full reads (`matched: "prime: <term>"`).
   Edits surfaced during a briefing are redirected to the sanctioned verbs
   (/wiki-ingest, /wiki-update).
4. **No auto-run.** Prime never self-triggers at session start; the user
   wires invocation (CLAUDE.md pointer, alias, or manual call). Mirrors the
   prune no-self-scheduling stance (prune.md REQ-622).
5. **Neighbors stay inside `wiki/`.** Link extraction does not expand into
   `para/`, `notes/`, or `glossary/` - the ownership contract
   (namespaces.md) keeps machine recall on the machine-written namespace.
6. **One-hop lands first.** Prime consumes the neighbor machinery
   (query REQ-480..485), so the query-side feature is the first PR and prime
   builds on it.
7. **Single-register briefing.** Prime output is routing, not synthesis; the
   dual-register rule (query REQ-435..437) applies to answers, not briefings.
   Attribution still appears once at the end.

## Issues (v3.7, in dependency order)

| # | Issue | Contents | Deps |
|---|---|---|---|
| R-1 (#142) | implement one-hop neighbor expansion in /wiki-query | query.md REQ-480..485: mechanical `[[wiki/...]]` link extraction from fully-read pages, ranked/capped `Related:` pointer list after attribution, archived flags, no neighbor reads, no Access-Log entries. `skills/wiki-query/SKILL.md` update, golden transcript, harness assertions, both tool modes. Drop the "not yet implemented" markers for the section. | - |
| R-2 (#143) | implement /wiki-query --prime (context priming) | prime.md REQ-1400..1431: context argument or derived-and-echoed context, lexical term extraction, breadth-first hub scan, optional index.db channel, bounded grep fallback, <= 3 full reads + pointers, neighbor lists via R-1, L1 pass, single-register briefing, read-only contract, `prime:` Access-Log reasons. `skills/wiki-query/SKILL.md` update, golden transcript, harness assertions, both tool modes. Drop the spec's "not yet implemented" status. | R-1 |

## Non-goals this cycle (parked, with reasons)

- **Per-type decay half-lives** (mnemion's continuous
  `0.5^(age/half_life)` relevance): LRU-Demote's binary 6-month threshold has
  not yet hurt in practice; parked until prune runs on a corpus old enough to
  show it (evidence-before-machinery).
- **Mechanical overlap detection at ingest** (mnemion's write-time
  near-duplicate advisories): the interactive checkpoint (ingest REQ-025)
  already presents contradictions; a wiki-core candidate-overlap script is a
  plausible later hardening, filed separately if the checkpoint keeps missing
  overlaps in practice.
- **Two-phase schema evolution** (mnemion's propose/apply): wiki-migrate
  covers the known migrations; revisit when the next schema change is drafted.
- **Embeddings in any form**: excluded by the zero-dependency rule, see
  design decision 1.

## Verification per PR

- `bash skills/wiki-core/scripts/test_pipeline.sh` green in both tool modes
- `python3 skills/wiki-core/scripts/check_canon.py` exit 0
- Golden transcript for the new behavior recorded under `tests/golden/`
- BDD scenarios of the touched spec walked manually (prime.md Scenarios 1-4,
  query.md Scenario 18)
