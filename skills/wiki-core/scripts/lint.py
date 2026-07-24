#!/usr/bin/env python3
"""lint.py - mechanical wiki linter (layer 1 of the two-layer lint).

Implements the mechanical subset of the 15 lint rules from
openspec/specs/lint.md. Finding ids equal spec REQ ids; findings that live
in openspec/specs/schema.md (date format, enums, provenance, format mixing)
use their schema.md REQ ids.

Mechanical rules covered here:

  Rule 1   Orphan Detection            REQ-110 (hub/system pages exempt)
  Rule 3   Missing Properties          REQ-132, REQ-502 + enum REQ ids
  Rule 4   Broken References           REQ-141
  Rule 5   Hub Completeness            REQ-151
  Rule 6   Credential Leak             REQ-163 (critical)
  Rule 7   Empty Pages                 REQ-171
  Rule 8   Cross-Ref Minimum           REQ-180
  Rule 10  Index Drift                 REQ-193 / REQ-194 / REQ-195
  Rule 11  Archived-in-Live-Index      REQ-197
  Rule 12  External Link Rot           REQ-220 / REQ-221 (canonical-url)
  Rule 13  Naming Hygiene              REQ-230 / REQ-231 (structural names)
  Rule 14  Namespace Hygiene           REQ-240 (pages outside the contract)
  Rule 15  Glossary Hygiene            REQ-250..253 (structure, never decisions)
  Rule 16  Paper-Hub Hygiene           REQ-260..263 (structure, reachability)

  Schema-level mechanical checks: date format (REQ-560, REQ-563),
  completed project without completed date (REQ-522, info),
  ingested-page provenance (REQ-584, REQ-585, REQ-586),
  format mixing (REQ-595).

Namespace scope (specs/namespaces.md): pages under the human-owned
para_dir/notes_dir namespaces are EXEMPT from every wiki-only rule
(REQ-961/966); the only rule that touches them is the advisory,
info-level structural part of naming hygiene. Rule 14 accepts them as
in-contract (REQ-242).

Rule 2 (Stale Detection) and Rule 9 (L1/L2 Duplicates) plus all quality
judgments run agent-side in the wiki-lint skill. This script is
REPORT-ONLY: --fix stays agent-side (the skill proposes fixes per finding
and applies them only after user confirmation).

Grandfather mode (issue #21): findings on a page that does not carry the
current `schema-spec-version::` property are downgraded one severity tier
(critical -> warning, warning -> info), EXCEPT credential leaks (REQ-163),
which stay critical regardless (the wiki is git-tracked; a leaked secret is
dangerous whatever the page's schema vintage). --strict disables the floor.

canonical-url handling (issue #7): a stub page carrying `canonical-url::`
is exempt from the missing-source-file flag and all ingested-page checks
(REQ-221 / REQ-584). Rule 12 validates URL shape by default (offline-safe;
the report marks the check as degraded) and performs a real HTTP check
(curl HEAD with a short timeout, GET range fallback) only with
--check-urls.

Exit codes: 0 = clean (info-only findings allowed), 1 = warnings,
2 = critical.
"""

import argparse
import datetime
import re
import subprocess
import sys

import wikilib

# The canonical contract version. check_canon.py verifies this constant
# matches the schema-spec-version stated in both templates/*/Schema.md.
SCHEMA_SPEC_VERSION = "2.0.0"

# The canonical number of lint rules. check_canon.py verifies this matches
# the "### Rule N:" headings in openspec/specs/lint.md and the rule lists
# in both templates/*/Schema.md.
LINT_RULE_COUNT = 16

SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}

PAGE_TYPES = {"entity", "project", "knowledge", "feedback", "hub",
              "paper-hub"}
# System page types recognized but carrying no required-property set
# (schema.md REQ-569 gives the Access-Log type:: reference).
AUX_TYPES = {"schema", "dashboard", "reference"}

REQUIRED_PROPS = {
    "entity": ["type", "entity-type", "created", "updated", "status", "source"],
    "project": ["type", "status", "created", "updated", "started"],
    "knowledge": ["type", "domain", "created", "updated", "confidence"],
    "feedback": ["type", "severity", "created", "verified", "applies-to"],
    "hub": ["type", "namespace"],
    "paper-hub": ["type", "status", "created", "updated"],
}

# Property enums; the REQ id is the finding id used when a value is
# outside the allowed list.
ENUMS = {
    "entity-type": (
        {"person", "client", "tool", "service", "technology", "dataset"},
        "REQ-511"),
    "domain": ({"tech", "business", "content", "ops"}, "REQ-531"),
    "confidence": ({"high", "medium", "low", "stale"}, "REQ-530"),
    "severity": ({"critical", "important", "nice-to-know"}, "REQ-540"),
    "source": ({"memory-migration", "ingest", "manual"}, "REQ-510"),
    "reliability": ({"high", "medium", "low"}, "REQ-586"),
}
STATUS_ENUMS = {
    "entity": {"active", "inactive", "archived"},
    "project": {"active", "completed", "on-hold", "cancelled"},
}

DATE_PROPS = ("created", "updated", "started", "completed", "verified",
              "archived", "last-reviewed")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Compared case-insensitively so pre-migration corpora (Wiki/Schema, ...)
# keep their system-page exemptions until the lowercase pass runs (REQ-580c).
SYSTEM_PAGE_NAMES = {"wiki/schema", "wiki/dashboard", "wiki/reference/access-log"}

# Rule 14 (REQ-241): deliberate root pages recognized by name
# (case-insensitive), per namespaces.md REQ-962. Contents is the Logseq
# built-in index page.
ROOT_PAGE_NAMES = {"schema", "dashboard", "access-log", "contents"}

# Rule 13 (REQ-230/231): the only word separator inside a structural name
# segment is the ASCII hyphen U+002D (schema.md REQ-580a). The en dash
# U+2013 and em dash U+2014 are matched as escaped codepoints on purpose:
# literal lookalike dashes in source are invisible grep traps.
EN_DASH = "\u2013"
EM_DASH = "\u2014"


def segment_problems(segment, leaf):
    """Naming problems in one page-name segment (rule 13).

    Non-leaf segments are structural by definition: spaces, uppercase,
    underscores, and en/em dashes are all violations (REQ-230). A leaf
    segment may be a proper noun, so only separator violations
    (underscore, en/em dash) are mechanical there (REQ-231); uppercase
    and spaces in a leaf stay a wiki-lint skill judgment.
    """
    problems = []
    if "_" in segment:
        problems.append("underscore")
    if EN_DASH in segment:
        problems.append("en dash (U+2013)")
    if EM_DASH in segment:
        problems.append("em dash (U+2014)")
    if not leaf:
        if " " in segment:
            problems.append("space")
        if segment != segment.lower():
            problems.append("uppercase")
    return problems


CREDENTIAL_PATTERNS = [
    (re.compile(r"\b(token|password|secret|api-key|api\.key)\s*::", re.I),
     "credential property pattern"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "GitHub token"),
    (re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9-]{20,}\b"), "API secret key"),
]

# The generic base64 pass runs separately (REQ-160, issue #104): `/` is in
# the character class, so a 40+ char [[wiki/...]] namespace path would match.
# Link spans are masked out first, and a candidate must show credential-shaped
# character diversity (both cases AND a digit), which a lowercase routing path
# fails.
BASE64_RE = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}(?![A-Za-z0-9+/])")


def has_base64_credential(text):
    masked = WIKI_LINK_RE.sub(" ", text)
    for match in BASE64_RE.finditer(masked):
        token = match.group(0)
        if (any(c.islower() for c in token)
                and any(c.isupper() for c in token)
                and any(c.isdigit() for c in token)):
            return True
    return False

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FENCE_RE = re.compile(r"^\s*(?:-\s+)?```")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HEADING_RE = re.compile(r"^\s*(?:-\s+)?#{1,6}\s+(.*)$")
URL_SHAPE_RE = re.compile(r"^https?://[^\s/]+\.[^\s/]+(/\S*)?$")


def strip_code(text):
    """Remove fenced code blocks and inline code spans.

    Needed so `[[wiki/...]]` placeholders inside backticks (e.g. the Hub
    template's routing-line example) are not treated as real links.
    """
    lines = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        lines.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(lines)


def wiki_links(stripped_text):
    """Outgoing [[wiki/...]] link targets (alias part removed).

    The prefix check is case-insensitive so pre-migration corpora with
    [[Wiki/...]] links keep working (grandfather floor, REQ-580c).
    """
    targets = []
    for raw in WIKI_LINK_RE.findall(stripped_text):
        target = raw.split("|")[0].strip()
        if target.lower().startswith("wiki/"):
            targets.append(target)
    return targets


def parse_hub_index(stripped_text):
    """Parse routing lines from a hub page's ### Index / ### Archive.

    Returns a list of (section, target, description) where section is
    "index" or "archive" and description is the text after the ` -- `
    separator with #tags removed (None when there is no separator).
    """
    entries = []
    section = None
    for line in stripped_text.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            title = heading.group(1).strip().lower()
            if title.startswith("index"):
                section = "index"
            elif title.startswith("archive"):
                section = "archive"
            else:
                section = None
            continue
        if section is None or "[[" not in line:
            continue
        match = WIKI_LINK_RE.search(line)
        if not match:
            continue
        target = match.group(1).split("|")[0].strip()
        if not target.lower().startswith("wiki/"):
            continue
        rest = line[match.end():]
        if " -- " in rest:
            desc = rest.split(" -- ", 1)[1]
            desc = re.sub(r"#[\w-]+", "", desc).strip()
        else:
            desc = None
        entries.append((section, target, desc))
    return entries


def content_lines_after_properties(text, tool):
    """Lines below the property block / frontmatter (empty-page check)."""
    lines = text.splitlines()
    if tool == "obsidian":
        if lines and lines[0].strip() == "---":
            try:
                end = lines[1:].index("---") + 2
            except ValueError:
                end = len(lines)
            lines = lines[end:]
        return [l for l in lines if l.strip()]
    end = 0
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            end += 1
            continue
        if wikilib._LOGSEQ_PROP_RE.match(line):
            end += 1
            continue
        break
    return [l for l in lines[end:] if l.strip()]


def is_valid_date(value):
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def curl_resolves(url, timeout=5):
    """HTTP check: 2xx/3xx via HEAD, GET range fallback. Returns (ok, note)."""
    for extra in (["-I"], ["-r", "0-0"]):
        cmd = (["curl", "-sS", "-o", "/dev/null", "-L",
                "--max-time", str(timeout), "-w", "%{http_code}"]
               + extra + [url])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout + 5)
        except FileNotFoundError:
            return None, "curl not available"
        except subprocess.TimeoutExpired:
            continue
        code = (proc.stdout or "").strip()[-3:]
        if code.isdigit() and 200 <= int(code) < 400:
            return True, "HTTP %s" % code
        note = "HTTP %s" % code if code.isdigit() and code != "000" else \
            "no response"
    return False, note


class Linter:
    def __init__(self, config, strict=False, check_urls=False):
        self.config = config
        self.tool = config.get("tool", "")
        self.strict = strict
        self.check_urls = check_urls
        self.findings = []
        self.degraded_linkrot = False
        self.pages = []
        # Human-owned namespaces, resolved from the optional para_dir /
        # notes_dir config keys (config.md REQ-625, namespaces REQ-980).
        self.para_prefix = (config.get("para_dir") or "para").strip("/")
        self.notes_prefix = (config.get("notes_dir") or "notes").strip("/")
        # Human-decided glossary namespace (config.md REQ-628,
        # specs/glossary.md): structure-linted by rule 15, exempt from the
        # wiki-only rules.
        self.glossary_prefix = (config.get("glossary_dir")
                                or wikilib.DEFAULT_GLOSSARY_DIR).strip("/")
        # Journal directory (config.md REQ-629): human-owned daily notes,
        # recognized as in-contract by rule 14.
        self.journals_prefix = (config.get("journals_dir")
                                or wikilib.DEFAULT_JOURNALS_DIR).strip("/")

    # -- infrastructure ----------------------------------------------------

    def classify_namespace(self, name):
        """Which namespace a page name belongs to (namespaces REQ-960).

        Returns "wiki", "para", "notes", "glossary", "journals", or
        "outside".
        Matching is case-insensitive so pre-migration Wiki/ corpora keep
        their wiki classification (grandfather floor, schema REQ-580c);
        the uppercase itself is rule 13's business.
        """
        lower = name.lower()
        prefixes = (
            ("wiki", "wiki"),
            ("para", self.para_prefix.lower()),
            ("notes", self.notes_prefix.lower()),
            ("glossary", self.glossary_prefix.lower()),
            ("journals", self.journals_prefix.lower()),
        )
        for namespace, prefix in prefixes:
            if prefix and (lower == prefix or lower.startswith(prefix + "/")):
                return namespace
        return "outside"

    def load_pages(self):
        for entry in wikilib.enumerate_pages(self.config):
            with open(entry["path"], "r", encoding="utf-8") as handle:
                text = handle.read()
            props = wikilib.parse_page_properties(text, self.tool)
            stripped = strip_code(text)
            page = {
                "name": entry["name"],
                "path": entry["path"],
                "text": text,
                "stripped": stripped,
                "props": props,
                "links": wiki_links(stripped),
                "type": props.get("type", ""),
            }
            page["is_hub"] = page["type"] == "hub"
            page["is_system"] = (
                page["name"].lower() in SYSTEM_PAGE_NAMES
                or props.get("access-log") == "true"
                or page["type"] in ("schema", "dashboard")
                # Logseq's built-in sidebar Contents page (REQ-241a, #105):
                # a tool system page, never held to the wiki-only rules.
                or (self.tool == "logseq"
                    and page["name"].lower() == "contents"))
            page["is_archived"] = "archived" in props
            page["is_migrated"] = (
                props.get("schema-spec-version") == SCHEMA_SPEC_VERSION)
            page["ns"] = self.classify_namespace(page["name"])
            self.pages.append(page)

    def add(self, page, req_id, rule, severity, message, fix=None):
        grandfathered = False
        if (not self.strict and not page["is_system"]
                and not page["is_migrated"] and req_id != "REQ-163"):
            if severity == "critical":
                severity, grandfathered = "warning", True
            elif severity == "warning":
                severity, grandfathered = "info", True
        finding = {
            "id": req_id,
            "rule": rule,
            "severity": severity,
            "page": page["name"],
            "message": message,
        }
        if fix:
            finding["fix"] = fix
        if grandfathered:
            finding["grandfathered"] = True
            finding["message"] += (
                " [grandfathered: page has no schema-spec-version:: %s]"
                % SCHEMA_SPEC_VERSION)
        self.findings.append(finding)

    # -- rules -------------------------------------------------------------

    def run(self):
        self.load_pages()
        names = {p["name"] for p in self.pages}
        incoming = {name: 0 for name in names}
        for page in self.pages:
            for target in set(page["links"]):
                if target in names and target != page["name"]:
                    incoming[target] += 1

        hubs = {p["name"]: p for p in self.pages if p["is_hub"]}
        hub_entries = {name: parse_hub_index(p["stripped"])
                       for name, p in hubs.items()}

        for page in self.pages:
            self.check_namespace_hygiene(page)                 # rule 14
            self.check_naming_hygiene(page)                    # rule 13
            if page["ns"] == "glossary":
                # Human-decided glossary: exempt from the wiki-only rules
                # (glossary REQ-1002); rule 15 checks structure only.
                self.check_glossary_hygiene(page)              # rule 15
                continue
            if page["ns"] in ("para", "notes"):
                # Human namespaces: exempt from every wiki-only rule
                # (namespaces REQ-961/966, rule 14 REQ-242). The wiki
                # toolchain never lints or audits their content.
                continue
            self.check_credentials(page)                       # rule 6
            self.check_broken_refs(page, names)                # rule 4
            self.check_format_mixing(page)                     # mixing
            self.check_dates(page)
            if page["is_system"]:
                continue
            self.check_orphan(page, incoming)                  # rule 1
            self.check_properties(page)                        # rule 3
            self.check_provenance(page)                        # provenance
            self.check_empty(page)                             # rule 7
            self.check_crossref_min(page)                      # rule 8
            self.check_canonical_url(page)                     # rule 12

        self.check_hubs(hubs, hub_entries, names)              # rules 5/10/11
        self.check_paper_hubs()                                # rule 16
        return self.findings

    def check_orphan(self, page, incoming):
        if page["is_hub"] or page["is_archived"]:
            return
        if incoming.get(page["name"], 0) == 0:
            hub = self.nearest_hub_name(page["name"])
            self.add(page, "REQ-110", "orphan", "warning",
                     "page has 0 incoming [[links]] from other wiki pages",
                     fix="add [[%s]] to the %s hub page"
                         % (page["name"], hub or "namespace"))

    def check_broken_refs(self, page, names):
        for target in sorted(set(page["links"])):
            if target not in names:
                # Person links legitimately precede their page: ingest
                # always links names (REQ-036a) but creates the person
                # page at the second-source threshold (REQ-024a). Info,
                # not warning, and never a --fix stub (REQ-141a).
                if target.lower().startswith("wiki/people/"):
                    self.add(page, "REQ-141a", "broken-reference", "info",
                             "link target [[%s]] does not exist yet "
                             "(pending person page)" % target,
                             fix="born through ingest when the author "
                                 "recurs (REQ-024a), or request the page "
                                 "at an ingest checkpoint; never a stub")
                    continue
                self.add(page, "REQ-141", "broken-reference", "warning",
                         "link target [[%s]] does not exist on disk" % target,
                         fix="create the page or remove the link "
                             "(--fix creates a stub, REQ-142)")

    def check_properties(self, page):
        ptype = page["type"]
        props = page["props"]
        if not ptype:
            self.add(page, "REQ-132", "missing-properties", "warning",
                     "missing required property 'type'")
            return
        if ptype in AUX_TYPES:
            return
        if ptype not in PAGE_TYPES:
            self.add(page, "REQ-502", "missing-properties", "warning",
                     "unknown type '%s'. Allowed: %s"
                     % (ptype, ", ".join(sorted(PAGE_TYPES))))
            return
        for prop in REQUIRED_PROPS[ptype]:
            if prop not in props or not props[prop]:
                self.add(page, "REQ-132", "missing-properties", "warning",
                         "missing required property '%s' for type '%s'"
                         % (prop, ptype))
        for prop, (allowed, req_id) in ENUMS.items():
            value = props.get(prop)
            if value and value not in allowed:
                self.add(page, req_id, "missing-properties", "warning",
                         "invalid %s '%s'. Allowed: %s"
                         % (prop, value, ", ".join(sorted(allowed))))
        status = props.get("status")
        if status and ptype in STATUS_ENUMS and status not in STATUS_ENUMS[ptype]:
            self.add(page, "REQ-512", "missing-properties", "warning",
                     "invalid status '%s' for type '%s'. Allowed: %s"
                     % (status, ptype,
                        ", ".join(sorted(STATUS_ENUMS[ptype]))))
        if (ptype == "project" and status == "completed"
                and "completed" not in props):
            self.add(page, "REQ-522", "missing-properties", "info",
                     "project is completed but has no completed:: date")

    def check_provenance(self, page):
        props = page["props"]
        if "canonical-url" in props:
            # Deliberate stub (REQ-584): exempt from ingested-page checks,
            # and it must not carry source-file.
            if "source-file" in props:
                self.add(page, "REQ-584", "provenance", "warning",
                         "stub with canonical-url:: must not carry "
                         "source-file::")
            return
        if "source-file" in props:
            if "reliability" not in props:
                self.add(page, "REQ-586", "provenance", "warning",
                         "ingested page (source-file:: present) is missing "
                         "reliability::")
        elif props.get("source") == "ingest":
            self.add(page, "REQ-585", "provenance", "warning",
                     "source:: ingest but no source-file:: (and no "
                     "canonical-url:: stub marker)")

    def check_dates(self, page):
        for prop in DATE_PROPS:
            value = page["props"].get(prop)
            if not value:
                continue
            if not DATE_RE.match(value):
                self.add(page, "REQ-560", "date-format", "warning",
                         "invalid date format '%s' in %s::. Required: "
                         "YYYY-MM-DD (zero-padded)" % (value, prop))
            elif not is_valid_date(value):
                self.add(page, "REQ-563", "date-format", "warning",
                         "'%s' in %s:: is not a real calendar date"
                         % (value, prop))

    def check_credentials(self, page):
        # Scans the FULL text including frontmatter (REQ-162); severity is
        # never floored by grandfather mode.
        labels = [label for pattern, label in CREDENTIAL_PATTERNS
                  if pattern.search(page["text"])]
        if has_base64_credential(page["text"]):
            labels.append("base64-like string (40+ chars)")
        for label in labels:
            self.add(page, "REQ-163", "credential-leak", "critical",
                     "possible credential leak: %s" % label,
                     fix="move the credential to L1 memory; wiki pages "
                         "are git-tracked (no auto-fix)")

    def check_empty(self, page):
        if page["is_hub"]:
            return
        if not content_lines_after_properties(page["text"], self.tool):
            self.add(page, "REQ-171", "empty-page", "warning",
                     "page has properties but no content",
                     fix="fill via /wiki-ingest or delete the page")

    def check_crossref_min(self, page):
        if page["is_hub"]:
            return
        if not page["links"]:
            hub = self.nearest_hub_name(page["name"])
            self.add(page, "REQ-180", "cross-ref-minimum", "warning",
                     "page has fewer than 1 outgoing [[wiki/...]] link",
                     fix="add a link to [[%s]]" % (hub or "the namespace hub"))

    def check_format_mixing(self, page):
        lines = [l for l in page["text"].splitlines() if l.strip()]
        first = lines[0] if lines else ""
        if self.tool == "logseq" and first.strip() == "---":
            self.add(page, "REQ-595", "format-mixing", "warning",
                     "page uses YAML frontmatter but the wiki is configured "
                     "for Logseq (properties must use key:: value)")
        elif self.tool == "obsidian" and "::" in first \
                and wikilib._LOGSEQ_PROP_RE.match(first):
            self.add(page, "REQ-595", "format-mixing", "warning",
                     "page uses Logseq outliner properties but the wiki is "
                     "configured for Obsidian (use YAML frontmatter)")

    def check_canonical_url(self, page):
        url = page["props"].get("canonical-url")
        if not url:
            return
        if not URL_SHAPE_RE.match(url):
            self.add(page, "REQ-221", "link-rot", "warning",
                     "canonical-url:: '%s' is not a valid http(s) URL" % url,
                     fix="fix the URL, ingest a snapshot, or archive the "
                         "stub (no auto-fix, REQ-222)")
            return
        if not self.check_urls:
            self.degraded_linkrot = True
            return
        ok, note = curl_resolves(url)
        if ok is None:
            self.degraded_linkrot = True
            return
        if not ok:
            self.add(page, "REQ-221", "link-rot", "warning",
                     "canonical-url:: target unreachable (%s): %s"
                     % (note, url),
                     fix="update the URL, ingest a snapshot, or archive the "
                         "stub (no auto-fix, REQ-222)")

    def check_naming_hygiene(self, page):
        """Rule 13 (REQ-230/231): structural names are lowercase-hyphen.

        Mechanical/judgment split (schema REQ-580..580b): NON-leaf
        segments are structural by definition, so spaces, uppercase,
        underscores, and en/em dashes (U+2013/U+2014; hyphen U+002D is
        the only separator) are always flagged there (REQ-230). A LEAF
        segment may be a proper noun (wiki/tools/Claude Code,
        notes/literature/@forte2022building), so mechanically it is flagged ONLY
        when it violates the hyphen rule (underscore, en/em dash,
        REQ-231); leaf uppercase and spaces stay a judgment call in the
        wiki-lint skill, which reviews leaf findings and dismisses
        proper-noun leaves (namespaces REQ-976).

        Severity: warning on wiki/ pages; info on para/notes pages,
        whose content is human-owned and exempt from the wiki
        conventions (the shared namespace STRUCTURE is still advisory
        territory, namespaces REQ-961).
        """
        if page["ns"] not in ("wiki", "para", "notes"):
            return
        severity = "warning" if page["ns"] == "wiki" else "info"
        segments = page["name"].split("/")
        structural_bad = []
        for segment in segments[:-1]:
            problems = segment_problems(segment, leaf=False)
            if problems:
                structural_bad.append(
                    "'%s' (%s)" % (segment, ", ".join(problems)))
        if structural_bad:
            self.add(page, "REQ-230", "naming-hygiene", severity,
                     "structural name segment(s) not lowercase with "
                     "hyphen U+002D as the only separator: %s"
                     % "; ".join(structural_bad),
                     fix="rename via the migration converter or by hand; "
                         "no auto-fix (REQ-232)")
        problems = segment_problems(segments[-1], leaf=True)
        if problems:
            self.add(page, "REQ-231", "naming-hygiene", severity,
                     "leaf segment '%s' uses a separator other than the "
                     "hyphen U+002D: %s"
                     % (segments[-1], ", ".join(problems)),
                     fix="rename by hand unless it is a proper noun "
                         "spelled as the world spells it; no auto-fix "
                         "(REQ-232)")

    def is_recognized_root(self, page):
        """Deliberate structural pages outside the content namespaces:
        Schema, Dashboard, Access-Log, Contents, hub pages, and query
        pages (namespaces REQ-962/977, rule 14 REQ-241)."""
        return (page["name"].lower() in ROOT_PAGE_NAMES
                or page["type"] in ("hub", "schema", "dashboard", "query")
                or page["props"].get("access-log") == "true"
                or "#+BEGIN_QUERY" in page["text"])

    def check_namespace_hygiene(self, page):
        """Rule 14 (REQ-240..242): every page lives under wiki/,
        para_dir, notes_dir, or journals, or is a recognized deliberate
        root page; anything else is a stray outside the namespace
        contract (namespaces REQ-960/962)."""
        if page["ns"] != "outside":
            return
        if self.is_recognized_root(page):
            return
        self.add(page, "REQ-240", "namespace-hygiene", "warning",
                 "page is outside wiki/, %s/, %s/, %s/, journals, and the "
                 "recognized root pages (namespace contract)"
                 % (self.para_prefix, self.notes_prefix,
                    self.glossary_prefix),
                 fix="ingest the content into wiki/, move it into %s/ or "
                     "%s/ by hand, or delete it; no auto-fix (REQ-242)"
                     % (self.para_prefix, self.notes_prefix))

    GLOSSARY_RULE_ENUM = ("keep-en", "translate", "context")
    GLOSSARY_HEADER = ("EN", "DE", "Rule", "Note")

    def check_glossary_hygiene(self, page):
        """Rule 15 (REQ-250..253): structure of glossary/ pages
        (specs/glossary.md). Table shape and the rule enum are mechanical;
        the decisions themselves are human and never judged. No auto-fix."""
        name = page["name"]
        rel = name[len(self.glossary_prefix):].strip("/")
        segments = [s for s in rel.split("/") if s] if rel else []
        is_staging = bool(segments) and segments[0].lower() == "imported"

        # REQ-252: staging pages carry source:: and status::.
        if is_staging and len(segments) >= 2:
            for prop in ("source", "status"):
                if prop not in page["props"]:
                    self.add(page, "REQ-252", "glossary-hygiene", "warning",
                             "staging page is missing %s:: "
                             "(specs/glossary.md REQ-1010)" % prop,
                             fix="add the property by hand; imports arrive "
                                 "with source:: and status:: unreviewed")

        # REQ-253: term pages carry rule:: with an enum value.
        if len(segments) == 2 and not is_staging:
            rule = page["props"].get("rule", "")
            if rule not in self.GLOSSARY_RULE_ENUM:
                detail = ("missing" if not rule
                          else "invalid ('%s')" % rule)
                self.add(page, "REQ-253", "glossary-hygiene", "warning",
                         "term page rule:: is %s; enum: %s"
                         % (detail, " | ".join(self.GLOSSARY_RULE_ENUM)),
                         fix="record the decision on the page; no auto-fix "
                             "(the rule is a human call, REQ-1000)")

        # REQ-250/251: terms-table shape and Rule cells.
        in_terms, header_seen = False, False
        for number, raw in enumerate(page["stripped"].splitlines(), 1):
            line = raw.strip().lstrip("-").strip()
            if line.startswith("#") and line.lstrip("#").strip():
                in_terms = line.lstrip("#").strip().lower() == "terms"
                header_seen = False
                continue
            if not in_terms or not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= {"-", " ", ":"} for c in cells):
                continue  # separator row
            if not header_seen:
                header_seen = True
                if tuple(cells) != self.GLOSSARY_HEADER:
                    self.add(page, "REQ-250", "glossary-hygiene", "warning",
                             "terms-table header is '| %s |'; canon is "
                             "'| EN | DE | Rule | Note |' "
                             "(specs/glossary.md REQ-1004)"
                             % " | ".join(cells))
                continue
            if len(cells) != len(self.GLOSSARY_HEADER):
                self.add(page, "REQ-250", "glossary-hygiene", "warning",
                         "terms-table row (line %d) has %d column(s); "
                         "the canon table has 4" % (number, len(cells)))
                continue
            rule = cells[2]
            if rule and rule not in self.GLOSSARY_RULE_ENUM:
                self.add(page, "REQ-251", "glossary-hygiene", "warning",
                         "invalid Rule '%s' (line %d); enum: %s"
                         % (rule, number,
                            " | ".join(self.GLOSSARY_RULE_ENUM)))
            elif not rule and not is_staging:
                self.add(page, "REQ-251", "glossary-hygiene", "warning",
                         "undecided row (line %d): empty Rule belongs on a "
                         "%s/imported/ staging page, not a domain page"
                         % (number, self.glossary_prefix))

    def nearest_hub_name(self, page_name):
        parts = page_name.split("/")
        hubs = {p["name"] for p in self.pages if p["is_hub"]}
        for depth in range(len(parts) - 1, 0, -1):
            candidate = "/".join(parts[:depth])
            if candidate in hubs:
                return candidate
        return None

    PAPER_HUB_SECTIONS = ("Manuscript", "Literature drawn on", "Data",
                          "Open questions", "Draft decisions", "AI use")
    AGENT_LOG_HEADER = ["Date", "Skill", "Model", "Sources touched",
                        "Pages written", "Human confirmations"]

    def check_paper_hubs(self):
        """Rule 16 (REQ-260..262): structure of wiki/papers/ hub pages
        (specs/paper.md). The type expectation, section skeleton, and
        child reachability are mechanical; section content and which
        pages a paper draws on are editorial. No auto-fix: sections and
        links are writing decisions. Required-property presence on a
        paper-hub page is rule 3's job (REQ-132 via REQUIRED_PROPS)."""
        papers = [p for p in self.pages
                  if p["name"].startswith("wiki/papers/")]
        hubs = {p["name"]: p for p in papers
                if len(p["name"].split("/")) == 3}
        for page in hubs.values():
            if page["type"] != "paper-hub":
                self.add(page, "REQ-260", "paper-hub-hygiene", "warning",
                         "page at wiki/papers/<slug> has type:: '%s', "
                         "expected 'paper-hub' (specs/paper.md REQ-1501)"
                         % (page["type"] or ""),
                         fix="set type:: paper-hub, or move the page "
                             "under a paper's namespace")
                continue
            found = set()
            for raw in page["stripped"].splitlines():
                line = raw.strip().lstrip("-").strip()
                if line.startswith("#") and line.lstrip("#").strip():
                    found.add(line.lstrip("#").strip().lower())
            for section in self.PAPER_HUB_SECTIONS:
                if section.lower() not in found:
                    self.add(page, "REQ-261", "paper-hub-hygiene",
                             "warning",
                             "hub is missing the '%s' section "
                             "(specs/paper.md REQ-1502)" % section,
                             fix="add the section heading; content is "
                                 "editorial, no auto-fix")
        for page in papers:
            parts = page["name"].split("/")
            if len(parts) < 4:
                continue
            hub_name = "/".join(parts[:3])
            hub = hubs.get(hub_name)
            if hub is None:
                self.add(page, "REQ-260", "paper-hub-hygiene", "warning",
                         "no hub page %s exists for this paper child "
                         "(specs/paper.md REQ-1500)" % hub_name,
                         fix="scaffold the hub with /wiki-paper new")
                continue
            if page["name"] not in set(hub["links"]):
                self.add(hub, "REQ-262", "paper-hub-hygiene", "warning",
                         "child page [[%s]] is not linked from the hub "
                         "and would drop out of the export walk "
                         "(specs/paper.md REQ-1505)" % page["name"],
                         fix="link the child from the matching hub "
                             "section; no auto-fix (linking is "
                             "editorial)")
            if parts[3] == "agent-log" and len(parts) == 4:
                self.check_agent_log(page)

    def check_agent_log(self, page):
        """REQ-263: the agent-log's first table carries the canonical
        header and consistent column counts (specs/paper.md REQ-1514).
        Row content is never judged; no auto-fix (the log is an
        append-only transparency record)."""
        rows = []
        for raw in page["stripped"].splitlines():
            line = raw.strip().lstrip("-").strip()
            if line.startswith("|"):
                rows.append(line)
            elif rows:
                break
        if not rows:
            return
        cells = [c.strip() for c in rows[0].strip("|").split("|")]
        if cells != self.AGENT_LOG_HEADER:
            self.add(page, "REQ-263", "paper-hub-hygiene", "warning",
                     "agent-log table header is off-canon "
                     "(specs/paper.md REQ-1514)",
                     fix="use | %s |; no auto-fix"
                         % " | ".join(self.AGENT_LOG_HEADER))
            return
        for line in rows[1:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= {"-", " ", ":"} for c in cells):
                continue
            if len(cells) != len(self.AGENT_LOG_HEADER):
                self.add(page, "REQ-263", "paper-hub-hygiene", "warning",
                         "agent-log row has %d columns, header has %d "
                         "(specs/paper.md REQ-1514)"
                         % (len(cells), len(self.AGENT_LOG_HEADER)),
                         fix="align the row with the header; no "
                             "auto-fix")

    def check_hubs(self, hubs, hub_entries, names):
        # Rule 10a: orphaned routing lines + Rule 10c: empty descriptions.
        for hub_name, entries in hub_entries.items():
            hub = hubs[hub_name]
            for section, target, desc in entries:
                if target not in names:
                    self.add(hub, "REQ-193", "index-drift", "warning",
                             "routing line targets [[%s]], which does not "
                             "exist on disk" % target,
                             fix="remove the orphaned routing line "
                                 "(--fix, REQ-196)")
                if section == "index" and not desc:
                    self.add(hub, "REQ-195", "index-drift", "warning",
                             "routing line for [[%s]] has no description "
                             "after the -- separator" % target)
        # Rules 5, 10b, 11: per-child checks against the nearest hub.
        for page in self.pages:
            if page["is_hub"] or page["is_system"] or page["ns"] != "wiki":
                continue
            hub_name = self.nearest_hub_name(page["name"])
            if not hub_name:
                continue
            hub = hubs[hub_name]
            entries = hub_entries[hub_name]
            in_index = any(s == "index" and t == page["name"]
                           for s, t, _ in entries)
            in_archive = any(s == "archive" and t == page["name"]
                             for s, t, _ in entries)
            if page["is_archived"]:
                if in_index:
                    self.add(page, "REQ-197", "archived-in-live-index",
                             "warning",
                             "archived page still has its routing line in "
                             "the %s hub ### Index" % hub_name,
                             fix="move the routing line to ### Archive; "
                                 "never rename or move the page file "
                                 "(--fix, REQ-198)")
                continue
            if f"[[{page['name']}]]" not in hub["stripped"]:
                self.add(hub, "REQ-151", "hub-completeness", "warning",
                         "hub is missing child [[%s]]" % page["name"],
                         fix="append the child link (--fix, REQ-152)")
            if not in_index and not in_archive:
                self.add(page, "REQ-194", "index-drift", "warning",
                         "active page has no routing line in the %s hub "
                         "### Index (unroutable, only findable via L3 grep)"
                         % hub_name,
                         fix="backfill a routing line (--fix, REQ-196)")


def build_report(linter):
    findings = sorted(
        linter.findings,
        key=lambda f: (SEVERITY_RANK[f["severity"]], f["page"], f["id"]))
    totals = {"critical": 0, "warning": 0, "info": 0}
    by_rule = {}
    flagged_pages = set()
    for finding in findings:
        totals[finding["severity"]] += 1
        by_rule[finding["rule"]] = by_rule.get(finding["rule"], 0) + 1
        flagged_pages.add(finding["page"])
    return {
        "schema_spec_version": SCHEMA_SPEC_VERSION,
        "tool": linter.tool,
        "strict": linter.strict,
        "check_urls": linter.check_urls,
        "linkrot_degraded": linter.degraded_linkrot,
        "pages_scanned": len(linter.pages),
        "healthy_pages": len(linter.pages) - len(flagged_pages),
        "totals": totals,
        "by_rule": by_rule,
        "findings": findings,
    }


def print_report(report):
    print("lint: scanned %d pages (tool: %s%s)"
          % (report["pages_scanned"], report["tool"],
             ", strict" if report["strict"] else ""))
    if report["linkrot_degraded"]:
        print("link-rot check degraded: URL-shape only "
              "(pass --check-urls for HTTP verification)")
    for severity in ("critical", "warning", "info"):
        group = [f for f in report["findings"]
                 if f["severity"] == severity]
        if not group:
            continue
        print("\n%s (%d)" % (severity.upper(), len(group)))
        for finding in group:
            print("  [%s] %s - %s" % (finding["id"], finding["page"],
                                      finding["message"]))
            if "fix" in finding:
                print("        fix: %s" % finding["fix"])
    totals = report["totals"]
    print("\ntotals: %d pages, %d healthy | %d critical, %d warning, %d info"
          % (report["pages_scanned"], report["healthy_pages"],
             totals["critical"], totals["warning"], totals["info"]))


def main():
    parser = argparse.ArgumentParser(
        description="Mechanical wiki linter (report-only; fixes are applied "
                    "agent-side by the wiki-lint skill).")
    parser.add_argument("--config", default=None,
                        help="path to llm-wiki.yml (default: discover)")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true",
                        help="disable the grandfather severity floor for "
                             "pages without the current schema-spec-version")
    parser.add_argument("--check-urls", action="store_true",
                        help="verify canonical-url targets over HTTP with "
                             "curl (default: URL-shape check only)")
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

    linter = Linter(config, strict=args.strict, check_urls=args.check_urls)
    linter.run()
    report = build_report(linter)

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
