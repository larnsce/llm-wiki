#!/usr/bin/env python3
"""migrate_wiki.py - one-time, idempotent corpus converter (two passes).

Default pass: upgrades v1-authored wiki pages (pages without
`schema-spec-version::`) to the v2 schema contract
(templates/*/Schema.md, openspec/specs/schema.md) for both tool modes.

`--lowercase` pass (specs/schema.md REQ-580c): renames the pre-migration
`Wiki/` corpus to `wiki/`. Structural segments are lowercased; proper-noun
leaves keep their natural casing (REQ-580b). The leaf heuristic, in order:

1. hub pages and the system leaves (schema, dashboard, access-log) are
   structural: lowercase
2. a leaf that matches (case-insensitively) a configured namespace or a
   segment of an existing hub name is structural: lowercase
3. an entity page names a person/tool/client/...: proper-noun leaf, kept
4. an already-lowercase leaf is conformant: kept
5. anything else with uppercase letters is AMBIGUOUS: kept unchanged and
   reported as a manual follow-up, never guessed

The pass renames files (`Wiki___*.md` -> `wiki___*.md`) and directories
(`Wiki/` -> `wiki/`), rewrites `[[Wiki/...]]` links (which covers the hub
`### Index` / `### Archive` routing lines), lowercases `namespace::`
property values and the `namespaces:` values in llm-wiki.yml, and converts
Roam task markers (`{{[[TODO]]}}` -> `TODO`, plus the
DOING/DONE/NOW/LATER/WAITING/CANCELED variants). The dry-run report
includes the full rename list plus the broken-link and orphan counts after
a simulated rename (the kill criterion for the corpus flip).

Both passes are DRY-RUN BY DEFAULT: without --apply nothing is written;
the report lists every mechanical change the converter would make plus the
manual follow-ups it will not make for you.

Mechanical changes (append-only discipline: existing content lines are
never deleted or rewritten; only page properties are added or normalized):

- add `schema-spec-version:: 2.0.0` (this ends grandfather mode for the
  page: lint.py then holds it to the full rule set)
- normalize property formatting: `key::value` -> `key:: value` spacing,
  known property keys lowercased (`Updated::` -> `updated::`)
- normalize date property values to YYYY-MM-DD where parseable
  (`03/15/2024` -> `2024-03-15`); ambiguous or unparseable dates become
  manual follow-ups, never guesses
- normalize enum values that are a case-variant of a valid member
  (`Confidence:: Medium` -> `confidence:: medium`)
- missing REQUIRED properties are NEVER invented (no fabricated
  confidence or reliability ratings); instead ONE `needs-review::` marker
  property lists what is missing for a human to fill in
- Schema page: append-only v2 upgrade; template sections missing from the
  vault's Schema page are appended verbatim (placeholders substituted);
  if the page diverges too far from the template it is reported and
  skipped, never rewritten

Everything non-mechanical (prose citations, Logseq lines without the block
prefix, format mixing, unknown types) is reported as a manual follow-up,
never edited.

--apply requires a git-clean working tree in the vault (checked via
`git status --porcelain`) and refuses otherwise. Idempotent: a second run
reports zero changes.

Stdlib only. Imports wikilib (config discovery, page enumeration,
property parsing) and lint (the canonical schema constants:
SCHEMA_SPEC_VERSION, REQUIRED_PROPS, ENUMS, DATE_PROPS), so the converter
can never drift from what the linter enforces.

Exit codes: 0 = nothing to migrate and no follow-ups, 1 = changes
pending/applied or manual follow-ups remain, 2 = critical (no config,
dirty tree on --apply, unknown --page).
"""

import argparse
import datetime
import os
import re
import subprocess
import sys

import lint as lintmod
import wikilib

SCHEMA_SPEC_VERSION = lintmod.SCHEMA_SPEC_VERSION
# Matched case-insensitively: pre-migration corpora still name it
# Wiki/Schema until the --lowercase pass runs (REQ-580c).
SCHEMA_PAGE_NAME = "wiki/schema"

# Property keys the converter is allowed to case-normalize.
KNOWN_KEYS = set()
for _props in lintmod.REQUIRED_PROPS.values():
    KNOWN_KEYS.update(_props)
KNOWN_KEYS.update(lintmod.ENUMS)
KNOWN_KEYS.update(lintmod.DATE_PROPS)
KNOWN_KEYS.update({
    "status", "namespace", "applies-to", "archived", "source-file",
    "canonical-url", "s2-metrics", "last-reviewed", "schema-spec-version",
    "access-log", "wiki-version", "last-updated", "maintained-by",
    "needs-review",
})

# Enum sets for case normalization (value fixed only when its lowercase
# form is already a valid member; nothing is ever invented).
ENUM_SETS = {prop: allowed for prop, (allowed, _req) in lintmod.ENUMS.items()}
ENUM_SETS["type"] = lintmod.PAGE_TYPES | lintmod.AUX_TYPES
ENUM_SETS["status"] = set()
for _allowed in lintmod.STATUS_ENUMS.values():
    ENUM_SETS["status"].update(_allowed)

DATE_KEYS = set(lintmod.DATE_PROPS) | {"last-updated"}

LOGSEQ_PROP_LINE_RE = re.compile(
    r"^(?P<prefix>\s*(?:-\s+)?)"
    r"(?P<key>[A-Za-z][A-Za-z0-9_-]*)\s*::\s*(?P<value>.*)$")
FRONTMATTER_LINE_RE = re.compile(
    r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*)\s*:\s*(?P<value>.*)$")
SENTINEL_START_RE = re.compile(
    r"^\s*(?:-\s+)?<!--\s*([A-Za-z0-9_:-]+)\s+start\s*-->")

MONTH_DATE_FORMATS = (
    "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y",
    "%d %B %Y", "%d %b %Y", "%d. %B %Y", "%Y %b %d",
)

CITATION_RES = (
    re.compile(r"\bet al\."),
    re.compile(r"\([A-Z][A-Za-z'-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z'-]+)?"
               r",?\s+(?:19|20)\d{2}[a-z]?\)"),
)


# ---------------------------------------------------------------------------
# Value normalization
# ---------------------------------------------------------------------------

def _build_date(year, month, day):
    try:
        return datetime.date(int(year), int(month), int(day)).isoformat(), None
    except ValueError:
        return None, "not a real calendar date"


def normalize_date(value):
    """Return (normalized YYYY-MM-DD, None) or (None, reason).

    Only unambiguous inputs are converted. `03/04/2024` (both fields could
    be the month) is reported for manual review, not guessed.
    """
    v = value.strip()
    if lintmod.DATE_RE.match(v):
        return v, None
    match = re.match(r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$", v)
    if match:
        return _build_date(match.group(1), match.group(2), match.group(3))
    match = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$", v)
    if match:
        first, second = int(match.group(1)), int(match.group(2))
        year = match.group(3)
        if first > 12 >= second:
            month, day = second, first
        elif second > 12 >= first:
            month, day = first, second
        elif first == second:
            month = day = first
        else:
            return None, "ambiguous day/month order"
        return _build_date(year, month, day)
    for fmt in MONTH_DATE_FORMATS:
        try:
            return datetime.datetime.strptime(v, fmt).date().isoformat(), None
        except ValueError:
            continue
    return None, "unparseable date"


class Migration:
    """Accumulates the change report for one page."""

    def __init__(self, page):
        self.page = page
        self.changes = []
        self.manual = []
        self.new_text = None

    def change(self, kind, detail):
        self.changes.append({"kind": kind, "detail": detail})

    def note(self, detail):
        self.manual.append(detail)

    def as_dict(self):
        return {
            "page": self.page["name"],
            "path": self.page["path"],
            "changes": self.changes,
            "manual": self.manual,
        }


def normalize_key(key, mig):
    if key != key.lower() and key.lower() in KNOWN_KEYS:
        mig.change("normalize-key",
                   "property key '%s' -> '%s'" % (key, key.lower()))
        return key.lower()
    return key


def normalize_scalar(key, scalar, mig):
    """Normalize one property value (already unquoted). Never invents."""
    if not scalar:
        return scalar
    if key == "schema-spec-version" and scalar != SCHEMA_SPEC_VERSION:
        mig.change("set-property",
                   "schema-spec-version '%s' -> '%s'"
                   % (scalar, SCHEMA_SPEC_VERSION))
        return SCHEMA_SPEC_VERSION
    if key in ENUM_SETS:
        allowed = ENUM_SETS[key]
        if scalar not in allowed and scalar.lower() in allowed:
            mig.change("normalize-value",
                       "%s '%s' -> '%s'" % (key, scalar, scalar.lower()))
            return scalar.lower()
    if key in DATE_KEYS:
        normalized, reason = normalize_date(scalar)
        if normalized is not None:
            if normalized != scalar:
                mig.change("normalize-date",
                           "%s '%s' -> '%s'" % (key, scalar, normalized))
            return normalized
        mig.note("date value '%s' in %s is %s; fix by hand (YYYY-MM-DD)"
                 % (scalar, key, reason))
    return scalar


def compute_additions(props, is_system, mig):
    """Additions for a page: version stamp + one needs-review marker."""
    additions = []
    if not is_system:
        ptype = props.get("type", "")
        gaps = []
        if not ptype:
            gaps.append("type (entity | project | knowledge | feedback "
                        "| hub)")
        elif ptype in lintmod.REQUIRED_PROPS:
            gaps.extend(p for p in lintmod.REQUIRED_PROPS[ptype]
                        if not props.get(p))
        elif ptype not in lintmod.PAGE_TYPES | lintmod.AUX_TYPES:
            mig.note("unknown type '%s'; set one of: %s by hand"
                     % (ptype, ", ".join(sorted(lintmod.PAGE_TYPES))))
        if gaps and not props.get("needs-review"):
            value = "missing required properties: " + ", ".join(gaps)
            additions.append(("needs-review", value))
            mig.change("add-property", "needs-review:: %s" % value)
    if not props.get("schema-spec-version"):
        additions.insert(0, ("schema-spec-version", SCHEMA_SPEC_VERSION))
        mig.change("add-property",
                   "schema-spec-version:: %s" % SCHEMA_SPEC_VERSION)
    return additions


# ---------------------------------------------------------------------------
# Per-tool property-block rewriting (append-only: content untouched)
# ---------------------------------------------------------------------------

def migrate_logseq_text(text, is_system, mig):
    lines = text.split("\n")
    first_nonblank = next((l for l in lines if l.strip()), "")
    if first_nonblank.strip() == "---":
        mig.note("format mixing (REQ-595): YAML frontmatter in a Logseq "
                 "wiki; convert this page by hand")
        return text

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    end = start
    while (end < len(lines) and lines[end].strip()
           and LOGSEQ_PROP_LINE_RE.match(lines[end])):
        end += 1

    props = {}
    prefix_style = "- "
    for index in range(start, end):
        match = LOGSEQ_PROP_LINE_RE.match(lines[index])
        prefix = match.group("prefix")
        key = match.group("key")
        value = match.group("value").strip()
        if index == start:
            prefix_style = "- " if prefix.strip() == "-" else ""
        nkey = normalize_key(key, mig)
        nvalue = normalize_scalar(nkey, value, mig)
        rebuilt = "%s%s:: %s" % (prefix, nkey, nvalue)
        if rebuilt != lines[index]:
            if nkey == key and nvalue == value:
                mig.change("normalize-spacing",
                           "property line '%s' reformatted as "
                           "'%s:: %s'" % (lines[index].strip(), nkey, nvalue))
            lines[index] = rebuilt
        props[nkey] = nvalue

    additions = compute_additions(props, is_system, mig)
    new_lines = ["%s%s:: %s" % (prefix_style, key, value)
                 for key, value in additions]
    insert_at = end if end > start else start
    lines[insert_at:insert_at] = new_lines
    return "\n".join(lines)


def _quote_aware(raw_value):
    """Split a frontmatter value into (scalar, quote character or '')."""
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1], value[0]
    return value, ""


def migrate_obsidian_text(text, is_system, mig):
    lines = text.split("\n")
    first_nonblank = next((l for l in lines if l.strip()), "")
    if (first_nonblank.strip() != "---"
            and LOGSEQ_PROP_LINE_RE.match(first_nonblank)
            and "::" in first_nonblank):
        mig.note("format mixing (REQ-595): Logseq outliner properties in "
                 "an Obsidian wiki; convert this page by hand")
        return text

    props = {}
    if lines and lines[0].strip() == "---":
        close = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                close = index
                break
        if close is None:
            mig.note("unterminated YAML frontmatter; fix by hand")
            return text
        for index in range(1, close):
            match = FRONTMATTER_LINE_RE.match(lines[index])
            if not match:
                continue
            key = match.group("key")
            scalar, quote = _quote_aware(match.group("value"))
            nkey = normalize_key(key, mig)
            nvalue = normalize_scalar(nkey, scalar, mig)
            rendered = "%s%s%s" % (quote, nvalue, quote) if quote else nvalue
            rebuilt = ("%s: %s" % (nkey, rendered)).rstrip()
            if rebuilt != lines[index]:
                if nkey == key and nvalue == scalar:
                    mig.change("normalize-spacing",
                               "property line '%s' reformatted as '%s'"
                               % (lines[index].strip(), rebuilt))
                lines[index] = rebuilt
            props[nkey] = nvalue
        additions = compute_additions(props, is_system, mig)
        new_lines = ["%s: \"%s\"" % (key, value) for key, value in additions]
        lines[close:close] = new_lines
        return "\n".join(lines)

    additions = compute_additions(props, is_system, mig)
    if not additions:
        return text
    block = ["---"]
    block.extend("%s: \"%s\"" % (key, value) for key, value in additions)
    block.extend(["---", ""])
    return "\n".join(block + lines)


# ---------------------------------------------------------------------------
# Body checks (report-only, never edited)
# ---------------------------------------------------------------------------

def report_body_followups(text, tool, mig):
    stripped = lintmod.strip_code(text)
    citation_lines = 0
    for line in stripped.splitlines():
        if any(pattern.search(line) for pattern in CITATION_RES):
            citation_lines += 1
    if citation_lines:
        mig.note("prose citations detected on %d line(s); restructure "
                 "into cited claims by hand (openspec/specs/citations.md)"
                 % citation_lines)
    if tool == "logseq":
        unprefixed = 0
        in_fence = False
        past_props = False
        for line in text.splitlines():
            if lintmod.FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence or not line.strip():
                continue
            if not past_props and LOGSEQ_PROP_LINE_RE.match(line):
                continue
            past_props = True
            if not line.startswith(("-", " ", "\t")):
                unprefixed += 1
        if unprefixed:
            mig.note("%d content line(s) lack the Logseq '- ' block prefix "
                     "(REQ-590); restructure by hand" % unprefixed)


# ---------------------------------------------------------------------------
# Schema page: append-only v2 upgrade
# ---------------------------------------------------------------------------

def _h2_re(tool):
    if tool == "logseq":
        return re.compile(r"^-\s+##\s+(.+?)\s*$")
    return re.compile(r"^##\s+(.+?)\s*$")


def split_template_chunks(text, tool):
    """Ordered (key, lines) chunks: sentinel regions and top-level H2s."""
    lines = text.split("\n")
    h2_re = _h2_re(tool)
    chunks = []
    key = "head"
    current = []

    def flush():
        if current:
            chunks.append((key, list(current)))
        del current[:]

    index = 0
    while index < len(lines):
        line = lines[index]
        sentinel = SENTINEL_START_RE.match(line)
        if sentinel:
            flush()
            name = sentinel.group(1)
            end_re = re.compile(r"^\s*(?:-\s+)?<!--\s*%s\s+end\s*-->"
                                % re.escape(name))
            block = [line]
            index += 1
            while index < len(lines):
                block.append(lines[index])
                if end_re.match(lines[index]):
                    index += 1
                    break
                index += 1
            chunks.append(("sentinel:" + name, block))
            key = "head"
            continue
        heading = h2_re.match(line)
        if heading:
            flush()
            key = "h2:" + heading.group(1).strip().lower()
        current.append(line)
        index += 1
    flush()
    return chunks


def page_section_keys(text, tool):
    """All sentinel names and H2 headings present anywhere in a page."""
    keys = set()
    h2_re = _h2_re(tool)
    for line in text.split("\n"):
        sentinel = SENTINEL_START_RE.match(line)
        if sentinel:
            keys.add("sentinel:" + sentinel.group(1))
            continue
        heading = h2_re.match(line)
        if heading:
            keys.add("h2:" + heading.group(1).strip().lower())
    return keys


def upgrade_schema_text(text, tool, template_text, namespaces, today, mig):
    ns_list = ", ".join("wiki/%s" % ns.lower() for ns in namespaces)
    template = template_text.replace("{{NAMESPACES}}", ns_list)
    template = template.replace("{{DATE}}", today)

    template_chunks = [(key, block)
                       for key, block in split_template_chunks(template, tool)
                       if key != "head"]
    vault_keys = page_section_keys(text, tool)
    matched = sum(1 for key, _ in template_chunks if key in vault_keys)
    if matched * 2 < len(template_chunks):
        mig.note("Schema page diverges too far from the v2 template "
                 "(%d/%d template sections recognized); upgrade it by hand "
                 "per the wiki-setup skill, Phase 5"
                 % (matched, len(template_chunks)))
        return text, False

    # Property normalization + version stamp on the recognized page.
    text = (migrate_logseq_text(text, False, mig) if tool == "logseq"
            else migrate_obsidian_text(text, False, mig))

    additions = []
    for key, block in template_chunks:
        if key in vault_keys:
            continue
        if key.startswith("sentinel:"):
            inner = page_section_keys("\n".join(block), tool) - {key}
            overlap = sorted(k for k in inner if k in vault_keys)
            if overlap:
                mig.note("Schema page already has section(s) %s but lacks "
                         "the %s markers; reconcile by hand"
                         % (", ".join(overlap), key.split(":", 1)[1]))
                continue
        additions.append((key, block))

    if not additions:
        return text, True

    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    for key, block in additions:
        trimmed = list(block)
        while trimmed and not trimmed[-1].strip():
            trimmed.pop()
        while trimmed and not trimmed[0].strip():
            trimmed.pop(0)
        if tool == "obsidian":
            lines.append("")
        lines.extend(trimmed)
        mig.change("schema-append",
                   "appended template section '%s'" % key.split(":", 1)[1])
    lines.append("")
    return "\n".join(lines), True


# ---------------------------------------------------------------------------
# Lowercase rename pass (REQ-580c): Wiki/ -> wiki/
# ---------------------------------------------------------------------------

ROAM_MARKER_RE = re.compile(
    r"\{\{\[\[(TODO|DOING|DONE|NOW|LATER|WAITING|CANCELED|CANCELLED)\]\]\}\}")

# Leaves of the recognized system pages: structural workflow pages, not
# proper nouns, so the rename lowercases them (wiki/schema, wiki/dashboard,
# wiki/reference/access-log).
SYSTEM_LEAVES = {"schema", "dashboard", "access-log"}


def _leaf_new_case(leaf, page_type, structural):
    """Apply the documented leaf heuristic. Returns (new_leaf, ambiguous)."""
    low = leaf.lower()
    if low == leaf:
        return leaf, False
    if page_type == "hub" or low in SYSTEM_LEAVES or low in structural:
        return low, False
    if page_type == "entity":
        return leaf, False  # proper-noun leaf (REQ-580b)
    return leaf, True  # ambiguous: kept, reported as a manual follow-up


def lowercase_name(name, page_type, structural):
    """New page name under REQ-580. Returns (new_name, ambiguous_leaf)."""
    segments = name.split("/")
    head = [seg.lower() for seg in segments[:-1]]
    leaf, ambiguous = _leaf_new_case(segments[-1], page_type, structural)
    return "/".join(head + [leaf]), ambiguous


def structural_segments(pages, namespaces):
    """Lowercase segment vocabulary: config namespaces + hub-name segments."""
    segments = {"wiki"}
    segments.update(ns.lower() for ns in namespaces)
    for page in pages:
        if page.get("type") == "hub":
            segments.update(s.lower() for s in page["name"].split("/"))
    return segments


def new_path_for(page, new_name, tool, root):
    if tool == "logseq":
        return os.path.join(root, new_name.replace("/", "___") + ".md")
    if os.path.basename(page["path"]) == "_index.md":
        return os.path.join(root, new_name.replace("/", os.sep), "_index.md")
    return os.path.join(root, new_name.replace("/", os.sep) + ".md")


def rewrite_wiki_links(text, rename_map, structural, counter):
    """Rewrite [[Wiki/...]] targets (covers hub routing lines too)."""

    def repl(match):
        raw = match.group(1)
        target, sep, alias = raw.partition("|")
        stripped = target.strip()
        new = rename_map.get(stripped)
        if new is None and stripped.lower().startswith("wiki/"):
            candidate, _ambiguous = lowercase_name(stripped, None, structural)
            if candidate != stripped:
                new = candidate
        if new is None or new == stripped:
            return match.group(0)
        counter["links"] += 1
        return "[[%s%s%s]]" % (new, sep, alias)

    return lintmod.WIKI_LINK_RE.sub(repl, text)


def rewrite_namespace_property(text, tool, counter):
    """Lowercase the namespace:: / namespace: property value (structural)."""
    lines = text.split("\n")
    if tool == "logseq":
        index = 0
        while index < len(lines) and not lines[index].strip():
            index += 1
        while index < len(lines):
            match = LOGSEQ_PROP_LINE_RE.match(lines[index])
            if not match or not lines[index].strip():
                break
            if match.group("key") == "namespace":
                value = match.group("value").strip()
                if value != value.lower():
                    lines[index] = "%snamespace:: %s" % (
                        match.group("prefix"), value.lower())
                    counter["namespace_props"] += 1
            index += 1
        return "\n".join(lines)

    if not lines or lines[0].strip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            break
        match = FRONTMATTER_LINE_RE.match(lines[index])
        if match and match.group("key") == "namespace":
            scalar, quote = _quote_aware(match.group("value"))
            if scalar != scalar.lower():
                rendered = ("%s%s%s" % (quote, scalar.lower(), quote)
                            if quote else scalar.lower())
                lines[index] = "namespace: %s" % rendered
                counter["namespace_props"] += 1
    return "\n".join(lines)


def convert_roam_markers(text, counter):
    def repl(match):
        counter["roam"] += 1
        return match.group(1)

    return ROAM_MARKER_RE.sub(repl, text)


def rewrite_config_namespaces(config_text):
    """Lowercase the namespaces: list values. Returns (new_text, changes)."""
    lines = config_text.split("\n")
    changes = []
    in_namespaces = False
    for index, line in enumerate(lines):
        key_match = wikilib._TOP_KEY_RE.match(line)
        if key_match:
            in_namespaces = (key_match.group(1) == "namespaces"
                             and not key_match.group(2).strip())
            continue
        if not in_namespaces:
            continue
        item_match = wikilib._LIST_ITEM_RE.match(line)
        if item_match:
            value = item_match.group(1)
            if value != value.lower():
                lines[index] = line[:item_match.start(1)] + value.lower()
                changes.append("namespaces value '%s' -> '%s'"
                               % (value, value.lower()))
    return "\n".join(lines), changes


def _git_mv(git_root, src, dst):
    try:
        proc = subprocess.run(
            ["git", "-C", git_root, "mv", src, dst],
            capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _rename_path(src, dst, git_root=None):
    """Rename src to dst, git-aware and safe for case-only renames.

    Always a two-step move through a temp sibling name: a direct case-only
    rename fails for directories (git mv reports 'Invalid argument' on
    case-insensitive filesystems such as macOS APFS). `git mv` is used
    when the vault is a git repository so the INDEX records the new
    casing; a plain os.rename would leave the old casing in git, which a
    fresh clone on a case-sensitive system would then restore. Falls back
    to os.rename when git mv is unavailable.
    """
    if src == dst:
        return
    parent = os.path.dirname(dst)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    tmp = src + ".lcmv-tmp"
    if git_root:
        if _git_mv(git_root, src, tmp):
            if _git_mv(git_root, tmp, dst):
                return
            os.rename(tmp, dst)
            return
    os.rename(src, tmp)
    os.rename(tmp, dst)


def _apply_renames(renamed, tool, root, git_root):
    """Execute the file/directory renames for the accepted rename set."""
    if tool == "logseq":
        for entry in renamed:
            _rename_path(entry["path"], entry["new_path"], git_root)
        return

    # Obsidian: rename directories first (deepest first; all structural),
    # then file leaves. Case-only directory renames need the git-aware move.
    dirs = set()
    for entry in renamed:
        rel_dir = os.path.relpath(os.path.dirname(entry["path"]), root)
        if rel_dir == ".":
            continue
        parts = rel_dir.split(os.sep)
        for depth in range(1, len(parts) + 1):
            prefix = parts[:depth]
            if prefix[-1] != prefix[-1].lower():
                dirs.add(os.sep.join(prefix))
    # Deepest first: at rename time a directory's PARENTS still carry the
    # original casing, so src and dst keep the parent segments as-is and
    # only the deepest segment changes case per step.
    for rel in sorted(dirs, key=lambda d: d.count(os.sep), reverse=True):
        parts = rel.split(os.sep)
        src = os.path.join(root, *parts)
        dst = os.path.join(root, *(parts[:-1] + [parts[-1].lower()]))
        if os.path.isdir(src):
            _rename_path(src, dst, git_root)
    for entry in renamed:
        rel = os.path.relpath(entry["path"], root)
        parts = rel.split(os.sep)
        current = os.path.join(
            root, *[p.lower() for p in parts[:-1]] + [parts[-1]])
        _rename_path(current, entry["new_path"], git_root)


def run_lowercase_pass(args, config, critical):
    tool = config.get("tool", "")
    root = wikilib.wiki_root(config)
    pages_dir = wikilib.pages_root(config)

    if args.apply:
        clean, detail = git_tree_is_clean(root)
        if clean is None:
            return critical("--apply requires a git repository at the "
                            "vault root (%s): %s" % (root, detail))
        if not clean:
            return critical("--apply refused: the vault working tree is "
                            "not clean. Commit or stash first.\n%s" % detail)

    namespaces = config.get("namespaces") or wikilib.DEFAULT_NAMESPACES
    if isinstance(namespaces, str):
        namespaces = [namespaces]

    pages = []
    for entry in wikilib.enumerate_pages(config):
        with open(entry["path"], "r", encoding="utf-8") as handle:
            text = handle.read()
        props = wikilib.parse_page_properties(text, tool)
        entry["text"] = text
        entry["type"] = props.get("type", "")
        pages.append(entry)

    structural = structural_segments(pages, namespaces)
    all_names = {p["name"] for p in pages}

    # Rename plan. Collisions (target name already taken by another page)
    # are skipped and reported; the converter never overwrites a page.
    rename_map = {}
    ambiguous = []
    manual = []
    for page in pages:
        if not page["name"].lower().startswith("wiki/"):
            continue
        new_name, is_ambiguous = lowercase_name(
            page["name"], page["type"], structural)
        if is_ambiguous:
            ambiguous.append(page["name"])
            manual.append(
                "leaf of '%s' kept its casing: lowercase it by hand if it "
                "is a structural name; keep it if it is a proper noun "
                "(REQ-580b). The converter does not guess." % page["name"])
        if new_name == page["name"]:
            continue
        if new_name in all_names:
            manual.append(
                "cannot rename '%s' -> '%s': the target page already "
                "exists; merge or rename by hand" % (page["name"], new_name))
            continue
        rename_map[page["name"]] = new_name

    renamed = []
    rewritten = []
    counter = {"links": 0, "roam": 0, "namespace_props": 0}
    for page in pages:
        new_name = rename_map.get(page["name"], page["name"])
        new_text = rewrite_wiki_links(
            page["text"], rename_map, structural, counter)
        new_text = rewrite_namespace_property(new_text, tool, counter)
        new_text = convert_roam_markers(new_text, counter)
        page["new_name"] = new_name
        page["new_text"] = new_text
        if new_text != page["text"]:
            rewritten.append(page)
        if new_name != page["name"]:
            page["new_path"] = new_path_for(page, new_name, tool, pages_dir)
            renamed.append(page)

    config_path = os.path.join(root, wikilib.CONFIG_FILENAME)
    config_changes = []
    new_config_text = None
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as handle:
            config_text = handle.read()
        candidate, config_changes = rewrite_config_namespaces(config_text)
        if config_changes:
            new_config_text = candidate

    # Simulated post-rename link graph: broken links and orphans.
    new_names = {page["new_name"] for page in pages}
    broken_links = []
    incoming = {name: 0 for name in new_names}
    for page in pages:
        stripped = lintmod.strip_code(page["new_text"])
        for target in lintmod.wiki_links(stripped):
            if target in new_names:
                if target != page["new_name"]:
                    incoming[target] += 1
            else:
                broken_links.append((page["new_name"], target))
    orphans = []
    for page in pages:
        if not page["new_name"].lower().startswith("wiki/"):
            continue
        if page["type"] == "hub" or is_system_page(page["new_name"], {}):
            continue
        props = wikilib.parse_page_properties(page["new_text"], tool)
        if is_system_page(page["new_name"], props) or "archived" in props:
            continue
        if incoming.get(page["new_name"], 0) == 0:
            orphans.append(page["new_name"])

    if args.apply:
        for page in rewritten:
            with open(page["path"], "w", encoding="utf-8") as handle:
                handle.write(page["new_text"])
        _apply_renames(renamed, tool, pages_dir, root)
        if new_config_text is not None:
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write(new_config_text)

    changes_total = (len(renamed) + counter["links"] + counter["roam"]
                     + counter["namespace_props"] + len(config_changes))
    report = {
        "pass": "lowercase",
        "tool": tool,
        "mode": "apply" if args.apply else "dry-run",
        "applied": bool(args.apply),
        "pages_scanned": len(pages),
        "renames": [{"from": p["name"], "to": p["new_name"],
                     "from_path": p["path"], "to_path": p["new_path"]}
                    for p in renamed],
        "files_rewritten": len(rewritten),
        "link_rewrites": counter["links"],
        "namespace_property_rewrites": counter["namespace_props"],
        "roam_marker_conversions": counter["roam"],
        "config_changes": config_changes,
        "ambiguous_leaves": ambiguous,
        "manual": manual,
        "broken_links_after_rename": len(broken_links),
        "broken_link_details": [
            {"page": page, "target": target}
            for page, target in sorted(set(broken_links))],
        "orphans_after_rename": sorted(orphans),
        "changes_total": changes_total,
        "manual_total": len(manual),
    }
    warnings = ["x"] * (changes_total + len(manual))
    status, exit_code = wikilib.status_from_counts([], warnings)
    report["status"] = status

    if args.json:
        wikilib.emit_json(report)
    else:
        print_lowercase_report(report)
    return exit_code


def print_lowercase_report(report):
    print("migrate --lowercase: scanned %d pages (tool: %s, mode: %s)"
          % (report["pages_scanned"], report["tool"], report["mode"]))
    for entry in report["renames"]:
        print("  ~ rename %s -> %s" % (entry["from"], entry["to"]))
    if report["link_rewrites"]:
        print("  ~ %d [[link]] target(s) rewritten (routing lines included)"
              % report["link_rewrites"])
    if report["namespace_property_rewrites"]:
        print("  ~ %d namespace:: property value(s) lowercased"
              % report["namespace_property_rewrites"])
    if report["roam_marker_conversions"]:
        print("  ~ %d Roam task marker(s) converted ({{[[TODO]]}} -> TODO)"
              % report["roam_marker_conversions"])
    for change in report["config_changes"]:
        print("  ~ llm-wiki.yml: %s" % change)
    for note in report["manual"]:
        print("  ! manual: %s" % note)
    print("\nafter simulated rename: %d broken link(s), %d orphan(s)"
          % (report["broken_links_after_rename"],
             len(report["orphans_after_rename"])))
    for detail in report["broken_link_details"]:
        print("  broken: %s -> [[%s]]" % (detail["page"], detail["target"]))
    print("\nsummary: %d rename(s), %d file(s) rewritten, %d mechanical "
          "change(s), %d manual follow-up(s)"
          % (len(report["renames"]), report["files_rewritten"],
             report["changes_total"], report["manual_total"]))
    if report["mode"] == "dry-run":
        if report["changes_total"]:
            print("dry run: no files were written. Re-run with --apply "
                  "(clean git tree required) to write.")
        else:
            print("dry run: nothing to rename; the corpus is already "
                  "lowercase.")
    elif not report["changes_total"]:
        print("applied: nothing to write; the corpus is already lowercase.")
    else:
        print("\napplied. Suggested commit message:\n")
        print("  wiki-migrate: lowercase namespace rename Wiki/ -> wiki/ "
              "(REQ-580c)")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def is_system_page(name, props):
    return (name.lower() in lintmod.SYSTEM_PAGE_NAMES
            or props.get("access-log") == "true"
            or props.get("type") in ("schema", "dashboard"))


def default_templates_dir(tool):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    return os.path.join(repo_root, "templates", tool)


def migrate_page(page, tool, template_text, namespaces, today):
    mig = Migration(page)
    with open(page["path"], "r", encoding="utf-8") as handle:
        text = handle.read()
    props = wikilib.parse_page_properties(text, tool)

    if page["name"].lower() == SCHEMA_PAGE_NAME:
        if template_text is None:
            mig.note("Schema.md template not found; run from a checkout of "
                     "the llm-wiki repository or pass --templates-dir to "
                     "upgrade the Schema page")
            new_text = text
        else:
            new_text, _upgraded = upgrade_schema_text(
                text, tool, template_text, namespaces, today, mig)
    else:
        # System pages (Dashboard, Access-Log) still get the version stamp
        # and normalization, but never a needs-review marker: they carry
        # no required-property set (lint exempts them the same way).
        system = is_system_page(page["name"], props)
        new_text = (migrate_logseq_text(text, system, mig)
                    if tool == "logseq"
                    else migrate_obsidian_text(text, system, mig))
        report_body_followups(text, tool, mig)

    mig.new_text = new_text if new_text != text else None
    return mig


def git_tree_is_clean(root):
    """Returns (clean, detail). detail explains a False or None result."""
    try:
        proc = subprocess.run(
            ["git", "-C", root, "status", "--porcelain", "--", "."],
            capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return None, "git not available on PATH"
    except subprocess.TimeoutExpired:
        return None, "git status timed out"
    if proc.returncode != 0:
        return None, ("not a git repository: %s"
                      % (proc.stderr.strip() or root))
    dirty = proc.stdout.strip()
    if dirty:
        return False, dirty
    return True, ""


def print_report(report, migrations):
    print("migrate: scanned %d pages (tool: %s, mode: %s)"
          % (report["pages_scanned"], report["tool"], report["mode"]))
    if report["pages_skipped_outside_wiki"]:
        print("skipped %d page(s) outside the wiki/ namespace"
              % report["pages_skipped_outside_wiki"])
    for mig in migrations:
        if not mig.changes and not mig.manual:
            continue
        print("\n%s (%s)" % (mig.page["name"], mig.page["path"]))
        for change in mig.changes:
            marker = "+" if change["kind"] in ("add-property",
                                               "set-property") else "~"
            print("  %s %s" % (marker, change["detail"]))
        for note in mig.manual:
            print("  ! manual: %s" % note)
    print("\nsummary: %d pages scanned, %d pages to migrate, "
          "%d mechanical changes, %d manual follow-ups"
          % (report["pages_scanned"], report["pages_to_migrate"],
             report["changes_total"], report["manual_total"]))
    if report["mode"] == "dry-run":
        if report["pages_to_migrate"]:
            print("dry run: no files were written. Re-run with --apply "
                  "(clean git tree required) to write.")
        else:
            print("dry run: nothing to migrate.")
    elif not report["pages_to_migrate"]:
        print("applied: nothing to write; the corpus is already migrated.")
    else:
        print("\napplied: %d page(s) written. Suggested commit message:\n"
              % report["pages_to_migrate"])
        print("  wiki-migrate: upgrade %d pages to schema-spec-version %s"
              % (report["pages_to_migrate"], SCHEMA_SPEC_VERSION))
        print("")
        print("  - %d mechanical changes (version stamp, needs-review "
              "markers," % report["changes_total"])
        print("    date/enum/key normalization, Schema section appends)")
        print("  - %d manual follow-up(s) remain; see needs-review:: "
              "markers" % report["manual_total"])


def main():
    parser = argparse.ArgumentParser(
        description="One-time, idempotent v1-to-v2 wiki converter. "
                    "Dry-run by default; --apply writes (requires a clean "
                    "git tree in the vault). Adds/normalizes page "
                    "properties only; content lines are never rewritten "
                    "and ratings are never invented.")
    parser.add_argument("--config", default=None,
                        help="path to llm-wiki.yml (default: discover)")
    parser.add_argument("--page", default=None,
                        help="migrate a single page by name "
                             "(e.g. wiki/tech/Docker)")
    parser.add_argument("--apply", action="store_true",
                        help="write the changes (default: dry-run report "
                             "only); refuses on a dirty git tree")
    parser.add_argument("--lowercase", action="store_true",
                        help="run the lowercase rename pass (Wiki/ -> "
                             "wiki/, REQ-580c) plus Roam task-marker "
                             "conversion instead of the v1-to-v2 schema "
                             "pass")
    parser.add_argument("--templates-dir", default=None,
                        help="template directory for the Schema-page "
                             "upgrade (default: the repo's "
                             "templates/<tool>/)")
    parser.add_argument("--date", default=None,
                        help="date stamp YYYY-MM-DD used for template "
                             "placeholders (default: today)")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    args = parser.parse_args()

    def critical(message):
        if args.json:
            wikilib.emit_json({"status": "critical", "criticals": [message]})
        else:
            print("CRITICAL: %s" % message, file=sys.stderr)
        return wikilib.EXIT_CRITICAL

    if args.config:
        config_path = args.config
        if not os.path.isfile(config_path):
            return critical("config file not found: %s" % config_path)
    else:
        try:
            config_path, _ = wikilib.discover_config()
        except ValueError as error:
            return critical(str(error))
        if not config_path:
            return critical(wikilib.DISCOVERY_FAILURE_MESSAGE)
    config = wikilib.load_config(config_path)
    tool = config.get("tool", "")
    if tool not in wikilib.VALID_TOOLS:
        return critical("invalid tool '%s' in %s" % (tool, config_path))

    if args.lowercase:
        if args.page:
            return critical("--page is not supported with --lowercase: the "
                            "rename pass is corpus-wide by nature (links "
                            "into a renamed page must be rewritten "
                            "everywhere)")
        return run_lowercase_pass(args, config, critical)

    root = wikilib.wiki_root(config)
    if args.apply:
        clean, detail = git_tree_is_clean(root)
        if clean is None:
            return critical("--apply requires a git repository at the "
                            "vault root (%s): %s" % (root, detail))
        if not clean:
            return critical("--apply refused: the vault working tree is "
                            "not clean. Commit or stash first.\n%s" % detail)

    pages = wikilib.enumerate_pages(config)
    skipped_outside = [p for p in pages
                       if not p["name"].lower().startswith("wiki/")]
    pages = [p for p in pages if p["name"].lower().startswith("wiki/")]
    if args.page:
        pages = [p for p in pages if p["name"] == args.page]
        if not pages:
            return critical("page '%s' not found in the wiki/ namespace "
                            "(names look like wiki/tech/Docker)" % args.page)

    namespaces = config.get("namespaces") or wikilib.DEFAULT_NAMESPACES
    if isinstance(namespaces, str):
        namespaces = [namespaces]
    today = args.date or datetime.date.today().isoformat()

    template_text = None
    templates_dir = args.templates_dir or default_templates_dir(tool)
    template_path = os.path.join(templates_dir, "Schema.md")
    if os.path.isfile(template_path):
        with open(template_path, "r", encoding="utf-8") as handle:
            template_text = handle.read()

    migrations = []
    for page in pages:
        migrations.append(
            migrate_page(page, tool, template_text, namespaces, today))

    to_write = [m for m in migrations if m.new_text is not None]
    if args.apply:
        for mig in to_write:
            with open(mig.page["path"], "w", encoding="utf-8") as handle:
                handle.write(mig.new_text)

    changes_total = sum(len(m.changes) for m in migrations)
    manual_total = sum(len(m.manual) for m in migrations)
    report = {
        "schema_spec_version": SCHEMA_SPEC_VERSION,
        "tool": tool,
        "mode": "apply" if args.apply else "dry-run",
        "applied": bool(args.apply),
        "pages_scanned": len(pages),
        "pages_skipped_outside_wiki": len(skipped_outside),
        "pages_to_migrate": len(to_write),
        "changes_total": changes_total,
        "manual_total": manual_total,
        "pages": [m.as_dict() for m in migrations
                  if m.changes or m.manual],
    }
    warnings = ["x"] * (changes_total + manual_total)
    status, exit_code = wikilib.status_from_counts([], warnings)
    report["status"] = status

    if args.json:
        wikilib.emit_json(report)
    else:
        print_report(report, migrations)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
