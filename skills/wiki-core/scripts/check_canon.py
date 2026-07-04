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

Comparisons performed:
   - lint-rule count: lint.md == both templates == lint.py
   - each property enum: schema.md == both templates (reliability also ==
     trust.md)
   - aggregation marker phrases present in schema.md, trust.md, and both
     templates
   - schema-spec-version: lint.py == both templates

A surface that fails to parse (marker or pattern missing) is itself a
failure: silent skips would defeat the check.

Stdlib only. Exit codes: 0 = aligned, 2 = disagreement or unparseable
surface.
"""

import os
import re
import sys

EXIT_OK = 0
EXIT_MISMATCH = 2

KNOWN_ENUM_PROPS = ("type", "entity-type", "status", "domain", "confidence",
                    "severity", "source", "reliability")

AGGREGATION_PHRASES = ("minimum across", "2+ independent sources",
                       "medium or better")

RULE_HEADING_RE = re.compile(r"^### Rule (\d+):", re.M)
TEMPLATE_RULE_RE = re.compile(r"\*\*Rule (\d+)\b")
ONE_OF_RE = re.compile(r"`([a-z-]+)`\s*=\s*one of:\s*(.+)")
BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")
TEMPLATE_ENUM_RE = re.compile(
    r"^\s*-?\s*(%s)::?\s+(.*\|.*)$" % "|".join(KNOWN_ENUM_PROPS))
VERSION_RE = re.compile(r"schema-spec-version::?\s*\"?([0-9][0-9A-Za-z.-]*)")
LINT_CONST_RE = re.compile(r'^SCHEMA_SPEC_VERSION\s*=\s*"([^"]+)"', re.M)
LINT_COUNT_RE = re.compile(r"^LINT_RULE_COUNT\s*=\s*(\d+)", re.M)
SEGMENT_TOKEN_RE = re.compile(r"^[a-z0-9-]+")


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    # scripts/ -> wiki-core/ -> skills/ -> repo root
    return os.path.dirname(os.path.dirname(os.path.dirname(here)))


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
    root = repo_root()
    paths = {
        "openspec/specs/lint.md": None,
        "openspec/specs/schema.md": None,
        "skills/wiki-core/references/trust.md": None,
        "templates/logseq/Schema.md": None,
        "templates/obsidian/Schema.md": None,
        "skills/wiki-core/scripts/lint.py": None,
    }
    canon = Canon()
    for rel in paths:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            canon.error("missing surface: %s" % rel)
        else:
            paths[rel] = read(path)
    if canon.errors:
        report(canon)
        return EXIT_MISMATCH

    lint_md = paths["openspec/specs/lint.md"]
    schema_md = paths["openspec/specs/schema.md"]
    trust_md = paths["skills/wiki-core/references/trust.md"]
    tpl_logseq = paths["templates/logseq/Schema.md"]
    tpl_obsidian = paths["templates/obsidian/Schema.md"]
    lint_py = paths["skills/wiki-core/scripts/lint.py"]

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
              "enums, reliability aggregation, schema-spec-version).")


if __name__ == "__main__":
    sys.exit(main())
