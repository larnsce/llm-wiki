---
name: wiki-audit
description: Verify a wiki page claim by claim against its cited sources. Builds the claim-to-source map mechanically via check_citations.py, dispatches one isolated verification subagent per cited source in parallel, reconciles the verdicts with the trust layer (reliability, Pending Review), and reports supported, partial, unsupported, and source-missing claims. Read-only by default; --fix writes property updates only after user confirmation. Use when the user asks to audit, verify, or fact-check a wiki page against its sources.
---

# wiki-audit

Verify a single page against its cited sources. `reliability::` answers "how
good are the sources"; audit answers "does the source actually say this". The
claim-to-source map comes from the block-native `cite::` convention; each cited
source is judged by its own isolated verification subagent, in parallel.

Spec: openspec/specs/audit.md REQ-920..926; consumes the citation layer,
openspec/specs/citations.md REQ-900..905

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool, wiki_path, pages_dir, source pipeline keys `raw_dir`,
  `ingested_dir`).
- [architecture](../wiki-core/references/architecture.md): namespace scope rule
  (audit operates ONLY on wiki-namespace pages, never `para/` or `notes/`),
  commit discipline.
- [formats](../wiki-core/references/formats.md): tool-specific block and
  property syntax the claim blocks are parsed in.
- [trust](../wiki-core/references/trust.md): `reliability::` rubric and
  claim-level corroboration, `confidence::` separation, Pending Review rules.
- [verdicts](references/verdicts.md): the verdict rubric, the subagent prompt
  template, and the isolation rules for this skill.

## Modes

- **Default (read-only):** report only; NO file is modified (REQ-920, REQ-925).
- **`--fix`:** propose the writes from the report (cite:: stubs, Pending Review
  moves, `reliability::` / `updated::` deltas) and apply them ONLY after
  explicit user confirmation of the proposed changes (REQ-920, REQ-926). Fix
  mode never rewrites claim text; it changes properties and section placement
  only.

<role>
Wiki maintainer for a personal or team knowledge base. You check that every
factual claim on a page is backed by the source it cites, keep the trust
properties honest, and never touch a page without an explicit --fix
confirmation.
</role>

<workflow>
## Phase 0 - Config

- Discover and read `llm-wiki.yml` (config reference above). Abort with the
  standard message if it is missing.
- Resolve the target page argument to a file in the wiki namespace. Refuse
  pages outside it per the namespace scope rule in
  [architecture](../wiki-core/references/architecture.md).

## Phase 1 - Claim Map (mechanical, then judgment; REQ-921)

- Run `python3 skills/wiki-core/scripts/check_citations.py --json` and take
  the target page's entries from the JSON claim-to-source map (claim block ->
  cite refs, per citations.md REQ-900/901). Exit codes follow the shared
  script idiom: 0 = clean, 1 = citation findings (the map is still produced),
  2 = critical failure (no usable map; report and stop).
- Report the script's citation findings for the page FIRST, before any
  verification: unresolvable cite targets, `source-file::` union mismatches
  (citations.md REQ-904), orphaned cites. An unresolvable `ingested/` target
  becomes a `source-missing` verdict in Phase 2 without dispatching a subagent
  for it.
- Then read the page and classify every remaining factual,
  non-common-knowledge claim that carries no `cite::` as UNCITED, listing each
  verbatim with its block location (REQ-921). The exemption judgment (common
  knowledge, marked synthesis/opinion) is made here, at audit time, per
  citations.md REQ-902.
- Blocks marked superseded (struck through with a `superseded::` property,
  the wiki-update convention per update.md REQ-953) are legible history, not
  live claims: exclude them from verification and from the UNCITED
  classification, and note their count in the report.

## Phase 2 - Verification (parallel subagents; REQ-922/923)

- Group the map by SOURCE: one verification subagent per cited source,
  dispatched IN PARALLEL (REQ-922). Use a generic subagent (it inherits
  the session model) with the prompt and isolation rules below.
- Isolation is the point: each subagent receives ONLY its own claim text(s)
  and its own source (an `ingested/` path is read from disk; a `url:` ref is
  fetched), never the page, the other claims, the other sources, or the other
  verdicts. Verdicts from one source MUST NOT leak into another's judgment
  (REQ-922). Prompt template and full rules:
  [verdicts](references/verdicts.md).
- Each subagent judges ONLY whether its source supports the specific claim(s)
  citing it and returns per claim one verdict from the closed set
  `supported | partial | unsupported | source-missing`, plus a one-line
  paraphrased justification, not long quotes (REQ-923).

## Phase 3 - Reconciliation (trust layer; REQ-924)

- Reconcile in the session (REQ-924); for a contested batch, escalate
  the session model manually (`/model`) before running. The rules are:
- Reconcile the verdicts with `reliability::` per schema REQ-586/588 (rubric
  summary in [trust](../wiki-core/references/trust.md)):
  - All cited claims `supported` with independent corroboration (citations.md
    REQ-903: different authors, publishers, or datasets) MAY raise claim
    ratings and thus the page minimum.
  - Any `unsupported`, `source-missing`, or UNCITED claim caps the page at
    `medium`; `low` when central claims fail. Each such claim MUST appear
    under `## Pending Review`.
- Compare against the page's CURRENT `reliability::` and `## Pending Review`
  section to compute the deltas: rating changes, claims to add to Pending
  Review, previously flagged claims now verified `supported` (resolvable).
- Never touch `confidence::`; it is a separate axis (schema REQ-587).

## Phase 4 - Report (REQ-925)

- Output the verdict table, one row per claim: claim (verbatim, truncated),
  citation ref(s), verdict, one-line justification.
- Plus explicit lists: UNCITED claims, unsupported claims, missing sources.
- Plus coverage stats: cited vs uncited factual claims, sources checked,
  verdict counts.
- Plus the proposed deltas from Phase 3: `reliability::` change and Pending
  Review additions/resolutions.
- In default mode STOP HERE; nothing is written (REQ-920/925).

## Fix Mode (only with --fix, always confirmed; REQ-926)

- Present the proposed changes and wait for explicit confirmation; never write
  on silence. Then, in the tool-specific format from
  [formats](../wiki-core/references/formats.md):
  - Add `cite::` stubs to UNCITED claims with the ref left for the user to
    fill.
  - Move unsupported and uncited claims under `## Pending Review`; NEVER
    silently delete prose, and never rewrite the claim text itself.
  - Update `reliability::` per the Phase 3 reconciliation and set `updated::`
    to today.
  - Append the log entry
    `## [YYYY-MM-DD] audit | <page> | <n> verified, <n> flagged`
    to the Dashboard page (legacy entries with a trailing
    `agents <...>` field stay valid; the field is retired, REQ-053).
  - Git commit the changes (commit discipline in
    [architecture](../wiki-core/references/architecture.md)).
- Claim-text corrections are out of scope even in fix mode: revising a wrong
  claim is wiki-update's job (the only sanctioned non-append edit path,
  openspec/specs/update.md REQ-950).
</workflow>
