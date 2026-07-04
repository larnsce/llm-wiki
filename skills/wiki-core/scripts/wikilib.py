#!/usr/bin/env python3
"""Shared library for llm-wiki scripts.

Stdlib only. Provides:

- a minimal line-based parser for the deliberately flat llm-wiki.yml
  (no PyYAML; the config format is flat key: value lines plus one level
  of "- item" lists, per specs/config.md)
- config discovery (specs/config.md REQ-652..654)
- page enumeration and page-property parsing for both tool modes
  (logseq: flat pages/ dir with "___" namespace separator in filenames;
  obsidian: directory hierarchy with _index.md hub files)
- the canonical normalization used for semantic-equivalence checks:
  canonical newlines, trailing whitespace stripped per line, sorted
  frontmatter / leading-property-block key order

Exit code convention for all llm-wiki scripts:
0 = clean, 1 = warnings, 2 = critical.
"""

import json
import os
import re
import sys

EXIT_OK = 0
EXIT_WARNINGS = 1
EXIT_CRITICAL = 2

VALID_TOOLS = ("logseq", "obsidian")

DEFAULT_NAMESPACES = [
    "Business", "Tech", "Content", "Projects", "People", "Learning", "Reference",
]

DEFAULT_SOURCE_TYPES = [
    "papers", "clippings", "articles", "data", "notes", "assets",
]

CONFIG_FILENAME = "llm-wiki.yml"
POINTER_FILE = os.path.join("~", ".config", "llm-wiki", "config.yml")

_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^\s+-\s+(.*)$")
_LOGSEQ_PROP_RE = re.compile(r"^\s*(?:-\s+)?([A-Za-z][A-Za-z0-9_-]*)::\s*(.*)$")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def _strip_inline_comment(value):
    """Remove a trailing comment from a scalar value.

    A comment starts at a '#' that is at the start of the value or preceded
    by whitespace. Quoted values are unwrapped first by _clean_scalar.
    """
    if value.startswith("#"):
        return ""
    idx = 0
    while True:
        idx = value.find("#", idx)
        if idx == -1:
            return value.rstrip()
        if value[idx - 1] in (" ", "\t"):
            return value[:idx].rstrip()
        idx += 1


def _clean_scalar(value):
    value = _strip_inline_comment(value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value


def parse_config_text(text):
    """Parse the flat llm-wiki.yml format into a dict.

    Values are strings, except keys followed by "- item" lines, which
    become lists of strings. Comment lines and blank lines are ignored.
    """
    config = {}
    open_key = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item_match = _LIST_ITEM_RE.match(line)
        if item_match and open_key is not None:
            if not isinstance(config[open_key], list):
                config[open_key] = []
            config[open_key].append(_clean_scalar(item_match.group(1)))
            continue
        key_match = _TOP_KEY_RE.match(line)
        if key_match:
            key = key_match.group(1)
            value = _clean_scalar(key_match.group(2))
            config[key] = value
            open_key = key if value == "" else None
            continue
        # Unrecognized line; the format is deliberately flat, ignore it.
        open_key = None
    return config


def load_config(path):
    """Read and parse a config file. Returns the dict; adds no keys."""
    with open(path, "r", encoding="utf-8") as handle:
        return parse_config_text(handle.read())


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def expand_path(path):
    return os.path.expanduser(path) if path else path


def wiki_root(config):
    return expand_path(config.get("wiki_path", ""))


def pages_root(config):
    """Resolve full_pages_path per REQ-641/642."""
    root = wiki_root(config)
    pages_dir = config.get("pages_dir", "")
    if pages_dir:
        return os.path.join(root, pages_dir)
    return root


# ---------------------------------------------------------------------------
# Config discovery (REQ-652..654)
# ---------------------------------------------------------------------------

def discover_config(cwd=None, env=None):
    """Locate llm-wiki.yml. Returns (path, method) or (None, None).

    Order, first hit wins:
    1. $LLM_WIKI_CONFIG environment variable
    2. walk up from cwd to $HOME (inclusive)
    3. global pointer file ~/.config/llm-wiki/config.yml (wiki_path key)

    Raises ValueError if $LLM_WIKI_CONFIG is set but does not point at an
    existing file (an explicitly set env var must not be silently skipped).
    """
    env = os.environ if env is None else env
    cwd = os.getcwd() if cwd is None else cwd

    env_path = env.get("LLM_WIKI_CONFIG", "")
    if env_path:
        candidate = expand_path(env_path)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate), "env"
        raise ValueError(
            "LLM_WIKI_CONFIG is set to '%s' but no file exists there." % env_path
        )

    home = os.path.realpath(os.path.expanduser("~"))
    current = os.path.realpath(cwd)
    while True:
        candidate = os.path.join(current, CONFIG_FILENAME)
        if os.path.isfile(candidate):
            return candidate, "walk-up"
        if current == home:
            break
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    pointer = expand_path(POINTER_FILE)
    if os.path.isfile(pointer):
        pointer_config = load_config(pointer)
        pointed_root = expand_path(pointer_config.get("wiki_path", ""))
        if pointed_root:
            candidate = os.path.join(pointed_root, CONFIG_FILENAME)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate), "pointer"

    return None, None


DISCOVERY_FAILURE_MESSAGE = (
    "llm-wiki.yml not found. Run /wiki-setup to create one.\n"
    "Discovery order: $LLM_WIKI_CONFIG, walk-up from the current directory\n"
    "to $HOME, then the pointer file ~/.config/llm-wiki/config.yml."
)


# ---------------------------------------------------------------------------
# Page enumeration
# ---------------------------------------------------------------------------

def _pruned_dirs(config):
    pruned = {
        config.get("raw_dir") or "raw",
        config.get("ingested_dir") or "ingested",
        "logseq",
        "journals",
        "assets",
    }
    for key in ("para_dir", "notes_dir"):
        value = config.get(key)
        if value:
            pruned.add(value.strip("/"))
    return pruned


def enumerate_pages(config):
    """List wiki pages as dicts: {"name": page name, "path": file path}.

    Logseq: flat *.md files directly in pages_dir; "___" in the filename
    is the namespace separator (Wiki___Tech___Docker.md -> Wiki/Tech/Docker).

    Obsidian: recursive walk of the vault; the relative path without .md is
    the page name; _index.md maps to its parent directory's namespace path.
    Hidden directories and the raw/ingested (and para/notes) trees are skipped.
    """
    tool = config.get("tool", "")
    root = pages_root(config)
    pages = []
    if not os.path.isdir(root):
        return pages

    if tool == "logseq":
        for entry in sorted(os.listdir(root)):
            if not entry.endswith(".md"):
                continue
            path = os.path.join(root, entry)
            if not os.path.isfile(path):
                continue
            name = entry[:-3].replace("___", "/")
            pages.append({"name": name, "path": path})
        return pages

    pruned = _pruned_dirs(config)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith(".")
            and (rel_dir != "." or d not in pruned)
        )
        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            path = os.path.join(dirpath, filename)
            rel = os.path.relpath(path, root)
            if filename == "_index.md":
                name = os.path.dirname(rel).replace(os.sep, "/")
                if not name or name == ".":
                    continue
            else:
                name = rel[:-3].replace(os.sep, "/")
            pages.append({"name": name, "path": path})
    pages.sort(key=lambda page: page["name"])
    return pages


# ---------------------------------------------------------------------------
# Page-property parsing
# ---------------------------------------------------------------------------

def parse_page_properties(text, tool):
    """Parse page properties (key -> value) from page text.

    Logseq: the leading block of "key:: value" (optionally "- key:: value")
    lines at the top of the file.

    Obsidian: flat "key: value" lines inside the YAML frontmatter fences.
    """
    props = {}
    lines = text.splitlines()
    if tool == "logseq":
        for line in lines:
            if not line.strip():
                if props:
                    break
                continue
            match = _LOGSEQ_PROP_RE.match(line)
            if match:
                props[match.group(1)] = _clean_scalar(match.group(2))
            else:
                break
        return props

    if not lines or lines[0].strip() != "---":
        return props
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = _FRONTMATTER_KEY_RE.match(line)
        if match:
            props[match.group(1)] = _clean_scalar(match.group(2))
    return props


def read_page_properties(path, tool):
    with open(path, "r", encoding="utf-8") as handle:
        return parse_page_properties(handle.read(), tool)


# ---------------------------------------------------------------------------
# Canonical normalization (semantic-equivalence checks)
# ---------------------------------------------------------------------------

def _prop_sort_key(line):
    match = _LOGSEQ_PROP_RE.match(line)
    return match.group(1) if match else line


def normalize_page_text(text, tool):
    """Return the canonical form of page text for equivalence comparison.

    Normalization, in order:
    1. newlines canonicalized to "\\n"
    2. trailing whitespace stripped from every line
    3. property keys sorted: the YAML frontmatter block (obsidian) or the
       leading "key:: value" property block (logseq)
    4. trailing blank lines collapsed to a single final newline

    Two files that differ only in whitespace, newline style, or property
    key order normalize to the same string.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]

    if tool == "obsidian" and lines and lines[0] == "---":
        try:
            end = lines[1:].index("---") + 1
        except ValueError:
            end = -1
        if end > 1:
            block = sorted(lines[1:end], key=_prop_sort_key)
            lines = [lines[0]] + block + lines[end:]
    elif tool == "logseq":
        end = 0
        while end < len(lines) and _LOGSEQ_PROP_RE.match(lines[end]):
            end += 1
        if end > 0:
            lines = sorted(lines[:end], key=_prop_sort_key) + lines[end:]

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def emit_json(payload):
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def status_from_counts(criticals, warnings):
    if criticals:
        return "critical", EXIT_CRITICAL
    if warnings:
        return "warnings", EXIT_WARNINGS
    return "ok", EXIT_OK
