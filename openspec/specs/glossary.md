# Spec: Glossary - Human-Decided Terminology Layer

## Description

The `glossary/` namespace holds EN-DE terminology decisions: a curated,
permanently maintained evergreen reference, modeled on the termbases
professional translators keep. Its ownership model is distinct from the
other namespaces of the REQ-960 contract: human-DECIDED (every Rule value is a human call,
made once and recorded forever), tool-READABLE (domain pages load as
drafting context and route via the glossary index), structure-LINTED
(lint rule 15 checks table shape, the rule enum, and staging hygiene, never
the decisions themselves). The hand-run layer (G-0, templates plus
`docs/glossary-workflow.md`) defined the conventions; this spec makes them
normative and adds the tooling contract (scaffold flag, lint rule, the
wiki-glossary skill, agent-transformed import).

> Spec version: introduced for v2.3 (issue #54), under the 2026-07-05 gate
> waiver (the 20-plus hand-decided rows gate). Uses the globally unique
> REQ-1000..1014 range. The namespace contract amendment is
> `specs/namespaces.md` REQ-960; the premortem revisions 4, 5, and 8
> (roadmap doc) are binding on this spec.

---

## Requirements

### Ownership Model

- REQ-1000: The tool SHALL NOT invent, edit, or delete a terminology
  decision: Rule values, DE equivalents, and Note content on decided rows
  are human-authored. The tool MAY scaffold glossary pages, MAY write rows
  the human explicitly confirmed at a checkpoint (the wiki-glossary skill),
  MAY read glossary pages, and SHALL lint structure only.
- REQ-1001: Wiki workflows (ingest, query, prune, audit, update) SHALL NOT
  write under `glossary/` (the scope rule, `specs/namespaces.md` REQ-965,
  is unchanged: they operate only on `wiki/`). The ONLY tool write path
  into `glossary/` is the wiki-glossary skill's confirmed checkpoint.
- REQ-1002: Glossary pages are EXEMPT from the wiki-only conventions:
  no `source-file::`, `reliability::`, `confidence::`, citations, or hub
  routing lines are required, and their absence SHALL NOT be flagged
  (mirroring `specs/namespaces.md` REQ-961). Naming (rule 13) applies as
  the advisory structural check; rule 15 is the glossary structure check.

### Layout and Table Canon

- REQ-1003: Layout: the `glossary` root page is the index (hub-style
  routing lines, one per domain, so query Stage-1 routing can load the
  right domain as context). Domain pages are `glossary/<domain>`
  (lowercase structural names, schema REQ-580). Term pages are
  `glossary/<domain>/<term>`; root-level term pages SHALL NOT be created.
- REQ-1004: The terms table is canon: a markdown table with the EXACT
  header `| EN | DE | Rule | Note |` under a `## Terms` heading. The Rule
  column is restricted to the enum `keep-en | translate | context`.
- REQ-1005: A term page SHALL carry `alias::` (the language forms that
  resolve to it), `domain::`, `rule::` (the REQ-1004 enum), and
  `conflicts::` (free text, the recorded why). Promote selectively: table
  rows are the default, term pages only for load-bearing terms.
- REQ-1006: Capture: terminology hesitations are tagged inline with
  `#glossary-todo` while writing; curation is a periodic human pass. The
  tool's role in capture is collection and presentation only.

### Staging and Import (premortem revisions 4 and 5)

- REQ-1010: Imported termbases SHALL land on `glossary/imported/<source>`
  staging pages carrying `source::` (attribution, e.g. CC-BY for Glosario)
  and `status:: unreviewed`. The Rule column arrives EMPTY: filling it is
  the human decision, row by row.
- REQ-1011: Import is AGENT-TRANSFORMED, never a parser script: the agent
  reads the downloaded termbase file (local file only, no network) and
  writes the staging rows, verifying its parsed row count against a
  mechanical count (`grep -c`) of the source. No YAML parser is written or
  vendored (premortem revision 4).
- REQ-1012: Import is PULL, not bulk: a staging import brings in ONLY the
  terms matching open `#glossary-todo` captures plus explicitly requested
  ones, never the full termbase (premortem revision 5).
- REQ-1013: Drafting context loads DOMAIN pages only, NEVER staging pages.
  A staging page is unreviewed material; treating it as context is how the
  Rule column dies (premortem revision 5).
- REQ-1014: The promote flow moves a decision, not a row: at the
  wiki-glossary checkpoint the human decides the Rule (and edits DE/Note),
  the confirmed row is written to the chosen domain page's terms table,
  and the staging row is removed (or the staging page deleted when it
  empties). An optional term page (REQ-1005) is offered for load-bearing
  terms.

---

## Scenarios

### Scenario 1: lint accepts a decided domain page

```
GIVEN glossary/tech with a | EN | DE | Rule | Note | table whose Rule cells
    are all keep-en, translate, or context
WHEN /wiki-lint runs
THEN rule 15 reports no findings for the page
AND no wiki-only rule (source-file, reliability, cite, routing) fires
```

### Scenario 2: lint flags a bad rule value

```
GIVEN a glossary/tech row | prompt | der Prompt | keep-english | ... |
WHEN /wiki-lint runs
THEN rule 15 flags the row: invalid Rule 'keep-english'
    (enum: keep-en | translate | context)
```

### Scenario 3: staging page without status

```
GIVEN glossary/imported/glosario without a status:: property
WHEN /wiki-lint runs
THEN rule 15 flags the missing staging property (REQ-1010)
```

### Scenario 4: undecided row on a decided page

```
GIVEN a glossary/tech row whose Rule cell is empty
WHEN /wiki-lint runs
THEN rule 15 flags it: undecided row on a domain page (empty Rule belongs
    on a glossary/imported/ staging page)
```

### Scenario 5: import is pull, not bulk

```
GIVEN 4 open #glossary-todo captures and a downloaded 400-term glossary.yml
WHEN /wiki-glossary import runs
THEN the staging page receives only the rows matching the 4 captures
    (plus explicitly requested terms), each with an EMPTY Rule cell
AND the agent verifies its row count against grep -c over the source
```

### Scenario 6: drafting context never loads staging

```
GIVEN glossary/tech (12 decided rows) and glossary/imported/glosario
    (40 unreviewed rows)
WHEN the user drafts with "use the conventions from glossary/tech"
THEN only the domain page is loaded as context
AND the staging page is never loaded as drafting context
```

---

## Acceptance Criteria

- [ ] The tool never writes a Rule value the human did not confirm
- [ ] Wiki verbs never write under glossary/; the skill checkpoint is the
      only tool write path
- [ ] Glossary pages are exempt from wiki-only rules; rule 15 lints
      structure (table shape, rule enum, staging hygiene)
- [ ] The table header and rule enum are canon and machine-checked
- [ ] Staging pages carry source:: and status::, with empty Rule cells
- [ ] Import is agent-transformed (no parser script) and pull-only
- [ ] Drafting context loads domain pages only

---

## Dependencies

- specs/namespaces.md REQ-960 (the four-namespace contract) and the
  check_canon namespace surface shipped in the same PR (premortem
  revision 8)
- specs/config.md REQ-628 - the `glossary_dir` key (default `glossary`)
- specs/lint.md Rule 15 - the mechanical enforcement of this spec
- specs/schema.md REQ-580 - lowercase structural names for domains
- templates/<tool>/glossary-domain.md and glossary-term.md (G-0) - the
  scaffold sources
- docs/glossary-workflow.md - the narrative capture/curate/promote guide
