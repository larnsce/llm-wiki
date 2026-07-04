# Architecture: L1/L2 cache, hub-index routing, LRU-Demote, scope

Spec: openspec/specs/l1-l2-routing.md REQ-300..364; openspec/specs/query.md
REQ-440..452; openspec/specs/prune.md REQ-600..622; openspec/specs/namespaces.md
REQ-960..981

## L1/L2 cache model

- L1 = Claude Memory (auto-loaded every session): rules, gotchas, identity,
  credentials.
- L2 = Wiki (on-demand): projects, workflows, research, deep knowledge.
- Routing rule: "Would a mistake without this knowledge be dangerous or
  embarrassing? -> L1. Merely inconvenient? -> L2." (REQ-300..304)
- Credentials MUST stay in L1; the wiki is git-tracked, so NEVER store credentials,
  passwords, or API tokens in wiki pages (REQ-312, REQ-330..332). This is a hard
  security boundary.
- New quick rules and gotchas -> recommend Memory, not Wiki. New projects,
  workflows, research -> Wiki (REQ-310..324). L1 feedback rules belong in Memory,
  not in the wiki.

## Hub-Index-Routing (the wiki's page table)

L1's auto-loaded memory index has no L2 counterpart by default. Each hub page
carries an `### Index` of routing lines, one per child (format in
[formats.md](formats.md)). Query becomes two-stage: read the cheap hub indexes,
pick the most relevant pages by description, read only those full pages. This is
the wiki's "page table / TLB"; no more grep-over-everything.

Full-text grep over all wiki pages is the L3 FALLBACK, the slow backing-store
scan: the exception, not the default retrieval path (query REQ-444). The trigger
conditions are operational steps of the wiki-query workflow.

## LRU-Demote (index eviction)

Query logs every full-page hit to the Access-Log; prune evicts cold pages (no
access in N months) from the live index. Invariants (prune REQ-611..615, schema
REQ-565..568):

- Eviction != deletion: the file stays, marked `archived::`, still greppable as the
  L3 fallback, all incoming `[[links]]` intact. The page is only out of routing,
  not out of the graph.
- NEVER rename a demoted page or move its file: the tool links by page name, so a
  move would break every incoming `[[link]]` (a broken-ref storm). Only the routing
  line and the page properties change; the exact demote steps are wiki-maintain's
  prune workflow.
- Re-promotion on a re-hit is query's responsibility, never prune's (query
  REQ-452).

## Access-Log (LRU signal + routing transparency)

The Access-Log page records every full-page read together with a `matched:` reason
(WHY the page was picked). It feeds prune's last-access computation and status's
cache profile. Format and rules in [formats.md](formats.md).

## Retrieval and commit discipline

- Load at most 3 wiki pages simultaneously (JIT retrieval); batch when more are
  relevant (query REQ-404).
- Git commit after every structural change (hub index edits, page property
  changes, page creation). The Access-Log append is the one exception: it is
  non-structural and never gets a per-query commit (rules in
  [formats.md](formats.md)).

## Namespace scope rule

Every wiki workflow (ingest, query, prune, lint, status, audit, update, and any
future verb) operates ONLY on pages in the wiki namespace (namespaces REQ-965).
Never create, modify, lint, or audit pages under `para/` or `notes/` (human-owned;
REQ-966), and never modify non-wiki pages such as existing notes or journals.
Reading `para/` or `notes/` pages for context when the user asks is allowed, but
never write to them as a side effect (REQ-967). The only path from `para/` or
`notes/` into the wiki is the promotion seam through `raw/` and the ingest
pipeline (REQ-970..973). This section is the single statement of the scope rule
loaded by every skill (REQ-968).
