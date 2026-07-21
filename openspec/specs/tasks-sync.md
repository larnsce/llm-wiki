# Spec: Tasks Sync - GitHub Issues as Canonical Task State

## Description

The tasks-sync seam makes GitHub Issues (plus, optionally, one user-level
GitHub Project v2) the canonical store for TASK STATE, while the Logseq
journal stays the capture layer and `para/projects/` pages stay the task
home. Two one-way flows, never a bidirectional sync:

- **open-sync (graph -> GitHub):** eligible open task blocks without an
  `issue::` property become GitHub issues after human confirmation; the
  block is stamped with `issue::` and `opened::`.
- **close-sync (GitHub -> graph, plus the graph-side companion):** issues
  closed on GitHub flip their tracked block to `DONE` and stamp `closed::`;
  a tracked block the human marked `DONE`/`CANCELED` closes its issue.
  GitHub wins on task state: an issue is never reopened from the graph.

tasks-sync is NOT a wiki workflow. It is a human-layer companion tool in
the same category as the literature sync (`scripts/lit_sync.py`, which
maintains managed properties on `notes/literature/` pages): deterministic
script, dry-run first, human confirmation before any mutation, and a
narrow, enumerated write budget. The namespace scope rule
(specs/namespaces.md REQ-965..968) is untouched; the carve-out that
sanctions this seam is namespaces REQ-969.

> Spec version: introduced for v3.7 (tasks-sync v0.1, exploration draft ->
> repo spec). This spec uses the globally unique REQ-1400..1417 range
> (the 900s, 1200s, and 1300s are taken by specs/namespaces.md, the voice
> conversation seam, and the transcript-source route landed in the same
> release; ids are unique across the spec canon). The config
> keys live in specs/config.md REQ-662..664. Deterministic behavior lives
> in `scripts/tasks_sync.py`; the `/tasks-sync` command
> (`.claude/commands/tasks-sync.md`) only orchestrates the dry-run ->
> confirm -> run ritual.

---

## Requirements

### Scope & Ownership

- REQ-1400: tasks-sync SHALL operate ONLY on journal pages (the
  `journals_dir` of specs/config.md REQ-629) and `para/projects/` pages
  (the `para_dir` of REQ-625). It SHALL NOT create, modify, or delete any
  page under `wiki/`, `notes/`, or `glossary/`, and SHALL NOT create or
  delete pages anywhere: it edits existing task blocks in place, within
  the write budget of REQ-1414, under the namespaces REQ-969 carve-out.
- REQ-1401: The seam is inert unless the config contains `tasks_repo`
  (specs/config.md REQ-662); without it every subcommand SHALL report the
  missing key and exit without touching the graph or calling `gh`. The
  GitHub Project v2 add-on (REQ-1406) activates only when `tasks_project`
  (REQ-663) is also set. tasks-sync is Logseq tier-1: on `tool: obsidian`
  it SHALL abort cleanly with a tiering message (task markers and `::`
  block properties are Logseq-native; same tiering posture as
  namespaces REQ-977).

### open-sync (graph -> GitHub)

- REQ-1402: An open-sync candidate is a block whose marker is one of
  `TODO | DOING | NOW | LATER | WAITING` and that lacks an `issue::`
  block property, AND that satisfies the promotion gate:
  - it lives on a `para/projects/` page (page ownership implies the
    project), OR
  - it lives on a journal page and links a `[[para/projects/...]]` page,
    OR
  - it lives on a journal page and carries the `#gh` tag.
  Nothing else is ever a candidate: an untagged, unlinked journal TODO
  ("buy milk") SHALL NOT reach GitHub.
- REQ-1403: The target repo for a candidate resolves in this order, first
  hit wins: the `repo::` page property of the owning or linked
  `para/projects/` page (an `owner/repo` slug, human-set); the config
  `tasks_repo`. A candidate with no resolvable repo is SKIPPED with a
  warning, never guessed.
- REQ-1404: open-sync SHALL present the full candidate list (stable
  candidate id, title, target repo, source file and line) and SHALL
  create nothing without confirmation. `--dry-run` SHALL write no graph
  bytes and SHALL invoke no mutating `gh` command. A run may be limited
  to confirmed candidates with `--ids`.
- REQ-1405: After a successful `gh issue create`, the tool SHALL write
  exactly two block-property lines under the block - `issue::
  <owner>/<repo>#<number>` and `opened:: [[<date>]]` - and nothing else.
  The stamp is written immediately per issue (never batched at the end of
  the run), so a crash mid-run cannot leave created issues unstamped
  behind later candidates.
- REQ-1406: When `tasks_project` is set, each created issue is added to
  the Project via `gh project item-add`. A failed add is a warning, not a
  rollback: the issue exists and the `issue::` stamp still lands.
  Project v2 FIELD mapping (PARA/Project single-selects) is Phase 2
  (REQ-1416).
- REQ-1407: Issue title and body are deterministic functions of the
  block: title = the block text with the marker, `[[para/projects/...]]`
  links, and `#gh` tags removed and other `[[refs]]` reduced to their
  leaf text; body = a provenance trailer naming the source file:line
  relative to the graph root and the resolved project page. After
  creation the issue is authoritative: retitling on GitHub does not touch
  the block, and editing the block text does not touch the issue (the
  link key is `issue::`, not the text).

### close-sync (GitHub <-> graph, two one-way halves)

- REQ-1410: GitHub -> graph: for every TRACKED block (has `issue::`,
  lacks `closed::`) whose issue is closed on GitHub, close-sync SHALL
  replace the marker token with `DONE` and append a `closed:: [[<date>]]`
  property line. No other byte of the block changes. Closed-issue state
  is fetched with ONE `gh issue list --state closed` call per distinct
  repo, never per issue.
- REQ-1411: graph -> GitHub: a tracked block whose marker is `DONE` or
  `CANCELED` and that lacks `closed::` SHALL close its issue (`gh issue
  close`, with reason "not planned" for `CANCELED`, and a "closed via
  journal (tasks-sync)" comment), then receive the `closed::` stamp.
  GitHub wins on state: tasks-sync SHALL NEVER reopen an issue; a block
  whose issue was closed on GitHub becomes `DONE`, not the reverse.
- REQ-1412: Idempotency is content-embedded, by construction: `issue::`
  is the sole link key; open-sync only touches blocks lacking `issue::`;
  close-sync only touches blocks lacking `closed::`. Re-running either
  flow with no external change is a byte-for-byte no-op. There is NO
  state file (the repo convention: state lives in vault content, like
  `zotero-last-sync::`); `--since` only narrows the closed-issue query
  and MUST NOT affect correctness - a full run without it yields the
  same graph.
- REQ-1415: Closed issues in a queried repo with NO tracked block, and
  tracked blocks whose `issue::` no longer resolves, are REPORTED only
  (the orphan report); tasks-sync SHALL NOT create blocks for them or
  delete their stamps.

### Mechanics & Write Budget

- REQ-1413: All `gh` invocations are single-line argv vectors executed
  without a shell. Before any flow that calls `gh`, the tool SHALL
  preflight `gh auth status`; a missing or unauthenticated `gh` is a
  clean stop (exit 2, actionable message, zero graph writes) - never
  worked around with a raw API token. Exit codes follow the suite
  convention: 0 clean, 1 warnings (skipped candidates, orphans), 2
  critical.
- REQ-1414: The complete write budget, per run: (a) insert `issue::`,
  `opened::`, `closed::` property lines under task blocks per
  REQ-1405/1410/1411; (b) replace one marker token per REQ-1410. The
  tool SHALL NOT create, reorder, or delete blocks or pages; SHALL NOT
  edit block text beyond the single marker token; SHALL NOT write a
  `#tag`; SHALL NOT touch journal content outside the stamped blocks
  (the ingest journal seam's append-only discipline, ingest REQ-094,
  stays intact for everything else).
- REQ-1417: `opened::`/`closed::` stamps are `[[YYYY-MM-DD]]` page
  references (ISO date, the journal-ref form used throughout this
  seam's design). Full `owner/repo#N` is always written to `issue::`;
  short forms (`repo#N`, `#N`) are accepted on read and resolved against
  `tasks_repo`.

### Phase 2 (specified, deferred)

- REQ-1416: Deferred to Phase 2, behind the same config gates:
  Project v2 single-select field mapping (`PARA`, `Project`) after
  `item-add`; the milestone hook (issues labeled with
  `tasks_milestone_label`, config REQ-664, append one line under a
  `## milestones` heading on the owning `para/projects/` page - inside
  the REQ-1414 budget extended by that single sanctioned append; note
  the hook targets the PARA page, never `wiki/projects/`, which would
  bypass ingest provenance); a richer standing orphan report. Until
  implemented, these are documentation only.

---

## Scenarios

### Scenario 1: first open-sync round-trip

```
GIVEN journals/2026_07_16.md contains
    - TODO Draft ingest prompt v3 [[para/projects/llm-wiki]]
AND para/projects/llm-wiki has repo:: larnsce/llm-wiki
WHEN open-sync runs and the user confirms the candidate
THEN gh issue create runs once against larnsce/llm-wiki
AND the block gains exactly two property lines:
    issue:: larnsce/llm-wiki#42
    opened:: [[2026-07-16]]
AND no other byte of the journal changes
```

### Scenario 2: re-run is a no-op

```
GIVEN the vault state after Scenario 1
WHEN open-sync runs again
THEN it finds zero candidates (the block carries issue::)
AND writes nothing and calls no mutating gh command
```

### Scenario 3: close round-trip from GitHub

```
GIVEN the block of Scenario 1 and its issue closed on GitHub
WHEN close-sync runs
THEN the marker flips TODO -> DONE
AND closed:: [[<today>]] is appended to the block's properties
AND a second close-sync run changes nothing (closed:: present)
```

### Scenario 4: graph-side completion closes the issue

```
GIVEN a tracked block the human marked DONE, with no closed::
WHEN close-sync runs
THEN gh issue close runs once with a "closed via journal" comment
AND the block gains closed:: [[<today>]]
AND the issue is never reopened afterwards even if the block is
    edited back to TODO (reported as an orphan-state warning only)
```

### Scenario 5: the gate holds

```
GIVEN a journal block "- TODO buy milk" with no project link and no #gh
WHEN open-sync runs
THEN the block is not listed as a candidate and never reaches GitHub
```

### Scenario 6: unauthenticated gh is a clean stop

```
GIVEN gh is absent or gh auth status fails
WHEN open-sync (real run) or close-sync starts
THEN the tool exits 2 with an actionable message
AND the graph is byte-for-byte unchanged
```

---

## Acceptance Criteria

- [ ] Eligibility gate: only linked/tagged/para-resident open blocks are candidates
- [ ] Confirmation before creation; dry-run mutates nothing anywhere
- [ ] Stamps are exactly issue::/opened::/closed:: lines plus one marker flip
- [ ] Both flows are idempotent with no state file; --since is efficiency-only
- [ ] One closed-issue listing per repo; never reopens an issue
- [ ] gh preflight failure exits 2 with zero graph writes
- [ ] wiki/, notes/, glossary/ untouched in every run

---

## Dependencies

- specs/namespaces.md - REQ-969 (the carve-out sanctioning this seam);
  the scope rule REQ-965..968 that tasks-sync is NOT bound by but must
  not disturb
- specs/config.md - REQ-662..664 (`tasks_repo`, `tasks_project`,
  `tasks_milestone_label`), REQ-625 (`para_dir`), REQ-629
  (`journals_dir`, amended to name this seam's journal stamps)
- specs/ingest.md - REQ-090..095 (the journal seam whose append-only
  discipline REQ-1414 preserves outside stamped blocks)
- docs/para-notes-workflow.md - task-marker conventions, the
  `para/projects/` layout, the archive procedure
- docs/tasks-sync-workflow.md - the vault-side guide (`repo::`
  convention, `#gh` gate, daily-review hook point)
