#!/usr/bin/env python3
"""check_canon.py - mechanical spec-consistency check across four surfaces.

The "no normative rule stated in more than one place" invariant is
unenforceable by hand: conventions narrated across the specs, the wiki-core
references, and BOTH template Schema pages drift silently. This script is
the crude but mechanical check that makes the invariant hold: it exits 2
with a diff-style report whenever the surfaces disagree, 0 when aligned.

Surfaces and what is extracted from each (the parsing contract):

1. openspec/specs/lint.md (source of truth for the rule set)
   - lint-rule count = number of `### Rule N:` headings.
     NOTE: deliberately NOT the prose sentence in the Description ("There
     are N lint rules"), which is narration, not structure.

2. openspec/specs/schema.md (source of truth for enums and aggregation)
   - property enums from lines of the form
     "- `prop` = one of: `a`, `b`, ..." (status appears twice: entity and
     project variants; both are collected),
   - the `type` enum from the REQ-500 "Valid values:" sentence,
   - the `reliability` enum from the REQ-586 "one of `high | medium | low`"
     phrase,
   - the reliability-aggregation rule as three marker phrases (checked on
     text normalized to lowercase, backticks removed, whitespace collapsed):
       "minimum across", "2+ independent sources", "medium or better".

3. skills/wiki-core/references/trust.md
   - the `reliability` enum from the "`reliability::` (`high | medium |
     low`)" phrase,
   - the three aggregation marker phrases.

4. templates/logseq/Schema.md and templates/obsidian/Schema.md
   - lint-rule count = lines matching `**Rule N` between the
     `<!-- canon:lint-rules start -->` / `<!-- canon:lint-rules end -->`
     markers (keep the markers when editing the templates),
   - property enums from lines "prop:: a | b | c" (Logseq) or
     "prop: a | b | c" (Obsidian, including inside YAML fences), restricted
     to the known schema properties; each pipe segment contributes its
     leading lowercase-kebab token (so trailing YAML comments are ignored),
   - the three aggregation marker phrases,
   - the schema-spec-version from the first "schema-spec-version:[:] X"
     line.

5. skills/wiki-core/scripts/lint.py
   - LINT_RULE_COUNT and SCHEMA_SPEC_VERSION module constants (regex, not
     import).

6. openspec/specs/citations.md (source of truth for the cite:: convention)
   - the source-file union invariant (REQ-904) as two marker phrases
     (same normalization as the aggregation phrases):
       "union of the page's ingested/ cite targets",
       "locators stripped, deduplicated".

Comparisons performed:
   - lint-rule count: lint.md == both templates == lint.py
   - each property enum: schema.md == both templates (reliability also ==
     trust.md)
   - aggregation marker phrases present in schema.md, trust.md, and both
     templates
   - citation union-invariant marker phrases present in citations.md,
     trust.md, and both templates
   - schema-spec-version: lint.py == both templates

A surface that fails to parse (marker or pattern missing) is itself a
failure: silent skips would defeat the check.

The surfaces live in the llm-wiki CHECKOUT, not in the installed skill
bundle (issue #106): running the installed copy from a vault would resolve
every surface relative to ~/.claude and report phantom "missing surface"
drift. The root is therefore resolved in this order: --repo <path> if
given, the script's own location (works inside the checkout), then the
current working directory. A root only qualifies when it actually holds
openspec/specs/ and templates/; when none does, the script fails fast with
exit 3, clearly distinguishable from real content drift (exit 2).

Stdlib only. Exit codes: 0 = aligned, 2 = disagreement or unparseable
surface, 3 = not in an llm-wiki checkout (or surfaces missing on disk).
"""

import argparse
import os
import re
import sys

EXIT_OK = 0
EXIT_MISMATCH = 2
EXIT_NO_REPO = 3

KNOWN_ENUM_PROPS = ("type", "entity-type", "status", "domain", "confidence",
                    "severity", "source", "reliability")

AGGREGATION_PHRASES = ("minimum across", "2+ independent sources",
                       "medium or better")

CITATION_PHRASES = ("union of the page's ingested/ cite targets",
                    "locators stripped, deduplicated")

RULE_HEADING_RE = re.compile(r"^### Rule (\d+):", re.M)
TEMPLATE_RULE_RE = re.compile(r"\*\*Rule (\d+)\b")
ONE_OF_RE = re.compile(r"`([a-z-]+)`\s*=\s*one of:\s*(.+)")
BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")
TEMPLATE_ENUM_RE = re.compile(
    r"^\s*-?\s*(%s)::?\s+(.*\|.*)$" % "|".join(KNOWN_ENUM_PROPS))
VERSION_RE = re.compile(r"schema-spec-version::?\s*\"?([0-9][0-9A-Za-z.-]*)")
LINT_CONST_RE = re.compile(r'^SCHEMA_SPEC_VERSION\s*=\s*"([^"]+)"', re.M)
LINT_COUNT_RE = re.compile(r"^LINT_RULE_COUNT\s*=\s*(\d+)", re.M)
# Namespace contract (specs/namespaces.md REQ-960, specs/glossary.md;
# premortem revision 8): the REQ-960 top-level bullets vs the wikilib
# CONTENT_NAMESPACES tuple, plus a repo-wide grep gate against stale
# "three namespaces" prose.
NS_BULLET_RE = re.compile(r"^  - `([a-z-]+)/` - ", re.M)
NS_TUPLE_RE = re.compile(r"^CONTENT_NAMESPACES\s*=\s*\(([^)]*)\)", re.M)
NS_STALE_PHRASES = ("three namespaces", "exactly three content namespaces",
                    "Three-Namespace", "three-namespace")
NS_GREP_DIRS = ("openspec/specs", "skills", "templates", "docs", "examples")
NS_GREP_EXCLUDE = ("docs/premortem-report", "docs/roadmap-",
                   "docs/migration")
SEGMENT_TOKEN_RE = re.compile(r"^[a-z0-9-]+")


def is_checkout(root):
    """A directory qualifies as the llm-wiki checkout when it holds the
    canon-surface directories the installed skill bundle does not ship."""
    return (os.path.isdir(os.path.join(root, "openspec", "specs"))
            and os.path.isdir(os.path.join(root, "templates")))


def resolve_root(repo_arg):
    here = os.path.dirname(os.path.abspath(__file__))
    # scripts/ -> wiki-core/ -> skills/ -> repo root
    script_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    if repo_arg:
        candidates = [os.path.abspath(os.path.expanduser(repo_arg))]
    else:
        candidates = [script_root, os.getcwd()]
    for candidate in candidates:
        if is_checkout(candidate):
            return candidate
    print("check_canon: not in an llm-wiki checkout "
          "(no openspec/specs/ under %s)."
          % " or ".join(candidates))
    print("The canon surfaces live in the llm-wiki repository, not in the "
          "installed skill bundle. Run from the llm-wiki repo root, or "
          "pass --repo <path-to-checkout>.")
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def normalize(text):
    return re.sub(r"\s+", " ", text.replace("`", "").lower())


class Canon:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)

    # -- extractors ---------------------------------------------------------

    def lint_md_rule_count(self, text, label):
        numbers = [int(n) for n in RULE_HEADING_RE.findall(text)]
        if not numbers:
            self.error("%s: no '### Rule N:' headings found (unparseable)"
                       % label)
            return None
        return len(numbers)

    def template_rule_count(self, text, label):
        match = re.search(
            r"<!-- canon:lint-rules start -->(.*?)<!-- canon:lint-rules end -->",
            text, re.S)
        if not match:
            self.error("%s: canon:lint-rules markers missing (unparseable)"
                       % label)
            return None
        numbers = [int(n) for n in TEMPLATE_RULE_RE.findall(match.group(1))]
        if not numbers:
            self.error("%s: no '**Rule N' entries inside the "
                       "canon:lint-rules markers" % label)
            return None
        return len(numbers)

    def schema_md_enums(self, text, label):
        enums = {}
        for prop, rest in ONE_OF_RE.findall(text):
            values = frozenset(BACKTICK_TOKEN_RE.findall(rest))
            if values:
                enums.setdefault(prop, []).append(values)
        type_match = re.search(r"Valid values:\s*(.+)", text)
        if type_match:
            enums.setdefault("type", []).append(
                frozenset(BACKTICK_TOKEN_RE.findall(type_match.group(1))))
        rel_match = re.search(r"`reliability::`\s+property,\s+one of\s+`([^`]+)`",
                              re.sub(r"\s+", " ", text))
        if rel_match:
            enums.setdefault("reliability", []).append(frozenset(
                v.strip() for v in rel_match.group(1).split("|")))
        for prop in KNOWN_ENUM_PROPS:
            if prop not in enums:
                self.error("%s: enum for '%s' not found (unparseable)"
                           % (label, prop))
        return {p: sorted(sets, key=sorted) for p, sets in enums.items()}

    def template_enums(self, text, label):
        enums = {}
        for line in text.splitlines():
            match = TEMPLATE_ENUM_RE.match(line)
            if not match:
                continue
            prop, value = match.group(1), match.group(2)
            values = []
            for segment in value.split("|"):
                token = SEGMENT_TOKEN_RE.match(segment.strip())
                if not token:
                    self.error("%s: enum line for '%s' has a segment "
                               "without a leading token: %r"
                               % (label, prop, segment.strip()))
                    break
                values.append(token.group(0))
            else:
                enums.setdefault(prop, []).append(frozenset(values))
        for prop in KNOWN_ENUM_PROPS:
            if prop not in enums:
                self.error("%s: enum for '%s' not found (unparseable)"
                           % (label, prop))
        return {p: sorted(sets, key=sorted) for p, sets in enums.items()}

    def trust_md_reliability(self, text, label):
        match = re.search(r"`reliability::`\s*\(`([^`]+)`\)", text)
        if not match:
            self.error("%s: reliability enum phrase not found (unparseable)"
                       % label)
            return None
        return [frozenset(v.strip() for v in match.group(1).split("|"))]

    def check_phrases(self, text, label):
        normalized = normalize(text)
        for phrase in AGGREGATION_PHRASES:
            if phrase not in normalized:
                self.error("%s: reliability-aggregation phrase %r missing"
                           % (label, phrase))

    def check_citation_phrases(self, text, label):
        normalized = normalize(text)
        for phrase in CITATION_PHRASES:
            if phrase not in normalized:
                self.error("%s: citation union-invariant phrase %r missing"
                           % (label, phrase))

    # -- comparison ---------------------------------------------------------

    def compare(self, item, values):
        """values: list of (surface-label, value). Specs come first."""
        present = [(label, value) for label, value in values
                   if value is not None]
        if len(present) < 2:
            return
        canonical_label, canonical = present[0]
        for label, value in present[1:]:
            if value != canonical:
                self.error(
                    "%s disagrees:\n    - %-42s %s\n    + %-42s %s"
                    % (item, canonical_label, fmt(canonical), label,
                       fmt(value)))


def fmt(value):
    if isinstance(value, list):
        return " / ".join("{%s}" % ", ".join(sorted(s)) for s in value)
    return str(value)


def main():
    parser = argparse.ArgumentParser(
        description="Mechanical spec-consistency check across the canon "
                    "surfaces of an llm-wiki checkout.")
    parser.add_argument(
        "--repo", metavar="PATH",
        help="path to the llm-wiki checkout (default: the script's own "
             "checkout, else the current working directory)")
    args = parser.parse_args()

    root = resolve_root(args.repo)
    if root is None:
        return EXIT_NO_REPO
    paths = {
        "openspec/specs/lint.md": None,
        "openspec/specs/schema.md": None,
        "openspec/specs/citations.md": None,
        "skills/wiki-core/references/trust.md": None,
        "templates/logseq/Schema.md": None,
        "templates/obsidian/Schema.md": None,
        "skills/wiki-core/scripts/lint.py": None,
        "openspec/specs/namespaces.md": None,
        "skills/wiki-core/scripts/wikilib.py": None,
    }
    canon = Canon()
    missing = []
    for rel in paths:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            missing.append(rel)
        else:
            paths[rel] = read(path)
    if missing:
        # Surfaces absent on disk are an incomplete checkout, not content
        # drift (issue #106): report them under their own exit code.
        print("check_canon: %d surface(s) missing under %s (incomplete "
              "checkout, not content drift)\n" % (len(missing), root))
        for rel in missing:
            print("  MISSING: %s" % rel)
        return EXIT_NO_REPO

    lint_md = paths["openspec/specs/lint.md"]
    schema_md = paths["openspec/specs/schema.md"]
    citations_md = paths["openspec/specs/citations.md"]
    trust_md = paths["skills/wiki-core/references/trust.md"]
    tpl_logseq = paths["templates/logseq/Schema.md"]
    tpl_obsidian = paths["templates/obsidian/Schema.md"]
    lint_py = paths["skills/wiki-core/scripts/lint.py"]
    namespaces_md = paths["openspec/specs/namespaces.md"]
    wikilib_py = paths["skills/wiki-core/scripts/wikilib.py"]

    # 1. Lint-rule count.
    count_spec = canon.lint_md_rule_count(lint_md, "openspec/specs/lint.md")
    count_logseq = canon.template_rule_count(tpl_logseq,
                                             "templates/logseq/Schema.md")
    count_obsidian = canon.template_rule_count(tpl_obsidian,
                                               "templates/obsidian/Schema.md")
    count_match = LINT_COUNT_RE.search(lint_py)
    count_lint_py = int(count_match.group(1)) if count_match else None
    if count_lint_py is None:
        canon.error("lint.py: LINT_RULE_COUNT constant not found")
    canon.compare("lint-rule count", [
        ("openspec/specs/lint.md (### Rule headings)", count_spec),
        ("templates/logseq/Schema.md", count_logseq),
        ("templates/obsidian/Schema.md", count_obsidian),
        ("skills/wiki-core/scripts/lint.py", count_lint_py),
    ])

    # 2. Property enums.
    spec_enums = canon.schema_md_enums(schema_md, "openspec/specs/schema.md")
    logseq_enums = canon.template_enums(tpl_logseq,
                                        "templates/logseq/Schema.md")
    obsidian_enums = canon.template_enums(tpl_obsidian,
                                          "templates/obsidian/Schema.md")
    trust_reliability = canon.trust_md_reliability(
        trust_md, "skills/wiki-core/references/trust.md")
    for prop in KNOWN_ENUM_PROPS:
        values = [
            ("openspec/specs/schema.md", spec_enums.get(prop)),
            ("templates/logseq/Schema.md", logseq_enums.get(prop)),
            ("templates/obsidian/Schema.md", obsidian_enums.get(prop)),
        ]
        if prop == "reliability":
            values.append(("skills/wiki-core/references/trust.md",
                           trust_reliability))
        canon.compare("enum '%s'" % prop, values)

    # 3. Reliability-aggregation rule (marker phrases on every surface).
    canon.check_phrases(schema_md, "openspec/specs/schema.md")
    canon.check_phrases(trust_md, "skills/wiki-core/references/trust.md")
    canon.check_phrases(tpl_logseq, "templates/logseq/Schema.md")
    canon.check_phrases(tpl_obsidian, "templates/obsidian/Schema.md")

    # 3a. Citation union invariant (marker phrases on every cite surface).
    canon.check_citation_phrases(citations_md, "openspec/specs/citations.md")
    canon.check_citation_phrases(trust_md,
                                 "skills/wiki-core/references/trust.md")
    canon.check_citation_phrases(tpl_logseq, "templates/logseq/Schema.md")
    canon.check_citation_phrases(tpl_obsidian,
                                 "templates/obsidian/Schema.md")

    # 4. schema-spec-version.
    version_match = LINT_CONST_RE.search(lint_py)
    version_lint_py = version_match.group(1) if version_match else None
    if version_lint_py is None:
        canon.error("lint.py: SCHEMA_SPEC_VERSION constant not found")

    def template_version(text, label):
        match = VERSION_RE.search(text)
        if not match:
            canon.error("%s: schema-spec-version not found (unparseable)"
                        % label)
            return None
        return match.group(1)

    canon.compare("schema-spec-version", [
        ("skills/wiki-core/scripts/lint.py", version_lint_py),
        ("templates/logseq/Schema.md",
         template_version(tpl_logseq, "templates/logseq/Schema.md")),
        ("templates/obsidian/Schema.md",
         template_version(tpl_obsidian, "templates/obsidian/Schema.md")),
    ])

    # 5. Namespace contract (REQ-960 vs wikilib.CONTENT_NAMESPACES) plus
    # the stale-phrase grep gate (premortem revision 8).
    req960 = namespaces_md.split("- REQ-960:", 1)
    bullets = NS_BULLET_RE.findall(req960[1].split("- REQ-961:", 1)[0]) \
        if len(req960) == 2 else []
    tuple_match = NS_TUPLE_RE.search(wikilib_py)
    tuple_count = len([v for v in tuple_match.group(1).split(",")
                       if v.strip()]) if tuple_match else None
    if tuple_count is None:
        canon.error("wikilib.py: CONTENT_NAMESPACES tuple not found")
    canon.compare("namespace count", [
        ("openspec/specs/namespaces.md (REQ-960 bullets)",
         len(bullets) or None),
        ("skills/wiki-core/scripts/wikilib.py (CONTENT_NAMESPACES)",
         tuple_count),
    ])
    for directory in NS_GREP_DIRS:
        base = os.path.join(root, directory)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in sorted(filenames):
                if not filename.endswith((".md", ".py")):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, filename), root)
                if any(rel.startswith(prefix) for prefix in NS_GREP_EXCLUDE):
                    continue
                if rel == "skills/wiki-core/scripts/check_canon.py":
                    continue  # holds the phrase list itself
                text = read(os.path.join(dirpath, filename))
                for phrase in NS_STALE_PHRASES:
                    if phrase in text:
                        canon.error(
                            "%s: stale namespace-count prose ('%s'); the "
                            "contract is REQ-960, narrated nowhere else"
                            % (rel, phrase))

    report(canon)
    return EXIT_MISMATCH if canon.errors else EXIT_OK


def report(canon):
    if canon.errors:
        print("check_canon: %d disagreement(s) between canon surfaces\n"
              % len(canon.errors))
        for error in canon.errors:
            print("  MISMATCH: %s" % error)
        print("\nSpecs (openspec/specs/) are the source of truth; align the "
              "other surfaces.")
    else:
        print("check_canon: all surfaces aligned (rule count, property "
              "enums, reliability aggregation, citation union invariant, "
              "schema-spec-version, namespace contract).")


if __name__ == "__main__":
    sys.exit(main())
