# Mail pipeline: daily Infomaniak IMAP capture into archive.db (macOS)

Maintainer-run plumbing for the personal pipeline (issue #123): a nightly,
deterministic pull of new mail from an Infomaniak mailbox into
`archive.db`, beside the Takeout-imported history from
[`docs/archive-layer.md`](archive-layer.md). Everything here is copy-paste
and runs on one machine; the repo documents it but does not ship or test it
(same rule as the rest of the archive layer).

> **Scope: capture only, no wiki route.** Email still has NO route into
> wiki pages (`docs/source-routes.md`, issue #107 decision 9), and
> automated inbox-to-wiki ingestion stays rejected (the funnel rule). This
> pipeline only moves bytes onto the machine plane -- `archive.db`, never
> the vault, never index.db (storage REQ-1132). Anything that matters
> enough for a page goes through `raw/` + `/wiki-ingest` with its
> checkpoint, by hand. The storage contract is
> [`openspec/specs/storage.md`](../openspec/specs/storage.md); where this
> guide and the spec disagree, the spec wins.

## 1. What this is

```
mail.infomaniak.com:993 (IMAP) --nightly launchd--> archive.db
                                                     (messages,
                                                      imap_sync_state)
                                                         |
                                    SQL when a question needs it;
                                    wiki pages only via raw/ +
                                    /wiki-ingest, by hand
```

Three rules shape the design:

1. **Deterministic script, no LLM, no MCP in the loop.** A daily fetch is
   mechanical; an unattended model reading arbitrary inbound mail would add
   cost, fragility, and a prompt-injection surface for nothing. Interactive
   mail work (search, triage, drafting a `raw/note-*.md` digest in-session)
   is the official Infomaniak Mail MCP server's job -- issue #124, separate
   from this pipeline on purpose.
2. **Incremental and append-only.** The script tracks `UIDVALIDITY` and the
   last-seen `UID` per folder and only appends new rows into the same
   `messages` table the Takeout mbox import uses (archive-layer section 5),
   so FTS and the lazy alias-resolution practice work unchanged across
   both. Nothing is ever updated or deleted.
3. **Takeout stays the historical backstop.** The archive layer's "no
   scheduled re-import" rule is unchanged: Takeout is for bulk history a
   few times a year; this pipeline is the day-to-day trickle. Unlike a
   Takeout import, IMAP-captured rows have no export file behind them --
   archive.db is their primary record, which is why section 2 comes first.

## 2. Preconditions: durability first

IMAP-captured mail exists ONLY in archive.db (the server keeps its copy,
but treat the local capture as primary data), so the standard discipline
binds BEFORE the first real run:

- The **nightly off-machine copy** of archive.db must already run (storage
  REQ-1120; [`docs/voice-pipeline.md`](voice-pipeline.md) section 2 has the
  backup script and launchd job). No backup, no capture job.
- The **quarterly restore drill** (REQ-1121) already counts the `messages`
  table (archive-layer section 2); rows added by this pipeline are covered
  by the same drill with no changes.
- archive.db stays **out of git** (REQ-1103). Nothing in this guide touches
  the vault or its history.

## 3. Infomaniak account setup

- IMAP endpoint: `mail.infomaniak.com`, port `993`, SSL/TLS. Username is
  the full address.
- With two-factor auth enabled (it should be), create an **application
  password** for IMAP in the Infomaniak Manager (Security section) instead
  of using the account password.
- The credential is L1 material: it lives in the macOS keychain, never in
  the vault, never in this repo.

```bash
security add-generic-password -a you@example.com -s infomaniak-imap -w
```

(Prompts for the app password and stores it; the script reads it back with
`security find-generic-password ... -w` via `password_cmd` below.)

## 4. The capture script

Config first. Save as `~/.config/imap_to_archive.json` (chmod 600):

```json
{
  "host": "mail.infomaniak.com",
  "port": 993,
  "username": "you@example.com",
  "password_cmd": ["security", "find-generic-password",
                   "-a", "you@example.com", "-s", "infomaniak-imap", "-w"],
  "folders": ["INBOX", "Sent"]
}
```

`Sent` capture is what the review-time sent-mail query (section 7, issue
#125) rests on. Folder names vary by account history; run the script with
`--list-folders` once and adjust (some accounts use `Sent Messages`).

Save as `~/bin/imap_to_archive.py` (stdlib only, same rule as the other
archive-layer snippets):

```python
#!/usr/bin/env python3
"""imap_to_archive.py - incremental IMAP capture into archive.db (stdlib only).

Usage:
  python3 imap_to_archive.py ~/archive/archive.db                  # fetch new mail
  python3 imap_to_archive.py ~/archive/archive.db --list-folders   # inspect names

Config: ~/.config/imap_to_archive.json (host, port, username,
password_cmd or password, folders). Tracks UIDVALIDITY + last UID per
folder in imap_sync_state and appends new messages into the same
`messages` table the Takeout mbox import uses; missing columns are added,
existing rows are never touched. Text parts only; attachments are skipped
(the mailbox stays the record for those).
"""
import email
import email.header
import email.utils
import imaplib
import json
import pathlib
import sqlite3
import subprocess
import sys

CONFIG = pathlib.Path.home() / ".config" / "imap_to_archive.json"
COLUMNS = ("message_id", "folder", "uid", "uidvalidity", "date",
           "from_addr", "to_addrs", "cc_addrs", "subject", "payload")


def get_password(cfg):
    if cfg.get("password"):
        return cfg["password"]
    return subprocess.check_output(cfg["password_cmd"], text=True).strip()


def ensure_schema(db):
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY)")
    have = {row[1] for row in db.execute("PRAGMA table_info(messages)")}
    for col in COLUMNS:
        if col not in have:
            db.execute("ALTER TABLE messages ADD COLUMN %s TEXT" % col)
    # NULLs compare distinct in SQLite unique indexes, so rows from the
    # Takeout mbox import (no folder/uid) are unaffected by this index.
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_imap"
               " ON messages (folder, uidvalidity, uid)")
    db.execute("""CREATE TABLE IF NOT EXISTS imap_sync_state (
        folder      TEXT PRIMARY KEY,
        uidvalidity INTEGER,
        last_uid    INTEGER
    )""")
    db.commit()


def decode_header(value):
    if value is None:
        return None
    out = []
    for text, enc in email.header.decode_header(value):
        if isinstance(text, bytes):
            text = text.decode(enc or "utf-8", "replace")
        out.append(text)
    return "".join(out)


def body_text(msg):
    """All text/plain parts joined; text/html only as a fallback."""
    plain, html = [], []
    for part in msg.walk():
        if part.get_content_maintype() != "text" or part.get_filename():
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8",
                              "replace")
        (plain if part.get_content_subtype() == "plain" else html).append(text)
    return "\n".join(plain) or "\n".join(html)


def iso_date(msg):
    try:
        dt = email.utils.parsedate_to_datetime(msg.get("Date"))
        return dt.astimezone().isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return msg.get("Date")


def fetch_folder(imap, db, folder):
    status, data = imap.select('"%s"' % folder, readonly=True)
    if status != "OK":
        print("skip %s: %s" % (folder, data))
        return 0
    uv_data = imap.response("UIDVALIDITY")[1]
    uidvalidity = int(uv_data[0]) if uv_data and uv_data[0] else 0
    row = db.execute("SELECT uidvalidity, last_uid FROM imap_sync_state"
                     " WHERE folder = ?", (folder,)).fetchone()
    # A changed UIDVALIDITY means the server renumbered the folder:
    # start over from UID 0 (the unique index absorbs true re-runs).
    last_uid = row[1] if row and row[0] == uidvalidity else 0
    status, data = imap.uid("search", None, "UID %d:*" % (last_uid + 1))
    if status != "OK":
        print("skip %s: search failed" % folder)
        return 0
    # IMAP quirk: "UID n:*" returns the last message even when its UID < n.
    uids = sorted(int(u) for u in data[0].split() if int(u) > last_uid)
    added = 0
    for uid in uids:
        status, data = imap.uid("fetch", str(uid), "(RFC822)")
        if status != "OK" or not data or data[0] is None:
            continue
        msg = email.message_from_bytes(data[0][1])
        cur = db.execute(
            "INSERT OR IGNORE INTO messages (message_id, folder, uid,"
            " uidvalidity, date, from_addr, to_addrs, cc_addrs, subject,"
            " payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (msg.get("Message-ID"), folder, uid, uidvalidity, iso_date(msg),
             decode_header(msg.get("From")), decode_header(msg.get("To")),
             decode_header(msg.get("Cc")), decode_header(msg.get("Subject")),
             body_text(msg)))
        added += max(cur.rowcount, 0)
        db.execute(
            "INSERT INTO imap_sync_state (folder, uidvalidity, last_uid)"
            " VALUES (?, ?, ?) ON CONFLICT(folder) DO UPDATE SET"
            " uidvalidity = excluded.uidvalidity,"
            " last_uid = excluded.last_uid", (folder, uidvalidity, uid))
        # Commit per message: the cursor only advances together with the
        # row it covers, so a crash mid-run never skips mail.
        db.commit()
    return added


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: imap_to_archive.py DB [--list-folders]")
    cfg = json.loads(CONFIG.read_text())
    imap = imaplib.IMAP4_SSL(cfg["host"], cfg.get("port", 993))
    imap.login(cfg["username"], get_password(cfg))
    if "--list-folders" in sys.argv:
        for line in imap.list()[1]:
            print(line.decode())
        imap.logout()
        return
    db = sqlite3.connect(sys.argv[1])
    ensure_schema(db)
    total = 0
    for folder in cfg.get("folders", ["INBOX", "Sent"]):
        count = fetch_folder(imap, db, folder)
        print("%s: %d new" % (folder, count))
        total += count
    imap.logout()
    print("captured %d new message(s)" % total)


if __name__ == "__main__":
    main()
```

First run: `--list-folders`, fix the config, then a real run. The first
real run fetches the whole mailbox (everything is "new" to an empty sync
state); with a Takeout mbox import already in the table you will hold the
same historical mail twice under different rows -- that is fine (different
provenance, same FTS), or start the sync state from a recent date by
deleting older UIDs' worth manually if it bothers you.

A rare `UIDVALIDITY` change (server-side folder rebuild) triggers a full
refetch under the new validity value; if that ever produces duplicates,
they are identifiable by `message_id`:

```bash
sqlite-utils ~/archive/archive.db "
  SELECT message_id, count(*) FROM messages
  WHERE message_id IS NOT NULL
  GROUP BY message_id HAVING count(*) > 1"
```

## 5. The launchd job

Capture at 02:30, BEFORE the 03:00 archive backup
([`docs/voice-pipeline.md`](voice-pipeline.md) section 2.2), so every
nightly snapshot already contains that night's capture. Save as
`~/Library/LaunchAgents/local.imap-to-archive.plist`, replacing `YOU`
(launchd does not expand `$HOME` in paths):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.imap-to-archive</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/YOU/bin/imap_to_archive.py</string>
    <string>/Users/YOU/archive/archive.db</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>30</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/YOU/archive/imap.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOU/archive/imap.log</string>
</dict>
</plist>
```

Load it and run it once now:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.imap-to-archive.plist
launchctl kickstart -k gui/$(id -u)/local.imap-to-archive
```

Same laptop note as the backup job: launchd runs a missed
`StartCalendarInterval` once on wake; cron would silently skip it.

## 6. Full-text search over captured mail

The archive-layer FTS setup carries over; for a table that now grows
nightly, create the triggers so new rows are indexed as they land:

```bash
sqlite-utils enable-fts ~/archive/archive.db messages subject payload --create-triggers
```

If FTS was already enabled without triggers (the archive-layer one-shot
setup), disable and re-enable it once:

```bash
sqlite-utils disable-fts ~/archive/archive.db messages
sqlite-utils enable-fts ~/archive/archive.db messages subject payload --create-triggers
```

## 7. The sent-mail overview: a query, not a journal block

Decision record (issue #125, 2026-07-16, Option B): the daily overview of
sent mail is a **review-time query with zero writes**. Nothing is
materialized into the journal -- no second machine writer on a human-owned,
git-tracked surface, no people-naming metadata entering git unattended.
Run it as part of the morning review (issue #65):

```bash
sqlite-utils ~/archive/archive.db "
  SELECT substr(date, 12, 5) AS at, to_addrs, subject
  FROM messages
  WHERE folder = 'Sent'
    AND substr(date, 1, 10) = date('now', '-1 day')
  ORDER BY date" -t
```

Plain-sqlite3 form of the same query:

```bash
sqlite3 -column -header ~/archive/archive.db \
  "SELECT substr(date, 12, 5) AS at, to_addrs, subject
   FROM messages
   WHERE folder = 'Sent' AND substr(date, 1, 10) = date('now', '-1 day')
   ORDER BY date"
```

Revisit trigger: promote this to a materialized journal block (the
rejected Option A) only on evidence the morning review would actually read
it -- and then as a new decision with the metadata-only and append-only
constraints from issue #125, not as a default.

## 8. What deliberately does NOT happen

- **No wiki or `raw/` writes from mail.** The funnel rule and #107
  decision 9 stay in force; promotion is manual, through the normal
  `raw/note-*.md` seam, ideally after interactive triage (issue #124, the
  official Infomaniak Mail MCP server -- interactive sessions only, never
  cron).
- **No LLM in the daily loop** (rule 1 above).
- **No journal writes** (section 7; issue #125 Option B).
- **No calendar or contacts sync.** Takeout remains the answer for both
  (archive-layer sections 7-8).
- **No change to the Takeout rules.** Bulk historical re-import stays
  occasional and manual; the export files stay the raw record for what
  they cover.

## Related

- [`docs/archive-layer.md`](archive-layer.md) -- the staging ground this
  extends; `messages` table, FTS, alias resolution
- [`docs/voice-pipeline.md`](voice-pipeline.md) -- backup script, restore
  drill, launchd patterns reused here
- [`docs/source-routes.md`](source-routes.md) -- why email has no wiki
  route; the capture carve-out recorded there
- [`openspec/specs/storage.md`](../openspec/specs/storage.md) -- the
  two-plane contract (REQ-1100..1141)
- Issues #123 (this pipeline), #124 (interactive MCP leg), #125 (sent-mail
  overview decision)
