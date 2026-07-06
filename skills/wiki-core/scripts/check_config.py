#!/usr/bin/env python3
"""Validate llm-wiki.yml against specs/config.md.

Checks:
- required keys: tool, wiki_path, pages_dir, namespaces (REQ-610..613)
- tool value strictly logseq or obsidian (REQ-630)
- wiki_path exists on disk after tilde expansion (REQ-631)
- pages_dir resolves; missing directory is a warning (REQ-632)
- namespaces non-empty (REQ-633), lowercase-structural advisory (REQ-634)
- v2 source-pipeline keys (REQ-623): raw_dir, ingested_dir, source_types,
  default_source_type; missing keys are WARNINGS with a copy-paste snippet
- sensitive_source_types subset of source_types (REQ-624)
- para_dir / notes_dir: optional keys (config.md REQ-625, namespaces.md
  REQ-980); defaults 'para' and 'notes' apply when absent. When present,
  shape-only validation: relative to the pages directory (no absolute
  path, no tilde), no '..' traversal (criticals), lowercase advisory
  (warning, schema.md REQ-580)
- archive_db: optional key (config.md REQ-626): path to the archive.db
  capture database for the voice ingest workflow. Shape-only: the file is
  not required to exist (absence means an empty voice queue)
- index_db: optional key (config.md REQ-627): path where rebuild_index.py
  writes the derived index database. Shape-only; created on first rebuild

Exit codes: 0 = clean, 1 = warnings only, 2 = critical.
"""

import argparse
import os
import sys

import wikilib

REQUIRED_KEYS = ("tool", "wiki_path", "pages_dir", "namespaces")

PIPELINE_KEYS = ("raw_dir", "ingested_dir", "source_types", "default_source_type")

# Optional human-namespace keys (REQ-625) and their defaults.
HUMAN_NAMESPACE_KEYS = (
    ("para_dir", wikilib.DEFAULT_PARA_DIR),
    ("notes_dir", wikilib.DEFAULT_NOTES_DIR),
)

KNOWN_KEYS = set(REQUIRED_KEYS) | set(PIPELINE_KEYS) | {
    "memory_path",
    "sensitive_source_types",
    "para_dir",
    "notes_dir",
    "archive_db",
    "index_db",
}

PIPELINE_SNIPPET = """raw_dir: raw
ingested_dir: ingested
source_types:
  - papers
  - clippings
  - articles
  - data
  - notes
  - assets
default_source_type: papers"""


def check(config, config_path, skip_path_checks=False):
    criticals = []
    warnings = []

    for key in REQUIRED_KEYS:
        if key not in config:
            criticals.append(
                "Missing required key '%s' in %s." % (key, config_path)
            )

    tool = config.get("tool")
    if tool is not None and tool not in wikilib.VALID_TOOLS:
        criticals.append(
            "Invalid tool '%s'. Must be 'logseq' or 'obsidian'." % tool
        )

    wiki_path = wikilib.expand_path(config.get("wiki_path", ""))
    if "wiki_path" in config and not skip_path_checks:
        if not wiki_path or not os.path.isdir(wiki_path):
            criticals.append(
                "Wiki path '%s' does not exist." % config.get("wiki_path", "")
            )

    pages_dir = config.get("pages_dir", "")
    if isinstance(pages_dir, str) and pages_dir and not skip_path_checks:
        if wiki_path and os.path.isdir(wiki_path):
            full_pages_path = os.path.join(wiki_path, pages_dir)
            if not os.path.isdir(full_pages_path):
                warnings.append(
                    "Pages directory '%s' does not exist yet (it may be "
                    "created during setup)." % full_pages_path
                )

    namespaces = config.get("namespaces")
    if "namespaces" in config:
        if not isinstance(namespaces, list) or not namespaces:
            criticals.append("No namespaces configured in llm-wiki.yml.")
        else:
            for namespace in namespaces:
                if (namespace != namespace.lower() or "_" in namespace
                        or " " in namespace):
                    suggested = namespace.lower().replace("_", "-")
                    suggested = suggested.replace(" ", "-")
                    warnings.append(
                        "Namespace '%s' is not lowercase-structural "
                        "(REQ-634; specs/schema.md REQ-580/580a: lowercase, "
                        "hyphen-only). Consider '%s'."
                        % (namespace, suggested)
                    )

    missing_pipeline = [key for key in PIPELINE_KEYS if key not in config]
    if missing_pipeline:
        warnings.append(
            "Source pipeline is disabled: missing key(s) %s (REQ-623). "
            "To enable it, add this to %s:\n%s"
            % (", ".join(missing_pipeline), config_path, PIPELINE_SNIPPET)
        )
    else:
        source_types = config.get("source_types")
        if not isinstance(source_types, list) or not source_types:
            criticals.append(
                "'source_types' must be a non-empty list (REQ-623)."
            )
            source_types = []
        default_type = config.get("default_source_type", "")
        if source_types and default_type not in source_types:
            warnings.append(
                "default_source_type '%s' is not in source_types %s "
                "(REQ-623)." % (default_type, source_types)
            )
        sensitive = config.get("sensitive_source_types")
        if isinstance(sensitive, list):
            extras = [t for t in sensitive if t not in source_types]
            if extras:
                warnings.append(
                    "sensitive_source_types entries %s are not in "
                    "source_types (REQ-624). Add them:\nsource_types:\n%s"
                    % (extras, "\n".join("  - %s" % t
                                         for t in source_types + extras))
                )

    # Human namespaces (REQ-625/REQ-980): optional; shape-only checks. The
    # defaults apply when a key is absent (or present but empty), so neither
    # case is an error.
    for key, default in HUMAN_NAMESPACE_KEYS:
        if key not in config:
            continue
        value = config.get(key)
        if not isinstance(value, str) or not value:
            warnings.append(
                "'%s' is present but empty; the default '%s' applies "
                "(REQ-625)." % (key, default)
            )
            continue
        if value.startswith(("/", "~")) or os.path.isabs(value):
            criticals.append(
                "'%s' must be a path relative to the pages directory, "
                "got '%s' (REQ-625)." % (key, value)
            )
        elif ".." in value.replace("\\", "/").split("/"):
            criticals.append(
                "'%s' must not contain path traversal ('..'), got '%s' "
                "(REQ-625)." % (key, value)
            )
        if value != value.lower():
            warnings.append(
                "'%s' should be lowercase (structural naming, "
                "specs/schema.md REQ-580). Consider '%s'."
                % (key, value.lower())
            )

    unknown = sorted(set(config) - KNOWN_KEYS)
    if unknown:
        warnings.append(
            "Unknown key(s) %s in %s; they are ignored. Check for typos."
            % (", ".join(unknown), config_path)
        )

    return criticals, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Validate llm-wiki.yml against specs/config.md."
    )
    parser.add_argument(
        "config", nargs="?", default=None,
        help="path to llm-wiki.yml (default: standard discovery order)",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    parser.add_argument(
        "--skip-path-checks", action="store_true",
        help="validate content only; do not check paths on disk",
    )
    args = parser.parse_args()

    if args.config:
        config_path = args.config
        if not os.path.isfile(config_path):
            message = "Config file '%s' not found." % config_path
            if args.json:
                wikilib.emit_json({"status": "critical",
                                   "criticals": [message], "warnings": []})
            else:
                print("CRITICAL: %s" % message, file=sys.stderr)
            return wikilib.EXIT_CRITICAL
    else:
        try:
            config_path, _ = wikilib.discover_config()
        except ValueError as error:
            config_path = None
            discovery_error = str(error)
        else:
            discovery_error = (
                "llm-wiki.yml not found. Run /wiki-setup to create one."
            )
        if config_path is None:
            if args.json:
                wikilib.emit_json({"status": "critical",
                                   "criticals": [discovery_error],
                                   "warnings": []})
            else:
                print("CRITICAL: %s" % discovery_error, file=sys.stderr)
            return wikilib.EXIT_CRITICAL

    config = wikilib.load_config(config_path)
    criticals, warnings = check(config, config_path,
                                skip_path_checks=args.skip_path_checks)
    status, exit_code = wikilib.status_from_counts(criticals, warnings)

    if args.json:
        wikilib.emit_json({
            "config_path": config_path,
            "status": status,
            "criticals": criticals,
            "warnings": warnings,
        })
        return exit_code

    print("Checking: %s" % config_path)
    for message in criticals:
        print("CRITICAL: %s" % message)
    for message in warnings:
        print("WARNING: %s" % message)
    if status == "ok":
        print("OK: config is valid.")
    else:
        print("Result: %d critical, %d warning(s)."
              % (len(criticals), len(warnings)))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
