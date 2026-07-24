# Spec: Paper Hubs - Per-Manuscript Anchor Pages

## Description

One namespace per manuscript: `wiki/papers/<slug>/`. The hub page
`wiki/papers/<slug>` is the single anchor for everything the wiki holds
about one paper - the literature drawn on, the datasets, the open
questions, and the dated draft decisions - so that material stops being
spread across literature pages, concept pages, and journal entries with
no per-manuscript view. The hub doubles as the homepage of a published
paper site (issue #145: the static viewer opens a hub as its default
route), and the export bundle (issue #148) walks the hub's link graph,
so hub completeness IS the publish boundary. The wiki-paper skill
scaffolds and maintains hubs; lint rule 16 checks their structure.

> Spec version: introduced for v3.8 (issue #146). Uses the globally
> unique REQ-1500..1518 range. Lint rule 16 uses REQ-260..263
> (specs/lint.md). `wiki/papers/` sits inside the machine-written
> `wiki/` namespace, so the REQ-960 namespace contract is unchanged.

---

## Requirements

### Namespace and Hub Page

- REQ-1500: A manuscript's anchor is the page `wiki/papers/<slug>` (the
  namespace page itself; lowercase structural slug per schema REQ-580).
  Material belonging to exactly one manuscript MAY live under
  `wiki/papers/<slug>/<child>`; shared material (literature notes,
  concept pages, datasets) stays where it lives and is LINKED, never
  copied.
- REQ-1501: The hub page SHALL carry `type:: paper-hub` (schema REQ-500)
  with required properties `status::`, `created::`, and `updated::`
  (lint REQ-260). `status::` SHOULD be one of `drafting`, `submitted`,
  or `published`; the value is not enum-enforced. A hub MAY carry
  `target::` (the venue) as free text.
- REQ-1502: The hub SHALL contain these sections, each as a heading:
  `Manuscript`, `Literature drawn on`, `Data`, `Open questions`,
  `Draft decisions`, and `AI use` (lint REQ-261). Section content is
  editorial and never linted.
- REQ-1503: Draft decisions are dated, append-only bullets under
  `Draft decisions`; a decision that supersedes an earlier one follows
  the wiki-update supersede convention rather than deleting the bullet.
- REQ-1504: The `AI use` section links the paper's agent-use log page
  (`wiki/papers/<slug>/agent-log`, REQ-1513, scaffolded with the hub);
  prose there stays welcome, the link is the requirement.

### Reachability (the export guarantee)

- REQ-1505: Every page under `wiki/papers/<slug>/` SHALL be reachable
  from its hub: the hub links every child page (lint REQ-262). This is
  what the issue #148 export walk and the issue #145 publish boundary
  rely on; an orphaned child would silently drop out of the published
  artifact.
- REQ-1506: The `wiki/papers` namespace hub (created on the first
  scaffold, `type:: hub`) carries one routing line per paper hub in its
  `### Index`, like any namespace hub. Users MAY add `papers` to the
  config `namespaces` list for Phase-0 query routing.

### The wiki-paper Skill

- REQ-1507 (scaffold): `wiki-paper new <slug>` SHALL scaffold the hub
  page with the REQ-1501 properties and REQ-1502 sections in the
  configured tool's format, create the `wiki/papers` namespace hub if
  absent, and add the paper's routing line to it. The scaffold is shown
  as a diff and written only after confirmation, then committed.
- REQ-1508 (attach): `wiki-paper attach <slug> <page>...` SHALL append
  links for the given pages to the matching hub section (literature
  pages to `Literature drawn on`, `wiki/data/` pages to `Data`,
  anything else offered with a section choice). Attaching NEVER
  rewrites the attached page (append-only is respected on both sides);
  a page already linked is skipped, not duplicated.
- REQ-1509 (status): `wiki-paper status <slug>` is read-only: it
  reports the hub's sections, linked pages, children not yet linked
  (REQ-262 candidates), and `status::`/`updated::`.
- REQ-1510: The skill SHALL NOT write outside `wiki/papers/` and the
  `wiki/papers` hub's routing lines. Literature, concept, and data
  pages are linked in place.

### Lifecycle and Seams

- REQ-1511 (cold papers): A finished paper's hub demotes like any cold
  page (prune.md LRU-Demote); demotion MUST NOT break the hub or its
  children, and a re-hit re-promotes it per query REQ-452. Nothing in
  this spec exempts paper pages from pruning.
- REQ-1512 (PARA seam, issue #140): a paper is also a project in the
  human layer. The hub MAY link to a `para/` project page and a `para/`
  project page may link back, but the hub SHALL NOT duplicate para/
  content and the skill SHALL NOT write under `para/` (namespaces
  REQ-966; the promotion seam stays the only crossing).

### The Agent Log (AI-transparency; issue #147)

- REQ-1513 (log page): Each paper MAY carry the child page
  `wiki/papers/<slug>/agent-log`, scaffolded by `wiki-paper new`
  together with the hub. The page is the SOURCE OF TRUTH for the
  paper's AI use: append-only, human-legible markdown, renderable by
  the #145 viewer and shipped in the #148 bundle. A queryable
  `index.db` mirror is parked (the two-plane pattern would allow one,
  rebuildable from the page) until a real query need appears.
- REQ-1514 (entry format): One markdown table under the page's h1 with
  the EXACT header
  `| Date | Skill | Model | Sources touched | Pages written | Human confirmations |`
  (lint REQ-263). One row per skill invocation. The `Model` value is
  the session model AS THE HUMAN CONFIRMS IT at the checkpoint, or
  `session` when unstated; it is NEVER introspected or guessed by the
  executing model (the REQ-053 dispatch-record lesson survives the
  tiering removal). Read-only invocations record `- (read-only)` under
  Pages written.
- REQ-1515 (append discipline): A skill invocation SHALL append exactly
  one row when it writes a page under `wiki/papers/<slug>/`, and SHOULD
  append one when it writes or updates a page the paper's hub links.
  Read paths (wiki-query) append their row without a per-query commit,
  mirroring the Access-Log discipline (query REQ-450 scope unchanged).
  Rows are never edited or deleted.
- REQ-1516 (disclosure statement): The log page MAY carry a
  `## Disclosure statement (generated)` section. It SHALL be
  regenerable from the table rows alone (no memory reconstruction);
  regenerating that marked section is the only sanctioned rewrite on
  the page, and the rows themselves stay append-only.
- REQ-1517 (supersession cross-reference): When a wiki-update run on a
  paper-linked page supersedes a claim, the log row's Pages written
  cell links that page, and the page-level supersede marker and the
  log row carry the same date, so the two artifacts reference each
  other.
- REQ-1518 (publishable content): The log is written to be published:
  rows carry page links, source titles, and citekeys, NEVER prompt
  fragments or local filesystem paths. The page passes the shared
  publish gate (`secret_scan.py`) like any exported page.

---

## Scenarios

### Scenario 1: Scaffold a new paper hub

```
GIVEN a configured wiki with no wiki/papers namespace
WHEN the user runs /wiki-paper new cbs-adoption
THEN the system SHALL show the hub page diff (properties + six sections)
AND on confirmation create wiki/papers/cbs-adoption and the wiki/papers
    namespace hub with one routing line
AND commit both in one commit
```

### Scenario 2: Attach existing pages

```
GIVEN literature page notes/literature/@tilley2024 and dataset page
      wiki/data/household-survey-2026 exist
WHEN the user runs /wiki-paper attach cbs-adoption @tilley2024
     wiki/data/household-survey-2026
THEN the hub gains a link under "Literature drawn on" and one under
     "Data", shown as a diff first
AND neither attached page is modified
```

### Scenario 3: Orphaned child flagged

```
GIVEN wiki/papers/cbs-adoption/agent-log exists but the hub does not
      link it
WHEN the user runs /wiki-lint
THEN rule 16 SHALL report REQ-262 on the hub (child not reachable)
AND propose no auto-fix (linking is editorial)
```

### Scenario 4: Ingest run appends one log row

```
GIVEN wiki/papers/cbs-adoption exists with its agent-log child
WHEN /wiki-ingest writes notes/literature/@tilley2024 and links it
     from the cbs-adoption hub at the checkpoint
THEN the run SHALL append exactly one row to
     wiki/papers/cbs-adoption/agent-log (date, skill wiki-ingest,
     human-confirmed model, source title, pages written,
     confirmations given)
AND the row rides the run's atomic commit
```
