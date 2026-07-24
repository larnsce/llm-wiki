#!/usr/bin/env python3
"""export_paper.py - export a paper's reachable subgraph as a bundle.

Walks the link graph from a paper hub (wiki/papers/<slug>, specs/paper.md
REQ-1519..1526) and emits a self-contained markdown bundle: the pages a
reader needs to inspect the knowledge base behind the paper, the agent-use
log among them, and the #145 viewer vendored into the bundle root so the
directory serves as a site with no build step.

The walk IS the publish boundary (issue #148): only pages reachable from
the hub are exported. Personal tiers are never exported and never dropped
silently - every excluded or unresolvable link target lands in the
manifest with its reason. Before anything is written, every included file
passes the shared publish gate (secret_scan.py); one blocking finding
aborts the whole export.

Usage:
  python3 export_paper.py --config <llm-wiki.yml> --slug <slug> --out <dir>
          [--viewer <index.html>] [--force] [--json]

Exit codes: 0 clean; 1 exported with warnings (excluded-but-linked
targets in the manifest); 2 blocking (missing hub, gate finding, or the
output directory exists without --force).
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

import wikilib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

# Personal tiers: never exported (specs/paper.md REQ-1521). notes/ is
# human-owned EXCEPT notes/literature/, which is the paper's citation
# layer and share-intended (the fixture bundle ships them deliberately).
EXCLUDED_PREFIXES = ("para/", "glossary/", "journals/")


def link_targets(text):
    """All wikilink targets in a page body, alias part removed."""
    targets = []
    for raw in LINK_RE.findall(text):
        target = raw.split("|")[0].strip()
        if target:
            targets.append(target)
    return targets


def classify(name):
    """Include the target, or return the manifest exclusion reason."""
    lower = name.lower()
    if lower.startswith("notes/literature/"):
        return None
    for prefix in EXCLUDED_PREFIXES:
        if lower.startswith(prefix):
            return "personal tier (%s)" % prefix.rstrip("/")
    if lower.startswith("notes/"):
        return "personal tier (notes outside notes/literature)"
    if lower.startswith("wiki/"):
        return None
    return "outside the exportable namespaces"


def bundle_relpath(page, tool):
    """Where a page's file lands inside the bundle.

    Obsidian: the nested viewer route itself (wiki/concept/foo.md).
    Logseq: the flat pages/ layout, verbatim; the viewer's pages/___
    fallback resolves namespace routes to it, so no outline transform
    is needed.
    """
    if tool == "logseq":
        return "pages/" + os.path.basename(page["path"])
    return page["name"] + ".md"


def vendor_viewer(template_path, out_dir, slug, hub_route, nav):
    html = open(template_path, encoding="utf-8").read()
    site = (
        "const SITE={\n"
        "  title:%s,\n"
        "  tagline:'paper wiki',\n"
        "  defaultRoute:%s,\n"
        "  nav:[\n    %s\n  ]\n"
        "};" % (
            json.dumps(slug),
            json.dumps(hub_route),
            ",\n    ".join("[%s,%s]" % (json.dumps(label), json.dumps(path))
                           for label, path in nav)))
    new_html, count = re.subn(r"const SITE=\{.*?\};", site, html,
                              count=1, flags=re.S)
    if count != 1:
        return False
    with open(os.path.join(out_dir, "index.html"), "w",
              encoding="utf-8") as handle:
        handle.write(new_html)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--viewer", default=None,
                        help="viewer template; default: the repo's "
                             "templates/site/index.html when present")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = wikilib.load_config(args.config)
    tool = config.get("tool", "")
    pages = wikilib.enumerate_pages(config)
    by_name = {p["name"]: p for p in pages}

    hub_name = "wiki/papers/" + args.slug
    if hub_name not in by_name:
        print("export_paper: no hub page %s (run /wiki-paper new first)"
              % hub_name, file=sys.stderr)
        return 2

    if os.path.exists(args.out):
        if not args.force:
            print("export_paper: %s exists (use --force to replace)"
                  % args.out, file=sys.stderr)
            return 2
        shutil.rmtree(args.out)

    # Reachability walk from the hub (REQ-1520).
    included, excluded, missing = [], [], []
    seen = {hub_name}
    queue = [hub_name]
    while queue:
        name = queue.pop(0)
        page = by_name[name]
        included.append(page)
        for target in link_targets(open(page["path"],
                                        encoding="utf-8").read()):
            if target in seen:
                continue
            seen.add(target)
            reason = classify(target)
            if reason:
                excluded.append((target, reason))
                continue
            if target not in by_name:
                missing.append(target)
                continue
            queue.append(target)

    # Shared publish gate BEFORE anything is written (REQ-1522).
    gate = os.path.join(SCRIPT_DIR, "secret_scan.py")
    for page in included:
        result = subprocess.run(
            [sys.executable, gate, page["path"]],
            capture_output=True, text=True)
        if result.returncode == 2:
            print("export_paper: publish gate BLOCKED on %s; nothing "
                  "exported. Redact first.\n%s"
                  % (page["name"], result.stdout.strip()), file=sys.stderr)
            return 2

    # Write the bundle (REQ-1523); ingested/ bytes never ship (REQ-1526).
    os.makedirs(args.out)
    for page in included:
        dest = os.path.join(args.out, bundle_relpath(page, tool))
        os.makedirs(os.path.dirname(dest) or args.out, exist_ok=True)
        shutil.copyfile(page["path"], dest)

    # Vendor the viewer (REQ-1524).
    template = args.viewer
    if template is None:
        candidate = os.path.normpath(os.path.join(
            SCRIPT_DIR, "..", "..", "..", "templates", "site", "index.html"))
        template = candidate if os.path.isfile(candidate) else None
    hub_route = hub_name + ".md"
    nav = [["Hub", hub_route]]
    log_name = hub_name + "/agent-log"
    if log_name in by_name:
        nav.append(["AI log", log_name + ".md"])
    vendored = bool(template) and vendor_viewer(
        template, args.out, args.slug, hub_route, nav)

    # Manifest (REQ-1521/1525): exclusions are visible, never silent.
    stamp = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds")
    lines = ["# Export manifest - %s" % args.slug, "",
             "Generated %s by export_paper.py; the hub graph walk is the"
             % stamp,
             "publish boundary (specs/paper.md REQ-1520). Source bytes",
             "under ingested/ are never exported (REQ-1526); citations",
             "stay textual provenance.", "",
             "## Included (%d pages)" % len(included), ""]
    for page in sorted(included, key=lambda p: p["name"]):
        lines.append("- %s (from %s)" % (
            page["name"], os.path.relpath(page["path"],
                                          wikilib.wiki_root(config))))
    lines += ["", "## Excluded linked targets (%d)" % len(excluded), ""]
    for target, reason in sorted(excluded):
        lines.append("- %s: %s" % (target, reason))
    lines += ["", "## Unresolvable linked targets (%d)" % len(missing), ""]
    for target in sorted(missing):
        lines.append("- %s: no such page (viewer shows the boundary "
                     "page)" % target)
    lines += ["", "## Gate", "",
              "- secret_scan.py: %d files scanned, no blocking findings"
              % len(included),
              "- viewer: %s" % ("vendored as index.html" if vendored else
                                "NOT vendored (no template found; copy "
                                "templates/site/index.html per "
                                "docs/publish-wiki.md)"), ""]
    with open(os.path.join(args.out, "export-manifest.md"), "w",
              encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    summary = {"slug": args.slug, "included": len(included),
               "excluded": len(excluded), "missing": len(missing),
               "viewer": vendored, "out": args.out}
    if args.json:
        wikilib.emit_json(summary)
    else:
        print("export_paper: %(included)d pages -> %(out)s "
              "(%(excluded)d excluded, %(missing)d unresolvable, "
              "viewer %(viewer)s)" % summary)
    return 1 if (excluded or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
