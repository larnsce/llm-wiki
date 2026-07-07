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

## Setup

```yaml
# llm-wiki.yml
data_packages:
  - larnsce/sanitationdata
data_snapshots_keep: 3
```

## The loop

1. **Sync** (first time or after an update): `/data-sync`, which runs
   `Rscript scripts/data_pkg_sync.R --dry-run` first, shows the plan
   (and the NEWS diff on updates), and writes only after you confirm.
2. Each sync writes ONE versioned snapshot
   `ingested/data/<pkg>-<version>/`: CSVs (materialized from
   `data/*.rda`, copied from `inst/extdata`), one extracted doc per
   dataset (title, description, variable dictionary, source, from the
   Rd files), and a provenance line. Snapshot paths are cite targets
   like any other `ingested/` path.
3. Each dataset gets a page `wiki/data/<pkg>/<dataset>` (`type::
   entity`, `entity-type:: dataset`): managed properties (`package`,
   `version`, `license`, `url`, `source-file`, `data-last-sync`) plus
   two machine-managed sections, `## description` and
   `## data dictionary`, regenerated on every sync. Your own notes go
   under `## my notes` (never touched) or nested UNDER a dictionary row
   (preserved across syncs). Routing lines land in the `wiki/data` hub
   and the package page.
4. **Query:** `/wiki-query` routes dataset questions via the dictionary,
   then computes read-only on the snapshot CSVs (stdlib csv/sqlite3),
   attributing file, package version, and row count. Answers stay
   reproducible from the vault alone.

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
