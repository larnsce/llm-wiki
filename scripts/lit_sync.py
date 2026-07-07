#!/usr/bin/env python3
"""lit_sync.py - plugin-free Zotero -> Logseq literature sync (issue #90).

Pulls items from Zotero's LOCAL HTTP API (Zotero 7+, API v3,
http://localhost:23119/api/users/0) and maintains one
notes/literature/@<citekey> page per item. Replaces the
logseq-zoterolocal-plugin recommendation of docs/zotero-setup.md.

Design decisions (issue #90; do not change without discussion):

1. Local API only. No Logseq plugin, no Zotero cloud API, no BBT export
   file. A failed local connection is a hard stop (exit 2), never worked
   around via the cloud API.
2. Idempotent metadata. Each run rewrites only the managed properties
   (type, citekey, authors, year, item-type, doi, zotero). source-file::
   and any user-added properties are preserved. "## my reading" is never
   touched (notes/ page: human-written, machine-exempt).
3. Incremental annotations. Annotations are children of PDF attachments;
   the script maps annotation -> attachment -> top item, sorts by
   annotationSortIndex, appends only annotations with Zotero version >
   the page's zotero-last-sync:: value, then stamps the current library
   version from the Last-Modified-Version response header.
4. Page filename: notes%2Fliterature%2F@<citekey>.md OR
   notes___literature___@<citekey>.md - whichever encoding the vault's
   existing namespace files already use (checked before writing;
   default ___).
5. source-file:: stays blank at creation; it is filled manually when the
   paper goes through /wiki-ingest (the "one source, two readings" seam).

Citekeys come from Better BibTeX pinned keys in the item's extra field
("Citation Key: xxx"). Items without a pinned citekey are SKIPPED with a
warning.

Usage:
    python3 scripts/lit_sync.py --vault <logseq-graph-root> [--dry-run]

Exit codes: 0 = success, 1 = bad arguments / vault problem,
2 = Zotero local API unreachable or refused (fix Zotero, do not work
around).
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:23119/api/users/0"
PAGE_LIMIT = 100
TIMEOUT = 15

MANAGED_PROPS = ("type", "citekey", "authors", "year", "item-type",
                 "doi", "zotero")
SYNC_PROP = "zotero-last-sync"

CITEKEY_RE = re.compile(r"^Citation Key:\s*(\S+)", re.M | re.I)
YEAR_RE = re.compile(r"\b(\d{4})\b")
PROP_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*)::\s*(.*)$")


# ---------------------------------------------------------------------------
# Zotero local API
# ---------------------------------------------------------------------------

def api_get(path, base_url):
    """GET one API page. Returns (json, headers). Hard-stops on 403."""
    url = base_url + path
    request = urllib.request.Request(url, headers={"Zotero-API-Version": "3"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response), dict(response.headers)
    except urllib.error.HTTPError as err:
        if err.code == 403:
            print(
                "lit_sync: Zotero local API refused the connection (403).\n"
                "Enable Settings -> Advanced -> 'Allow other applications "
                "on this computer to communicate with Zotero', then retry.\n"
                "Do NOT work around this with the cloud API.",
                file=sys.stderr,
            )
        else:
            print("lit_sync: HTTP %s on %s" % (err.code, url),
                  file=sys.stderr)
        sys.exit(2)
    except urllib.error.URLError as err:
        print(
            "lit_sync: cannot reach the Zotero local API at %s (%s).\n"
            "Is Zotero running? Is 'Allow other applications on this "
            "computer to communicate with Zotero' enabled (Settings -> "
            "Advanced)? STOP here; do not fall back to the cloud API."
            % (base_url, err.reason),
            file=sys.stderr,
        )
        sys.exit(2)


def api_get_all(path_base, base_url):
    """Paginate through a listing endpoint. Returns (items, last_headers)."""
    items = []
    start = 0
    headers = {}
    separator = "&" if "?" in path_base else "?"
    while True:
        path = "%s%slimit=%d&start=%d" % (path_base, separator,
                                          PAGE_LIMIT, start)
        page, headers = api_get(path, base_url)
        items.extend(page)
        if len(page) < PAGE_LIMIT:
            return items, headers
        start += PAGE_LIMIT


# ---------------------------------------------------------------------------
# Item -> page mapping
# ---------------------------------------------------------------------------

def extract_citekey(data):
    match = CITEKEY_RE.search(data.get("extra") or "")
    return match.group(1) if match else None


def format_authors(data):
    names = []
    for creator in data.get("creators") or []:
        if creator.get("creatorType") not in ("author", "editor", None):
            continue
        if creator.get("name"):
            names.append(creator["name"])
        else:
            full = "%s %s" % (creator.get("firstName", ""),
                              creator.get("lastName", ""))
            names.append(full.strip())
    return ", ".join(n for n in names if n)


def extract_year(item):
    for candidate in ((item.get("data") or {}).get("date", ""),
                      (item.get("meta") or {}).get("parsedDate", "")):
        match = YEAR_RE.search(candidate or "")
        if match:
            return match.group(1)
    return ""


def managed_values(item, citekey):
    data = item["data"]
    return {
        "type": "literature",
        "citekey": citekey,
        "authors": format_authors(data),
        "year": extract_year(item),
        "item-type": data.get("itemType", ""),
        "doi": data.get("DOI", ""),
        "zotero": "zotero://select/library/items/%s" % data.get("key", ""),
    }


def detect_separator(pages_dir):
    """Match the vault's existing namespace-filename encoding.

    %2F wins only if the vault already uses it; default is ___ (the
    encoding Logseq MD graphs use on disk, issue #90 decision 4).
    """
    for name in os.listdir(pages_dir):
        if "%2F" in name:
            return "%2F"
    return "___"


def page_path(pages_dir, citekey, separator):
    name = separator.join(("notes", "literature", "@" + citekey))
    return os.path.join(pages_dir, name + ".md")


# ---------------------------------------------------------------------------
# Page read / write (Logseq MD format)
# ---------------------------------------------------------------------------

def split_property_block(lines):
    """Index of the first line AFTER the leading property block."""
    end = 0
    for line in lines:
        if PROP_RE.match(line):
            end += 1
        else:
            break
    return end


def read_page(path):
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    props = {}
    for line in lines[:split_property_block(lines)]:
        match = PROP_RE.match(line)
        props[match.group(1)] = match.group(2).strip()
    return lines, props


def rewrite_properties(lines, values, sync_version):
    """Rewrite ONLY managed property lines; preserve everything else."""
    end = split_property_block(lines)
    block, rest = lines[:end], lines[end:]
    seen = set()
    new_block = []
    for line in block:
        key = PROP_RE.match(line).group(1)
        if key in MANAGED_PROPS:
            new_block.append("%s:: %s" % (key, values[key]))
            seen.add(key)
        elif key == SYNC_PROP:
            new_block.append("%s:: %s" % (SYNC_PROP, sync_version))
            seen.add(SYNC_PROP)
        else:
            new_block.append(line)  # source-file::, user-added props
    for key in MANAGED_PROPS:
        if key not in seen:
            new_block.append("%s:: %s" % (key, values[key]))
    if SYNC_PROP not in seen:
        new_block.append("%s:: %s" % (SYNC_PROP, sync_version))
    return new_block + rest


def new_page(values, sync_version):
    lines = ["%s:: %s" % (key, values[key]) for key in MANAGED_PROPS]
    lines.append("source-file:: ")
    lines.append("%s:: %s" % (SYNC_PROP, sync_version))
    lines.append("")
    lines.append("- ## my reading")
    lines.append("\t- ")
    lines.append("- ## annotations")
    lines.append("\t- (synced from Zotero below this line)")
    return lines


def format_annotation(annotation):
    data = annotation["data"]
    page = data.get("annotationPageLabel", "")
    suffix = " (p. %s)" % page if page else ""
    kind = data.get("annotationType", "")
    if kind in ("image", "ink"):
        text = "[%s annotation%s]" % (kind, suffix)
    else:
        quote = (data.get("annotationText") or "").strip()
        text = '"%s"%s' % (quote, suffix) if quote else "[note%s]" % suffix
    lines = ["\t- %s" % text]
    comment = (data.get("annotationComment") or "").strip()
    if comment:
        lines.append("\t\t- %s" % comment.replace("\n", " "))
    return lines


def append_annotations(lines, annotation_lines):
    """Append under the '## annotations' block (created at EOF if absent)."""
    heading = None
    for index, line in enumerate(lines):
        if line.strip().lstrip("- ").lower() == "## annotations":
            heading = index
            break
    if heading is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("- ## annotations")
        return lines + annotation_lines
    end = heading + 1
    while end < len(lines) and (lines[end].startswith(("\t", "  "))
                                or not lines[end].strip()):
        if not lines[end].strip():
            break
        end += 1
    return lines[:end] + annotation_lines + lines[end:]


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def sync(vault, base_url, dry_run):
    pages_dir = os.path.join(vault, "pages")
    if not os.path.isdir(pages_dir):
        print("lit_sync: no pages/ directory under %s (is --vault the "
              "Logseq graph root?)" % vault, file=sys.stderr)
        return 1
    separator = detect_separator(pages_dir)

    tops, headers = api_get_all("/items/top", base_url)
    attachments, _ = api_get_all("/items?itemType=attachment", base_url)
    annotations, _ = api_get_all("/items?itemType=annotation", base_url)
    library_version = headers.get("Last-Modified-Version", "0")

    attachment_parent = {a["data"]["key"]: a["data"].get("parentItem")
                         for a in attachments}
    by_top = {}
    for annotation in annotations:
        top_key = attachment_parent.get(
            annotation["data"].get("parentItem"))
        if top_key:
            by_top.setdefault(top_key, []).append(annotation)

    created, updated, appended, unchanged, skipped = 0, 0, 0, 0, []
    for item in tops:
        data = item["data"]
        if data.get("itemType") in ("attachment", "note", "annotation"):
            continue
        citekey = extract_citekey(data)
        title = data.get("title", "(untitled)")
        if not citekey:
            skipped.append(title)
            continue
        values = managed_values(item, citekey)
        path = page_path(pages_dir, citekey, separator)
        item_annotations = sorted(
            by_top.get(data["key"], []),
            key=lambda a: a["data"].get("annotationSortIndex", ""))

        if os.path.exists(path):
            lines, props = read_page(path)
            last_sync = int(props.get(SYNC_PROP) or 0)
            fresh = [a for a in item_annotations
                     if int(a.get("version", 0)) > last_sync]
            new_lines = rewrite_properties(lines, values, library_version)
            annotation_lines = []
            for annotation in fresh:
                annotation_lines.extend(format_annotation(annotation))
            if annotation_lines:
                new_lines = append_annotations(new_lines, annotation_lines)
            if new_lines == lines:
                unchanged += 1
                continue
            action = []
            if annotation_lines:
                appended += len(fresh)
                action.append("+%d annotations" % len(fresh))
            updated += 1
            action.append("metadata")
            print("update  %s (%s)" % (os.path.basename(path),
                                       ", ".join(action)))
        else:
            new_lines = new_page(values, library_version)
            annotation_lines = []
            for annotation in item_annotations:
                annotation_lines.extend(format_annotation(annotation))
            if annotation_lines:
                new_lines = append_annotations(new_lines, annotation_lines)
                appended += len(item_annotations)
            created += 1
            print("create  %s (%d annotations)"
                  % (os.path.basename(path), len(item_annotations)))

        if not dry_run:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(new_lines) + "\n")

    print()
    print("lit_sync summary%s: %d created, %d updated, %d annotations "
          "appended, %d unchanged, %d skipped (no pinned citekey)"
          % (" (dry-run, nothing written)" if dry_run else "",
             created, updated, appended, unchanged, len(skipped)))
    for title in skipped:
        print("  skipped: %s  <- pin its citekey in Better BibTeX" % title)
    print("library version stamped: %s (namespace encoding: %s)"
          % (library_version, separator))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Sync Zotero (local API) into notes/literature/@citekey "
                    "pages. See issue #90 and docs/zotero-setup.md.")
    parser.add_argument("--vault", required=True,
                        help="Logseq graph root (contains pages/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report planned actions, write nothing")
    parser.add_argument("--base-url", default=BASE_URL,
                        help="Zotero local API base (default %(default)s)")
    args = parser.parse_args()
    return sync(os.path.expanduser(args.vault), args.base_url, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
