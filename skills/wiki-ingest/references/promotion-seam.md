# Promotion seam: para/ and notes/ content entering the wiki

Reference for the para/notes promotion seam (specs/namespaces.md
REQ-970..973, REQ-981). Implements issue #24. The namespace scope rule that
frames this seam is stated once in
[architecture](../../wiki-core/references/architecture.md); this file does
not restate it.

## What qualifies (REQ-970)

The ONLY sanctioned path from the human-owned `para/` or `notes/` namespaces
into `wiki/` is via `raw/`: the human copies the durable content into a
source file and runs the normal ingest pipeline. The wiki never silently
absorbs para/notes content by any other route (a `[[link]]` from a wiki page
into `notes/` is not absorption; rewriting note content onto a wiki page
without a `raw/` source is).

Recognize a promoted source by its filename in the queue:

- `raw/para-<project>.md`: durable blocks harvested from a `para/` project
  (typically at archive time; the human procedure is in
  `docs/para-notes-workflow.md`)
- `raw/note-<name>.md`: a note promoted from `notes/` (a permanent note, or
  a literature note; see the literature variant below)

A promoted source is a NORMAL source: it takes the same queue position
(oldest first), the same phases, the same checkpoint row, the same quality
gate. Nothing below exempts it from any standard ingest step; this file only
adds the seam-specific defaults.

## Source type and sensitivity (REQ-981, ingest REQ-046)

- Infer the type as `notes` (personal note) unless the content is clearly
  something else, per the standard Phase 0 inference.
- `para` and `notes` content is candidate `sensitive_source_types` material:
  personal projects and notes are where governed personal data is most
  likely to live. The pre-archive secret gate
  ([secret-gate](secret-gate.md)) applies to every promoted source like any
  other; when the source's type is listed in `sensitive_source_types`, the
  untracked flow keeps its bytes out of git history.

## Reliability default: personal synthesis (REQ-971)

A promoted source is personal synthesis. The reliability rubric's
personal-synthesis case (specs/schema.md REQ-586) is the single normative
statement of the default; this seam binds to it:

- Default: `reliability:: medium`, checkpoint rationale "personal synthesis
  (promoted from para/notes; schema REQ-586)".
- Exception: when the promoted content carries external citations whose
  sources justify a higher rating under the rubric (for example claims each
  backed by two independent peer-reviewed sources also in `ingested/`), rate
  it higher. The rubric decides; medium is a default, not a hard floor.
- The rating is claim-level with the page-minimum roll-up, exactly as for
  any source ([trust](../../wiki-core/references/trust.md)).

## Lifecycle, provenance, citations (REQ-972)

Being personal in origin exempts a promoted source from nothing:

- Standard `raw/` to `ingested/<type>/` lifecycle and the atomic move+commit
  (schema REQ-589, ingest REQ-075): the page edits and the file move land in
  ONE commit.
- `source-file::` records the `ingested/` path on every page written from
  the source (ingest REQ-073).
- `cite::` emission applies to promoted claims like any source (ingest
  REQ-033b, [citations](citations.md)): non-common-knowledge factual claims
  cite the promoted source's `ingested/` path; the source-file union
  invariant holds.
- Single-source pages not rated `high` get `## Pending Review` as usual
  (ingest REQ-074).

## The literature variant: one archived source, two readings (REQ-973)

When a `notes/literature/@<citekey>` page and a `wiki/` page both derive
from the same archived source, the note's `source-file::` SHOULD point at
the SAME `ingested/<type>/<file>` path the wiki page cites. One archived
source, two readings: the human's reading lives in `notes/literature/`, the
machine's synthesis in `wiki/`, both auditable back to the same file.

Ingest's part is a REMINDER, never a write:

- When a processed source is recognizably a literature note (the filename is
  `raw/note-@<citekey>.md`, or its metadata carries `citekey::` or
  `type:: literature`), add a reminder line to the Phase 5 report: "This
  looks like a literature note for @<citekey>. If a
  notes/literature/@<citekey> page exists, set its source-file:: to
  <ingested/path> so both readings point at the same archived source
  (REQ-973)."
- Setting that property is the human's edit. Never write it into `notes/`
  as a side effect: `notes/` is human-authored and the scope rule (REQ-966)
  forbids it.

Full claim-level auditability of this seam rides on the block-native
citations the wiki side already emits (specs/citations.md).
