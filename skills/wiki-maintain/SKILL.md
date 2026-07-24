---
name: wiki-maintain
description: Wiki maintenance in two modes. Status (default, read-only) reports metrics, health, the hot/cold cache profile, and recent activity. Prune (write action, on request or "prune" argument) runs LRU-Demote, evicting cold pages from the live hub index. Use for "how is the wiki doing" and for periodic pruning.
---

# wiki-maintain

Maintain the wiki's cache hygiene. Two modes:

- **status** (default, read-only): metrics and health overview including the
  hot/cold cache profile. Runs when the skill is invoked without arguments or with
  `status`. It modifies NO vault files. The single exception is an OPT-IN
  index.db rebuild (Phase 2d, storage REQ-1142): on an explicit yes it may
  rewrite the derived, gitignored `index.db` (never a vault page); detection is
  read-only and a rebuild never happens without confirmation.
- **prune** (write action): LRU-Demote; evict cold pages from the live hub index.
  Runs only when explicitly requested (`prune`, optionally `--months N`, default
  6 months).

Spec: openspec/specs/prune.md REQ-600..622 (prune); status is the read-only report
ported from the status verb of the legacy v1 single command, reusing the health rules of
openspec/specs/lint.md REQ-100..222 without writes

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool mode, paths, namespaces).
- [architecture](../wiki-core/references/architecture.md): LRU-Demote invariants
  (eviction is not deletion, never rename or move files), commit discipline,
  namespace scope rule.
- [formats](../wiki-core/references/formats.md): hub `### Index` / `### Archive`
  routing-line format, Access-Log format and parsing rules.

<role>
Wiki maintainer for a personal or team knowledge base. You keep two-stage routing
precise as the wiki grows: report its health and access profile, and evict cold
pages from the live index without ever breaking a link.
</role>

<workflow>
## Mode: status (read-only report)

Phase 1 - Metrics:

- Count wiki pages
- Break down by namespace
- Break down by type (entity, project, knowledge, feedback, hub)
- Find the oldest and newest updated dates
- Count total [[cross-references]]

Phase 2 - Health:

- Lightweight lint (NO file modifications)
- Report: orphans, stale pages, broken refs, index drift

Phase 2b - Cache Profile (from the Access-Log page):

- Hot pages: most-queried pages (last 30 days), top 5
- Cold pages: active pages with last access > N months (demote-ready for the next
  prune)
- Live-index size per namespace (routing lines in `### Index`) vs. archive-index
  size
- Last prune run (newest archived:: date) plus a recommendation when the cold-page
  count is high
- Routing transparency: break down the most frequent `matched:` reasons per hot
  page from recent log lines; shows not just WHICH pages are hot but WHY (which
  index description / grep term pulls them). Surfaces mis-routing: a page always
  hit via the same grep term instead of its index line signals a weak or missing
  routing description in its hub `### Index`

Phase 2c - Data-package staleness (only when `data_packages` is
configured, ingest REQ-106):

- Run `Rscript scripts/data_pkg_sync.R --check` and include its report:
  which registered packages have a newer version on GitHub than the
  newest local snapshot. Detection only; when something is stale,
  recommend `/data-sync`, never sync from here. Skip silently when the
  config key is absent or Rscript is unavailable (note the degradation
  in the report)

Phase 2d - index.db freshness (storage REQ-1140a/1142):

- `index.db` is rebuilt lazily at query time (storage REQ-1133), so a stale
  or missing index here is EXPECTED when no index-plane query has run, not a
  defect. Run
  `python3 skills/wiki-core/scripts/rebuild_index.py --config <llm-wiki.yml> --stale-check`
  and report the freshness state:
  - missing (`index n/a`): informational - "builds on the first index-plane
    query"; do not flag as a problem;
  - fresh (stamp matches): report the rebuild age from the index.db mtime;
  - stale (exit 1): report how far the index lags, then OFFER to rebuild:
    "index.db is stale (vault moved since last rebuild). Rebuild now? [y/N]".
- This is the ONE place status may propose a write. Detection is read-only;
  the rebuild happens only on an explicit yes and runs
  `rebuild_index.py --config <llm-wiki.yml>` (no flag). A no leaves the index
  untouched - the next index-plane query rebuilds it lazily (REQ-1133).
  Status modifies no vault files regardless; a confirmed rebuild only writes
  the derived `index.db`, never a page. Skip silently when no `index_db` path
  is configured or the script is unavailable (note the degradation).

Phase 3 - Activity:

- Git log for wiki changes (last 7 days, last 30 days)
- Most recently updated pages
- Pages with most incoming links

Phase 4 - Output:

- Formatted dashboard with metrics
- Comparison to the last status run (if a Dashboard page exists)

## Mode: prune (LRU-Demote, scheduled)

Purpose: evict cold pages from the live hub index so two-stage routing stays
precise as the wiki grows (cache analogy: eviction from the index/TLB; the
LRU-Demote mechanism and its invariants are defined in
[architecture](../wiki-core/references/architecture.md)). Meant as a periodic run
(default cadence N = 6 months); wire it via your scheduler. The skill does NOT
self-schedule.

Phase 1 - Access Profile:

- Read llm-wiki.yml first (tool mode, paths)
- Read the Access-Log page (wiki/reference/access-log)
- Determine last access per page (newest log entry; never logged -> use created::
  as a proxy)
- Threshold: no access in N months (default 6, via --months N)
- EXEMPT from demotion: hub pages (type hub), Schema, Dashboard, the Access-Log
  itself, and status:: active projects (never evict in-flight work, even if
  unread)

Phase 2 - Demote Candidates:

- List candidates (page -- last access -- age in months) and SHOW the user before
  any write (demotion is opt-in)
- For each confirmed candidate:
  - Add `archived:: <today>`, the canonical "demoted" marker, valid on any page
    type (NEVER touch created::/updated::). For entity pages (whose status enum
    allows it) ALSO set status:: archived; for project/knowledge pages do NOT set
    an out-of-enum status value (openspec/specs/schema.md REQ-565/566)
  - Move the routing line from the hub's `### Index` VERBATIM into the hub's
    `### Archive` section (move, not delete)
  - Leave the page file itself untouched apart from the property change; the
    never-rename / never-move invariant and its rationale (a rename breaks every
    incoming [[link]]) are defined in
    [architecture](../wiki-core/references/architecture.md), as is the rule that
    re-promotion on a later re-hit belongs to wiki-query, never to prune

Phase 3 - Report + Commit:

- Demoted list, new live-index size per namespace, hot pages (top access) for
  contrast
- Git commit (structural change: hub index + page properties); this commit also
  carries any pending Access-Log appends (openspec/specs/prune.md REQ-621)
- Note: next prune due in N months; the user may wire it via their scheduler
</workflow>
