#!/usr/bin/env python3
"""check_citations.py - block-native claim-citation checker (specs/citations.md).

Checks the `cite::` convention (REQ-900..905) on wiki pages, per page:

- cite coverage stats: claim blocks with vs. without a `cite::` reference
  (REQ-902 / ingest REQ-033b, born-cited pages),
- every cite target resolves: `ingested/` refs must exist on disk (or be
  pending in `raw_dir`, see below); `url:` refs must be http(s)-URL-shaped,
- the source-file union invariant (REQ-904): the page-level `source-file::`
  equals the union of the page's `ingested/` cite targets (paths only,
  locators stripped, deduplicated),
- orphaned cites: a cite target missing from the `source-file::` union, a
  `source-file::` entry no claim cites, or a `cite::` line with no claim
  block above it,
- cite refs written as `[[links]]` (REQ-905: refs are plain text).

Claim-block heuristic (documented honestly): a claim block is a bullet line
(`- ...`, any indent) in the page body that is NOT a heading, a `key:: value`
property line, a `{{query}}`/embed line, a bare `[[link]]`-only bullet, a
hub routing line (`[[...]] -- ...`), inside a fenced code block, or under one
of the structural sections Cross-References (canonical; Related and See also
are tolerated synonyms), Pending Review, Index, Archive, or Log. Prose paragraphs (Obsidian) and block continuation lines (Logseq)
are OUTSIDE the heuristic: the cite convention attaches to bullets (REQ-900),
so only bullets are counted. Whether an uncited bullet is common knowledge
or marked synthesis (both exempt per REQ-902) is a judgment call, so the
COVERAGE findings are advisory (warning, never critical). The resolution and
union checks are mechanical and blocking (critical).

A cite line attaches to the nearest preceding claim bullet with a smaller
indent (Logseq block property: an unbulleted `cite:: ...` continuation line;
Obsidian: an indented `- cite:: ...` child bullet; both match one grep shape).

Staging (ingest REQ-033b): pages written before v2.1 carry `source-file::`
but no `cite::` lines. On such a page the union check is SKIPPED and the
missing citations are reported as a REQ-902 coverage warning, not a critical
failure. The union invariant is enforced as critical once a page carries at
least one `cite::` line.

Pending-move accommodation: the ingest quality gate runs BEFORE the source
file is moved from `raw_dir` into `ingested/` (ingest REQ-075), so an
`ingested/<type>/<file>` target whose file does not exist yet counts as
resolved when a file with the same basename sits in `raw_dir`.

Severity map (finding ids = spec REQ ids):

  REQ-900  warning   cite:: line not attached to any claim block
  REQ-901  critical  ingested/ cite target resolves to no file (and is not
                     pending in raw_dir)
  REQ-901  warning   malformed ref (neither an ingested/ path nor url:<...>)
                     or url: ref that is not http(s)-URL-shaped
  REQ-902  warning   claim blocks without cite:: on an ingested page
                     (advisory coverage)
  REQ-904  critical  source-file union invariant violated (either direction)
  REQ-905  warning   cite ref written as a [[link]]

Skipped pages: hubs, system pages (Schema, Dashboard, Access-Log), and
deliberate stubs carrying `canonical-url::` (schema REQ-584).

Stdlib only; imports wikilib. Exit codes: 0 = clean, 1 = warnings,
2 = critical.
"""

import argparse
import os
import re
import sys

import wikilib

SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}

# Compared case-insensitively so pre-migration corpora (Wiki/Schema, ...)
# keep their system-page exemptions (REQ-580c grandfather).
SYSTEM_PAGE_NAMES = {"wiki/schema", "wiki/dashboard",
                     "wiki/reference/access-log"}

# One grep shape for both tool modes: optional bullet, then cite::.
CITE_LINE_RE = re.compile(r"^(\s*)(?:-\s+)?cite::\s*(.*)$")
BULLET_RE = re.compile(r"^(\s*)-\s+(.*)$")
PROP_LINE_RE = re.compile(r"^\s*(?:-\s+)?[A-Za-z][A-Za-z0-9_-]*::\s")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
FENCE_RE = re.compile(r"^\s*(?:-\s+)?```")
LINK_ONLY_RE = re.compile(r"^\[\[[^\]]+\]\]$")
ROUTING_LINE_RE = re.compile(r"^\[\[[^\]]+\]\]\s+--\s")
INGESTED_REF_RE = re.compile(r"^ingested/[^\s#]+(?:#\S+)?$")
URL_REF_RE = re.compile(r"^url:<?(https?://[^\s>]+)>?$")
URL_SHAPE_RE = re.compile(r"^https?://[^\s/]+\.[^\s/]+(/\S*)?$")

# "related" and "see also" are tolerated synonyms for pre-existing pages;
# ingest writes the canonical "## Cross-References" heading (ingest REQ-034).
EXCLUDED_SECTIONS = {"cross-references", "related", "see also",
                     "pending review", "index", "archive", "log"}


def indent_width(whitespace):
    """Indentation width with tabs expanded (tab = 4)."""
    return len(whitespace.expandtabs(4))


def parse_claims(text, tool):
    """Extract claim blocks and their cite refs from page text.

    Returns (claims, orphan_cites): claims is a list of dicts
    {"line", "text", "cites"}; orphan_cites is a list of dicts
    {"line", "refs"} for cite lines with no claim block above them.
    """
    lines = text.splitlines()
    start = 0
    if tool == "obsidian" and lines and lines[0].strip() == "---":
        try:
            start = lines[1:].index("---") + 2
        except ValueError:
            start = len(lines)

    claims = []
    orphan_cites = []
    stack = []  # open claim bullets, outermost first
    section = None
    in_fence = False

    for offset, raw in enumerate(lines[start:]):
        lineno = start + offset + 1
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence or not raw.strip():
            continue

        bullet = BULLET_RE.match(raw)
        content = bullet.group(2).strip() if bullet else raw.strip()

        heading = HEADING_RE.match(content)
        if heading:
            section = heading.group(1).strip().lower()
            stack = []
            continue

        cite = CITE_LINE_RE.match(raw)
        if cite:
            refs = [r.strip() for r in cite.group(2).split(",") if r.strip()]
            ind = indent_width(cite.group(1))
            owner = None
            for claim in reversed(stack):
                if claim["indent"] < ind:
                    owner = claim
                    break
            if owner is not None:
                owner["cites"].extend(refs)
            else:
                orphan_cites.append({"line": lineno, "refs": refs})
            continue

        if not bullet:
            # Prose paragraph / block continuation: outside the heuristic.
            continue

        ind = indent_width(bullet.group(1))
        while stack and stack[-1]["indent"] >= ind:
            stack.pop()

        if PROP_LINE_RE.match(raw):
            continue
        if section in EXCLUDED_SECTIONS:
            continue
        if content.startswith("{{"):
            continue
        if LINK_ONLY_RE.match(content) or ROUTING_LINE_RE.match(content):
            continue

        claim = {"line": lineno, "indent": ind, "text": content, "cites": []}
        claims.append(claim)
        stack.append(claim)

    for claim in claims:
        claim.pop("indent", None)
    return claims, orphan_cites


class Checker:
    def __init__(self, config):
        self.config = config
        self.tool = config.get("tool", "")
        self.root = wikilib.wiki_root(config)
        self.raw_dir = os.path.join(self.root, config.get("raw_dir") or "raw")
        self.findings = []
        self.coverage = []
        self.pages_scanned = 0
        self.pages_with_source_file = 0
        self.pages_with_cites = 0
        self.claims_total = 0
        self.claims_cited = 0

    def add(self, page_name, req_id, severity, message):
        self.findings.append({
            "id": req_id,
            "severity": severity,
            "page": page_name,
            "message": message,
        })

    def target_resolves(self, target):
        """An ingested/ target resolves if the file exists, or a file with
        the same basename is pending in raw_dir (pre-move gate run)."""
        if os.path.isfile(os.path.join(self.root, target)):
            return True
        pending = os.path.join(self.raw_dir, os.path.basename(target))
        return os.path.isfile(pending)

    def check_page(self, name, text):
        props = wikilib.parse_page_properties(text, self.tool)
        if props.get("type") == "hub":
            return
        if (name.lower() in SYSTEM_PAGE_NAMES
                or props.get("access-log") == "true"
                or props.get("type") in ("schema", "dashboard")):
            return
        if "canonical-url" in props:
            return  # deliberate stub, exempt (schema REQ-584)
        self.pages_scanned += 1

        source_file = props.get("source-file", "")
        sf_set = {p.strip() for p in source_file.split(",") if p.strip()}
        claims, orphan_cites = parse_claims(text, self.tool)

        all_refs = [ref for claim in claims for ref in claim["cites"]]
        all_refs += [ref for entry in orphan_cites for ref in entry["refs"]]
        has_cites = bool(all_refs)

        if not sf_set and not has_cites:
            return  # hand-written page, nothing citation-relevant

        if sf_set:
            self.pages_with_source_file += 1
        if has_cites:
            self.pages_with_cites += 1

        for entry in orphan_cites:
            self.add(name, "REQ-900", "warning",
                     "cite:: line (line %d) is not attached to any claim "
                     "block" % entry["line"])

        # Ref shape + resolution (mechanical).
        ingested_targets = set()
        unresolved_reported = set()
        for ref in all_refs:
            if "[[" in ref:
                self.add(name, "REQ-905", "warning",
                         "cite ref '%s' uses [[link]] syntax; refs are plain "
                         "text paths, not wiki links" % ref)
                continue
            if INGESTED_REF_RE.match(ref):
                target = ref.split("#", 1)[0]
                ingested_targets.add(target)
                if (target not in unresolved_reported
                        and not self.target_resolves(target)):
                    unresolved_reported.add(target)
                    self.add(name, "REQ-901", "critical",
                             "cite target '%s' resolves to no file under "
                             "ingested/ (and no matching pending file in "
                             "raw_dir)" % target)
                continue
            url_match = URL_REF_RE.match(ref)
            if url_match:
                if not URL_SHAPE_RE.match(url_match.group(1)):
                    self.add(name, "REQ-901", "warning",
                             "url cite ref '%s' is not a valid http(s) URL"
                             % ref)
                continue
            self.add(name, "REQ-901", "warning",
                     "malformed cite ref '%s' (expected an ingested/ path "
                     "with optional #locator, or url:<https://...>)" % ref)

        # Union invariant (mechanical, blocking) - enforced once the page
        # carries at least one cite:: line (staging per ingest REQ-033b).
        if has_cites:
            missing_from_sf = sorted(ingested_targets - sf_set)
            uncited_sf = sorted(sf_set - ingested_targets)
            if missing_from_sf:
                self.add(name, "REQ-904", "critical",
                         "source-file union invariant violated: cited "
                         "target(s) missing from source-file:: %s"
                         % ", ".join(missing_from_sf))
            if uncited_sf:
                self.add(name, "REQ-904", "critical",
                         "source-file union invariant violated: "
                         "source-file:: entr%s cited by no claim: %s"
                         % ("y" if len(uncited_sf) == 1 else "ies",
                            ", ".join(uncited_sf)))

        # Coverage (advisory; exemption is a judgment call per REQ-902).
        if sf_set:
            uncited = [c for c in claims if not c["cites"]]
            self.claims_total += len(claims)
            self.claims_cited += len(claims) - len(uncited)
            self.coverage.append({
                "page": name,
                "claims": len(claims),
                "cited": len(claims) - len(uncited),
                "uncited": len(uncited),
            })
            if uncited:
                sample = "; ".join(
                    "line %d: %.60s" % (c["line"], c["text"])
                    for c in uncited[:3])
                self.add(name, "REQ-902", "warning",
                         "%d of %d claim block(s) lack cite:: (%s). Common "
                         "knowledge and marked synthesis are exempt; when "
                         "unsure, cite." % (len(uncited), len(claims), sample))

    def run(self):
        for entry in wikilib.enumerate_pages(self.config):
            with open(entry["path"], "r", encoding="utf-8") as handle:
                text = handle.read()
            self.check_page(entry["name"], text)
        return self.findings


def build_report(checker):
    findings = sorted(
        checker.findings,
        key=lambda f: (SEVERITY_RANK[f["severity"]], f["page"], f["id"]))
    totals = {"critical": 0, "warning": 0, "info": 0}
    for finding in findings:
        totals[finding["severity"]] += 1
    return {
        "tool": checker.tool,
        "pages_scanned": checker.pages_scanned,
        "pages_with_source_file": checker.pages_with_source_file,
        "pages_with_cites": checker.pages_with_cites,
        "claims_total": checker.claims_total,
        "claims_cited": checker.claims_cited,
        "coverage": checker.coverage,
        "totals": totals,
        "findings": findings,
    }


def print_report(report):
    print("check_citations: scanned %d page(s) (tool: %s); %d with "
          "source-file::, %d with cite::"
          % (report["pages_scanned"], report["tool"],
             report["pages_with_source_file"], report["pages_with_cites"]))
    if report["claims_total"]:
        print("coverage: %d of %d claim block(s) cited on ingested pages"
              % (report["claims_cited"], report["claims_total"]))
    for row in report["coverage"]:
        print("  %s: %d claim(s), %d cited, %d uncited"
              % (row["page"], row["claims"], row["cited"], row["uncited"]))
    for severity in ("critical", "warning", "info"):
        group = [f for f in report["findings"] if f["severity"] == severity]
        if not group:
            continue
        print("\n%s (%d)" % (severity.upper(), len(group)))
        for finding in group:
            print("  [%s] %s - %s" % (finding["id"], finding["page"],
                                      finding["message"]))
    totals = report["totals"]
    print("\ntotals: %d critical, %d warning, %d info"
          % (totals["critical"], totals["warning"], totals["info"]))


def main():
    parser = argparse.ArgumentParser(
        description="Block-native claim-citation checker: cite:: coverage, "
                    "ref resolution, and the source-file union invariant "
                    "(specs/citations.md REQ-900..905).")
    parser.add_argument("--config", default=None,
                        help="path to llm-wiki.yml (default: discover)")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    args = parser.parse_args()

    if args.config:
        config_path = args.config
    else:
        try:
            config_path, _ = wikilib.discover_config()
        except ValueError as error:
            print("CRITICAL: %s" % error, file=sys.stderr)
            return wikilib.EXIT_CRITICAL
        if not config_path:
            print(wikilib.DISCOVERY_FAILURE_MESSAGE, file=sys.stderr)
            return wikilib.EXIT_CRITICAL
    config = wikilib.load_config(config_path)
    if config.get("tool") not in wikilib.VALID_TOOLS:
        print("CRITICAL: invalid tool '%s' in %s"
              % (config.get("tool", ""), config_path), file=sys.stderr)
        return wikilib.EXIT_CRITICAL

    checker = Checker(config)
    checker.run()
    report = build_report(checker)

    criticals = ["x"] * report["totals"]["critical"]
    warnings = ["x"] * report["totals"]["warning"]
    status, exit_code = wikilib.status_from_counts(criticals, warnings)
    report["status"] = status

    if args.json:
        wikilib.emit_json(report)
    else:
        print_report(report)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
