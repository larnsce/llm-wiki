# Spec: Namespaces - wiki/ | para/ | notes/ Contract & Scope

## Description

The graph holds three top-level namespaces with different ownership and different obligations.
`wiki/` is machine-written and source-backed: the full schema, provenance, citation, reliability,
lint, and audit conventions apply to it. `para/` (PARA task/project layer) and `notes/`
(Zettelkasten layer) are human-authored and EXEMPT from the wiki conventions - the wiki
toolchain never creates, edits, lints, or audits them. The only path from `para/` or `notes/` into
`wiki/` is the explicit promotion seam: content is copied into `raw/` and enters through the normal
ingest pipeline, receiving provenance like any other source.

This spec defines the namespace contract, the scope rule that binds every wiki workflow, the
promotion seam, the note-type vocabulary the tool recognizes but does not author, and the
query-page tiering decision for the human layers.

> Spec version: introduced for v2.2. This spec uses the globally unique REQ-960..981 range
> (the merged draft used IDs in the 600s, which collided with `specs/config.md` and
> `specs/prune.md`). Naming rules live in `specs/schema.md` (Namespace Conventions);
> mechanical enforcement lives in `specs/lint.md` (naming-hygiene, namespace-hygiene).

---

## Requirements

### The Three-Namespace Contract

- REQ-960: The graph SHALL define exactly three content namespaces at the top level:
  - `wiki/` - machine-written, source-backed knowledge. The full schema (`specs/schema.md`),
    provenance/trust, citations, lint, and audit conventions apply.
  - `para/` - human-owned tasks and projects (PARA). EXEMPT from all wiki conventions.
  - `notes/` - human-written thinking (Zettelkasten). EXEMPT from all wiki conventions. Never
    machine-generated.
- REQ-961: `para/` and `notes/` pages SHALL NOT be required to carry `source-file::`,
  `reliability::`, `confidence::`, citations, routing lines, or any other wiki-only property. Their
  absence on a `para/`/`notes/` page SHALL NOT be flagged by lint.
- REQ-962: Journals and a small set of deliberate root pages (Schema, hub pages, query pages,
  Dashboard, Access-Log) are recognized structural pages outside the three content namespaces and
  SHALL NOT be treated as stray by namespace-hygiene checks.

### Scope Rule (binds every wiki workflow)

- REQ-965: Every wiki workflow (ingest, query, prune, lint, status, audit, update, and any
  future verb) SHALL operate ONLY on pages whose name starts with `wiki/`.
- REQ-966: A wiki workflow SHALL NOT create, modify, lint, or audit any page under `para/` or
  `notes/`. These namespaces are human-authored.
- REQ-967: A wiki workflow MAY READ `para/` and `notes/` pages when the user asks for context
  (e.g. a query that references a linked note), but SHALL NOT write to them as a side effect.
- REQ-968: This scope rule is a shared invariant stated once (wiki-core reference) and loaded by
  every skill; it SHALL NOT be restated divergently per skill (enforced by `check_canon.py`).

### The Promotion Seam (the only path in)

- REQ-970: The ONLY sanctioned path from `para/` or `notes/` into `wiki/` is via `raw/`: the human
  copies the durable content into a source file (`raw/para-<project>.md` or `raw/note-<name>.md`)
  and runs the normal ingest pipeline (`specs/ingest.md`). The wiki SHALL NOT silently absorb
  para/notes content by any other route.
- REQ-971: A page ingested from a `para/`/`notes/`-derived source is personal synthesis: it SHALL
  receive the default rating given by the reliability rubric's personal-synthesis case
  (`specs/schema.md` REQ-586), UNLESS it carries external citations that justify a higher rating
  under that rubric. The rubric is the single normative statement of the default value; this
  requirement only binds the seam to it.
- REQ-972: A promoted source SHALL follow the standard `raw/` → `ingested/<type>/` lifecycle and
  atomic move+commit (REQ-589). The provenance seam is identical to any other source; being
  personal in origin does not exempt it from provenance.
- REQ-973: When a `notes/literature/@<citekey>` page and a `wiki/` page both derive from the same
  archived source, the note's `source-file::` SHOULD point at the SAME `ingested/<type>/<file>`
  path the wiki page cites - one archived source, two readings. (Full claim-level auditability of
  this seam depends on block-native citations, `specs/citations.md`.)

### Note-Type Vocabulary (recognized, not authored)

- REQ-975: The tool SHALL recognize the `notes/` type vocabulary carried as a `type::` property:
  `fleeting | literature | permanent`. These types are informational to the tool (they scope the
  human's own queries); the tool does not create or mutate them.
- REQ-976: Lint SHALL treat a `notes/literature/@<citekey>` leaf segment (a proper-noun citekey) as
  a valid name under the naming rules (proper-noun-leaf exemption, `specs/schema.md`), NOT as a
  structural-name violation.

### Query-Page Tiering (decision)

- REQ-977: The vault-side query pages documented for the human layers (`para/live-list`,
  `notes/fleeting-inbox`; see `docs/para-notes-workflow.md`) are Logseq tier-1: the documented
  `#+BEGIN_QUERY` pages are the supported form. The Dataview equivalent on Obsidian is
  EXPERIMENTAL and NOT maintained by this project. These query pages are human-created; the tool
  does not scaffold, edit, or lint them (they are recognized structural pages per REQ-962).

### Configuration

- REQ-980: The scope rule and namespace-hygiene SHALL resolve the human namespaces from the
  optional `para_dir` and `notes_dir` keys defined in `specs/config.md` (REQ-625). Absent keys
  default as defined there (`para/` and `notes/` relative to the pages directory).
- REQ-981: `para/` and `notes/` are candidate members of `sensitive_source_types`
  (`specs/config.md`); when a promoted source is of a sensitive type, the pre-archive secret gate
  (`specs/ingest.md`) applies before any commit into `ingested/`.

---

## Scenarios

### Scenario 1: ingest never writes a human namespace

```
GIVEN a vault with pages under wiki/, para/, and notes/
WHEN /wiki-ingest drains the raw/ queue
THEN it SHALL create/update pages only under wiki/
AND it SHALL NOT create, edit, or move any page under para/ or notes/
```

### Scenario 2: lint exempts human namespaces

```
GIVEN a para/projects/blog-relaunch page with no source-file::, no reliability::, and no routing line
WHEN /wiki-lint runs
THEN it SHALL NOT flag any of those as missing
AND it SHALL NOT report the page as an orphan or unroutable
```

### Scenario 3: promotion enters through raw/ with provenance

```
GIVEN the human copies a permanent note into raw/note-tidy-data-principle.md
WHEN /wiki-ingest processes it
THEN a wiki/ page is created carrying source-file:: ingested/notes/note-tidy-data-principle.md
AND reliability:: medium (personal synthesis)
AND the source file is moved to ingested/ in the same atomic commit
```

### Scenario 4: higher reliability when externally cited

```
GIVEN a promoted note whose claims cite two independent peer-reviewed sources also in ingested/
WHEN /wiki-ingest processes it
THEN reliability:: MAY be raised above medium per the rubric (not fixed at medium)
```

### Scenario 5: query may read a note for context without writing it

```
GIVEN a query that references [[notes/permanent/regression-to-the-mean]]
WHEN /wiki-query answers it
THEN it MAY read the note for context
AND it SHALL NOT modify the note or add a routing line for it
```

### Scenario 6: literature citekey is a valid name

```
GIVEN a page named notes/literature/@Forte2022
WHEN /wiki-lint runs the naming-hygiene check
THEN the @Forte2022 leaf SHALL be accepted (proper-noun exemption)
AND SHALL NOT be flagged for the capital letter or the @ character
```

### Scenario 7: stray page outside the three namespaces

```
GIVEN a page "Scratchpad" that is not under wiki/, para/, notes/, journals, or a deliberate root page
WHEN /wiki-lint runs the namespace-hygiene check
THEN it SHALL flag the page as outside the namespace contract (info/warning)
```

---

## Acceptance Criteria

- [ ] The three namespaces and their obligations are defined with no overlap
- [ ] The scope rule binds every wiki workflow and is stated once (check_canon-enforceable)
- [ ] The promotion seam is the only sanctioned path in, with provenance and a medium default
- [ ] para/ and notes/ pages are exempt from wiki-only lint rules
- [ ] The notes type vocabulary is recognized without being authored by the tool
- [ ] The literature citekey naming exemption is specified
- [ ] The Obsidian query-page tiering decision is recorded (Logseq tier-1, Dataview experimental)

---

## Dependencies

- specs/schema.md - naming rules (lowercase structural names, proper-noun-leaf exemption),
  reliability rubric incl. the "personal synthesis = medium" case (REQ-586)
- specs/lint.md - naming-hygiene and namespace-hygiene rules that enforce this contract
- specs/ingest.md - the promotion seam runs on the standard ingest pipeline + pre-archive secret gate
- specs/config.md - `para_dir`, `notes_dir` (REQ-625), `sensitive_source_types` (REQ-624)
- specs/citations.md (v2.1) - full claim-level auditability of the "one source, two readings" seam
