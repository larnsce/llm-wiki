# /tasks-sync - GitHub Issues as canonical task state

Sync open task blocks (journal + `para/projects/` pages) into GitHub
Issues, and closed issues back into the graph, via two one-way flows.
GitHub wins on task state; the graph never reopens a closed issue.
Spec: `openspec/specs/tasks-sync.md` (REQ-1400..1417; the `para/`
write carve-out is namespaces REQ-969). Guide:
`docs/tasks-sync-workflow.md`.

## Preconditions (tell the user and stop if unmet)

1. The GitHub CLI is installed and authenticated (`gh auth status`).
   Never work around a failed auth with a raw API token (REQ-1413).
2. `tasks_repo` is set in `llm-wiki.yml` (config REQ-662); without it
   the seam is inert. `tasks_project` (REQ-663) is optional.
3. The vault resolves via `llm-wiki.yml` discovery (or pass
   `--config <path>`); `tool: logseq` - tasks-sync is Logseq tier-1.

## Workflow

1. **open-sync, dry-run first, always:**

   ```
   python3 scripts/tasks_sync.py open --dry-run
   ```

   Show the user the candidate table (id, title, repo, source). Only
   blocks passing the promotion gate appear: on a `para/projects/`
   page, or in a journal with a `[[para/projects/...]]` link or `#gh`
   tag (REQ-1402). "buy milk" never reaches GitHub.

2. **Real run only after the user confirms** (all candidates, or a
   subset via the ids from the dry-run list):

   ```
   python3 scripts/tasks_sync.py open
   python3 scripts/tasks_sync.py open --ids a1b2c3d4,e5f6a7b8
   ```

3. **close-sync, dry-run first,** then real run after confirmation:

   ```
   python3 scripts/tasks_sync.py close --dry-run
   python3 scripts/tasks_sync.py close
   ```

   Relay the orphan report (closed issues with no tracked block,
   blocks edited back to TODO after their issue closed) - report
   only, never acted on (REQ-1415).

4. **Review and commit** (in the vault repo, not this repo): show
   `git status` of the touched journal and `para/projects/` files,
   then commit as `tasks: sync GitHub issues (<n> opened, <n> closed)`.

Standalone or as a daily-review step: a personal daily-review skill
should invoke `/tasks-sync` as one step (this repo does not ship
daily-review). After a failed run, just rerun - both flows are
idempotent by construction.

## Guarantees the script keeps (do not break them by hand-editing output)

- The only writes are `issue::`/`opened::`/`closed::` property lines
  under task blocks and one open-marker -> `DONE` flip per closed
  issue (REQ-1414). No block or page is ever created, reordered, or
  deleted; block text is never edited; no `#tag` is ever written.
- `issue::` is the sole link key and the only state - there is no
  state file (REQ-1412). open-sync only touches blocks lacking
  `issue::`; close-sync only touches blocks lacking `closed::`;
  re-running either flow is a byte-for-byte no-op. `--since` only
  narrows the closed-issue query.
- Stamps land immediately per issue (REQ-1405): a crash mid-run never
  leaves created issues unstamped behind later candidates.
- A missing or unauthenticated `gh` is a clean stop (exit 2) with
  zero graph writes; `wiki/`, `notes/`, and `glossary/` are never
  touched in any run (REQ-1400).
- Issues are never reopened from the graph: a block edited back to
  `TODO` after its issue closed is reported, not acted on (REQ-1411).
