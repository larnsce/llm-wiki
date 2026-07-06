#!/usr/bin/env python3
"""Rebuild index.db from the vault (specs/storage.md REQ-1130..1133).

index.db is DERIVED and DISPOSABLE: this script deletes and fully rebuilds
it as a deterministic function of the vault's markdown (pages plus
journals). Two rebuilds from the same vault state produce identical dumps
(REQ-1131): row order is fixed (sorted), and the rebuild stamp is a content
hash of the indexed files, never wall-clock time. The rebuild AGE for the
dead-man status line (REQ-1140) is the index.db file's mtime.

Frozen schema (REQ-1130; any change amends the spec first):
  people(page, name, aliases, updated)           one row per people page
  meetings(page, line, date, text)               one row per #meeting block
  page_properties(page, key, value)              every page-level property
  page_text                                      FTS5 over (page, text)
  rebuild_stamp(stamp)                           single-row content stamp

Placement (REQ-1103, config REQ-627): the target path comes from the
`index_db` config key (default ~/archive/index.db). A path inside the
vault's git-tracked tree that is not gitignored is refused (exit 2):
index.db never enters git.

Data with no markdown source never enters index.db (REQ-1132): the ONLY
input this script reads is the vault's markdown.

Modes:
  (default)      full rebuild, atomic replace (build to .tmp, then rename)
  --stale-check  compare the stored stamp against the recomputed content
                 hash; exit 0 fresh, 1 stale or missing, 2 error
  --json         machine-readable report

Exit codes: 0 = ok/fresh, 1 = stale (--stale-check only), 2 = error.
"""

import argparse
import hashlib
import os
import re
import sqlite3
import subprocess
import sys

import wikilib

MEETING_TAG_RE = re.compile(r"(^|\s)#meeting\b")
JOURNAL_DATE_RE = re.compile(r"^(\d{4})[-_](\d{2})[-_](\d{2})$")


def fail(message):
    print("rebuild_index: ERROR: %s" % message, file=sys.stderr)
    sys.exit(2)


def resolve_index_db(config):
    raw = config.get("index_db") or "~/archive/index.db"
    return os.path.abspath(wikilib.expand_path(raw))


def journal_files(config):
    """Journal markdown files, sorted: <wiki_path>/journals/*.md."""
    root = os.path.join(wikilib.wiki_root(config), "journals")
    if not os.path.isdir(root):
        return []
    files = []
    for entry in sorted(os.listdir(root)):
        if entry.endswith(".md") and os.path.isfile(os.path.join(root, entry)):
            files.append({"name": "journals/" + entry[:-3],
                          "path": os.path.join(root, entry)})
    return files


def journal_date(name):
    """journals/2026_07_06 -> 2026-07-06 ('' when the name is not a date)."""
    leaf = name.rsplit("/", 1)[-1]
    match = JOURNAL_DATE_RE.match(leaf)
    if match:
        return "-".join(match.groups())
    return ""


def indexed_files(config):
    """All files entering the index: wiki pages plus journals, sorted."""
    entries = list(wikilib.enumerate_pages(config)) + journal_files(config)
    entries.sort(key=lambda entry: entry["name"])
    return entries


def content_stamp(entries):
    """Deterministic hash of the indexed markdown (REQ-1131)."""
    digest = hashlib.sha256()
    for entry in entries:
        with open(entry["path"], "rb") as handle:
            file_hash = hashlib.sha256(handle.read()).hexdigest()
        digest.update(("%s\n%s\n" % (entry["name"], file_hash)).encode())
    return digest.hexdigest()


def guard_placement(index_db, config):
    """Refuse a target inside the vault's git tree that is not ignored
    (REQ-1103): index.db never enters git."""
    vault = os.path.abspath(wikilib.wiki_root(config))
    if not index_db.startswith(vault + os.sep):
        return
    if not os.path.isdir(os.path.join(vault, ".git")):
        return
    rel = os.path.relpath(index_db, vault)
    check = subprocess.run(
        ["git", "-C", vault, "check-ignore", "--quiet", rel])
    if check.returncode != 0:
        fail("index_db '%s' is inside the vault's git tree and not "
             "gitignored (storage REQ-1103); gitignore the path or move it "
             "outside the vault" % rel)


def block_lines(text):
    """(line_number, block_text) pairs for #meeting scanning.

    A block is a bullet line (with its indented continuations) or a plain
    paragraph line. Line numbers are 1-based positions of the block's
    first line. Tool-independent: both markdown shapes parse the same way.
    """
    blocks = []
    current = None
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        is_bullet = stripped.startswith("- ")
        if is_bullet:
            if current:
                blocks.append(current)
            current = [number, stripped[2:].strip()]
        elif current and (line.startswith((" ", "\t")) and stripped):
            current[1] += " " + stripped
        else:
            if current:
                blocks.append(current)
                current = None
            if stripped:
                blocks.append([number, stripped])
    if current:
        blocks.append(current)
    return blocks


def build(db_path, entries, stamp, tool):
    tmp_path = db_path + ".tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    db = sqlite3.connect(tmp_path)
    db.executescript("""
        CREATE TABLE people (
            page TEXT PRIMARY KEY, name TEXT, aliases TEXT, updated TEXT);
        CREATE TABLE meetings (
            page TEXT, line INTEGER, date TEXT, text TEXT,
            PRIMARY KEY (page, line));
        CREATE TABLE page_properties (
            page TEXT, key TEXT, value TEXT, PRIMARY KEY (page, key));
        CREATE VIRTUAL TABLE page_text USING fts5(page, text);
        CREATE TABLE rebuild_stamp (stamp TEXT);
    """)

    counts = {"people": 0, "meetings": 0, "page_properties": 0,
              "page_text": 0}
    for entry in entries:
        name, path = entry["name"], entry["path"]
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        props = wikilib.parse_page_properties(text, tool)

        for key in sorted(props):
            db.execute("INSERT OR REPLACE INTO page_properties VALUES "
                       "(?, ?, ?)", (name, key, props[key]))
            counts["page_properties"] += 1

        segments = name.split("/")
        if len(segments) >= 2 and segments[-2] == "people":
            db.execute("INSERT OR REPLACE INTO people VALUES (?, ?, ?, ?)",
                       (name, segments[-1], props.get("alias", ""),
                        props.get("updated", "")))
            counts["people"] += 1

        date = journal_date(name) or props.get("date", "") \
            or props.get("updated", "")
        for line, block in block_lines(text):
            if MEETING_TAG_RE.search(block):
                db.execute("INSERT OR REPLACE INTO meetings VALUES "
                           "(?, ?, ?, ?)", (name, line, date, block))
                counts["meetings"] += 1

        db.execute("INSERT INTO page_text VALUES (?, ?)", (name, text))
        counts["page_text"] += 1

    db.execute("INSERT INTO rebuild_stamp VALUES (?)", (stamp,))
    db.commit()
    db.close()
    os.replace(tmp_path, db_path)
    return counts


def stored_stamp(db_path):
    if not os.path.exists(db_path):
        return None
    try:
        db = sqlite3.connect(db_path)
        row = db.execute("SELECT stamp FROM rebuild_stamp").fetchone()
        db.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild index.db from the vault "
                    "(storage.md REQ-1130..1133).")
    parser.add_argument("--config", default=None,
                        help="path to llm-wiki.yml (default: discover)")
    parser.add_argument("--stale-check", action="store_true",
                        help="compare the stored stamp to the vault; "
                             "exit 0 fresh, 1 stale or missing")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="machine-readable report")
    args = parser.parse_args()

    if args.config:
        config_path = args.config
    else:
        config_path = wikilib.discover_config()
        if not config_path:
            fail("no llm-wiki.yml found (pass --config)")
    try:
        config = wikilib.load_config(config_path)
    except OSError as error:
        fail("cannot read config: %s" % error)

    index_db = resolve_index_db(config)
    entries = indexed_files(config)
    stamp = content_stamp(entries)

    if args.stale_check:
        stored = stored_stamp(index_db)
        fresh = stored == stamp
        payload = {"index_db": index_db, "fresh": fresh,
                   "stamp": stamp, "stored_stamp": stored}
        if args.as_json:
            wikilib.emit_json(payload)
        elif fresh:
            print("rebuild_index: fresh (stamp matches the vault)")
        elif stored is None:
            print("rebuild_index: STALE (no index.db or no stamp; rebuild)")
        else:
            print("rebuild_index: STALE (vault changed since the last "
                  "rebuild)")
        sys.exit(0 if fresh else 1)

    guard_placement(index_db, config)
    counts = build(index_db, entries, stamp, config.get("tool", ""))
    payload = {"index_db": index_db, "stamp": stamp, "files": len(entries)}
    payload.update(counts)
    if args.as_json:
        wikilib.emit_json(payload)
    else:
        print("rebuild_index: %s rebuilt from %d file(s): %d people, "
              "%d meetings, %d properties, %d FTS rows"
              % (index_db, len(entries), counts["people"],
                 counts["meetings"], counts["page_properties"],
                 counts["page_text"]))
        print("stamp: %s" % stamp)
    sys.exit(0)


if __name__ == "__main__":
    main()
