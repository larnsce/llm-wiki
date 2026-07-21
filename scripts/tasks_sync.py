#!/usr/bin/env python3
"""tasks_sync.py - GitHub Issues as canonical task state (tasks-sync seam).

Two one-way flows over the human task layer (journal pages and
para/projects/ pages), never a bidirectional sync
(openspec/specs/tasks-sync.md REQ-1400..1417):

  open   graph -> GitHub: eligible open task blocks without issue::
         become issues; the block is stamped issue:: + opened::.
  close  both one-way halves: issues closed on GitHub flip their
         tracked block to DONE and stamp closed::; a tracked block the
         human marked DONE/CANCELED closes its issue. Never reopens.
  status read-only report: tracked/open/closed counts, orphans.

Design decisions (do not change without discussion):

1. No state file. Idempotency is content-embedded (REQ-1412): issue::
   is the sole link key; open only touches blocks lacking issue::,
   close only touches blocks lacking closed::. --since merely narrows
   the closed-issue query and never affects correctness.
2. Stamps land immediately per created/closed issue (REQ-1405), so a
   crash mid-run cannot leave issues unstamped behind later candidates.
3. gh CLI only, argv vectors, no shell. A missing or unauthenticated
   gh is exit 2 with zero graph writes (REQ-1413); never worked around
   with a raw API token.
4. Write budget (REQ-1414): insert issue::/opened::/closed:: property
   lines and flip one marker token per closed issue. Nothing else -
   no block/page creation, no reordering, no other text edits.
5. Logseq tier-1 (REQ-1401): tool: obsidian aborts cleanly.

Usage:
    python3 scripts/tasks_sync.py open   [--dry-run] [--ids a1b2,c3d4]
    python3 scripts/tasks_sync.py close  [--dry-run] [--since YYYY-MM-DD]
    python3 scripts/tasks_sync.py status
    common: [--config PATH] [--scope journals|para|both] [--gh PATH]
            [--json]

Exit codes: 0 = clean, 1 = warnings (skipped candidates, orphans),
2 = critical (config problem, gh missing/unauthenticated, gh failure).
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "skills", "wiki-core", "scripts"))
import wikilib  # noqa: E402

OPEN_MARKERS = ("TODO", "DOING", "NOW", "LATER", "WAITING")
DONE_MARKERS = ("DONE", "CANCELED", "CANCELLED")

MARKER_RE = re.compile(
    r"^(\s*)-\s+(TODO|DOING|NOW|LATER|WAITING|DONE|CANCELLED|CANCELED)"
    r"(?:\s+(.*))?$")
PROP_LINE_RE = re.compile(r"^(\s+)([A-Za-z][A-Za-z0-9_-]*)::\s*(.*)$")
GH_TAG_RE = re.compile(r"(?:^|(?<=\s))#gh(?=\s|$)")
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
ISSUE_REF_RE = re.compile(r"^(?:([\w.-]+)/([\w.-]+))?#?(\d+)$")
ISSUE_URL_RE = re.compile(r"github\.com/([\w.-]+)/([\w.-]+)/issues/(\d+)")


# ---------------------------------------------------------------------------
# Context (config + layout)
# ---------------------------------------------------------------------------

class Ctx(object):
    pass


def load_ctx(args):
    """Resolve config, gate on tool/tasks_repo, compute scan roots."""
    if args.config:
        config_path = os.path.abspath(wikilib.expand_path(args.config))
        if not os.path.isfile(config_path):
            print("tasks_sync: no config file at %s" % config_path,
                  file=sys.stderr)
            sys.exit(2)
    else:
        try:
            config_path, _ = wikilib.discover_config()
        except ValueError as err:
            print("tasks_sync: %s" % err, file=sys.stderr)
            sys.exit(2)
        if not config_path:
            print(wikilib.DISCOVERY_FAILURE_MESSAGE, file=sys.stderr)
            sys.exit(2)

    config = wikilib.load_config(config_path)
    tool = config.get("tool", "")
    if tool != "logseq":
        print(
            "tasks_sync: tasks-sync is Logseq tier-1 (REQ-1401); tool is "
            "'%s'. Task markers and '::' block properties are "
            "Logseq-native - no Obsidian support in v0.1." % tool,
            file=sys.stderr)
        sys.exit(2)

    ctx = Ctx()
    ctx.config = config
    ctx.config_path = config_path
    ctx.root = wikilib.wiki_root(config)
    ctx.pages_dir = wikilib.pages_root(config)
    ctx.journals_dir = os.path.join(
        ctx.root,
        (config.get("journals_dir") or wikilib.DEFAULT_JOURNALS_DIR)
        .strip("/"))
    ctx.para_prefix = ((config.get("para_dir") or wikilib.DEFAULT_PARA_DIR)
                       .strip("/") + "/projects/")
    ctx.tasks_repo = config.get("tasks_repo", "")
    ctx.tasks_project = config.get("tasks_project", "")
    ctx.gh_bin = args.gh
    ctx.dry_run = getattr(args, "dry_run", False)

    if not ctx.tasks_repo:
        print(
            "tasks_sync: no tasks_repo in %s - the tasks-sync seam is "
            "inert (specs/config.md REQ-662). Add e.g.\n"
            "    tasks_repo: owner/tasks\n"
            "to enable it." % config_path, file=sys.stderr)
        sys.exit(2)
    if ctx.tasks_repo.count("/") != 1 or not all(
            part for part in ctx.tasks_repo.split("/")):
        print("tasks_sync: tasks_repo '%s' is not an owner/repo slug "
              "(REQ-662)." % ctx.tasks_repo, file=sys.stderr)
        sys.exit(2)
    return ctx


# ---------------------------------------------------------------------------
# Graph scanning
# ---------------------------------------------------------------------------

def journal_files(ctx):
    if not os.path.isdir(ctx.journals_dir):
        return []
    return [os.path.join(ctx.journals_dir, name)
            for name in sorted(os.listdir(ctx.journals_dir))
            if name.endswith(".md")]


def para_project_files(ctx):
    """(path, page-name) for para/projects/ pages, either encoding."""
    if not os.path.isdir(ctx.pages_dir):
        return []
    found = []
    for entry in sorted(os.listdir(ctx.pages_dir)):
        if not entry.endswith(".md"):
            continue
        name = entry[:-3].replace("___", "/").replace("%2F", "/")
        if name.startswith(ctx.para_prefix):
            found.append((os.path.join(ctx.pages_dir, entry), name))
    return found


def scan_blocks(path):
    """Yield task blocks: marker line + contiguous property child lines.

    A block's properties are the "key:: value" lines immediately under
    the marker line with deeper indentation and no bullet (the Logseq MD
    block-property form). prop_end is the line index AFTER the last
    property line - the insertion point for new stamps.
    """
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    blocks = []
    for index, line in enumerate(lines):
        match = MARKER_RE.match(line)
        if not match:
            continue
        indent, marker, text = match.group(1), match.group(2), \
            match.group(3) or ""
        props = {}
        prop_indent = None
        prop_end = index + 1
        for child in lines[index + 1:]:
            prop_match = PROP_LINE_RE.match(child)
            if not prop_match or len(prop_match.group(1)) <= len(indent):
                break
            props[prop_match.group(2)] = prop_match.group(3).strip()
            prop_indent = prop_match.group(1)
            prop_end += 1
        blocks.append({
            "path": path, "lineno": index, "indent": indent,
            "marker": marker, "text": text.strip(), "props": props,
            "prop_indent": prop_indent, "prop_end": prop_end,
        })
    return lines, blocks


def rel(ctx, path):
    return os.path.relpath(path, ctx.root)


def candidate_id(ctx, block):
    key = "%s:%s" % (rel(ctx, block["path"]), block["text"])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


def linked_project(ctx, text):
    for target in LINK_RE.findall(text):
        if target.startswith(ctx.para_prefix):
            return target
    return None


def page_repo(ctx, page_name):
    """repo:: page property of a para/projects/ page, if any."""
    for encoded in (page_name.replace("/", "___"),
                    page_name.replace("/", "%2F")):
        path = os.path.join(ctx.pages_dir, encoded + ".md")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                props = wikilib.parse_page_properties(handle.read(),
                                                      "logseq")
            return props.get("repo", "")
    return ""


def gather(ctx, scope):
    """All task blocks in scope as (block, origin, page_name) tuples."""
    entries = []
    if scope in ("journals", "both"):
        for path in journal_files(ctx):
            _, blocks = scan_blocks(path)
            for block in blocks:
                entries.append((block, "journal", None))
    if scope in ("para", "both"):
        for path, name in para_project_files(ctx):
            _, blocks = scan_blocks(path)
            for block in blocks:
                entries.append((block, "para", name))
    return entries


def open_candidates(ctx, scope):
    """Eligibility gate (REQ-1402) + repo resolution (REQ-1403)."""
    candidates, skipped = [], []
    for block, origin, page_name in gather(ctx, scope):
        if block["marker"] not in OPEN_MARKERS or "issue" in block["props"]:
            continue
        project = page_name if origin == "para" \
            else linked_project(ctx, block["text"])
        if origin == "journal" and not project \
                and not GH_TAG_RE.search(block["text"]):
            continue
        repo = (page_repo(ctx, project) if project else "") \
            or ctx.tasks_repo
        candidate = {
            "id": candidate_id(ctx, block),
            "title": clean_title(ctx, block["text"]),
            "repo": repo,
            "project": project or "",
            "source": "%s:%d" % (rel(ctx, block["path"]),
                                 block["lineno"] + 1),
            "block": block,
        }
        if not candidate["title"]:
            skipped.append((candidate, "empty title after cleanup"))
            continue
        candidates.append(candidate)
    return candidates, skipped


def clean_title(ctx, text):
    """Deterministic title (REQ-1407): drop the para link and #gh tag,
    reduce other [[refs]] to their leaf text, collapse whitespace."""
    def link_sub(match):
        target = match.group(1)
        if target.startswith(ctx.para_prefix):
            return ""
        return target.rsplit("/", 1)[-1]
    text = LINK_RE.sub(link_sub, text)
    text = GH_TAG_RE.sub("", text)
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Graph writes (the REQ-1414 budget: stamps + one marker token)
# ---------------------------------------------------------------------------

def stamp(ctx, block, new_props, flip_marker=None):
    """Insert property lines under the block; optionally flip its marker.

    Re-reads the file and relocates the block by marker+text so earlier
    stamps in the same run cannot desynchronize line numbers.
    """
    path = block["path"]
    lines, blocks = scan_blocks(path)
    target = None
    for current in blocks:
        if (current["marker"], current["text"]) == (block["marker"],
                                                    block["text"]) \
                and current["props"] == block["props"]:
            target = current
            break
    if target is None:
        return False
    indent = target["prop_indent"] or (target["indent"] + "  ")
    inserted = ["%s%s:: %s" % (indent, key, value)
                for key, value in new_props]
    lines[target["prop_end"]:target["prop_end"]] = inserted
    if flip_marker:
        old = lines[target["lineno"]]
        lines[target["lineno"]] = old.replace(
            "- %s" % target["marker"], "- %s" % flip_marker, 1)
    if not ctx.dry_run:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return True


def today_ref():
    return "[[%s]]" % datetime.date.today().isoformat()


# ---------------------------------------------------------------------------
# gh CLI (REQ-1413: argv vectors, preflight, clean stop)
# ---------------------------------------------------------------------------

def gh(ctx, *argv, **kwargs):
    """Run gh. mutating=True commands are printed, not run, in dry-run.
    fatal=False returns None on failure instead of exiting (REQ-1406)."""
    mutating = kwargs.pop("mutating", False)
    fatal = kwargs.pop("fatal", True)
    command = [ctx.gh_bin] + list(argv)
    if mutating and ctx.dry_run:
        print("would run: %s" % " ".join(command))
        return ""
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        print("tasks_sync: gh CLI not found ('%s'). Install GitHub CLI "
              "and run 'gh auth login'; do NOT work around it with a "
              "raw API token (REQ-1413)." % ctx.gh_bin, file=sys.stderr)
        sys.exit(2)
    if result.returncode != 0:
        if not fatal:
            print("  warning: gh %s failed: %s"
                  % (" ".join(argv[:3]), result.stderr.strip()))
            return None
        print("tasks_sync: gh failed (%s): %s"
              % (" ".join(argv[:3]), result.stderr.strip()),
              file=sys.stderr)
        sys.exit(2)
    return result.stdout


def gh_preflight(ctx):
    """gh present and authenticated, else exit 2 with zero writes."""
    try:
        result = subprocess.run([ctx.gh_bin, "auth", "status"],
                                capture_output=True, text=True)
    except FileNotFoundError:
        print("tasks_sync: gh CLI not found ('%s'). Install GitHub CLI "
              "and run 'gh auth login'; do NOT work around it with a "
              "raw API token (REQ-1413)." % ctx.gh_bin, file=sys.stderr)
        sys.exit(2)
    if result.returncode != 0:
        print("tasks_sync: gh is not authenticated. Run 'gh auth login' "
              "and retry; the graph was not touched (REQ-1413).\n%s"
              % result.stderr.strip(), file=sys.stderr)
        sys.exit(2)


def parse_issue_ref(ctx, value):
    """issue:: value -> (owner/repo, number); short forms resolve
    against tasks_repo (REQ-1417). None if unparseable."""
    match = ISSUE_REF_RE.match(value.strip())
    if not match:
        return None
    owner, repo, number = match.groups()
    slug = "%s/%s" % (owner, repo) if owner else ctx.tasks_repo
    return slug, int(number)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_open(ctx, args):
    candidates, skipped = open_candidates(ctx, args.scope)
    if args.ids:
        wanted = set(args.ids.split(","))
        unknown = wanted - {c["id"] for c in candidates}
        if unknown:
            print("tasks_sync: unknown candidate id(s): %s"
                  % ", ".join(sorted(unknown)), file=sys.stderr)
            sys.exit(2)
        candidates = [c for c in candidates if c["id"] in wanted]

    if args.json:
        print(json.dumps({"candidates": [
            {key: c[key] for key in ("id", "title", "repo", "project",
                                     "source")}
            for c in candidates]}, indent=2))
    else:
        if not candidates:
            print("open-sync: no eligible candidates%s."
                  % (" (dry-run)" if ctx.dry_run else ""))
        for c in candidates:
            print("%s  %-50s  %s  %s"
                  % (c["id"], c["title"][:50], c["repo"], c["source"]))
    for candidate, reason in skipped:
        print("  skipped: %s (%s)" % (candidate["source"], reason))

    if ctx.dry_run:
        if candidates:
            print("\nopen-sync dry-run: %d candidate(s); nothing written, "
                  "no issues created. Confirm, then rerun without "
                  "--dry-run (optionally --ids id1,id2)."
                  % len(candidates))
        return 1 if skipped else 0

    if not candidates:
        return 1 if skipped else 0
    gh_preflight(ctx)
    created = 0
    for c in candidates:
        body = ("Opened by tasks-sync from the Logseq graph.\n\n"
                "- source: %s\n" % c["source"])
        if c["project"]:
            body += "- project: %s\n" % c["project"]
        out = gh(ctx, "issue", "create", "-R", c["repo"],
                 "--title", c["title"], "--body", body, mutating=True)
        url_match = ISSUE_URL_RE.search(out or "")
        if not url_match:
            print("tasks_sync: could not parse issue URL from gh output "
                  "for %r; stopping before the stamp (fix by hand: add "
                  "issue:: to %s)." % (c["title"], c["source"]),
                  file=sys.stderr)
            sys.exit(2)
        issue_ref = "%s/%s#%s" % url_match.groups()
        stamp(ctx, c["block"], [("issue", issue_ref),
                                ("opened", today_ref())])
        created += 1
        print("created %s  %s" % (issue_ref, c["title"]))
        if ctx.tasks_project:
            owner, number = ctx.tasks_project.split("/", 1)
            url = "https://github.com/%s/issues/%s" % (
                c["repo"], issue_ref.rsplit("#", 1)[1])
            # A failed add is a warning, not a rollback (REQ-1406).
            gh(ctx, "project", "item-add", number, "--owner", owner,
               "--url", url, mutating=True, fatal=False)
    print("\nopen-sync: %d issue(s) created and stamped." % created)
    return 1 if skipped else 0


def tracked_blocks(ctx, scope):
    """Blocks with issue::, split into (open, done, closed) buckets."""
    open_blocks, done_blocks, closed_refs = [], [], set()
    for block, _, _ in gather(ctx, scope):
        if "issue" not in block["props"]:
            continue
        parsed = parse_issue_ref(ctx, block["props"]["issue"])
        if not parsed:
            print("  warning: unparseable issue:: '%s' at %s:%d"
                  % (block["props"]["issue"], rel(ctx, block["path"]),
                     block["lineno"] + 1))
            continue
        if "closed" in block["props"]:
            if block["marker"] in OPEN_MARKERS:
                # GitHub wins on state (REQ-1411): never reopened.
                print("  warning: %s:%d was edited back to %s but its "
                      "issue %s is closed; the issue stays closed "
                      "(report only)"
                      % (rel(ctx, block["path"]), block["lineno"] + 1,
                         block["marker"], block["props"]["issue"]))
            closed_refs.add(parsed)
        elif block["marker"] in DONE_MARKERS:
            done_blocks.append((block, parsed))
        else:
            open_blocks.append((block, parsed))
    return open_blocks, done_blocks, closed_refs


def fetch_closed(ctx, repo, since):
    """Closed issue numbers for one repo, one gh call (REQ-1410)."""
    argv = ["issue", "list", "-R", repo, "--state", "closed",
            "--json", "number", "--limit", "1000"]
    if since:
        argv += ["--search", "closed:>%s" % since]
    try:
        return {item["number"] for item in json.loads(gh(ctx, *argv))}
    except ValueError:
        print("tasks_sync: unparseable gh issue list output for %s"
              % repo, file=sys.stderr)
        sys.exit(2)


def cmd_close(ctx, args):
    gh_preflight(ctx)
    open_blocks, done_blocks, closed_refs = tracked_blocks(ctx, args.scope)
    warnings = 0

    # graph -> GitHub (REQ-1411): human-completed blocks close issues.
    for block, (repo, number) in done_blocks:
        argv = ["issue", "close", str(number), "-R", repo,
                "--comment", "closed via journal (tasks-sync)"]
        if block["marker"] in ("CANCELED", "CANCELLED"):
            argv += ["--reason", "not planned"]
        gh(ctx, *argv, mutating=True)
        stamp(ctx, block, [("closed", today_ref())])
        print("closed  %s#%d  %s%s" % (repo, number, block["text"][:50],
                                       "  (dry-run)" if ctx.dry_run
                                       else ""))

    # GitHub -> graph (REQ-1410): closed issues flip blocks to DONE.
    flipped = 0
    repos = sorted({repo for _, (repo, _) in open_blocks})
    closed_on_github = {repo: fetch_closed(ctx, repo, args.since)
                        for repo in repos}
    for block, (repo, number) in open_blocks:
        if number not in closed_on_github[repo]:
            continue
        if ctx.dry_run:
            print("would flip %s -> DONE  %s#%d  %s"
                  % (block["marker"], repo, number, block["text"][:50]))
        else:
            stamp(ctx, block, [("closed", today_ref())],
                  flip_marker="DONE")
            print("flipped %s -> DONE  %s#%d  %s"
                  % (block["marker"], repo, number, block["text"][:50]))
        flipped += 1

    # Orphan report (REQ-1415): report only, never act.
    tracked_numbers = {(repo, number)
                       for _, (repo, number) in open_blocks + done_blocks} \
        | closed_refs
    for repo in repos:
        for number in sorted(closed_on_github[repo]):
            if (repo, number) not in tracked_numbers:
                print("  orphan: %s#%d closed on GitHub, no tracked "
                      "block in the graph (report only)" % (repo, number))
                warnings += 1

    print("\nclose-sync%s: %d issue(s) closed from the graph, %d "
          "block(s) flipped to DONE, %d orphan(s)."
          % (" dry-run (nothing written)" if ctx.dry_run else "",
             len(done_blocks), flipped, warnings))
    return 1 if warnings else 0


def cmd_status(ctx, args):
    open_blocks, done_blocks, closed_refs = tracked_blocks(ctx, args.scope)
    candidates, _ = open_candidates(ctx, args.scope)
    report = {
        "candidates": len(candidates),
        "tracked_open": len(open_blocks),
        "pending_close": len(done_blocks),
        "closed": len(closed_refs),
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("tasks-sync status: %(candidates)d candidate(s) for "
              "open-sync, %(tracked_open)d tracked open, "
              "%(pending_close)d done awaiting issue close, "
              "%(closed)d closed." % report)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Issues as canonical task state "
                    "(specs/tasks-sync.md). Dry-run first, always.")
    parser.add_argument("command", choices=("open", "close", "status"))
    parser.add_argument("--config", default=None,
                        help="path to llm-wiki.yml (default: standard "
                             "discovery order)")
    parser.add_argument("--scope", choices=("journals", "para", "both"),
                        default="both",
                        help="where to scan for task blocks "
                             "(default both)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report planned actions; write nothing, "
                             "run no mutating gh command")
    parser.add_argument("--ids", default="",
                        help="open: comma-separated candidate ids to "
                             "sync (from the dry-run list)")
    parser.add_argument("--since", default="",
                        help="close: only query issues closed after "
                             "YYYY-MM-DD (efficiency only, REQ-1412)")
    parser.add_argument("--gh", default="gh",
                        help="gh binary (default: gh on PATH)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output where supported")
    args = parser.parse_args()

    ctx = load_ctx(args)
    if args.command == "open":
        return cmd_open(ctx, args)
    if args.command == "close":
        return cmd_close(ctx, args)
    return cmd_status(ctx, args)


if __name__ == "__main__":
    sys.exit(main())
