---
name: wiki-update
description: Revise an existing wiki page deliberately; the only workflow allowed to modify or supersede existing content blocks. Diff-first (before/after shown and confirmed before any write) and source-required (a factual change without an ingested/ file or URL is refused). Superseded claims stay legible on the page, marked with a date and pointer, never silently deleted. Use when the user asks to correct, revise, or supersede existing wiki content.
---

# wiki-update

Revise an EXISTING page to correct or supersede content. This is the ONLY
sanctioned non-append edit path; ingest stays append-only
(openspec/specs/ingest.md REQ-032). Diff-first and source-required: a factual
change needs evidence, and superseded claims stay legible so the history of a
belief can be read on the page, not just in git.

Spec: openspec/specs/update.md REQ-950..954; carries the citation layer,
openspec/specs/citations.md REQ-900..905

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read `llm-wiki.yml`
  FIRST (tool, wiki_path, pages_dir, source pipeline keys `raw_dir`,
  `ingested_dir`).
- [architecture](../wiki-core/references/architecture.md): namespace scope rule
  (update operates ONLY on wiki-namespace pages, never `para/` or `notes/`),
  commit discipline.
- [formats](../wiki-core/references/formats.md): tool-specific block and
  property syntax, write discipline.
- [trust](../wiki-core/references/trust.md): source lifecycle, `source-file::`,
  `reliability::` rubric, `confidence::` separation, Pending Review.
- [supersede](references/supersede.md): the supersede marking convention (both
  tool modes) and the placement rules for the replacement claim.

<role>
Wiki maintainer for a personal or team knowledge base. You are the one gate
through which existing wiki content may change: you demand a source for every
factual change, show the exact diff before writing, and keep superseded claims
readable instead of erasing them.
</role>

<workflow>
## Phase 0 - Config and scope

- Discover and read `llm-wiki.yml` (config reference above). Abort with the
  standard message if it is missing.
- Resolve the target page to a file in the wiki namespace; refuse pages
  outside it per the namespace scope rule in
  [architecture](../wiki-core/references/architecture.md). The page must
  EXIST: creating pages and adding new knowledge is wiki-ingest's job, not
  update's (REQ-950 covers revision of existing blocks only).

## Phase 1 - Classify the change and require the source (REQ-951)

- Classify the requested change:
  - **Non-factual** (typo, formatting, broken `[[link]]`, wording that does
    not change what is claimed): exempt from the source requirement; go to
    Phase 2.
  - **Factual** (a claim's substance changes: numbers, dates, names,
    directions, additions or retractions of fact): a source is REQUIRED, an
    `ingested/` file or a URL.
- If a factual change arrives without a source, REFUSE to proceed: ask for
  one and make no edit until it is provided (REQ-951). Point the user at the
  options:
  - a path into `ingested/` (already-processed source),
  - a URL (recorded as a `url:<https://...>` cite ref, citations.md REQ-901),
  - or, for genuinely new source material, run wiki-ingest first and come
    back with the resulting `ingested/` path.
- Assess the provided source's `reliability::` rubric rating per
  [trust](../wiki-core/references/trust.md), with a one-line rationale for
  the checkpoint.

## Phase 2 - Read and draft

- Read the target page. Locate the exact block(s) to change.
- Draft the edit:
  - A plain correction (the old claim was wrong in a way its own source does
    not actually support, e.g. a transcription slip) rewrites the block and
    sets its `cite::` to the provided source.
  - New information that CONTRADICTS an existing cited claim NEVER erases it
    silently (REQ-953): mark the old claim superseded and add the new claim
    with its own `cite::`, per the convention in
    [supersede](references/supersede.md). Git already holds the literal prior
    text; the page keeps the legible belief history.
- The new or changed claim carries its `cite::` in the block-native form for
  the configured tool (citations.md REQ-900/901).

## Phase 3 - Diff checkpoint (mandatory; REQ-952)

- Show the exact before/after diff of every block the edit touches, plus the
  property deltas (`cite::`, `source-file::`, `reliability::`, `updated::`)
  and any Pending Review changes from Phase 4.
- Wait for explicit confirmation. NO write happens before the user approves;
  never proceed on silence (REQ-952). If the user amends, redraft and show
  the diff again.

## Phase 4 - Write and maintain the trust layer (REQ-954)

Only after approval, in the tool-specific format from
[formats](../wiki-core/references/formats.md):

- Apply the approved edit: set or adjust `cite::` on the changed claims.
- Keep `source-file::` consistent: the page-level value stays the union of
  the page's `ingested/` cite targets, paths only, locators stripped,
  deduplicated (citations.md REQ-904). A new `ingested/` source is appended;
  a source no longer cited by any live claim is still cited by the superseded
  claim it backed, so it normally stays in the union.
- Recompute `reliability::` per schema REQ-586 (claim-level corroboration,
  page-minimum roll-up; summary in
  [trust](../wiki-core/references/trust.md)). Never touch `confidence::`
  (schema REQ-587).
- Re-check `## Pending Review`: resolve items the new source supports; remove
  the section when all resolve (schema REQ-588).
- Set `updated::` to today.
- Append the log entry
  `## [YYYY-MM-DD] update | <page> | <one-line reason>` to the Dashboard
  page.
- Paper agent-log (paper.md REQ-1515/1517): when the edited page lives
  under `wiki/papers/<slug>/` or a paper hub links it, append one row
  to that paper's agent-log (format paper.md REQ-1514); on a
  supersession, the row's Pages written cell links the page and the
  row's date matches the page-level supersede marker, so the two
  artifacts reference each other.
- Git commit referencing the source, e.g.
  `wiki: update <page> (<reason>, source <ref>)` (REQ-954; commit discipline
  in [architecture](../wiki-core/references/architecture.md)).

## Phase 5 - Report

- Summarize: blocks changed, claims superseded, cite refs added,
  `source-file::` / `reliability::` deltas, Pending Review items resolved,
  and the commit.
- If the audit trail matters right now, suggest a follow-up `/wiki-audit
  <page>` run to verify the revised page end to end.
</workflow>
