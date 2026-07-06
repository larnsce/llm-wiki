# Archive layer: email, calendar, and contacts into archive.db (macOS)

Maintainer-run plumbing for the personal pipeline (v3.0, Phase 3 of
[`prompts/llm-wiki-setup-plan.md`](../prompts/llm-wiki-setup-plan.md)): get
your bulk personal history -- Gmail, Google Calendar, contacts -- into
`archive.db` beside the `voice_notes` rows, queryable with plain SQL.
Everything here is copy-paste and runs on one machine; the repo documents it
but does not ship or test it (premortem revision 12 in
[`docs/roadmap-glossary-personal-pipeline.md`](roadmap-glossary-personal-pipeline.md):
the repo stays a generic tool, and Dogsheep-style importers are used instead
of hand-written ones).

> **Scope.** This guide covers requesting the exports, importing them into
> `archive.db`, and the lazy alias-resolution practice that makes the data
> usable per person. The storage contract it implements is
> [`openspec/specs/storage.md`](../openspec/specs/storage.md)
> (REQ-1100..1141); where this guide and the spec disagree, the spec wins.
> Timing: this serves Phase 3 of the adoption plan (weeks 3-5). Doing it
> before the base loop and the voice leg are alive is front-loading the
> premortem warns against -- the only step to do EARLY is section 3
> (requesting Takeout), because the export takes days to arrive.

## 1. What this is

```
takeout.google.com --(days later)--> ~/archive/exports/  (raw zips, keep forever)
                                          |
             mbox-to-sqlite / google-takeout-to-sqlite / two stdlib snippets
                                          |
                                  archive.db  (messages, meetings,
                                   meeting_attendees, contacts, ...)
                                          |
                     SQL when a question needs it; people pages seeded
                     through NORMAL ingest; aliases resolved lazily
```

Two rules shape every step:

1. **Importers write to archive.db or (via `raw/` and `/wiki-ingest`) to the
   vault -- NEVER to index.db** (storage REQ-1132). index.db is derived from
   the vault's markdown and disposable; nothing enters it without a markdown
   source. If a meeting or an email matters enough to query through the wiki,
   it gets a page or a journal line first; index.db only re-arranges what the
   markdown already says. Note the two `meetings` tables are different
   things: `archive.db:meetings` (this guide) is raw calendar capture;
   `index.db:meetings` (the frozen three-table schema, REQ-1130) is rebuilt
   from vault pages. They never mix.
2. **The export files are the raw record.** Keep the Takeout zips, `.ics`,
   and `.vcf` files in cold storage (`~/archive/exports/`). The importer
   tables are convenient access, rebuilt from those files at will; the files
   are what makes archive.db re-derivable if an import goes wrong (setup
   plan, "data loss" guardrail).

## 2. Before anything: archive.db durability

Same discipline as the voice pipeline, recapped because this guide multiplies
what is in the database:

- The **nightly off-machine copy** of archive.db must exist BEFORE real data
  enters it (storage REQ-1120). If you followed
  [`docs/voice-pipeline.md`](voice-pipeline.md) section 2, it already runs;
  if you are starting here, do that section first -- backup script, launchd
  job, and the vault CLAUDE.md line forbidding `git clean -xfd` and any
  ignored-file-removing command (REQ-1122).
- **Quarterly restore drill** (REQ-1121): restore from the off-machine copy
  to a scratch path and compare row counts. After this guide, extend the
  drill's count check beyond `voice_notes`:

  ```bash
  for t in voice_notes messages meetings meeting_attendees contacts; do
    python3 -c "import sqlite3,sys; print('$t', sqlite3.connect(sys.argv[1]).execute('SELECT count(*) FROM $t').fetchone()[0])" ~/archive/archive.db
  done
  ```

- archive.db and every export file stay **out of git** (REQ-1103). Nothing in
  this guide touches the vault's git history except the people pages that go
  through the normal ingest checkpoint.

## 3. Request Takeout EARLY (multi-day wait)

> **Warning: a Google Takeout export takes days.** Google prepares the
> archive asynchronously and emails you a download link when it is ready --
> commonly 1-3 days, longer for large mailboxes. Request it at the START of
> Phase 3 (or during Phase 2, the export sitting unopened costs nothing) so
> the wait overlaps work you are doing anyway.

At [takeout.google.com](https://takeout.google.com):

1. Deselect all, then select **Mail** (delivered as `.mbox`), **Calendar**
   (delivered as `.ics`, one per calendar), and **Contacts** (choose
   **vCard** format).
2. Optionally add **My Activity** (JSON) if you want search/activity history
   queryable; skip **Location History** by default -- it is huge and the
   privacy surface is out of proportion to its usefulness here.
3. Export once (not scheduled), `.zip`, largest archive size so the mailbox
   does not split.

When the link arrives, download into cold storage and unpack:

```bash
mkdir -p ~/archive/exports
cd ~/archive/exports
unzip takeout-*.zip -d takeout-$(date +%F)
```

## 4. Tooling

The importer CLIs are Python tools; install them isolated with
[pipx](https://pipx.pypa.io) (macOS pythons refuse bare `pip install`
system-wide, and a venv would work equally well):

```bash
brew install pipx
pipx install mbox-to-sqlite          # Gmail .mbox -> SQLite (simonw)
pipx install google-takeout-to-sqlite  # My Activity etc. (dogsheep)
pipx install sqlite-utils            # FTS setup + ad-hoc queries
pipx install datasette               # optional: browse archive.db in a browser
```

These are personal-machine tools. The repo's own zero-dependency rule
(bash/python3/git) applies to the shipped scripts and is unchanged; the two
snippets below are stdlib-only on purpose.

## 5. Email: .mbox into archive.db, with full-text search

```bash
mbox-to-sqlite mbox ~/archive/archive.db \
  ~/archive/exports/takeout-*/Takeout/Mail/"All mail Including Spam and Trash.mbox"
```

Then check what landed and enable FTS5 over it (the setup plan's "email into
archive.db; add FTS5" step). Inspect first -- the table is `messages` and the
useful text columns are typically `subject` and `payload`; confirm against
your own import before enabling:

```bash
sqlite-utils schema ~/archive/archive.db
sqlite-utils enable-fts ~/archive/archive.db messages subject payload
sqlite-utils search ~/archive/archive.db messages "sanitation planning" -c subject | head
```

A large mailbox takes a while; re-running the import later with a fresh
Takeout re-imports the file it is given (keep each export's zip -- section 1,
rule 2).

## 6. My Activity (optional)

```bash
google-takeout-to-sqlite my-activity ~/archive/archive.db \
  ~/archive/exports/takeout-*.zip
```

The tool reads the zip directly. (Its other documented command is
`location-history`; skipped by default per section 3.)

## 7. Calendar: .ics into meetings / meeting_attendees

No Dogsheep tool covers `.ics`, and the format is simple enough that a
stdlib snippet beats a dependency. Save as `~/bin/ics_to_meetings.py`:

```python
#!/usr/bin/env python3
"""ics_to_meetings.py - calendar .ics export into archive.db (stdlib only).

Usage: python3 ics_to_meetings.py ~/archive/archive.db calendar.ics [more.ics ...]

Rebuilds the meetings and meeting_attendees tables from the given .ics
file(s) on every run (full re-import, no incremental state). The .ics files
are the raw record: keep them in cold storage so the tables stay
re-derivable (storage spec, premortem "data loss" guardrail).
"""
import re
import sqlite3
import sys

DT_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})(Z?))?$")
ESCAPES = {"\\n": "\n", "\\N": "\n", "\\,": ",", "\\;": ";", "\\\\": "\\"}


def unfold(handle):
    """RFC 5545 line unfolding: continuation lines start with space/tab."""
    out = []
    for line in handle:
        line = line.rstrip("\r\n")
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def parse_line(line):
    """NAME;PARAM=x;PARAM=y:value -> (NAME, {PARAM: x, ...}, value)."""
    head, _, value = line.partition(":")
    parts = head.split(";")
    params = {}
    for part in parts[1:]:
        key, _, val = part.partition("=")
        params[key.upper()] = val.strip('"')
    return parts[0].upper(), params, value


def iso(value):
    """20260706T090000Z -> 2026-07-06T09:00:00Z; date-only stays a date."""
    match = DT_RE.match(value)
    if not match:
        return value
    date = "%s-%s-%s" % match.group(1, 2, 3)
    if match.group(4):
        return "%sT%s:%s:%s%s" % ((date,) + match.group(4, 5, 6, 7))
    return date


def unescape(value):
    return re.sub(r"\\[nN,;\\]", lambda m: ESCAPES[m.group(0)], value)


def parse_events(path):
    events, event = [], None
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in unfold(handle):
            name, params, value = parse_line(line)
            if name == "BEGIN" and value == "VEVENT":
                event = {"attendees": []}
            elif name == "END" and value == "VEVENT" and event is not None:
                events.append(event)
                event = None
            elif event is None:
                continue
            elif name in ("DTSTART", "DTEND"):
                event[name.lower()] = iso(value)
            elif name in ("UID", "SUMMARY", "LOCATION", "DESCRIPTION",
                          "STATUS"):
                event[name.lower()] = unescape(value)
            elif name == "ORGANIZER":
                event["organizer"] = value.replace("mailto:", "").lower()
            elif name == "ATTENDEE":
                event["attendees"].append({
                    "email": value.replace("mailto:", "").lower(),
                    "name": params.get("CN", ""),
                    "response": params.get("PARTSTAT", ""),
                })
    return events


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: ics_to_meetings.py DB CALENDAR.ics [MORE.ics ...]")
    db = sqlite3.connect(sys.argv[1])
    db.executescript("""
        DROP TABLE IF EXISTS meetings;
        DROP TABLE IF EXISTS meeting_attendees;
        CREATE TABLE meetings (
            id            INTEGER PRIMARY KEY,
            uid           TEXT,
            starts_at     TEXT,
            ends_at       TEXT,
            summary       TEXT,
            location      TEXT,
            description   TEXT,
            organizer     TEXT,
            status        TEXT,
            calendar_file TEXT
        );
        CREATE TABLE meeting_attendees (
            meeting_id INTEGER REFERENCES meetings(id),
            email      TEXT,
            name       TEXT,
            response   TEXT
        );
    """)
    total = 0
    for path in sys.argv[2:]:
        for ev in parse_events(path):
            cur = db.execute(
                "INSERT INTO meetings (uid, starts_at, ends_at, summary, "
                "location, description, organizer, status, calendar_file) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ev.get("uid"), ev.get("dtstart"), ev.get("dtend"),
                 ev.get("summary"), ev.get("location"),
                 ev.get("description"), ev.get("organizer"),
                 ev.get("status"), path))
            db.executemany(
                "INSERT INTO meeting_attendees VALUES (?, ?, ?, ?)",
                [(cur.lastrowid, a["email"], a["name"], a["response"])
                 for a in ev["attendees"]])
            total += 1
    db.commit()
    print("imported %d event(s) from %d file(s)"
          % (total, len(sys.argv) - 2))


if __name__ == "__main__":
    main()
```

Run it over every calendar in the export:

```bash
python3 ~/bin/ics_to_meetings.py ~/archive/archive.db \
  ~/archive/exports/takeout-*/Takeout/Calendar/*.ics
```

Handles the Google-export quirks: folded long lines, `TZID=` datetime
parameters (normalized to ISO 8601), all-day `VALUE=DATE` events, escaped
`\,`/`\n` text, and quoted `CN="Doe, Jane"` attendee names. Re-running is a
full rebuild of the two tables, so a fresh export simply replaces the old
import.

Who-did-I-meet queries then work directly:

```bash
sqlite-utils ~/archive/archive.db "
  SELECT m.starts_at, m.summary
  FROM meetings m JOIN meeting_attendees a ON a.meeting_id = m.id
  WHERE a.email = 'jane@example.com'
  ORDER BY m.starts_at DESC LIMIT 20"
```

## 8. Contacts: vCard into archive.db, then a SEED, not a dump

Save as `~/bin/vcf_to_contacts.py`:

```python
#!/usr/bin/env python3
"""vcf_to_contacts.py - Takeout contacts (vCard) into archive.db (stdlib only).

Usage: python3 vcf_to_contacts.py ~/archive/archive.db contacts.vcf [more.vcf ...]

Rebuilds the contacts table from the given .vcf file(s) on every run. The
.vcf files are the raw record: keep them in cold storage so the table stays
re-derivable.
"""
import sqlite3
import sys


def unfold(handle):
    out = []
    for line in handle:
        line = line.rstrip("\r\n")
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def parse_cards(path):
    cards, card = [], None
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in unfold(handle):
            head, _, value = line.partition(":")
            name = head.split(";")[0].upper()
            if name == "BEGIN" and value.upper() == "VCARD":
                card = {"emails": [], "phones": []}
            elif name == "END" and value.upper() == "VCARD" and card:
                cards.append(card)
                card = None
            elif card is None:
                continue
            elif name == "FN":
                card["full_name"] = value.strip()
            elif name == "ORG":
                card["org"] = value.replace(";", " ").strip()
            elif name == "EMAIL" and value.strip():
                card["emails"].append(value.strip().lower())
            elif name == "TEL" and value.strip():
                card["phones"].append(value.strip())
    return cards


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: vcf_to_contacts.py DB CONTACTS.vcf [MORE.vcf ...]")
    db = sqlite3.connect(sys.argv[1])
    db.executescript("""
        DROP TABLE IF EXISTS contacts;
        CREATE TABLE contacts (
            id          INTEGER PRIMARY KEY,
            full_name   TEXT,
            emails      TEXT,   -- comma-separated, lowercased
            phones      TEXT,   -- comma-separated
            org         TEXT,
            source_file TEXT
        );
    """)
    total = 0
    for path in sys.argv[2:]:
        for card in parse_cards(path):
            db.execute(
                "INSERT INTO contacts (full_name, emails, phones, org, "
                "source_file) VALUES (?, ?, ?, ?, ?)",
                (card.get("full_name"), ", ".join(card["emails"]),
                 ", ".join(card["phones"]), card.get("org"), path))
            total += 1
    db.commit()
    print("imported %d contact(s) from %d file(s)"
          % (total, len(sys.argv) - 2))


if __name__ == "__main__":
    main()
```

```bash
python3 ~/bin/vcf_to_contacts.py ~/archive/archive.db \
  ~/archive/exports/takeout-*/Takeout/Contacts/*.vcf
```

**Seeding people pages: curate, never dump.** A contacts table is hundreds
of rows; a `wiki/people/` namespace with hundreds of orphan stubs is lint
noise and premortem failure material. The seed flow:

1. Pick the people who ALREADY matter -- collaborators you meet, co-authors,
   the names that keep coming up in your journal. A dozen is a good start.
2. Write a short digest by hand into `raw/people-seed.md`: one bullet per
   person -- name, role/org, why they matter to you. Names and roles only;
   leave email addresses OUT of the digest (they would land on git-tracked
   pages, and the secret gate will advisory-flag them anyway).
3. Run `/wiki-ingest`. The normal checkpoint, quality gate, and hub routing
   apply; the pages arrive as `wiki/people/<name>` entities with provenance.

Everyone else stays in `archive.db:contacts`, findable by SQL, costing
nothing. A person gets a page when they surface, not before -- same
philosophy as the next section.

## 9. Alias resolution: lazy, per person, over months

One human is many strings: `Jane Doe`, `Doe, Jane`, `jane@example.com`,
`jd@work.example`, `Jane (ETH)`. Queries like "everything with Jane" only
work when those strings are mapped to one identity.

**Do NOT front-load this.** Resolving aliases for a whole contacts table is
the setup plan's explicit anti-goal: it is 5-15 hours of judgment work spread
over months, and most of it would be wasted on people who never surface.
The practice instead:

- The mapping lives in archive.db (machine-matching data on the machine
  plane, and email addresses stay out of git). Create the table once:

  ```bash
  python3 - <<'PY'
  import pathlib, sqlite3
  db = sqlite3.connect(pathlib.Path.home() / "archive" / "archive.db")
  db.execute("""CREATE TABLE IF NOT EXISTS person_aliases (
      person_page TEXT,   -- vault page name, e.g. wiki/people/Jane Doe
      alias       TEXT,   -- an email or name variant as it appears in the data
      kind        TEXT,   -- email | name
      added_at    TEXT    -- ISO 8601
  )""")
  db.commit(); print("person_aliases ready")
  PY
  ```

- WHEN a person first matters (a query about them comes up, a meeting
  analysis needs them), spend the five minutes THEN: grep their variants out
  of `contacts`, `meeting_attendees`, and `messages`, and insert the alias
  rows pointing at their `wiki/people/` page. Unlike captured rows, these
  are your own curation notes -- correcting or extending them later is fine.
- Name variants that should resolve as links inside the graph can ALSO go
  on the person's page as a Logseq `alias::` property; email addresses stay
  in `person_aliases` only.
- Done lazily, coverage grows exactly as fast as your actual use of the
  archive layer -- weeks 1-2 might resolve three people. That is the plan
  working, not the plan failing.

## 10. What deliberately does NOT happen

- **No writes to index.db, ever** (storage REQ-1132). When the index layer
  lands (v3.0 P-4, issue #58), it is rebuilt from the vault's markdown only;
  a calendar event reaches it only if it reached a vault page first.
- **No automatic page creation.** Nothing in this guide writes to the vault
  except through `raw/` + `/wiki-ingest` with its checkpoint.
- **No scheduled re-import.** Takeout is a bulk historical backstop, not a
  sync; re-run it a few times a year when a question actually needs fresher
  history. Day-to-day knowledge keeps flowing through the normal ingest and
  voice legs.
- **No provenance-to-SQLite.** `source-file::`/`cite::` stay the provenance
  system; the parked Phase 5 refactor stays parked (roadmap design
  decision 6).

## Related

- [`openspec/specs/storage.md`](../openspec/specs/storage.md) -- the
  two-plane contract this guide implements (REQ-1100..1141)
- [`docs/voice-pipeline.md`](voice-pipeline.md) -- the backup script,
  restore drill, and launchd patterns reused here
- [`docs/roadmap-glossary-personal-pipeline.md`](roadmap-glossary-personal-pipeline.md)
  -- where the archive layer sits in v3.0 (P-6) and why Dogsheep over
  hand-written importers
- [`prompts/llm-wiki-setup-plan.md`](../prompts/llm-wiki-setup-plan.md) --
  Phase 3 checklist this guide executes
- [Dogsheep](https://dogsheep.github.io/) /
  [google-takeout-to-sqlite](https://github.com/dogsheep/google-takeout-to-sqlite) /
  [mbox-to-sqlite](https://github.com/simonw/mbox-to-sqlite) /
  [sqlite-utils](https://sqlite-utils.datasette.io/) /
  [Datasette](https://datasette.io/) -- the toolchain
