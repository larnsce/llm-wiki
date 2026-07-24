# Spec: /wiki-query --prime - Context Priming (Auto-Associative Recall)

## Description

Prime is the proactive read path. Instead of answering a question, it takes a
description of what the session is about ("I'm drafting the sanitation course
module with Anna this week") and surfaces the wiki pages, routing pointers,
one-hop neighbors, and L1 rules that are relevant to that context - before
anyone has formulated a precise question. The output is a context briefing,
not an answer.

The design is adapted from the `prime` tool in daniloc/mnemion (auto-associative
recall: describe the conversational context, get relevant entries plus their
one-hop links back). mnemion implements it with embeddings and KNN search;
llm-wiki implements the same recall shape lexically, on the existing two-stage
routing machinery (hub indexes, optional index.db FTS, bounded grep), because
the zero-dependency constraint (bash, python3 stdlib, git) excludes embedding
models and vector stores.

Prime is a mode of the query skill (`/wiki-query --prime`), not a separate
skill: it shares Phase 0 routing, the JIT page budget, Access-Logging, and the
one-hop neighbor machinery (query.md REQ-480..485).

Status: implemented in skills/wiki-query (2026-07-24). Canon drafted
2026-07-21; the cycle plan is `docs/roadmap-v3.7-recall.md`.

---

## Requirements

### Phase 0: Input

- REQ-1400: The system SHALL read `llm-wiki.yml` first to determine tool mode,
  wiki path, and memory path (config.md binds).
- REQ-1401 (context source): The context SHALL come from the explicit argument
  (`/wiki-query --prime "<context description>"`) when given. When invoked
  without an argument, the system SHALL derive the context from the current
  conversation (topics, entities, and tasks discussed so far) and SHALL echo
  the derived context back verbatim at the top of the briefing, so the user
  sees what was primed on. Priming on an unstated, invisible context is not
  allowed.
- REQ-1402 (lexical term extraction): The system SHALL extract candidate
  entities, topics, and project names from the context as search terms. All
  retrieval SHALL be lexical (routing-line matching, FTS, grep). The system
  MUST NOT use embeddings, vector search, or any network model call; the
  zero-dependency constraint (project.md) binds this spec explicitly.

### Phase 1: Recall (breadth-first Stage 1)

- REQ-1403 (hub breadth): Unlike question routing (query.md REQ-441..443,
  which narrows to candidate namespaces), prime SHALL read the `### Index`
  section of EVERY hub page and match all routing lines
  (`[[link]] -- description #tags`) against the extracted terms. Hubs are the
  bounded, cheap surface built for exactly this scan; full pages are not
  opened in this phase.
- REQ-1404 (index.db channel): When the two-plane storage is configured
  (config REQ-627, storage REQ-1130..1133), the system MAY additionally run
  full-text SELECTs over index.db for the extracted terms as a recall channel.
  The staleness check before every index read (query REQ-461) and the
  SELECT-only frozen-schema rule (query REQ-462) bind unchanged. Index hits
  are pointers that route page reads, never quoted content (query REQ-464).
- REQ-1405 (bounded grep fallback): Terms that match no routing line and no
  index row MAY be checked with a bounded L3 grep (at most the 3 strongest
  terms, at most 3 matches each). An unbounded full-corpus sweep is not a
  prime behavior.
- REQ-1406 (L1 pass): The system SHALL check L1 Memory files for rules,
  gotchas, or identity facts topically relevant to the context
  (l1-l2-routing.md binds) and include matching files as pointers in the
  briefing.

### Phase 2: Selection and Reads

- REQ-1410 (budget): The system SHALL rank recall candidates by match strength
  (routing-line term hits, cross-channel agreement) and read AT MOST 3 pages
  in full - the JIT budget (query REQ-404) binds, with no batching loop: prime
  is a briefing, not an exhaustive sweep. Up to 5 further candidates SHALL be
  listed as routing pointers only (link + hub routing description), unread.
- REQ-1411 (one-hop neighbors): For each page read in full, the system SHALL
  list its one-hop neighbors per the neighbor machinery in query.md
  REQ-480..485 (pointers with routing descriptions, never additional full
  reads).
- REQ-1412 (access logging): Each page read IN FULL SHALL be Access-Logged per
  query REQ-450, with the matched reason recording the prime route, e.g.
  `matched: "prime: <term>"`. Hub-index reads, pointers, and neighbors are NOT
  logged (query REQ-450 already scopes logging to full reads). The append is
  non-structural (query REQ-451: no per-run git commit).
- REQ-1413 (archived re-hit): If a full read lands on a page marked
  `archived::`, the re-promotion offer of query REQ-452 applies.

### Phase 3: Briefing Output

- REQ-1420 (briefing shape): The output SHALL be a context briefing: for each
  fully-read page, 1-3 lines on what the wiki knows and why it matched;
  then the unread routing pointers; then the one-hop neighbor list; then the
  L1 pointers. It MUST NOT dump raw page content and MUST NOT answer
  questions that were not asked - synthesis belongs to the question path
  (query REQ-410..414).
- REQ-1421 (flags carry over): Staleness (updated:: > 90 days, query REQ-431),
  low confidence (query REQ-432), and `archived::` status SHALL be flagged
  inline on the affected briefing entries, in compact form.
- REQ-1422 (no fabrication): The no-fabrication rule (query REQ-414) binds:
  every briefing line traces to a page, a routing line, an index row, or an
  L1 file. If a context term has no wiki presence, the briefing says so in
  one line rather than inventing a summary.
- REQ-1423 (single register): The briefing is routing output, not a
  synthesized answer; the dual-register requirement (query REQ-435..437)
  does NOT apply to prime. Source attribution (query REQ-430) and plane
  attribution (query REQ-463, when index.db was consulted) DO apply, once,
  at the end of the briefing.
- REQ-1424 (empty result): When nothing relevant is found on any channel, the
  system SHALL state that briefly ("Nothing in the wiki bears on this
  context yet.") and stop. It MUST NOT offer write-back and MUST NOT widen
  the search beyond REQ-1405.

### Read-Only Contract

- REQ-1430 (read-only): Prime NEVER writes, creates, or modifies wiki pages
  and NEVER offers write-back (unlike query Phase 3, REQ-420..423). The ONLY
  write a prime run may perform is the Access-Log append of REQ-1412. Requests
  to change content that surface during a prime run are redirected to
  `/wiki-ingest` or `/wiki-update`.
- REQ-1431 (no auto-run): The skill MUST NOT self-trigger at session start or
  on any schedule. The user wires invocation themselves (a CLAUDE.md pointer,
  an alias, or a manual call). This mirrors the no-self-scheduling stance of
  prune (prune.md REQ-622).

---

## Scenarios

### Scenario 1: Prime with explicit context

```
GIVEN the wiki/tech hub `### Index` routes [[wiki/tech/strapi]] -- Headless CMS, ports, deploy gotchas #strapi #deploy
AND the wiki/projects hub routes [[wiki/projects/blog-relaunch]] -- Strapi blog migration, status, decisions #strapi
AND L1 Memory contains feedback_deploy_ram.md ("Stop ClamAV before deploy")
WHEN the user runs /wiki-query --prime "working on the blog deploy pipeline today"
THEN the system SHALL read every hub `### Index` (Phase 1) but no full page yet
AND select and fully read wiki/tech/strapi and wiki/projects/blog-relaunch (<= 3 reads)
AND list each page's one-hop neighbors as pointers (query REQ-480..485)
AND include the L1 pointer feedback_deploy_ram.md (deploy gotcha)
AND append Access-Log lines with matched: "prime: deploy" / "prime: strapi" for the two full reads only
AND output a briefing (no raw dumps, no question answered)
    ending with: Sources: [[wiki/tech/strapi]], [[wiki/projects/blog-relaunch]] + L1 Memory
```

### Scenario 2: Prime without an argument echoes the derived context

```
GIVEN an ongoing conversation about migrating voice notes into the journal
WHEN the user runs /wiki-query --prime with no argument
THEN the system SHALL derive the context from the conversation
AND open the briefing with: Priming on: "voice note migration, journal summaries"
AND proceed as in Scenario 1 with terms extracted from that derived context
```

### Scenario 3: Nothing relevant

```
GIVEN no hub routing line, index row, or L1 file matches "beekeeping"
WHEN the user runs /wiki-query --prime "planning the beekeeping season"
THEN the system SHALL run at most the bounded grep of REQ-1405
AND output one line: "Nothing in the wiki bears on this context yet."
AND NOT offer to create a page (REQ-1424, REQ-1430)
```

### Scenario 4: Prime stays read-only

```
GIVEN a prime briefing surfaced a stale claim on wiki/tech/strapi
WHEN the user says "fix that port number while you're at it"
THEN the system SHALL NOT edit the page inside the prime run
AND SHALL redirect: "That's an edit - run /wiki-update on wiki/tech/strapi."
```

---

## Acceptance Criteria

- [ ] Explicit context argument is used verbatim; missing argument derives
      context from the conversation and echoes it at the top of the briefing
- [ ] All retrieval is lexical - no embeddings, no vector store, no network
- [ ] Phase 1 reads hub `### Index` sections only (all hubs, no full pages)
- [ ] index.db, when configured, is consulted SELECT-only with a prior
      stale-check; hits become page reads, never quoted content
- [ ] Grep fallback is bounded (<= 3 terms, <= 3 matches each)
- [ ] At most 3 full page reads; further candidates appear as pointers only
- [ ] One-hop neighbors listed per query REQ-480..485
- [ ] L1 Memory checked and relevant files included as pointers
- [ ] Every full read Access-Logged with a `prime: "<term>"` matched reason;
      no per-run git commit
- [ ] Stale, low-confidence, and archived flags carried into the briefing
- [ ] Single-register briefing; attribution once at the end
- [ ] No fabrication; empty result is one line, with no write-back offer
- [ ] No wiki writes of any kind besides the Access-Log append
- [ ] No auto-run at session start; invocation is always user-wired
- [ ] Works in both Logseq and Obsidian modes

---

## Dependencies

- specs/config.md - `llm-wiki.yml` loading; REQ-627 for the optional index.db
- specs/query.md - REQ-404 (JIT budget), REQ-414 (no fabrication), REQ-430..432
  (attribution and flags), REQ-450..452 (Access-Log, re-promotion), REQ-461..464
  (two-plane rules), REQ-480..485 (one-hop neighbors; implemented first, see
  `docs/roadmap-v3.7-recall.md`)
- specs/schema.md - hub `### Index`/`### Archive` structure, page properties
- specs/l1-l2-routing.md - when L1 Memory is relevant
- specs/storage.md - REQ-1130..1133 (index.db schema and staleness), optional
