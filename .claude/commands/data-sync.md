# /data-sync - R data packages into the vault

Sync the registered R data packages (`data_packages` in `llm-wiki.yml`)
into versioned `ingested/data/<pkg>-<version>/` snapshots and
`wiki/data/<pkg>/<dataset>` pages. Data-package seam:
specs/ingest.md REQ-100..106; guide: `docs/data-package-workflow.md`.

## Modes

- `/data-sync check` - staleness only:

  ```
  Rscript scripts/data_pkg_sync.R --check
  ```

  Report which packages have a newer version on GitHub. Never writes.

- `/data-sync [<owner/repo> | --local <dir>]` - sync, with the checkpoint:

  1. **Dry-run first, always:**

     ```
     Rscript scripts/data_pkg_sync.R --dry-run [--pkg <owner/repo>] [--local <dir>]
     ```

     Show the user the plan (creates/updates, snapshot, retention). When
     this is a version UPDATE, fetch the package's NEWS.md from GitHub
     and show what changed between the vault version and the new one
     (REQ-103) before asking for confirmation.
  2. **Real run only after the user confirms** (drop `--dry-run`).
  3. **Review and commit** (in the vault repo): the new snapshot, the
     touched `wiki/data` pages, and the hub routing lines land in ONE
     commit: `data: sync <pkg> <version> (<n> datasets)`.

## Guarantees (do not break them by hand-editing the flow)

- Old snapshots stay put; `cite::`/`source-file::` refs to them remain
  valid after an update. Retention keeps the last `data_snapshots_keep`
  snapshots and NEVER deletes one referenced by any page (REQ-105).
- On dataset pages, only the managed properties and the machine-managed
  `## description` and `## data dictionary` sections regenerate; notes
  under `## my notes` and annotations nested UNDER a dictionary row are
  preserved. Free-standing bullets at machine level inside the two
  managed sections are machine territory; tell the user to write under
  `## my notes` or as children of a row.
- Detection is automated, writes are confirmed: never run a writing sync
  without showing the dry-run first (REQ-104).
- A download failure is a clean stop; do not improvise another source
  for the package.
