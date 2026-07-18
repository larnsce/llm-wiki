# Spec: Storage - Two-Plane Contract (index.db / archive.db)

## Description

The personal pipeline (v3.0) adds a machine plane beside the markdown vault. The
contract is one sentence: markdown is what a human writes (or the tool writes as
curated synthesis); SQLite is what a machine accumulates. Two databases carry the
SQLite plane: `index.db`, derived from the vault and disposable, and `archive.db`,
raw personal capture and irreplaceable. They are never merged and neither ever
enters git. This spec defines the two-plane contract, the `voice_notes` schema,
the durability requirements that protect archive.db, the derivation requirements
that keep index.db provably disposable, and the dead-man status line that makes
pipeline silence visible.

> Spec version: introduced for v3.0 (P-1). This spec uses the globally unique
> REQ-1100..1141 range. The workflow that consumes `voice_notes` rows is
> specified in `specs/ingest.md` (Voice Sources); the reliability default for
> capture-backed claims is `specs/schema.md` REQ-586b; the audit verdict for
> them is `specs/audit.md` REQ-927.

---

## Requirements

### The Two-Plane Contract

- REQ-1100: The system SHALL maintain exactly two content planes: the markdown
  plane (the vault: journals and pages a human writes, plus pages the wiki
  toolchain writes as curated synthesis under `wiki/`) and the SQLite plane
  (what a machine accumulates: raw capture and derived indexes). The rule that
  binds every future feature: markdown is what a human writes; SQLite is what a
  machine accumulates. Content SHALL NOT be placed on the wrong plane.
- REQ-1101: The SQLite plane SHALL consist of exactly two databases:
  - `index.db` - DERIVED from the vault and DISPOSABLE. It can be deleted and
    rebuilt from the markdown at any time with zero information loss.
  - `archive.db` - SOURCE data and IRREPLACEABLE. Raw personal capture (voice
    transcripts; later emails, calendar, contacts) that exists nowhere else.
- REQ-1102: The two databases SHALL NEVER be merged into one file, attached into
  a combined schema, or cross-written. One is disposable and one is not;
  separate files keep the distinction impossible to get wrong.
- REQ-1103: Both databases SHALL live OUTSIDE git: neither file, nor any dump or
  copy of one, is ever committed. Default placement is outside the vault's
  git-tracked tree; when a database file is placed inside the vault directory,
  its path MUST be gitignored (managed by the system, like the sensitive-type
  paths of `specs/ingest.md` REQ-046).
- REQ-1104: All database access SHALL use python3's stdlib `sqlite3` module. The
  zero-external-dependency rule applies to the storage plane unchanged.

### archive.db - Source of Record

- REQ-1110: archive.db holds raw capture: rows are appended by capture pipelines
  (voice transcription; later importers such as email or calendar) and read by
  ingest workflows. Captured content is append-only: the system SHALL NOT edit
  or delete a row's captured fields. The only sanctioned mutation is workflow
  state (the `processed` flag, whose lifecycle is owned by `specs/ingest.md`
  REQ-080).
- REQ-1111: The `voice_notes` table SHALL have exactly these columns:

  | column | type | meaning |
  |---|---|---|
  | `id` | INTEGER PRIMARY KEY | the provenance id referenced as `archive.db:voice_notes/<id>` |
  | `recorded_at` | TEXT (ISO 8601) | when the memo was recorded |
  | `duration` | REAL (seconds) | length of the recording |
  | `transcript` | TEXT | the full transcript (the ingest input) |
  | `audio_path` | TEXT | path to the audio file (moved to cold storage after transcription) |
  | `processed` | INTEGER (0/1) | whether ingest has consumed the row |

### archive.db - Durability (premortem #10)

- REQ-1120: A nightly off-machine copy of archive.db SHALL exist BEFORE any real
  (non-test) data enters the database. "Off-machine" means a target that
  survives loss of the capturing machine (e.g. Time Machine plus one cloud or
  offsite copy). Starting capture without the copy job in place is a spec
  violation, not a docs footnote.
- REQ-1121: A restore drill SHALL be executed quarterly: restore archive.db from
  the off-machine copy to a scratch location and verify row counts against the
  live file. A backup that has never been restored is a hypothesis, not a
  backup. The drill date and result SHOULD be recorded (journal entry or the
  pipeline docs).
- REQ-1122: The vault's agent guidance (the vault-level CLAUDE.md or equivalent)
  SHALL forbid `git clean -xfd` and any equivalent command that removes ignored
  or untracked files inside the vault or the database location. Agents are the
  likeliest executor of the deletion; the ban SHALL be stated where agents read
  it, not only in this spec.

### index.db - Derived and Disposable (premortem #6)

- REQ-1130 (frozen schema): index.db SHALL contain exactly three content
  tables, plus the rebuild stamp and FTS5 index structures over page text,
  with exactly these columns (concrete schema fixed for P-4):
  - `people(page TEXT PRIMARY KEY, name TEXT, aliases TEXT, updated TEXT)`:
    one row per page in the people namespace; `name` is the leaf segment,
    `aliases` the page's `alias::` value verbatim (empty string when
    absent), `updated` the page's `updated::` value.
  - `meetings(page TEXT, line INTEGER, date TEXT, text TEXT,
    PRIMARY KEY (page, line))`: one row per `#meeting`-tagged block in a
    page or journal; `date` is the journal date for journal blocks, else
    the page's `date::` (else `updated::`, else empty), `text` the block
    text.
  - `page_properties(page TEXT, key TEXT, value TEXT,
    PRIMARY KEY (page, key))`: every page-level property of every page and
    journal.
  - `page_text`: an FTS5 virtual table over `(page, text)`, one row per
    page and journal, full markdown text.
  - `rebuild_stamp(stamp TEXT)`: a single row holding the REQ-1131 content
    stamp.
  Adding any further table or column requires amending THIS spec
  first; an implementation-side schema addition is a spec violation.
- REQ-1131 (reproducible rebuild): The rebuild SHALL be a deterministic function
  of the vault's content: two rebuilds from the same vault state SHALL produce
  identical database dumps. The harness asserts this reproducibility (v3.0,
  P-4/P-7). To keep dumps identical, the stamp is a deterministic content
  hash of the indexed markdown (sorted relative paths plus per-file
  hashes), NEVER wall-clock time; the rebuild AGE shown in the dead-man
  status line (REQ-1140) is read from the index.db file's mtime instead.
- REQ-1132 (nothing without a markdown source): Data that has no markdown source
  in the vault SHALL NOT enter index.db. Importers write to archive.db or, via
  the ingest pipeline, to the vault - NEVER to index.db. If a fact matters
  enough to query, it has a page or journal line; index.db only re-arranges what
  the markdown already says.
- REQ-1133 (no hooks; staleness at query time): No pre-commit or other git hook
  SHALL rebuild index.db. Staleness is checked at QUERY time: when the rebuild
  stamp recorded at the last rebuild lags the vault head (the stored stamp
  differs from the recomputed REQ-1131 content hash;
  `rebuild_index.py --stale-check`), the query workflow SHALL warn and MAY
  rebuild before answering (`specs/query.md`, extended by P-5).

### Dead-Man Pipeline Status (premortem #4)

- REQ-1140: The daily journal summary (the voice workflow's output block on
  today's journal page, `specs/ingest.md` REQ-082) SHALL begin with a one-line
  pipeline status: the age of the newest file in the voice inbox, the count of
  unprocessed `voice_notes` rows, and the age of the last index rebuild.
  Example: `pipeline: inbox newest 2h | unprocessed 3 | index rebuilt 26h ago`.
  Silence becomes visible in the one place the maintainer already looks.
- REQ-1140a (index freshness follows query traffic, by design): `index.db` is
  rebuilt lazily at query time (REQ-1133), never on a timer or a git hook, so
  its freshness is a function of index-plane query traffic, not edit activity.
  The `index rebuilt` field of the status line SHALL reflect this without
  reading as a defect. When no `index.db` exists yet (a valid state after a
  fresh setup, or when no index-plane query has ever run), the field reads
  `index n/a` and is INFORMATIONAL, not a warning: it means "will build on the
  first index-plane query," not "the pipeline is broken." A large `index
  rebuilt Nh ago` age is likewise expected when no routed query has run in that
  span; it is a prompt to rebuild if desired (REQ-1142), never a failure. The
  inbox-age and unprocessed-count fields keep their warning semantics (a stale
  inbox is an upstream capture failure, Scenario 5); only the index field is
  reframed here.
- REQ-1141: The voice pipeline documentation (v3.0, P-2) SHALL document a weekly
  canary memo: speak one test memo on the phone and expect it in tomorrow's
  journal. Mac-side monitoring cannot see a dead phone-side leg; the canary
  closes that gap.
- REQ-1142 (opt-in rebuild from routine skills, never automatic): A skill that
  is already running for another purpose and computes or reports index
  freshness (`wiki-maintain status`, `wiki-ingest-voice`) MAY run
  `rebuild_index.py --stale-check` and, on a stale or missing index, OFFER to
  rebuild - detection plus an explicit offer, exactly the shape of the
  data-package staleness check (ingest REQ-106). The rebuild is a write and
  SHALL NOT happen automatically inside a read-only status or status-line path:
  it requires explicit user confirmation, and declining leaves the index as-is
  (the next index-plane query still handles it lazily, REQ-1133). This closes
  the freshness loop for a maintainer who never runs index-plane queries
  without turning the read-only report into a writer or reintroducing the
  background rebuild REQ-1133 forbids.

---

## Scenarios

### Scenario 1: index.db rebuild is reproducible

```
GIVEN a vault at a fixed git commit
WHEN the index is rebuilt twice from that same vault state
THEN the two runs produce identical database dumps
AND deleting index.db between the runs changes nothing (the vault is the source)
```

### Scenario 2: importer data with no markdown source is refused

```
GIVEN a calendar importer holding events that appear on no vault page
WHEN the importer runs
THEN it writes rows to archive.db (or pages to the vault via the ingest pipeline)
AND it SHALL NOT write to index.db
AND a later rebuild of index.db contains an event only if it reached a vault page
```

### Scenario 3: no real data before the off-machine copy exists

```
GIVEN a freshly created archive.db that holds only test rows
AND no nightly off-machine copy job is configured yet
WHEN the first real voice note is about to be inserted
THEN the durability requirement (REQ-1120) is not met
AND capture SHALL NOT start until the copy job exists and has produced one copy
```

### Scenario 4: agent asked to clean the vault

```
GIVEN an agent working inside the vault repository
WHEN it considers running git clean -xfd (or any ignored-file-removing command)
THEN the vault's agent guidance forbids the command and the agent SHALL NOT run it
AND the gitignored database files survive the cleanup
```

### Scenario 5: dead-man status line surfaces a stalled phone sync

```
GIVEN the newest file in the voice inbox is 5 days old
AND the unprocessed voice_notes count is 0
WHEN the daily journal summary is written
THEN it begins with: "pipeline: inbox newest 5d | unprocessed 0 | index rebuilt 1d ago"
AND the 5-day inbox age is the visible warning that capture has stalled upstream
```

### Scenario 6: staleness is checked at query time, not commit time

```
GIVEN index.db was last rebuilt before the vault's latest commit
WHEN a query routes to index.db
THEN the system warns that the index is stale and MAY rebuild before answering
AND no pre-commit hook has rebuilt the index (none exists)
```

### Scenario 7: a never-built index reads as informational, not a defect

```
GIVEN a vault where no index-plane query has ever run, so index.db does not exist
WHEN the daily journal summary (or wiki-maintain status) reports pipeline status
THEN the index field reads "index n/a" as an informational state
    ("builds on the first index-plane query"), NOT a warning (REQ-1140a)
AND the run is not treated as a defect for the missing index
```

### Scenario 8: a routine skill offers, never forces, an index rebuild

```
GIVEN wiki-maintain status runs and index.db is stale (or missing)
WHEN it reports index freshness (rebuild_index.py --stale-check)
THEN it OFFERS to rebuild with explicit confirmation (REQ-1142)
AND if the user declines, index.db is left unchanged and the status path
    performs no write; the next index-plane query still rebuilds lazily
```

---

## Acceptance Criteria

- [ ] The two planes and the two databases are defined with no overlap; the
      never-merge rule is explicit
- [ ] Both databases stay out of git by construction (placement plus gitignore);
      no dump or copy is ever committed
- [ ] A nightly off-machine copy of archive.db exists before real data enters it
- [ ] A restore drill is executed quarterly and its result recorded
- [ ] Vault agent guidance forbids `git clean -xfd` and equivalent
      ignored-file-removing commands
- [ ] `voice_notes` has exactly the six specified columns
- [ ] index.db is frozen to the three content tables, the rebuild stamp, and
      FTS5, with the REQ-1130 columns; any addition amends this spec first
- [ ] Two rebuilds from the same vault state produce identical dumps
- [ ] Nothing without a markdown source enters index.db; importers never write
      to it
- [ ] No pre-commit rebuild hooks; staleness is checked at query time
- [ ] The daily journal summary begins with the pipeline status line
- [ ] A missing/never-built index reads as informational (`index n/a`), not a
      warning, when no index-plane query has run (REQ-1140a)
- [ ] A routine skill (`wiki-maintain status`, `wiki-ingest-voice`) offers, with
      explicit confirmation, to rebuild a stale/missing index; it never rebuilds
      automatically in a read-only status path (REQ-1142)

---

## Dependencies

- specs/ingest.md (Voice Sources, REQ-080..087) - the only workflow that
  consumes `voice_notes` rows; owns the `processed` lifecycle and the provenance
  shape `archive.db:voice_notes/<id>`
- specs/schema.md REQ-586b - the capture-backed reliability default for claims
  with archive.db provenance
- specs/audit.md REQ-927 - the capture-backed verdict and the dangling-id
  resolution check against archive.db
- specs/query.md - query-time staleness handling and two-plane routing (extended
  by v3.0 P-5)
- python3 stdlib `sqlite3` only (zero-external-dependency rule)
- Concrete database file locations are resolved by configuration when the
  storage plane is implemented (v3.0 P-4); the placement invariants of REQ-1103
  bind any choice
