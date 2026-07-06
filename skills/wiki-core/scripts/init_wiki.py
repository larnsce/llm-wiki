#!/usr/bin/env python3
"""Non-interactive wiki scaffolding, extracted from setup.sh.

Creates, for either tool mode:
- the pages directory and the initial pages rendered from templates/
  (Schema, Dashboard, one Hub per namespace, the Access-Log page)
- the source-pipeline scaffold: raw/ and ingested/<type>/ with .gitkeep
- Logseq mode: :hidden ["raw" "ingested"] in logseq/config.edn so the
  source trees stay out of the Logseq index (created, or merged into an
  existing :hidden vector; specs/setup.md REQ-787)
- the tool-specific .gitignore (unless --no-gitignore)
- llm-wiki.yml (unless --no-config; existing config is kept unless
  --overwrite-config)
- with --with-para-notes: the opt-in human layer (specs/namespaces.md,
  specs/config.md REQ-625, issue #29): human-editable para/schema and
  notes/schema seed pages; in Obsidian mode also the PARA and Zettelkasten
  directory trees (para/{projects,areas,resources,archives}/,
  notes/{literature,permanent}/). In Logseq mode the namespaces are
  page-name prefixes, so no directories are needed. The config then gains
  para_dir/notes_dir keys. Without the flag, behavior is unchanged.

It does NOT run git init or git commit; that stays in setup.sh.

Existing pages are never overwritten; they are skipped with a warning
(specs/setup.md REQ-786), which yields exit code 1.

Exit codes: 0 = clean, 1 = warnings, 2 = critical.
"""

import argparse
import datetime
import os
import re
import sys

import wikilib

NAMESPACE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")

# Stamped on every scaffolded page so fresh pages are NOT grandfathered by
# lint. Must match SCHEMA_SPEC_VERSION in lint.py and both Schema templates
# (check_canon.py verifies those surfaces).
SCHEMA_SPEC_VERSION = "2.0.0"

GITIGNORE = {
    "logseq": """logseq/bak/
logseq/.recycle/
.DS_Store
.logseq/
# Source-pipeline binaries. Provenance is the .md notes in ingested/, not the
# PDFs themselves. Uncomment the next two lines to keep heavy binaries out of git
# history. For a reproducibility setup where the PDFs MUST be versioned, leave
# them commented and instead run: git lfs track "*.pdf"
# raw/**/*.pdf
# ingested/**/*.pdf
""",
    "obsidian": """.obsidian/workspace.json
.obsidian/workspace-mobile.json
.DS_Store
.trash/
# Source-pipeline binaries. Provenance is the .md notes in ingested/, not the
# PDFs themselves. Uncomment the next two lines to keep heavy binaries out of git
# history. For a reproducibility setup where the PDFs MUST be versioned, leave
# them commented and instead run: git lfs track "*.pdf"
# raw/**/*.pdf
# ingested/**/*.pdf
""",
}

# Human-layer scaffold (--with-para-notes, issue #29). The subdirectory
# names follow docs/para-notes-workflow.md.
PARA_SUBDIRS = ("projects", "areas", "resources", "archives")
NOTES_SUBDIRS = ("literature", "permanent")

# Seed pages for the human layer. They are human-editable references, NOT
# wiki pages: the wiki toolchain never edits, lints, or audits them again
# (specs/namespaces.md REQ-961/966), so they carry no schema-spec-version
# stamp. type:: schema marks them as reference pages for the human's own
# queries. Content condenses docs/para-notes-workflow.md.
PARA_SCHEMA_LOGSEQ = """\
type:: schema
last-updated:: {date}

- ## para/ conventions
	- This page and everything under `para/` is yours: the wiki toolchain never creates, edits, lints, or audits it (see `docs/para-notes-workflow.md` in the llm-wiki repository). Edit this page freely; the tool does not read it.
- ## layout
	- `para/projects/<project-name>`: one page per active project, tasks as blocks
	- `para/areas/<area-name>`: ongoing responsibilities
	- `para/resources/<topic>`: reference material by interest
	- `para/archives/<project-name>`: completed or inactive projects
- ## page conventions
	- Human-authored. No `source-file::`, no citations, no `reliability::`.
	- Tasks are native Logseq markers (`TODO` / `DOING` / `NOW` / `DONE` / `CANCELED`) on blocks inside the owning project or area page.
	- Every project page starts with `type:: project`, `status:: active | paused | archived`, and `outcome::` (one line: what "done" looks like).
	- Link freely into `[[wiki/...]]` and `[[notes/...]]` pages; that is the point of one graph.
	- `para/resources/` is a waiting room, not a destination: source-backed and stable content belongs in `wiki/`; your own thinking belongs in `notes/`.
- ## promotion into wiki/
	- The ONLY path into `wiki/` is through `raw/`: copy durable content into `raw/para-<project>.md` and run /wiki-ingest. It enters at `reliability:: medium` (personal synthesis) unless external citations justify higher.
- See `docs/para-notes-workflow.md` for the full workflow: the `para/live-list` query page and the manual project-archiving procedure.
"""

NOTES_SCHEMA_LOGSEQ = """\
type:: schema
last-updated:: {date}

- ## notes/ conventions
	- This page and everything under `notes/` is yours: human-written, always. The wiki toolchain never creates, edits, lints, or audits it (see `docs/para-notes-workflow.md` in the llm-wiki repository). If Claude drafts it, it is not a note; it is a `wiki/` page.
- ## note types
	- One `type::` property per page: `fleeting | literature | permanent`. Properties, not tags, carry the note type; queries filter on them.
	- fleeting: NOT pages. Journal blocks tagged `#fleeting`.
	- literature: `notes/literature/@<citekey>` (born from Zotero). Carries `source-file::` pointing at the SAME `ingested/...` path the wiki pages cite: one archived source, two readings.
	- permanent: `notes/permanent/<idea-in-a-few-words>`. Atomic: one idea, your own words, densely linked to other `[[notes/...]]` and `[[wiki/...]]` pages.
- ## promotion (an act of writing, not a rename)
	- fleeting to permanent: write the permanent note fresh, link the journal block to it, remove `#fleeting` or mark the block `DONE`.
	- fleeting to task: move it to the owning `para/` page as a `TODO`.
	- Anything not promoted within about two weeks: delete without guilt.
	- notes to wiki (deliberate only): copy the note into `raw/note-<name>.md` and run /wiki-ingest. It arrives at `reliability:: medium`.
- See `docs/para-notes-workflow.md` for the full workflow: the `notes/fleeting-inbox` query page and the Zotero funnel.
"""

PARA_SCHEMA_OBSIDIAN = """\
---
type: schema
last-updated: "{date}"
---

# para/ conventions

This page and everything under `para/` is yours: the wiki toolchain never
creates, edits, lints, or audits it (see `docs/para-notes-workflow.md` in the
llm-wiki repository). Edit this page freely; the tool does not read it.

## Layout

- `para/projects/<project-name>`: one page per active project, tasks as list items
- `para/areas/<area-name>`: ongoing responsibilities
- `para/resources/<topic>`: reference material by interest
- `para/archives/<project-name>`: completed or inactive projects

## Page conventions

- Human-authored. No `source-file`, no citations, no `reliability`.
- Every project page starts with `type: project`, `status: active | paused |
  archived`, and `outcome` (one line: what "done" looks like) in its
  frontmatter.
- Link freely into `[[wiki/...]]` and `[[notes/...]]` pages; that is the
  point of one graph.
- `para/resources/` is a waiting room, not a destination: source-backed and
  stable content belongs in `wiki/`; your own thinking belongs in `notes/`.

## Promotion into wiki/

The ONLY path into `wiki/` is through `raw/`: copy durable content into
`raw/para-<project>.md` and run /wiki-ingest. It enters at
`reliability: medium` (personal synthesis) unless external citations justify
higher.

See `docs/para-notes-workflow.md` for the full workflow, including the manual
project-archiving procedure. The task query pages described there are Logseq
tier-1; the Dataview equivalent on Obsidian is experimental.
"""

NOTES_SCHEMA_OBSIDIAN = """\
---
type: schema
last-updated: "{date}"
---

# notes/ conventions

This page and everything under `notes/` is yours: human-written, always. The
wiki toolchain never creates, edits, lints, or audits it (see
`docs/para-notes-workflow.md` in the llm-wiki repository). If Claude drafts
it, it is not a note; it is a `wiki/` page.

## Note types

One `type` property per page: `fleeting | literature | permanent`.
Properties, not tags, carry the note type; queries filter on them.

- fleeting: NOT pages. Daily-note items tagged `#fleeting`.
- literature: `notes/literature/@<citekey>` (born from Zotero). Carries
  `source-file` pointing at the SAME `ingested/...` path the wiki pages
  cite: one archived source, two readings.
- permanent: `notes/permanent/<idea-in-a-few-words>`. Atomic: one idea, your
  own words, densely linked to other `[[notes/...]]` and `[[wiki/...]]` pages.

## Promotion (an act of writing, not a rename)

- fleeting to permanent: write the permanent note fresh, link the daily-note
  item to it, remove `#fleeting`.
- fleeting to task: move it to the owning `para/` page as a task.
- Anything not promoted within about two weeks: delete without guilt.
- notes to wiki (deliberate only): copy the note into `raw/note-<name>.md`
  and run /wiki-ingest. It arrives at `reliability: medium`.

See `docs/para-notes-workflow.md` for the full workflow and the Zotero
funnel. The query pages described there are Logseq tier-1; the Dataview
equivalent on Obsidian is experimental.
"""

GLOSSARY_CONFIG_BLOCK = """\
# Glossary namespace (specs/config.md REQ-628, specs/glossary.md):
# human-decided terminology; the tool scaffolds and structure-lints it and
# writes only rows confirmed at the /wiki-glossary checkpoint.
glossary_dir: {glossary_dir}
"""

GLOSSARY_INDEX_LOGSEQ = """\
type:: glossary-index

- ## glossary
	- The EN-DE terminology layer: one domain page per subject, decisions recorded once. See `docs/glossary-workflow.md` in the llm-wiki repository.
	- ### Index
		- [[glossary/tech]] -- software, git, and computing terms #glossary
"""

GLOSSARY_INDEX_OBSIDIAN = """\
---
type: glossary-index
---

# glossary

The EN-DE terminology layer: one domain page per subject, decisions
recorded once. See `docs/glossary-workflow.md` in the llm-wiki repository.

## Index

- [[glossary/tech]] -- software, git, and computing terms #glossary
"""

PARA_NOTES_CONFIG_BLOCK = """\
# Human namespaces (specs/config.md REQ-625, specs/namespaces.md REQ-980):
# para/ (PARA task layer) and notes/ (Zettelkasten) are human-owned; the
# wiki toolchain never writes to them. See docs/para-notes-workflow.md.
para_dir: {para_dir}
notes_dir: {notes_dir}
"""

CONFIG_TEMPLATE = """# llm-wiki configuration
# Generated by init_wiki.py on {date}

tool: {tool}
wiki_path: {wiki_path}
pages_dir: {pages_dir}
memory_path: {memory_path}

namespaces:
{namespace_lines}
# Source pipeline: drop sources in raw/, ingest synthesises them into pages,
# then the source file is moved into ingested/<type>/. The move is the
# provenance record (in raw/ = pending, in ingested/ = processed).
raw_dir: raw
ingested_dir: ingested
source_types:
{source_type_lines}
default_source_type: papers
{para_notes_block}"""


class Scaffold:
    def __init__(self):
        self.created = []
        self.skipped = []
        self.quiet = False

    def note(self, message):
        if not self.quiet:
            print(message)

    def write_file(self, path, content, label=None):
        """Create a file; never overwrite. Returns True if written."""
        label = label or os.path.basename(path)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if os.path.exists(path):
            self.skipped.append(label)
            self.note("  Skipped (already exists): %s" % label)
            return False
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.created.append(label)
        self.note("  Created: %s" % label)
        return True


def read_template(template_dir, name):
    with open(os.path.join(template_dir, name), encoding="utf-8") as handle:
        return handle.read()


def stamp_schema_version(content, tool):
    """Ensure the page carries `schema-spec-version` (correct syntax per mode).

    Every page init_wiki.py scaffolds conforms to the current schema, so it
    gets the stamp; pages without it are treated as pre-2.0.0 by lint
    (grandfather mode). Templates that already carry the property (the
    Schema page) are left untouched.
    """
    if "schema-spec-version" in content:
        return content
    if tool == "logseq":
        # Page properties are unbulleted per schema REQ-591; the stamp joins
        # the template's leading property block.
        return "schema-spec-version:: %s\n%s" % (SCHEMA_SPEC_VERSION,
                                                 content)
    lines = content.splitlines(True)
    if lines and lines[0].strip() == "---":
        lines.insert(1, 'schema-spec-version: "%s"\n' % SCHEMA_SPEC_VERSION)
        return "".join(lines)
    return '---\nschema-spec-version: "%s"\n---\n%s' % (SCHEMA_SPEC_VERSION,
                                                        content)


def render_pages(scaffold, tool, wiki_path, pages_path, template_dir,
                 namespaces, today):
    """Page creation, ported from the python heredoc in setup.sh Step 8."""
    ns_list = ", ".join("wiki/%s" % ns for ns in namespaces)
    schema = read_template(template_dir, "Schema.md")
    schema = schema.replace("{{NAMESPACES}}", ns_list)
    schema = schema.replace("{{DATE}}", today)

    dashboard = read_template(template_dir, "Dashboard.md")
    dashboard = dashboard.replace("{{DATE}}", today)

    hub_tpl = read_template(template_dir, "Hub.md")
    access_log = read_template(template_dir, "Access-Log.md")
    access_log = access_log.replace("{{DATE}}", today)

    if tool == "logseq":
        ns_links = "\n".join("\t- [[wiki/%s]]" % ns for ns in namespaces)
        dashboard = dashboard.replace("{{NAMESPACE_LINKS}}", ns_links)

        scaffold.write_file(os.path.join(pages_path, "wiki___schema.md"),
                            stamp_schema_version(schema, tool), "wiki/schema")
        scaffold.write_file(os.path.join(pages_path, "wiki___dashboard.md"),
                            stamp_schema_version(dashboard, tool),
                            "wiki/dashboard")
        for ns in namespaces:
            hub = hub_tpl.replace("{{NAMESPACE}}", ns).replace("{{DATE}}", today)
            scaffold.write_file(os.path.join(pages_path, "wiki___%s.md" % ns),
                                stamp_schema_version(hub, tool),
                                "wiki/%s" % ns)
        scaffold.write_file(
            os.path.join(pages_path, "wiki___reference___access-log.md"),
            stamp_schema_version(access_log, tool),
            "wiki/reference/access-log")
    else:
        wiki_dir = os.path.join(wiki_path, "wiki")
        ns_links = "\n".join("- [[wiki/%s]]" % ns for ns in namespaces)
        dashboard = dashboard.replace("{{NAMESPACE_LINKS}}", ns_links)

        scaffold.write_file(os.path.join(wiki_dir, "schema.md"),
                            stamp_schema_version(schema, tool),
                            "wiki/schema.md")
        scaffold.write_file(os.path.join(wiki_dir, "dashboard.md"),
                            stamp_schema_version(dashboard, tool),
                            "wiki/dashboard.md")
        for ns in namespaces:
            hub = hub_tpl.replace("{{NAMESPACE}}", ns).replace("{{DATE}}", today)
            scaffold.write_file(os.path.join(wiki_dir, ns, "_index.md"),
                                stamp_schema_version(hub, tool),
                                "wiki/%s/_index.md" % ns)
        scaffold.write_file(
            os.path.join(wiki_dir, "reference", "access-log.md"),
            stamp_schema_version(access_log, tool),
            "wiki/reference/access-log.md")


def scaffold_pipeline(scaffold, wiki_path):
    """raw/ and ingested/<type>/ beside the pages dir, with .gitkeep files."""
    dirs = [os.path.join(wiki_path, "raw")]
    dirs += [os.path.join(wiki_path, "ingested", t)
             for t in wikilib.DEFAULT_SOURCE_TYPES]
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        if not os.listdir(directory):
            gitkeep = os.path.join(directory, ".gitkeep")
            with open(gitkeep, "w", encoding="utf-8"):
                pass
            scaffold.created.append(os.path.relpath(gitkeep, wiki_path))
    scaffold.note("  Scaffolded: raw/ and ingested/{%s}/"
                  % ",".join(wikilib.DEFAULT_SOURCE_TYPES))


def ensure_logseq_hidden(scaffold, wiki_path, hidden_dirs):
    """Hide the source dirs from the Logseq index (issue #69, REQ-787).

    Logseq indexes every markdown file under the graph root recursively
    unless the directory is listed in :hidden in logseq/config.edn. Living
    beside pages/ keeps raw/ and ingested/ out of the pages directory, but
    only :hidden keeps them out of the index; without it archived sources
    render as graph pages and their TOC anchor links parse as #hashtags.

    Creates a minimal config.edn when none exists; otherwise merges the
    missing entries into the first uncommented :hidden vector (the app
    writes :hidden [] on graph init). An existing config.edn with no
    parseable :hidden gets the key appended before its closing brace.
    """
    config_path = os.path.join(wiki_path, "logseq", "config.edn")
    rel = os.path.join("logseq", "config.edn")
    quoted = " ".join('"%s"' % d for d in hidden_dirs)
    if not os.path.exists(config_path):
        scaffold.write_file(config_path, "{:hidden [%s]}\n" % quoted, rel)
        return

    with open(config_path, "r", encoding="utf-8") as handle:
        text = handle.read()
    match = None
    for candidate in re.finditer(r":hidden\s*\[([^\]]*)\]", text):
        line_start = text.rfind("\n", 0, candidate.start()) + 1
        if ";" not in text[line_start:candidate.start()]:
            match = candidate
            break
    if match:
        existing = set(re.findall(r'"([^"]+)"', match.group(1)))
        missing = [d for d in hidden_dirs if d not in existing]
        if not missing:
            scaffold.note("  Unchanged: %s (:hidden already covers %s)"
                          % (rel, ", ".join(hidden_dirs)))
            return
        inner = match.group(1).strip()
        merged = ((inner + " ") if inner else "") \
            + " ".join('"%s"' % d for d in missing)
        text = text[:match.start()] + ":hidden [%s]" % merged \
            + text[match.end():]
    else:
        brace = text.rfind("}")
        if brace == -1:
            scaffold.skipped.append(rel)
            scaffold.note("  Skipped: %s exists but is not a parseable EDN "
                          "map; add :hidden [%s] manually" % (rel, quoted))
            return
        text = text[:brace] + " :hidden [%s]\n" % quoted + text[brace:]
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    scaffold.created.append("%s (:hidden)" % rel)
    scaffold.note("  Updated: %s (:hidden now covers %s); re-index the "
                  "graph in Logseq to apply" % (rel, ", ".join(hidden_dirs)))


def scaffold_para_notes(scaffold, tool, pages_path, today):
    """Opt-in human layer (issue #29; specs/namespaces.md).

    Logseq: namespaces are page-name prefixes, so only the two seed pages
    are needed. Obsidian: the PARA and Zettelkasten directory trees (with
    .gitkeep, mirroring scaffold_pipeline) plus the two seed pages. The
    seed pages are human-editable; the toolchain never touches them again.
    """
    if tool == "logseq":
        scaffold.write_file(os.path.join(pages_path, "para___schema.md"),
                            PARA_SCHEMA_LOGSEQ.format(date=today),
                            "para/schema")
        scaffold.write_file(os.path.join(pages_path, "notes___schema.md"),
                            NOTES_SCHEMA_LOGSEQ.format(date=today),
                            "notes/schema")
        return

    para_root = os.path.join(pages_path, wikilib.DEFAULT_PARA_DIR)
    notes_root = os.path.join(pages_path, wikilib.DEFAULT_NOTES_DIR)
    dirs = [os.path.join(para_root, d) for d in PARA_SUBDIRS]
    dirs += [os.path.join(notes_root, d) for d in NOTES_SUBDIRS]
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        if not os.listdir(directory):
            gitkeep = os.path.join(directory, ".gitkeep")
            with open(gitkeep, "w", encoding="utf-8"):
                pass
            scaffold.created.append(os.path.relpath(gitkeep, pages_path))
    scaffold.note("  Scaffolded: %s/{%s}/ and %s/{%s}/"
                  % (wikilib.DEFAULT_PARA_DIR, ",".join(PARA_SUBDIRS),
                     wikilib.DEFAULT_NOTES_DIR, ",".join(NOTES_SUBDIRS)))
    scaffold.write_file(os.path.join(para_root, "schema.md"),
                        PARA_SCHEMA_OBSIDIAN.format(date=today),
                        "para/schema.md")
    scaffold.write_file(os.path.join(notes_root, "schema.md"),
                        NOTES_SCHEMA_OBSIDIAN.format(date=today),
                        "notes/schema.md")


def scaffold_glossary(scaffold, tool, pages_path, template_dir, today):
    """Opt-in glossary layer (issue #54; specs/glossary.md REQ-1003): the
    index page plus one seed domain page from the G-0 template. Both are
    human-editable after scaffolding; the toolchain writes rows only at the
    /wiki-glossary checkpoint."""
    domain = stamp_schema_version(
        read_template(template_dir, "glossary-domain.md"), tool)
    if tool == "logseq":
        scaffold.write_file(os.path.join(pages_path, "glossary.md"),
                            stamp_schema_version(GLOSSARY_INDEX_LOGSEQ,
                                                 tool),
                            "glossary")
        scaffold.write_file(os.path.join(pages_path, "glossary___tech.md"),
                            domain, "glossary/tech")
        return
    root = os.path.join(pages_path, wikilib.DEFAULT_GLOSSARY_DIR)
    os.makedirs(root, exist_ok=True)
    scaffold.write_file(os.path.join(root, "_index.md"),
                        stamp_schema_version(GLOSSARY_INDEX_OBSIDIAN, tool),
                        "glossary/_index.md")
    scaffold.write_file(os.path.join(root, "tech.md"), domain,
                        "glossary/tech.md")


def build_config(tool, wiki_path, pages_dir, memory_path, namespaces, today,
                 with_para_notes=False, with_glossary=False):
    para_notes_block = ""
    if with_para_notes:
        para_notes_block = "\n" + PARA_NOTES_CONFIG_BLOCK.format(
            para_dir=wikilib.DEFAULT_PARA_DIR,
            notes_dir=wikilib.DEFAULT_NOTES_DIR,
        )
    if with_glossary:
        para_notes_block += "\n" + GLOSSARY_CONFIG_BLOCK.format(
            glossary_dir=wikilib.DEFAULT_GLOSSARY_DIR,
        )
    text = CONFIG_TEMPLATE.format(
        date=today,
        tool=tool,
        wiki_path=wiki_path,
        pages_dir=pages_dir,
        memory_path=memory_path,
        namespace_lines="\n".join("  - %s" % ns for ns in namespaces),
        source_type_lines="\n".join("  - %s" % t
                                    for t in wikilib.DEFAULT_SOURCE_TYPES),
        para_notes_block=para_notes_block,
    )
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


def default_templates_dir(tool):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    return os.path.join(repo_root, "templates", tool)


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold an llm-wiki vault (non-interactive)."
    )
    parser.add_argument("--wiki-path", required=True,
                        help="wiki/vault root directory (created if missing)")
    parser.add_argument("--tool", required=True,
                        help="note-taking tool: logseq or obsidian")
    parser.add_argument("--namespaces", nargs="+",
                        default=list(wikilib.DEFAULT_NAMESPACES),
                        help="namespace names (default: %s)"
                             % " ".join(wikilib.DEFAULT_NAMESPACES))
    parser.add_argument("--memory-path", default="",
                        help="Claude Code memory directory (optional)")
    parser.add_argument("--templates-dir", default=None,
                        help="template directory (default: the repo's "
                             "templates/<tool>/)")
    parser.add_argument("--date", default=None,
                        help="date stamp YYYY-MM-DD (default: today)")
    parser.add_argument("--with-glossary", action="store_true",
                        help="also scaffold the glossary layer: index page "
                             "plus one seed domain page "
                             "(specs/glossary.md, issue #54)")
    parser.add_argument("--with-para-notes", action="store_true",
                        help="also scaffold the human para/ + notes/ layer "
                             "(PARA + Zettelkasten seed pages; adds "
                             "para_dir/notes_dir to the config; see "
                             "docs/para-notes-workflow.md)")
    parser.add_argument("--no-gitignore", action="store_true",
                        help="do not write .gitignore")
    parser.add_argument("--no-config", action="store_true",
                        help="do not write llm-wiki.yml")
    parser.add_argument("--overwrite-config", action="store_true",
                        help="overwrite an existing llm-wiki.yml")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    args = parser.parse_args()

    scaffold = Scaffold()
    scaffold.quiet = args.json

    if args.tool not in wikilib.VALID_TOOLS:
        message = ("Invalid tool '%s'. Must be 'logseq' or 'obsidian'."
                   % args.tool)
        if args.json:
            wikilib.emit_json({"status": "critical", "criticals": [message]})
        else:
            print("CRITICAL: %s" % message, file=sys.stderr)
        return wikilib.EXIT_CRITICAL

    # Structural namespace names are lowercase (specs/schema.md REQ-580);
    # normalize whatever casing the caller passed.
    args.namespaces = [ns.lower() for ns in args.namespaces]

    for ns in args.namespaces:
        if not NAMESPACE_RE.match(ns):
            message = ("Invalid namespace name: '%s'. Namespace names must "
                       "start with a letter and contain only letters, "
                       "numbers, and hyphens." % ns)
            if args.json:
                wikilib.emit_json({"status": "critical",
                                   "criticals": [message]})
            else:
                print("CRITICAL: %s" % message, file=sys.stderr)
            return wikilib.EXIT_CRITICAL

    template_dir = args.templates_dir or default_templates_dir(args.tool)
    if not os.path.isdir(template_dir):
        message = ("Templates not found at %s. Pass --templates-dir or run "
                   "from a checkout of the llm-wiki repository."
                   % template_dir)
        if args.json:
            wikilib.emit_json({"status": "critical", "criticals": [message]})
        else:
            print("CRITICAL: %s" % message, file=sys.stderr)
        return wikilib.EXIT_CRITICAL

    wiki_path = os.path.abspath(wikilib.expand_path(args.wiki_path))
    memory_path = wikilib.expand_path(args.memory_path)
    pages_dir = "pages" if args.tool == "logseq" else ""
    pages_path = os.path.join(wiki_path, pages_dir) if pages_dir else wiki_path
    today = args.date or datetime.date.today().isoformat()

    os.makedirs(pages_path, exist_ok=True)

    scaffold.note("Creating wiki pages...")
    render_pages(scaffold, args.tool, wiki_path, pages_path, template_dir,
                 args.namespaces, today)

    scaffold.note("Scaffolding source pipeline (raw/ + ingested/)...")
    scaffold_pipeline(scaffold, wiki_path)

    if args.tool == "logseq":
        ensure_logseq_hidden(scaffold, wiki_path, ("raw", "ingested"))

    if args.with_para_notes:
        scaffold.note("Scaffolding human layer (para/ + notes/)...")
        scaffold_para_notes(scaffold, args.tool, pages_path, today)

    if args.with_glossary:
        scaffold.note("Scaffolding glossary layer (index + seed domain)...")
        scaffold_glossary(scaffold, args.tool, pages_path, template_dir,
                          today)

    if not args.no_gitignore:
        scaffold.write_file(os.path.join(wiki_path, ".gitignore"),
                            GITIGNORE[args.tool], ".gitignore")

    config_path = os.path.join(wiki_path, wikilib.CONFIG_FILENAME)
    if not args.no_config:
        content = build_config(args.tool, wiki_path, pages_dir, memory_path,
                               args.namespaces, today,
                               with_para_notes=args.with_para_notes,
                               with_glossary=args.with_glossary)
        if os.path.exists(config_path) and args.overwrite_config:
            os.remove(config_path)
        scaffold.write_file(config_path, content, wikilib.CONFIG_FILENAME)

    status, exit_code = wikilib.status_from_counts([], scaffold.skipped)
    if args.json:
        wikilib.emit_json({
            "status": status,
            "tool": args.tool,
            "wiki_path": wiki_path,
            "config_path": config_path if not args.no_config else None,
            "with_para_notes": args.with_para_notes,
            "with_glossary": args.with_glossary,
            "created": scaffold.created,
            "skipped": scaffold.skipped,
        })
    else:
        scaffold.note("Done. Wiki at: %s" % wiki_path)
        if scaffold.skipped:
            scaffold.note("Skipped %d existing file(s); nothing was "
                          "overwritten." % len(scaffold.skipped))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
