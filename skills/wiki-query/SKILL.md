---
name: wiki-query
description: Search the wiki for an answer to a question. Two-stage retrieval via hub indexes, targeted page reads with an L3 grep fallback, Access-Log update, and a synthesized answer with source attribution. With --prime, no question is needed - describe the session's context and get a read-only briefing of relevant pages, pointers, neighbors, and L1 rules. Use when the user asks what the wiki knows about a topic, or wants context loaded for a work session.
---

# wiki-query

Search the wiki (two-stage via hub index) and synthesize an answer. This is the
primary read path; the counterpart to wiki-ingest (write path). When the
storage plane is configured, aggregate, temporal, and full-text questions
route to index.db SQL (the second plane); entity questions stay on pages.

Spec: openspec/specs/query.md REQ-400..452 (dual-register output
REQ-435..437), two-plane routing REQ-460..464, one-hop neighbor
expansion REQ-480..485; --prime mode openspec/specs/prime.md
REQ-1400..1431

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool, wiki_path, pages_dir, memory_path, namespaces; optional
  `index_db`, config REQ-627, enables the index plane).
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

- Plane decision first (REQ-460), only when `index_db` is configured AND the
  file exists; otherwise skip straight to hub routing:
  - Entity/topic questions ("what do we know about X", "how do I Y") ->
    markdown plane (below), the default. When in doubt, the markdown plane
    wins.
  - Aggregate (counts/lists across many pages), temporal (date ranges over
    journals and meetings), or needle-in-haystack full-text ("which page
    mentions X") -> the index plane (Phase 0b)
- Parse the question -> identify candidate namespaces (Business, Tech, Content,
  Projects, People, Learning, Reference, Careers, plus any configured in
  llm-wiki.yml)
- Read ONLY the hub page for each candidate namespace, NOT every full page
- Match the routing lines in the hub's `### Index` (routing-line format:
  [formats](../wiki-core/references/formats.md)) against the question
- Pick the 3 most relevant child pages (max 5). This is the "page table": index,
  not full scan

## Phase 0b - Index plane (only when routed there, REQ-460..462)

- Staleness first (REQ-461, storage REQ-1133): run

  ```
  python3 skills/wiki-core/scripts/rebuild_index.py --config <llm-wiki.yml> --stale-check
  ```

  Exit 1 (stale): either rebuild now (same script without the flag) and
  answer fresh, or answer from the stale index with an EXPLICIT staleness
  warning in the output. Never answer from a stale index silently.
- Read with python3 stdlib `sqlite3`, SELECT-only against the frozen schema
  (storage REQ-1130). Starting shapes:
  - people: `SELECT page, name, aliases FROM people WHERE name LIKE ? OR aliases LIKE ?`
  - meetings: `SELECT page, date, text FROM meetings WHERE date BETWEEN ? AND ? ORDER BY date, page`
  - full-text: `SELECT page FROM page_text WHERE page_text MATCH ? ORDER BY rank`
- Index results are pointers, not sources (REQ-464): aggregate answers
  (counts, page-name or date lists) may come from SQL alone; anything
  quoted as content routes a Phase 1 read of the hit's `page` instead.
  Never write to index.db from this workflow.

## Phase 1 - Targeted Read (Stage 2, only the chosen pages)

- Read ONLY the 3-5 pages chosen in Phase 0, JIT, respecting the simultaneous-read
  cap in [architecture](../wiki-core/references/architecture.md); batch if needed
- L3 fallback when routing yields nothing useful (namespace unclear, hub index
  missing/empty, no routing line matches): classic grep across all wiki pages ->
  top 3-5. This is the slow backing-store scan and should be the exception, not
  the default
- Data reads (REQ-470..472, only when dataset pages exist): a question
  about a dataset's CONTENTS routes via the wiki/data hub; the dataset
  page's `## data dictionary` picks the dataset and columns; row-level
  answers are computed READ-ONLY from the snapshot CSVs at the page's
  `source-file::` (python3 stdlib csv/sqlite3). Attribute the
  computation with file, package version, and row count, e.g.
  `computed from ingested/data/<pkg>-<version>/<file>.csv (n rows)`.
  Never consult a live R session for content answers (REQ-472)
- If needed, also read L1 Memory for the complete picture

## Phase 1b - Access Logging (LRU signal + routing transparency)

- For each page ACTUALLY read in full (not the Phase 0 hub-index reads), append
  one line with the verb `query` to the Access-Log page
  (wiki/reference/access-log), in the Access-Log line format from
  [formats](../wiki-core/references/formats.md)
- The `matched:` reason = the "and why" of the routing (loading transparency): on
  index routing (Phase 0) the hub `### Index` routing description / #tag that
  matched the question; on the L3 fallback the grep term that found the page;
  on an index-plane hit (Phase 0b) the index route, e.g. `fts: <term>` or
  `meetings: <range>` (REQ-464)
  (length and quoting rules: [formats](../wiki-core/references/formats.md)). The
  log then shows not just WHICH page loaded but WHY it was picked for this
  question; surfaced via the wiki-maintain status report (cache profile)
- The append is non-structural; the Access-Log commit rules in
  [formats](../wiki-core/references/formats.md) apply (no per-query git commit)
- Paper agent-log (paper.md REQ-1515): when a fully-read page is a
  paper hub or lives under `wiki/papers/<slug>/`, also append one
  read-only row to that paper's agent-log (`- (read-only)` under Pages
  written, paper.md REQ-1514); same commit discipline as the
  Access-Log append
- If the L3 fallback hits an archived page (`archived::` set), a re-hit on an
  evicted page: offer to re-promote it; move its routing line from the hub
  `### Archive` back into the `### Index`, drop the archived:: property (and reset
  status:: where it was set)

## Phase 1c - One-hop neighbors (pointers only, REQ-480..485)

- After the Phase 1 reads, collect the outgoing `[[wiki/...]]` links from the
  BODIES of the fully-read pages. Extraction is mechanical (the link text as
  written). Links into `para/`, `notes/`, and `glossary/` are NOT expanded:
  neighbor expansion stays inside the machine-written namespace (REQ-480)
- Neighbors are POINTERS, never additional reads (REQ-481): do not read a
  neighbor in full unless Phase 0 routing already selected it within the
  page budget. Present each neighbor with its hub routing description when
  one exists; the `### Index` or `### Archive` lines are already in context
  from the Phase 0 hub reads, so this costs nothing extra
- Rank by the number of DISTINCT read pages linking to the neighbor; break
  ties with live-index pages before archived ones. Cap the list at 7.
  Exclude already-read pages, hub pages, and the Schema, Dashboard, and
  Access-Log pages (REQ-482)
- Flag a neighbor whose page carries `archived::` as archived (REQ-484).
  The re-promotion offer (Phase 1b) applies only when a page is actually
  read in full, not to its appearance as a pointer
- Never Access-Log a neighbor; they are not full reads (REQ-485). A broken
  neighbor link (the target page does not exist) is reported to the user as
  a candidate lint issue, not silently dropped

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

- Two registers, always both, in this order (REQ-435):
  1. **Precise register:** the Phase 2 synthesis as-is; technical vocabulary
     intact
  2. **Plain register**, under the marker heading `In plain terms`: the SAME
     facts and caveats rewritten so a non-specialist can follow them. No
     unexplained jargon (an unavoidable technical term is explained in the
     sentence that uses it) and NO new claims; the no-fabrication rule
     (REQ-414) binds both registers (REQ-436)
- Flag stale sources (updated:: more than 90 days ago) and low-confidence sources
  with an explicit warning, in BOTH registers, phrased for each; the plain
  register never drops a warning (REQ-436). Contradictions (REQ-413) appear
  in both registers too
- After both registers, ONCE (REQ-437): source pages, "Sources:
  [[wiki/tech/deployment]], [[wiki/reference/gotchas]]"
- Plane attribution (REQ-463), part of the same shared attribution: state
  which plane answered: pages, index.db,
  or both, e.g. "Sources: [[wiki/tech/deployment]]; index.db (meetings,
  12 rows)". Include the staleness warning here when answering from a stale
  index (REQ-461)
- After the shared attribution, ONCE per answer: the Phase 1c neighbor list
  under a `Related:` line, each pointer with its routing description and
  archived flag where applicable (REQ-483). This list IS the related-pages
  suggestion; do not add a second, improvised one
- If no relevant pages are found, state clearly: "No information found in the wiki
  for this topic." and offer write-back (Phase 3); the plain register
  restates that the wiki has no answer (REQ-435)
## Mode: --prime (context briefing; prime.md REQ-1400..1431)

Prime is the proactive read path: no question, just a context. Output
is a briefing of what the wiki holds that bears on the session, not an
answer. It reuses this skill's machinery with these deltas:

- Context (REQ-1401): use the argument verbatim. Without one, derive
  the context from the conversation so far and ECHO it back at the top
  of the briefing (`Priming on: "..."`); never prime on an invisible
  context. Extract entities, topics, and project names as lexical
  terms (REQ-1402): routing-line matching, FTS, grep only - no
  embeddings, no vector store, no network model call, ever.
- Recall breadth, not routing depth (REQ-1403): read the `### Index`
  of EVERY hub (not just candidate namespaces) and match all routing
  lines against the terms. No full page opens in this phase. When
  `index_db` is configured, the Phase 0b channel MAY add FTS hits
  (stale-check first, SELECT-only, pointers never quoted content;
  REQ-1404). Terms with no routing or index hit MAY get a BOUNDED L3
  grep: at most the 3 strongest terms, at most 3 matches each
  (REQ-1405). Also check L1 Memory for topically relevant rules and
  gotchas; include matches as pointers (REQ-1406).
- Budget (REQ-1410): rank candidates by match strength and
  cross-channel agreement; read AT MOST 3 pages in full, no batching
  loop. Up to 5 further candidates are listed as pointers only (link
  plus hub routing description), unread. Each full read gets its
  one-hop neighbor list per Phase 1c (REQ-1411), is Access-Logged with
  `matched: "prime: <term>"` (REQ-1412; hubs, pointers, and neighbors
  are never logged; no per-run commit), and an `archived::` hit gets
  the Phase 1b re-promotion offer (REQ-1413).
- Briefing (REQ-1420..1424): per fully-read page, 1-3 lines on what
  the wiki knows and why it matched; then the unread pointers; then
  the neighbors; then the L1 pointers. No raw dumps, no answering
  unasked questions. Staleness, low confidence, and archived flags are
  inline and compact (REQ-1421). Every line traces to a page, routing
  line, index row, or L1 file; a term with no wiki presence gets one
  line saying so (REQ-1422). SINGLE register - the dual-register rule
  does not apply; source and plane attribution appear once at the end
  (REQ-1423). A fully empty result is exactly: "Nothing in the wiki
  bears on this context yet." - then stop; no write-back offer, no
  widened search (REQ-1424).
- Read-only contract (REQ-1430/1431): prime NEVER writes or offers
  write-back; the Access-Log append is the only write. Edit requests
  surfacing mid-run are redirected to /wiki-update or /wiki-ingest.
  Never self-trigger at session start or on a schedule; the user wires
  invocation themselves.
</workflow>
