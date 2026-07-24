# Design Review: llm-wiki vs. the Karpathy Gist

A two-way review of this tool against [Andrej Karpathy's "LLM Wiki" gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), the concept this project implements. Direction one: where the gist's intent was lost in v1 and restored in v2. Direction two: where this tool goes beyond what the gist describes.

Claims below are grounded in the spec canon (`openspec/specs/`) by REQ ID where they describe tool behavior. Statements about intent, emphasis, or quality are narrative judgments and are marked as such.

## Direction one: what the gist wants that v1 lacked, and v2 restores

### Human-in-the-loop ingest

The gist is explicit that the human stays in the loop: "I prefer to ingest sources one at a time and stay involved." The wiki is a collaboration in which the LLM drafts and the human curates, not a batch ETL job.

v1 drifted from this. The v1 ingest workflow ran all five phases (analyze, scan, write, gate, report) without a pause; with the source pipeline configured, a bare ingest drained the whole `raw/` queue, oldest first. The human saw a report after the writes were committed. That is a narrative judgment about v1's shape, but the v1 workflow text had no checkpoint step to point at.

v2 restores the gist's stance and makes it the default:

- **Interactive checkpoint (REQ-025, openspec/specs/ingest.md).** After the page operation plan and before any write, ingest presents the consolidated plan (pages to create and update, the routing lines, the reliability ratings) and waits for approval. One checkpoint per run, covering the whole batch, so involvement does not degenerate into per-page nagging.
- **Opt-out, not opt-in (REQ-026).** Batch draining requires the explicit `--auto` flag; the plan still lands in the report, and the quality gate (REQ-040/042/045) still blocks on failures even under `--auto`. The default is the gist's preference; automation is the exception you ask for.

### Findings for approval, not silent auto-repair

The same stance applies to maintenance. v1's lint had a `--fix` flag that applied every auto-fixable repair and committed the result in one motion. v2's `wiki-lint` separates the layers: the mechanical layer (`lint.py`, `check_canon.py`) is report-only by design, and fixes are proposed per finding and applied agent-side only after user confirmation (see `skills/wiki-lint/SKILL.md`; the reporting contract is REQ-200..203, openspec/specs/lint.md). Rules where repair needs human judgment are specified as no-auto-fix, for example empty pages (REQ-172) and canonical-url link rot (REQ-222).

The forthcoming edit path keeps the same discipline: `wiki-update` (v2.1, openspec/specs/update.md REQ-950..954) is the only workflow allowed non-append edits, requires a source for every factual change, and shows a before/after diff for confirmation first.

## Direction two: what this tool adds beyond the gist

The gist describes what to build: a structured, cross-referenced, LLM-maintained wiki. It does not describe how retrieval stays precise as the wiki grows, or how you know why the LLM loaded what it loaded, or how a synthesized claim traces back to a source. Those are this tool's additions. Calling them the interesting part of the design is a narrative judgment; what follows is where each lives in the canon.

### L1/L2 cache hierarchy

Knowledge is split across two layers by consequence-of-ignorance: rules and gotchas the LLM must know before it acts live in auto-loaded memory (L1); deep knowledge loads on demand from the wiki (L2). The boundary is specified as a decision procedure (openspec/specs/l1-l2-routing.md; applied at ingest time by REQ-360), and lint patrols it: L1 files unreferenced for 90+ days and L2 pages queried every session are both flagged (REQ-353, REQ-354), as are L1/L2 duplicates. Credentials are pinned to L1 because L2 is git-tracked. See [l1-l2-architecture.md](l1-l2-architecture.md).

### Hub-index routing

Every hub page carries an `### Index` of routing lines, one per child: `[[page]] -- description #tags` (openspec/specs/schema.md REQ-555..557). Query is two-stage: read the cheap hub indexes of candidate namespaces, pick the best 3-5 pages by description, read only those (openspec/specs/query.md REQ-440..444). Full-text grep over the corpus is demoted to an L3 fallback. The analogy in the docs is a page table: retrieval cost stays near-constant as the page count grows.

### LRU-Demote

Query appends every full-page read to an Access-Log; prune evicts pages with no access in N months (default 6) from the live index (openspec/specs/prune.md REQ-600..622). Eviction is not deletion: the file stays in place, incoming links stay valid, the page stays greppable, and a re-hit re-promotes it (schema REQ-565..568). Hubs, the Schema page, and active projects are exempt (REQ-604). This is the piece a growing wiki needs and no note-taking convention provides: access-frequency-based index hygiene.

### Access-Log transparency

Each logged read records not just which page loaded but why: the matched routing description or the grep term that found it (query REQ-450, REQ-450b; the page itself is specified in schema REQ-569). The status report aggregates these reasons, so mis-routing is visible (a page always found by grep instead of its index line has a weak routing description). The log is append-only and non-structural; it never generates its own commits (REQ-451).

### Provenance and trust layer

Every ingested page records which archived source file it rests on (`source-file::`, schema REQ-585) and how strong its sourcing is (`reliability:: high | medium | low`, rolled up as the minimum across claims, REQ-586). Reliability and confidence are separate axes, never cross-derived (REQ-587). Single-source, non-high pages carry a visible `## Pending Review` section until corroborated (REQ-588). The source file's move from `raw/` to `ingested/` is the atomic provenance commit (REQ-589; ingest REQ-075), and deliberate external-truth stubs are marked `canonical-url::` instead (REQ-584). Two guards keep the archive safe: a pre-archive secret gate scans source bytes before anything enters the git-tracked tree (ingest REQ-045), and configured sensitive source types never enter history at all (REQ-046).

Claim-level citations (`cite::`, openspec/specs/citations.md) and claim-by-claim verification (`wiki-audit`, openspec/specs/audit.md) extend this layer in v2.1.

## Summary

| Theme | Gist | v1 | v2 |
|-------|------|----|----|
| Ingest involvement | One at a time, stay involved | Batch, report after write | Checkpoint before write (REQ-025), `--auto` opt-out (REQ-026) |
| Fix approval | Human curates | `--fix` applied and committed | Findings proposed, applied on confirmation (wiki-lint) |
| Retrieval scaling | Not addressed | Hub-index routing (added in 1.2.0) | Same, spec-canonical (REQ-440..444, REQ-555..557) |
| Eviction | Not addressed | LRU-Demote (added in 1.2.0) | Same, spec-canonical (REQ-600..622) |
| Loading transparency | Not addressed | Access-Log with matched-reason (added in 1.3.0) | Same, spec-canonical (REQ-450b) |
| Provenance and trust | Not addressed | Source pipeline (added in 1.4.0) | Same plus secret gate (REQ-045/046); citations and audit in v2.1 |

## Addendum (2026-07-24): the public-site half

The site that popularized the gist, andrej-karpathy.com, added a second
half to the pattern: the wiki published as a markdown-first website,
where humans read rendered pages and agents fetch the identical raw
`.md` at the same paths. llm-wiki now ships that half natively. The
single-file viewer (`templates/site/index.html`) renders both page
flavors with hash routes over raw markdown and no build step,
`docs/publish-wiki.md` documents the publish boundary and the
`secret_scan.py` gate, and the paper workflow (`docs/paper-workflow.md`)
derives a public supplementary site from a manuscript's hub page, with
the link walk as the boundary and a manifest instead of silent
exclusions. The prior-art check on the cognee front end that runs
andrej-karpathy.com found a built React bundle entangled with its
backend, so the viewer here is a from-scratch single file (issue #145).
