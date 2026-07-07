# R data packages -> `wiki/data` (the data-package seam)

How tabular data enters the vault so `/wiki-query` can answer questions
about it, and how the vault stays current when a data package updates on
GitHub. Spec: `openspec/specs/ingest.md` REQ-100..106, config
REQ-660/661, query REQ-470..472. Issues #92..#95.

## Why whole packages, not CSVs

An R data package is a self-describing, versioned dataset bundle:

- `DESCRIPTION` - name, version, license, URL: the provenance record and
  the version signal
- `man/*.Rd` (from roxygen `R/data.R`) - description and the
  per-variable dictionary (`\describe`): the routing key `/wiki-query`
  needs, already machine-readable
- `data/*.rda` - the canonical data objects
- `inst/extdata/*.csv` - portable copies
- `NEWS.md` - what changed between versions

Ingesting only a CSV throws away the dictionary and the version signal
and forces you to recreate both by hand. Plain CSVs without a package
still work: drop them in `raw/` and `/wiki-ingest` as type `data`; the
seam below is for the packaged case.

## What makes a package syncable

Before registering a package, check it has the three things the sync
reads. Any package that passes `R CMD check` with documented data has
all of them:

1. **`DESCRIPTION`** with a `Version:` field. This is the version
   signal for snapshots and the staleness check.
2. **Data**: `data/*.rda` (or `.RData`) files containing data frames,
   and/or CSVs in `inst/extdata/`. Only data frames are materialized to
   CSV; matrices, lists, and other objects inside an `.rda` are skipped
   silently. A data frame with list columns will fail `write.csv`; flag
   such a package rather than syncing it.
3. **Rd documentation** (`man/<dataset>.Rd` with `\docType{data}`),
   usually generated from a roxygen `R/data.R`. The `\description`
   becomes the page's description; the `\format`'s
   `\describe{\item{var}{...}}` entries become the data dictionary; the
   `\source` lands in the snapshot doc. A dataset without an Rd file
   still syncs, but its page says "(no variable dictionary in the
   package docs)", which makes it nearly invisible to `/wiki-query`
   routing. Documenting the data in the package is the fix, not editing
   the page.

## Adding a package, step by step

### 1. Register it in `llm-wiki.yml`

Add the GitHub slug (`owner/repo`, exactly one slash) under
`data_packages`, and set the retention if you have not already:

```yaml
# llm-wiki.yml (in the vault root)
data_packages:
  - larnsce/sanitationdata
  - larnsce/washdata
data_snapshots_keep: 3
```

Validate the config before the first run:

```
python3 skills/wiki-core/scripts/check_config.py <vault>/llm-wiki.yml
```

A bad slug (no slash, or an absolute path pasted by accident) is a
CRITICAL here, not a runtime surprise.

### 2. Dry-run

Run `/data-sync`, or directly:

```
Rscript scripts/data_pkg_sync.R --dry-run
```

The script discovers `llm-wiki.yml` the same way the Python tooling
does (env var, walk-up, pointer file); pass `--config <path>` to be
explicit. To sync ONE package out of several registered, add
`--pkg owner/repo`.

Read the plan. For each package you should see one line per dataset
page and one snapshot line:

```
create  wiki___data___sanidata___toilets.md
create  wiki___data___sanidata___pumps.md
snapshot ingested/data/sanidata-1.0.0 (2 datasets) [dry-run, nothing written]
```

Things to check at this point:

- **Dataset count.** Fewer datasets than expected usually means an
  `.rda` holds something that is not a data frame, or the file sits
  outside `data/`.
- **`create` vs `update`.** `update` on a first-ever sync means a page
  with that name already exists; look at it before proceeding.
- **`skip ... (snapshot <version> already exists)`.** The version on
  GitHub is already in the vault. Nothing to do; the script never
  rewrites an existing snapshot. (To force a redo of the same version,
  for example after fixing the package's Rd docs without a version
  bump, delete `ingested/data/<pkg>-<version>/` and re-run. Bumping the
  package version is the cleaner path.)
- **`prune` lines.** Retention runs at the end of a sync; anything
  listed as `prune` will be deleted on the real run. `retain ...
  (referenced by a page, REQ-105)` means a page cites that snapshot and
  it is safe forever.

### 3. Real run and commit

Drop `--dry-run`, run again, then review and commit in the vault repo:

```
Rscript scripts/data_pkg_sync.R
cd <vault> && git status
git add pages/wiki___data* ingested/data/<pkg>-<version>
git commit -m "data: sync <pkg> <version> (<n> datasets)"
```

One commit per sync: the snapshot, the dataset pages, and the hub
routing lines belong together, the same atomicity rule as ingest.

### 4. Look at what landed

- `ingested/data/<pkg>-<version>/` holds one `<dataset>.csv` and one
  `<dataset>.md` per dataset. The `.md` is the extracted documentation;
  open it once to confirm the variable dictionary came through.
- `pages/` gained `wiki___data.md` (the hub, created on first sync),
  `wiki___data___<pkg>.md` (the package page with one routing line per
  dataset), and `wiki___data___<pkg>___<dataset>.md` per dataset. The
  filename separator matches your vault's existing convention (`___`
  by default; `%2F` if the vault already uses it).
- In Logseq, the dataset page shows the managed properties, the
  description, and the data dictionary. Test the seam end to end with
  one `/wiki-query` question the dictionary can answer.

### 5. Write your notes in the right place

Two places on a dataset page survive every future sync:

- **`## my notes`** - free-form, never touched by the machine.
- **Nested under a dictionary row** - indent one level deeper than the
  row (a child bullet of it). Preserved across regenerations, though it
  re-attaches at the end of the dictionary block when the rows change.

Do NOT write free-standing bullets at the same level as the dictionary
rows inside `## description` or `## data dictionary`: those two blocks
are machine territory and are regenerated wholesale on the next sync
(ingest REQ-102).

## Special cases

- **A package you develop locally** (or one not on GitHub): sync from
  the checkout instead of a slug:

  ```
  Rscript scripts/data_pkg_sync.R --local ~/gitrepos/mypkg --dry-run
  ```

  The version still comes from the checkout's DESCRIPTION, so bump it
  there when the data changes. Local packages do not need to be in
  `data_packages` (that key drives the GitHub download and `--check`).
- **Private GitHub repos:** the downloader uses the public codeload
  endpoint and cannot authenticate. Clone the repo yourself and use
  `--local <clone>`; `--check` will report the package as unreachable,
  which is expected.
- **Same dataset name in `data/` and `inst/extdata/`:** the `.rda`
  version wins (it is materialized first; the extdata copy is not
  double-counted).
- **Large data:** snapshots are git-tracked in the vault. Above a few
  MB per version, reconsider: keep `data_snapshots_keep` low, or treat
  the package as out of scope for the seam and ingest a summary
  instead.

## Query it

`/wiki-query` routes dataset questions via the `wiki/data` hub and the
data-dictionary sections, then computes read-only on the snapshot CSVs
(stdlib csv/sqlite3), attributing file, package version, and row count:
`computed from ingested/data/<pkg>-<version>/<file>.csv (n rows)`
(query REQ-470..472). Answers stay reproducible from the vault alone,
pinned to the version the page records.

## Staying current

- `Rscript scripts/data_pkg_sync.R --check` compares each registered
  package's GitHub `DESCRIPTION` Version against the newest local
  snapshot (one HTTP GET per package, no R install, no clone). Exit 1
  when anything is stale.
- Detection is automated; writes are confirmed. The check runs whenever
  you ask `/wiki-maintain` for status, and you can wire it as a nightly
  launchd job (same pattern as the voice watcher) that appends one line
  to tomorrow's journal when an update is available. The update itself
  is always one confirmed `/data-sync` run.

## Version updates and retention

- A new version means a NEW snapshot directory. Wiki claims that cite an
  old snapshot keep citing it; the old files stay put.
- Retention keeps the last `data_snapshots_keep` snapshots per package
  (default 3) and NEVER deletes a snapshot referenced by any page's
  `cite::` or `source-file::` (REQ-105).

## Where mcptools fits (and where it does not)

[mcptools](https://github.com/posit-dev/mcptools) exposes your live R
session to MCP clients (serving [btw](https://github.com/posit-dev/btw)
tools: describe a data frame, read help pages, run code). Use it for
interactive analysis: "fit a model on pkg::dataset and discuss" is a
live-session conversation, not a vault query.

It is NOT the system of record and not the freshness mechanism:

- MCP solves access, not freshness: a server answers when called; it
  does not watch GitHub. The version check above is what keeps the
  vault current.
- A live session is not provenance: it is unversioned, session-state
  dependent, and unavailable when R is not running. `/wiki-query`
  content answers come from snapshots so they stay pinned to the version
  the page records (query REQ-472). A spec'd live query plane is parked
  by maintainer decision (2026-07-07).

## Related

- [`openspec/specs/ingest.md`](../openspec/specs/ingest.md) - the seam contract
- [`openspec/specs/query.md`](../openspec/specs/query.md) - data reads
- [PARA + Zettelkasten workflow](para-notes-workflow.md) - the human namespaces
