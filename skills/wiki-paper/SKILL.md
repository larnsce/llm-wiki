---
name: wiki-paper
description: Scaffold and maintain one hub page per manuscript under wiki/papers/<slug>. The hub anchors the literature drawn on, datasets, open questions, and dated draft decisions, and doubles as the homepage of a published paper site; attach links existing pages without rewriting them, status reports hub health read-only. Use when the user starts a paper, wants to attach sources or data to one, or asks how a paper's wiki material stands.
---

# wiki-paper

One anchor page per manuscript: `wiki/papers/<slug>` collects what the
wiki holds for one paper, as links. The hub is also the table of
contents of the published paper site (the #145 viewer opens a hub as
its default route) and the root of the #148 export walk, so hub
completeness is the publish boundary. Shared material (literature
notes, concept pages, datasets) stays where it lives and is linked,
never copied.

Spec: openspec/specs/paper.md REQ-1500..1512; hub structure is linted
by rule 16 (specs/lint.md REQ-260..262).

Shared conventions (read before executing):

- [config](../wiki-core/references/config.md): discover and read
  `llm-wiki.yml` FIRST (`tool`, `wiki_path`, `pages_dir`, namespaces).
- [formats](../wiki-core/references/formats.md): tool-specific page
  formats, routing-line format, heading and property syntax.
- [architecture](../wiki-core/references/architecture.md): hub routing,
  commit discipline, namespace scope rule.

<role>
Wiki maintainer for a researcher writing manuscripts on top of the
wiki. You scaffold paper hubs, keep them complete, and never move or
rewrite the pages a paper draws on.
</role>

<workflow>
## Mode: new <slug> (scaffold; REQ-1507)

- Slugify the argument (lowercase kebab, schema REQ-580); refuse a slug
  whose hub already exists.
- Draft the hub page `wiki/papers/<slug>` in the configured tool's
  format:
  - Properties (REQ-1501): `type:: paper-hub`, `status:: drafting`,
    `created::`/`updated::` today, optional `target::` when the user
    named a venue.
  - The six sections (REQ-1502), each with a placeholder bullet:
    `## Manuscript` (working title, status line),
    `## Literature drawn on`, `## Data`, `## Open questions`,
    `## Draft decisions` (dated, append-only bullets; supersede via
    wiki-update, never delete), `## AI use` (link the paper's
    agent-log page once one exists; until then one prose line).
- Draft the `wiki/papers` namespace hub if it does not exist
  (`type:: hub`, `### Index`), and add one routing line for the new
  paper (REQ-1506). Suggest adding `papers` to the config `namespaces`
  list for query routing; never edit the config yourself.
- Show both diffs, write only after confirmation, git commit the
  scaffold as one commit.

## Mode: attach <slug> <page>... (append links; REQ-1508)

- Resolve each argument to an existing page (a bare `@citekey` resolves
  to `notes/literature/@citekey`). A page that does not exist is
  reported, not created.
- Route each page to its hub section: literature pages to
  `Literature drawn on`, `wiki/data/` pages to `Data`, anything else is
  offered with a section choice at the confirmation.
- Append one link bullet per page to the section; a page already
  linked anywhere on the hub is skipped, not duplicated. Update
  `updated::`.
- APPEND-ONLY on both sides: the hub gains bullets, and the attached
  page is NEVER rewritten (no back-link is forced onto it; provenance
  and cross-references stay ingest's job).
- Show the hub diff, write only after confirmation, commit.

## Mode: status <slug> (read-only; REQ-1509)

- Report: `status::` and `updated::`, the six sections with their link
  counts, children under `wiki/papers/<slug>/` not linked from the hub
  (REQ-262 candidates for the export walk), and any linked page that
  does not exist (broken anchor).
- Write nothing; suggest `/wiki-lint` for the mechanical pass and
  `/wiki-paper attach` for gaps.

## Boundaries (always)

- Write only under `wiki/papers/` plus the `wiki/papers` hub routing
  lines (REQ-1510).
- A paper is also a PARA project: the hub MAY link a `para/` project
  page, but never duplicates its content and this skill never writes
  under `para/` (REQ-1512, namespaces REQ-966).
- Finished papers demote like any cold page (REQ-1511); do not exempt
  paper pages from pruning and do not pre-archive them.
</workflow>
