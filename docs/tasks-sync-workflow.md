# GitHub Issues as canonical task state (tasks-sync)

How to run task state through GitHub Issues (plus, optionally, one
user-level GitHub Project v2) while the Logseq journal stays the capture
layer and `para/projects/` pages stay the task home. Driven by the
`/tasks-sync` command (`scripts/tasks_sync.py`); the normative spec is
[`openspec/specs/tasks-sync.md`](../openspec/specs/tasks-sync.md).

> **Scope.** This extends the [PARA workflow](para-notes-workflow.md).
> `para/` stays human-owned; tasks-sync is the one sanctioned machine
> writer in it (namespaces REQ-969) and its write budget is tiny:
> `issue::`/`opened::`/`closed::` property stamps and a marker flip to
> `DONE` when an issue closes. Everything else in this guide is
> something **you** set up (the repos, the Project, the `repo::`
> properties) or do in Logseq (write TODOs, mark them DONE).

## The model

Two one-way flows, never a bidirectional sync:

- **open-sync (graph -> GitHub).** Eligible open task blocks without an
  `issue::` property become GitHub issues after you confirm a candidate
  list. The block is stamped so re-runs cannot duplicate.
- **close-sync (GitHub -> graph).** Issues closed on GitHub flip their
  block to `DONE` and stamp `closed::`. The companion half: a tracked
  block you marked `DONE`/`CANCELED` in Logseq closes its issue.
  **GitHub wins on task state** - the graph never reopens an issue.

Idempotency is content-embedded: `issue::` is the sole link key, there
is no state file, and a full re-run is always safe and always correct.

## One-time setup

1. **Create a private issues-only `tasks` repo** for everything without
   a code repo (the GitHub personal-tracking pattern). Issues for
   coding projects live in the real code repo.
2. Optionally **create one user-level GitHub Project (v2)** spanning all
   repos as the unified view.
3. Configure the seam in `llm-wiki.yml` (config REQ-662..664):

   ```yaml
   tasks_repo: <owner>/tasks       # default repo for issues
   tasks_project: <owner>/1        # optional: Project v2 as owner/number
   ```

4. On each `para/projects/<name>` page that has its own code repo, add
   a `repo::` page property (human-set; the tool only reads it):

   ```
   type:: project
   status:: active
   outcome:: ...
   repo:: <owner>/<repo>
   ```

   Tasks from that project's page (or journal tasks linking it) file
   there; everything else defaults to `tasks_repo`.

## The promotion gate

Only these blocks are open-sync candidates - deliberate promotion, like
the `raw/` seam, never silent absorption:

- any open-marker block (`TODO`/`DOING`/`NOW`/`LATER`/`WAITING`) **on a
  `para/projects/` page**, or
- a journal block that **links a project page**:
  `- TODO Draft ingest prompt v3 [[para/projects/llm-wiki]]`, or
- a journal block with the explicit **`#gh` tag**:
  `- TODO Renew domain #gh`.

An untagged, unlinked journal TODO ("buy milk") never reaches GitHub.

## What a synced block looks like

After open-sync:

```
- TODO Draft ingest prompt v3 [[para/projects/llm-wiki]]
  issue:: larnsce/llm-wiki#42
  opened:: [[2026-07-16]]
```

After close-sync (the issue was closed on GitHub):

```
- DONE Draft ingest prompt v3 [[para/projects/llm-wiki]]
  issue:: larnsce/llm-wiki#42
  opened:: [[2026-07-16]]
  closed:: [[2026-07-18]]
```

`issue::` is written as the full `owner/repo#N` and is the stable link
key - the analogue of `zotero-last-sync::` on literature pages. Edit
the block text freely afterwards; the issue title is frozen at creation
and GitHub is authoritative from then on (REQ-1407).

## Daily rhythm

Run `/tasks-sync` standalone or as one step of your daily review:

1. `open --dry-run` -> confirm the candidate list -> `open`.
2. `close --dry-run` -> confirm -> `close`.
3. Commit the vault (`tasks: sync GitHub issues (...)`).

`status` prints a read-only count of candidates, tracked-open blocks,
and blocks awaiting an issue close. After any failure, just re-run.

## Edge cases (v0.1 stances)

| Case | Stance |
|---|---|
| Block text edited after the issue exists | Issue title frozen; GitHub authoritative (link key still matches) |
| Issue retitled/edited on GitHub | Block untouched |
| Block edited back to `TODO` after its issue closed | Reported only; the issue stays closed - never reopened |
| Issue closed on GitHub with no tracked block | Orphan report only; no block is created |
| Issue deleted | Orphaned `issue::` reported; manual cleanup |
| Duplicate task captured twice | Two candidates - the confirm list is the catch |
| Obsidian vault | Clean abort; tasks-sync is Logseq tier-1 (REQ-1401) |

## Archiving a project

Unchanged from the [manual procedure](para-notes-workflow.md): finish or
cancel the open tasks (close-sync closes their issues), distill, harvest
via `raw/para-<project>.md` if durable, move the page to
`para/archives/`. On the GitHub side, close what remains and archive the
Project view entry. No repo deletion involved.

## Phase 2 (specified, not yet implemented)

Per spec REQ-1416: Project v2 single-select field mapping (`PARA`,
`Project`), the milestone hook (issues labeled `milestone` append one
line under `## milestones` on the owning **para** project page - never
`wiki/projects/`, which would bypass ingest provenance), and a richer
standing orphan report.
