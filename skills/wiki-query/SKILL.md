---
name: wiki-query
description: Search the wiki for an answer to a question. Two-stage retrieval via hub indexes, targeted page reads with an L3 grep fallback, Access-Log update, and a synthesized answer with source attribution. Use when the user asks what the wiki knows about a topic.
---

# wiki-query

Search the wiki (two-stage via hub index) and synthesize an answer. This is the
primary read path; the counterpart to wiki-ingest (write path).

Spec: openspec/specs/query.md REQ-400..452

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool, wiki_path, pages_dir, memory_path, namespaces).
- [architecture](../wiki-core/references/architecture.md): L1/L2 boundary,
  two-stage routing, L3 fallback, LRU-Demote, retrieval and commit discipline,
  namespace scope rule.
- [formats](../wiki-core/references/formats.md): tool-specific formats, routing-line
  format, Access-Log format and rules.

<role>
Wiki maintainer for a personal or team knowledge base. You retrieve knowledge
through the hub routing index, synthesize answers from multiple pages, and keep the
access log that makes retrieval auditable.
</role>

<workflow>
## Phase 0 - Routing (Stage 1, cheap index read)

- Parse the question -> identify candidate namespaces (Business, Tech, Content,
  Projects, People, Learning, Reference, Careers, plus any configured in
  llm-wiki.yml)
- Read ONLY the hub page for each candidate namespace, NOT every full page
- Match the routing lines in the hub's `### Index` (routing-line format:
  [formats](../wiki-core/references/formats.md)) against the question
- Pick the 3 most relevant child pages (max 5). This is the "page table": index,
  not full scan

## Phase 1 - Targeted Read (Stage 2, only the chosen pages)

- Read ONLY the 3-5 pages chosen in Phase 0, JIT, respecting the simultaneous-read
  cap in [architecture](../wiki-core/references/architecture.md); batch if needed
- L3 fallback when routing yields nothing useful (namespace unclear, hub index
  missing/empty, no routing line matches): classic grep across all wiki pages ->
  top 3-5. This is the slow backing-store scan and should be the exception, not
  the default
- If needed, also read L1 Memory for the complete picture

## Phase 1b - Access Logging (LRU signal + routing transparency)

- For each page ACTUALLY read in full (not the Phase 0 hub-index reads), append
  one line with the verb `query` to the Access-Log page
  (wiki/reference/access-log), in the Access-Log line format from
  [formats](../wiki-core/references/formats.md)
- The `matched:` reason = the "and why" of the routing (loading transparency): on
  index routing (Phase 0) the hub `### Index` routing description / #tag that
  matched the question; on the L3 fallback the grep term that found the page
  (length and quoting rules: [formats](../wiki-core/references/formats.md)). The
  log then shows not just WHICH page loaded but WHY it was picked for this
  question; surfaced via the wiki-maintain status report (cache profile)
- The append is non-structural; the Access-Log commit rules in
  [formats](../wiki-core/references/formats.md) apply (no per-query git commit)
- If the L3 fallback hits an archived page (`archived::` set), a re-hit on an
  evicted page: offer to re-promote it; move its routing line from the hub
  `### Archive` back into the `### Index`, drop the archived:: property (and reset
  status:: where it was set)

## Phase 2 - Synthesize

- Combine information from multiple wiki pages
- Note confidence levels (from page properties)
- Check staleness (updated dates)
- Formulate a comprehensive answer with source attribution
- When sources contradict each other, present both perspectives; never silently
  pick one (REQ-413)
- Never fabricate information that is not in the wiki or L1 memory; if the wiki has
  no answer, say so (REQ-414)

## Phase 3 - Optional Write-Back

- If the query reveals a wiki gap -> offer to create/update pages
- If the synthesis produces a useful summary -> offer to file it as a new page
- The user must confirm before any writes (write-back is opt-in, never automatic)
- Write-back follows the ingest page-operation rules: required properties per the
  Schema, append-only, cross-references, hub routing line (openspec/specs/query.md
  REQ-423, openspec/specs/ingest.md Phase 3)

## Phase 4 - Output

- Answer with source pages: "Sources: [[wiki/tech/deployment]],
  [[wiki/reference/gotchas]]"
- Flag stale sources (updated:: more than 90 days ago) and low-confidence sources
  with an explicit warning
- Suggest related pages
- If no relevant pages are found, state clearly: "No information found in the wiki
  for this topic." and offer write-back (Phase 3)
</workflow>
