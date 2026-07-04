---
name: wiki-ingest
description: Process a source (URL, file path, inline text, or the raw/ queue when the source pipeline is configured) and distribute extracted knowledge across wiki pages with provenance. Interactive by default with one consolidated batch checkpoint before any write; --auto skips the checkpoint for queue draining; --import pulls existing notes into wiki format without a file move. This is the primary write path into the wiki.
---

# wiki-ingest

Analyze source material, plan page operations, pause at ONE consolidated
checkpoint for the whole run, then write: create and update pages append-only
with hub routing lines, cross-references, and provenance, and archive processed
sources with an atomic move-plus-commit. Counterpart to wiki-query (read path).

Spec: openspec/specs/ingest.md REQ-010..075

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool, wiki_path, pages_dir, namespaces; source pipeline keys `raw_dir`,
  `ingested_dir`, `source_types`, `default_source_type`,
  `sensitive_source_types`).
- [architecture](../wiki-core/references/architecture.md): L1/L2 routing rule,
  credential boundary, retrieval and commit discipline, namespace scope rule.
- [formats](../wiki-core/references/formats.md): tool-specific formats, required
  properties per page type, routing-line format, write discipline.
- [trust](../wiki-core/references/trust.md): source lifecycle (raw/ ->
  ingested/), `source-file::`, `reliability::` rubric, `confidence::`
  separation, Pending Review.
- [secret-gate](references/secret-gate.md): the pre-archive secret gate
  (`secret_scan.py`), the "ingested/ is committed history, keep it
  secret-free" invariant, blocking vs advisory findings, and the
  `sensitive_source_types` untracked flow.
- [citations](references/citations.md): block-native `cite::` emission on
  claim blocks (specs/citations.md REQ-900..905, ingest REQ-033b), the
  source-file union invariant, and the `check_citations.py` gate step.
- [promotion-seam](references/promotion-seam.md): the para/notes promotion
  seam (specs/namespaces.md REQ-970..973): recognizing
  `raw/para-<project>.md` / `raw/note-<name>.md` sources, the
  personal-synthesis reliability default, the literature variant, and
  sensitive-type handling.

## Modes

- **Interactive (default):** the run pauses at the batch checkpoint before any
  write (REQ-025).
- **`--auto`:** skips the checkpoint for queue draining. The plan table still
  goes into the Phase 5 report, and the quality gate still blocks on failures;
  `--auto` never bypasses a blocking gate (REQ-026). Usage is tracked as a
  success signal (see "Success signal" below).
- **`--import`:** pull notes already written in the graph (or a directory of
  existing markdown notes) into wiki format. Same write path and quality gate,
  but NO file move and NO `source-file::`; see
  [import](references/import.md). Replaces the import verb of the legacy v1
  single command.

Steps marked "(source pipeline)" apply only when `llm-wiki.yml` configures the
pipeline keys (`raw_dir`, `ingested_dir`, `source_types`,
`default_source_type`). When those keys are absent, skip the marked steps and
run on the argument source alone; everything else is unchanged.

<role>
Wiki maintainer for a personal or team knowledge base. You process source
material and distribute extracted knowledge across wiki pages, keep the human
in the loop before anything is written, maintain cross-references and
provenance, and ensure structural integrity.
</role>

<workflow>
## Phase 0 - Source Intake (source pipeline)

- Read `raw_dir`, `ingested_dir`, `source_types`, `default_source_type` from
  `llm-wiki.yml` ([config](../wiki-core/references/config.md))
- No argument -> scan `raw_dir` and process every file there oldest first
  (drain the queue) (REQ-070)
- A path/URL argument -> that single source. A local file outside `raw_dir` is
  copied into `raw_dir` first so the lifecycle is consistent (REQ-070)
- Infer each source's type (one of `source_types`): paper/PDF/Zotero export ->
  `papers`; web clip -> `clippings`; news/blog -> `articles`; dataset/CSV ->
  `data`; personal note -> `notes`; image/binary -> `assets`. Fall back to
  `default_source_type`; ask only if genuinely ambiguous (REQ-071)
- A `raw/para-<project>.md` or `raw/note-<name>.md` filename marks a PROMOTED
  source: content the human copied out of the `para/` or `notes/` namespaces
  (the promotion seam, specs/namespaces.md REQ-970). Treat it as a normal
  source in the queue; it usually infers as type `notes`, and para/notes
  content is candidate `sensitive_source_types` material. Seam specifics in
  [promotion-seam](references/promotion-seam.md)
- If processing fails partway, LEAVE the file in `raw_dir` (the queue is
  resumable). Never move a half-processed source (REQ-072)

## Phase 1 - Source Analysis (per source)

- Identify the source type: URL -> WebFetch, file path -> Read, inline text ->
  parse directly (REQ-010)
- Extract entities, facts, relationships, dates, decisions (REQ-011)
- Classify into exactly one of: business, technical, content, project,
  learning, reference (REQ-012)
- L1/L2 check per the routing rule in
  [architecture](../wiki-core/references/architecture.md): quick rule or gotcha
  -> recommend Memory; deep knowledge -> wiki (REQ-013)
- Credentials or secrets in the source MUST NOT reach wiki pages (REQ-014); the
  pre-archive secret gate in Phase 4 additionally guards the source bytes
- (source pipeline) Assess `reliability::` for the source per the rubric in
  [trust](../wiki-core/references/trust.md) (high | medium | low), with a
  one-line rationale for the checkpoint. A promoted para/notes source
  defaults to `medium` per the rubric's personal-synthesis case (schema
  REQ-586), UNLESS its external citations justify higher under the rubric
  (namespaces REQ-971; the rubric decides, medium is not a hard floor);
  see [promotion-seam](references/promotion-seam.md)
- (source pipeline, optional) Semantic Scholar enrichment per REQ-073a: only
  when an S2 MCP is configured, resolve the source and record `s2-metrics::`
  verbatim. Metrics inform the qualitative judgment, never determine it by
  formula; absence of the MCP never blocks the ingest

## Phase 2 - Wiki Scan and Plan (per source; analysis BEFORE any generation)

- Read `llm-wiki.yml` and the Schema page (REQ-020/021)
- Glob for existing pages matching extracted entities and topics (REQ-022);
  read target pages before modifying them, max 3 loaded simultaneously
  (REQ-023)
- Contradiction check BEFORE any generation: compare each extracted claim
  against the existing target pages and record every conflict (existing claim
  vs. source claim) for the checkpoint. Nothing is generated or written until
  the user has seen the contradictions
- (source pipeline) Corroboration check: if `ingested_dir` already holds a
  source on the same topic, this ingest is CORROBORATION: plan to update the
  existing page, raise `reliability::` if warranted (rubric in
  [trust](../wiki-core/references/trust.md)), and resolve any Pending Review
  items it can
- Produce the page operation plan: pages to create, pages to update,
  cross-references to add, hub pages to update (REQ-024)

## Checkpoint - Batch review (mandatory before any write; skipped only by --auto)

After ALL sources in the run are analyzed and planned, and BEFORE any write,
present ONE consolidated checkpoint for the whole run (REQ-025). Never one
prompt per source; a single-source run is the degenerate one-row case of the
same table.

The checkpoint table, one row per source:

| # | Source | Proposed page touches | Reliability (one-line rationale) | Contradictions |
|---|--------|-----------------------|----------------------------------|----------------|

- Page touches: create/update/hub counts plus the page names; (source
  pipeline) each create/update entry carries its planned cite targets (the
  `ingested/` paths, with locators where known) so the row shows what the
  claims will cite (REQ-033b)
- Reliability: the Phase 1 rating with its one-line rationale (omit this column
  when the source pipeline is not configured)
- Contradictions: count plus one line each, or "none"

Then ask, verbatim from REQ-025: "What should I emphasize, skip, or route to
L1 Memory?"

Interaction rules:

- Any row is expandable on request ("expand 3", "show the plan for
  smith-2024"): print that source's full page-operation plan, extracted
  claims with their planned cite targets, and contradiction details
- Any row is overridable ("skip 2", "rate 4 low", "route the PM2 gotcha to
  L1", "emphasize the method, skip the pricing"): apply the guidance to the
  plan
- Only after the user responds does Phase 3 write. Apply the user's guidance to
  the plan first (REQ-025); never proceed on silence

## Phase 3 - Page Operations (target 5-15 page touches, REQ-037)

- Create new pages with ALL required properties for their declared type per the
  Schema (REQ-030), in the correct tool format and file naming
  ([formats](../wiki-core/references/formats.md), REQ-031/038). Stamp every
  NEW page with `schema-spec-version:: 2.0.0` (Logseq) or
  `schema-spec-version: "2.0.0"` in the YAML frontmatter (Obsidian) so it is
  not grandfathered by lint; existing pages keep whatever they have (the
  stamp is written on creation, never backfilled by ingest). Namespace depth
  max 3 (REQ-039): on overflow, merge the content into the parent page and note
  it in the report
- Update existing pages append-only: NEVER overwrite existing content blocks
  (REQ-032). Use `[[wiki/...]]` link syntax for entities that have their own
  pages (REQ-036)
- Hub routing line, REQUIRED for every created or updated page: set or refresh
  the line in the namespace hub's `### Index` in the routing-line format from
  [formats](../wiki-core/references/formats.md) (REQ-033/033a). The description
  is the routing key consumed by query Phase 0
- Add `[[cross-references]]` between all affected pages; every touched page
  needs at least 1 outgoing wiki link (REQ-034)
- Set `updated::` (or the YAML `updated` field) to today on every modified
  page (REQ-035); ISO 8601 dates throughout (REQ-061)
- (source pipeline) On every created or updated ingested page: set
  `source-file::` to the path the source WILL live at
  (`ingested/<type>/<filename>`; append comma-separated when corroborating) and
  `reliability::` per REQ-073 (claim-level corroboration and page-minimum
  roll-up: schema REQ-586, summarized in
  [trust](../wiki-core/references/trust.md)). Do NOT touch `confidence::`; it
  is a separate axis (schema REQ-587)
- (source pipeline) Pending Review per REQ-074: a page resting on a SINGLE
  source with `reliability::` not `high` gets a `## Pending Review` section
  listing the specific claims needing corroboration. A corroborating ingest
  re-checks each flagged claim, removes resolved ones, deletes the section when
  all resolve, and raises `reliability::`
- (source pipeline) `cite::` on every non-common-knowledge factual claim
  block written (REQ-033b, specs/citations.md REQ-900..905): Logseq block
  property (`cite:: <refs>` on the line under the claim), Obsidian indented
  child bullet (`- cite:: <refs>`). Refs are comma-separated, each an
  `ingested/` path with an optional `#locator` or `url:<https://...>`;
  plain text, never a `[[link]]` (REQ-905). Common knowledge and
  clearly-marked synthesis are exempt; when unsure, cite (REQ-902). Keep
  the page-level `source-file::` equal to the union of the page's ingested/
  cite targets, paths only, locators stripped, deduplicated (REQ-904): when
  a claim cites a new source, append its path to `source-file::` in the
  same edit. Pages are born cited; details in
  [citations](references/citations.md)

## Phase 4 - Quality Gate

Blocking failures (REQ-044): credential detection (REQ-042), pre-archive secret
detection (REQ-045), missing required properties (REQ-040), and citation
invariant failures (specs/citations.md REQ-904/901, exit 2 from
`check_citations.py`). Warnings never block, and `--auto` never bypasses a
blocking failure (REQ-026).

- All new pages have ALL required properties for their type? (REQ-040)
- Every touched page has at least 1 outgoing `[[wiki/...]]` cross-reference?
  (REQ-041)
- Every new or updated active page has a routing line in its hub `### Index`?
  A missing line is a warning: the page is unroutable until `lint --fix`
  backfills it (REQ-041a)
- Scan all created/updated content for credential patterns (`token::`,
  `password::`, `secret::`, `api-key::`, base64 strings of 40+ chars); any
  match BLOCKS the ingest with a warning (REQ-042)
- Page touch count: warn below 5 or above 20; never blocks (REQ-043/044)
- (source pipeline) Every ingested page has `source-file::` and
  `reliability::`? Every single-source non-high page carries
  `## Pending Review`? (REQ-073/074)
- (source pipeline) Citation gate (REQ-033b, specs/citations.md): run

  ```
  python3 skills/wiki-core/scripts/check_citations.py --config <llm-wiki.yml>
  ```

  after the page writes, BEFORE the archive move (cite targets pending in
  `raw_dir` count as resolved). Handle the exit code:
  - **Exit 2 (blocking):** source-file union mismatch (REQ-904) or a cite
    target resolving to no file (REQ-901). Do NOT archive, do NOT commit;
    fix the pages and re-run the gate, exactly like the other blocking
    gate failures
  - **Exit 1 (advisory):** coverage gaps (uncited claim blocks, REQ-902)
    or ref-shape warnings. Present them; the exemption call is judgment,
    so they never block. In `--auto` mode carry them into the report
  - **Exit 0 (clean):** proceed. See
    [citations](references/citations.md) for the convention and staging
- (source pipeline) Pre-archive secret gate (REQ-045/046): BEFORE any source
  file is moved into git-tracked `ingested/`, run

  ```
  python3 skills/wiki-core/scripts/secret_scan.py <source-file>
  ```

  on each source file. The script scans the raw source BYTES (text pass plus
  a strings-style pass over binary formats) against a source-byte-tuned
  pattern set; see [secret-gate](references/secret-gate.md) for the invariant
  and the blocking-vs-advisory model. Handle the exit code:
  - **Exit 2 (blocking: credentials, key material, tokens):** do NOT archive,
    do NOT commit. The file stays in `raw_dir`; relay the script's finding
    locations and remediation message. Redaction (or an explicit
    `--allow-secret` override from the user) is required before re-ingest
    (REQ-045)
  - **Exit 1 (advisory: email addresses, national-ID shapes, other PII):**
    present the findings and require explicit confirmation before archiving
    (interactive mode). In `--auto` mode advisory findings BLOCK (the file
    stays in `raw_dir`) unless the source's type is in
    `sensitive_source_types`, whose untracked flow below keeps the bytes out
    of git anyway
  - **Exit 0 (clean):** proceed. A clean scan is an assist, not a
    certification; the script prints this disclaimer itself
- (source pipeline) Sensitive source types (REQ-046): sources whose type is
  listed in `sensitive_source_types` are ALWAYS scanned, and their bytes stay
  out of git regardless of the result: the file moves to `ingested/<type>/`
  UNTRACKED. Ensure the vault `.gitignore` covers `ingested/<type>/` (add the
  entry if missing; commit the `.gitignore` change, never the source bytes),
  then verify BEFORE the move:

  ```
  python3 skills/wiki-core/scripts/secret_scan.py \
    --gitignore-check <vault-root> ingested/<type>/<filename>
  ```

  Exit 0 means the path is ignored and the move is safe; exit 2 means the
  path would enter git history (not ignored, or already tracked), so do not
  move the file until that is fixed. `source-file::` still records the path;
  the provenance stays valid locally while the bytes stay out of history.
  Rationale for both bullets: `ingested/` is committed git history, so
  exposure there is sticky

## Phase 5 - Archive, Commit, Report

- (source pipeline) Only after the quality gate passes: MOVE each processed
  source from `raw_dir` to `ingested_dir/<type>/<filename>`. The new location
  MUST match what `source-file::` records (REQ-075). Use plain `mv` followed
  by `git add` of BOTH paths (the vanished `raw_dir` path and the new
  `ingested/` path); do NOT use `git mv`, which fails on a source that
  entered `raw_dir` after the last commit (untracked). Alternatively,
  `git add` the raw file first and then `git mv`; either way the move and
  the page edits land in the same commit
- (source pipeline) Stage the page edits AND the file move together and commit
  as ONE atomic commit: `wiki: ingest <filename> (<n> pages, reliability
  <level>)` (REQ-075; the atomicity invariant is stated in
  [trust](../wiki-core/references/trust.md)). A quality-gate failure on one
  source blocks only that source: it stays in `raw_dir`, the rest of the queue
  proceeds
- (source pipeline) Sensitive-typed sources (REQ-046): the file move still
  happens, but the moved file is NEVER staged; the atomic commit contains the
  page edits (plus the `.gitignore` addition, if one was needed). Verify with
  `git status` that the moved file shows as ignored, not untracked, before
  committing
- Without the source pipeline: recommend a git commit after the structural
  changes (REQ-052)
- Report summary: pages created (with types), pages updated, cross-references
  added, hub pages updated (REQ-050); all warnings (page-touch count, L1
  candidates found, skipped items) with their reasons (REQ-051); Pending Review
  flags raised or resolved
- (source pipeline) Literature-note reminder (namespaces REQ-973): when a
  processed source is recognizably a literature note (filename
  `raw/note-@<citekey>.md`, or metadata with `citekey::` or
  `type:: literature`), remind the user in the report to point the
  `notes/literature/@<citekey>` page's `source-file::` at the SAME
  `ingested/` path the wiki pages cite (one archived source, two readings).
  A reminder only: NEVER write into `notes/` (scope rule, REQ-966); details
  in [promotion-seam](references/promotion-seam.md)
- `--auto` runs: include the FULL checkpoint plan table (the same table the
  checkpoint would have shown) in the report, one row per source with
  reliability rationale and contradictions (REQ-026)
- Run log entry: append
  `## [YYYY-MM-DD] ingest | <filename or n sources> -> <n> pages | reliability <level> | mode <interactive|auto>`
  to the Dashboard page. This extends the legacy ingest log entry with the
  `mode` field; it feeds the success signal below

## Success signal: track the --auto share

- Every run log entry records `mode <interactive|auto>` (Phase 5). Compute the
  `--auto` share over the recent run log entries (last 10). A sustained share
  above 50% is a signal that the batch checkpoint is being routed around and
  the checkpoint design (not the user) needs revisiting; flag this in the
  report when the threshold is crossed
- This is recorded in the Phase 5 run log entries on the Dashboard page, NOT in
  the Access-Log. Reason: the Access-Log format is a per-page-read LRU record,
  parsed positionally by prune and status
  ([formats](../wiki-core/references/formats.md), schema REQ-569); it has no
  run-level entry type, and adding one would pollute its parsing. The ingest
  run log entry is the existing run-level record, so the `mode` field lives
  there
</workflow>
