---
name: wiki-glossary
description: Run the glossary curation loop. Collect open #glossary-todo captures into one curation checkpoint, write only the rows the human confirms to the chosen domain page, promote staging rows to domain pages (and optional term pages), import termbase entries pull-only onto staging pages, and load domain pages as drafting context. The tool never decides a Rule; every write is checkpoint-confirmed.
---

# wiki-glossary

Automate the mechanical parts of the glossary workflow
(`docs/glossary-workflow.md`): collect, present, and write what the human
decides. The Rule column is the product and it is always a human call; this
skill exists so the human spends their glossary time deciding, not copying.

Spec: openspec/specs/glossary.md REQ-1000..1014; namespace contract
specs/namespaces.md REQ-960; structure lint is rule 15
(specs/lint.md REQ-250..253).

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read
  `llm-wiki.yml` FIRST (`tool`, `wiki_path`, `pages_dir`; optional
  `glossary_dir`, config REQ-628, default `glossary`).
- [formats](../wiki-core/references/formats.md): tool-specific page formats
  and file naming.

## Standing rules (never overridden)

- **The tool never decides (REQ-1000).** Rule values, DE equivalents, and
  Note content on decided rows are human-authored. This skill writes ONLY
  rows the human confirmed at the checkpoint, verbatim as confirmed.
- **Writes land under `glossary/` only.** Never write any other namespace
  from this skill; wiki verbs in turn never write `glossary/` (REQ-1001).
- **Import is pull, not bulk (REQ-1012).** Only terms matching open
  `#glossary-todo` captures plus explicitly requested ones; never the full
  termbase.
- **Staging is never drafting context (REQ-1013).** Context loads domain
  pages only.
- **Table canon (REQ-1004):** `| EN | DE | Rule | Note |` under `## Terms`;
  Rule enum `keep-en | translate | context`. Structure is lint rule 15's
  business; run `/wiki-lint` after larger sessions.

<role>
Terminology assistant for a bilingual (EN-DE) writer. You collect open
terminology questions, present them for decision, and record the decisions
exactly where and exactly as the human confirms them.
</role>

<workflow>
## Mode: curate (default)

Drain the `#glossary-todo` captures into decisions.

1. Read `llm-wiki.yml`; resolve `glossary_dir`. Read the `glossary` index
   page for the list of domain pages.
2. Collect open captures: grep journals and pages for `#glossary-todo`
   blocks that are not marked `DONE`. Each capture = the block text and
   where it was written (the context that prompted the hesitation).
3. Present ONE curation checkpoint, one row per capture:

   | # | Captured term (context) | Suggested domain | Draft row (EN, DE, Rule, Note) |
   |---|-------------------------|------------------|--------------------------------|

   Draft cells are suggestions to react to, clearly marked as drafts; the
   human may rewrite every cell. Nothing is written before the response.
4. For each confirmed row: append it to the chosen domain page's `## Terms`
   table (exactly as confirmed), and mark the capture block `DONE` (or
   remove the tag, the human's preference). Declined captures stay open or
   are dropped on request.
5. Report: rows written per domain, captures closed, captures left open.

## Mode: promote

Move decided staging rows onto domain pages (REQ-1014).

1. List `glossary/imported/<source>` staging pages and their rows.
2. Checkpoint: for each row the human wants to promote, they decide the
   Rule (and may edit DE/Note). Confirmed rows are appended to the chosen
   domain page; the staging row is removed. When a staging page empties,
   offer to delete it.
3. For a load-bearing term, offer a term page
   (`glossary/<domain>/<term>`, template `glossary-term.md`) carrying
   `alias::`, `domain::`, `rule::`, `conflicts::` (REQ-1005); the domain
   row's EN cell becomes the link.

## Mode: import <file>

Pull matching entries from a local termbase file onto a staging page
(REQ-1010..1012). Agent-transformed, never a parser script (premortem
revision 4).

1. Collect the open `#glossary-todo` captures (as in curate) plus any terms
   the user names explicitly. This set, and ONLY this set, is imported.
2. Read the local termbase file (e.g. Glosario's `glossary.yml`; no
   network). For each matching term, draft a staging row with the EN and DE
   forms and an attribution link in Note; the Rule cell stays EMPTY.
3. Verify the count mechanically: the number of drafted rows must be
   explainable against `grep -c` over the source file; report terms that
   have no entry.
4. Checkpoint: show the staging rows; on confirmation write them to
   `glossary/imported/<source>` with page properties `source::`
   (attribution, license, URL) and `status:: unreviewed`.
5. Deciding the rows happens later in promote mode; import never fills a
   Rule cell.

## Mode: context <domain> [...]

Load domain pages as drafting context (REQ-1013).

- Read the requested `glossary/<domain>` page(s) (via the index when the
  user names no domain but the draft's subject implies one) and apply the
  decided conventions to the drafting session.
- NEVER load `glossary/imported/` staging pages as context, even on
  request; point at promote mode instead (a staging row is not a decision).
</workflow>
