# Import mode (--import)

Spec: openspec/specs/ingest.md (write path, Phases 2-5). Replaces the import
verb of the legacy v1 single command.

Import pulls notes ALREADY written in the graph, or a directory of existing
markdown files, into wiki format. The content originates from the conversation
and the user's own notes, not from a `raw/` source file, so the provenance file
lifecycle does not apply: nothing is moved, and no `source-file::` is assigned.

## Differences from ingest

| Aspect | ingest (default / --auto) | --import |
|--------|---------------------------|----------|
| Input | URL, file path, inline text, or the `raw/` queue | Existing notes in the graph or a source directory of markdown files |
| File move | `raw/` -> `ingested/<type>/`, atomic move plus commit (REQ-075) | NO file move; the original notes stay untouched where they are |
| `source-file::` | Set on every ingested page (REQ-073) | NEVER set; there is no archived origin file |
| `reliability::` / Pending Review | Set per the rubric in [trust](../../wiki-core/references/trust.md); single-source non-high pages get `## Pending Review` (REQ-073/074) | Omitted; these properties belong to pages with `source-file::` (schema REQ-585/586) |
| `source::` (method) | `ingest` | `manual` (the content is human-authored; schema REQ-510 enum: memory-migration, ingest, manual) |
| Pre-archive secret gate (REQ-045/046) | Scans source bytes before the move | No move, so no pre-archive scan; the REQ-042 content scan on the written pages still applies |
| Checkpoint | Batch checkpoint before any write; `--auto` skips it | Same: the batch checkpoint applies (one consolidated table for the run) |
| Quality gate | Phases 4 blocking and warning checks | Identical; same write path, same gate |
| Commit | One atomic commit including the file move | Git commit of the page changes with an import summary |

## Workflow

Import runs the same write path as ingest; only Phases 1-2 intake differs and
Phase 5 has no move.

Phase 1 - Inventory:

- Scan the source directory (or the named notes) for markdown files
- Classify each file by content type (entity, project, knowledge, reference)
- Identify a potential namespace mapping for each file

Phase 2 - Conversion planning:

- Plan the conversion to wiki format for the configured tool (outliner or flat
  markdown: [formats](../../wiki-core/references/formats.md))
- Plan the required properties per page type (schema REQ-510..530), including
  `type`, `created`, `updated`, and `source:: manual`
- Plan the conversion of internal links to `[[Wiki/...]]` cross-references
- Then the batch checkpoint from SKILL.md applies: one consolidated table, no
  write before the user responds (REQ-025); `--auto` skips it (REQ-026)

Phase 3 - Create pages (ingest Phase 3 rules apply):

- Create hub pages first, then content pages
- Update all hub pages with routing lines for their new children
  (REQ-033/033a)
- Append-only on any existing page (REQ-032); never modify the original
  non-wiki notes (REQ-060 and the namespace scope rule in
  [architecture](../../wiki-core/references/architecture.md))

Phase 4 - Verification:

- Run the ingest quality gate (SKILL.md Phase 4) on the imported pages,
  minus the pre-archive steps
- Run lint on the imported pages
- Report pages imported and issues found; git commit with an import summary

## Boundary with the promotion seam (v2.2)

Once the `para/` / `notes/` namespace contract applies (v2.2,
openspec/specs/namespaces.md REQ-970..973), content under `para/` or `notes/`
enters the wiki ONLY through the promotion seam: the human copies it into
`raw/` and runs the regular ingest pipeline. `--import` is for other existing
notes; it does not bypass that seam.
