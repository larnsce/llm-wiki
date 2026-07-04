#!/usr/bin/env python3
"""Locate llm-wiki.yml per the discovery order in specs/config.md.

Order (REQ-652, first hit wins):
1. the path in the $LLM_WIKI_CONFIG environment variable, if set
2. walking up from the current working directory to $HOME (inclusive)
3. the global pointer file ~/.config/llm-wiki/config.yml, whose wiki_path
   names the wiki root containing the real llm-wiki.yml

Exit codes: 0 = found, 2 = not found (REQ-602/654) or env var invalid.
"""

import argparse
import sys

import wikilib


def main():
    parser = argparse.ArgumentParser(
        description="Locate llm-wiki.yml via the standard discovery order."
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    args = parser.parse_args()

    try:
        path, method = wikilib.discover_config()
    except ValueError as error:
        if args.json:
            wikilib.emit_json({
                "found": False,
                "error": str(error),
                "status": "critical",
            })
        else:
            print("ERROR: %s" % error, file=sys.stderr)
        return wikilib.EXIT_CRITICAL

    if path is None:
        if args.json:
            wikilib.emit_json({
                "found": False,
                "error": "llm-wiki.yml not found. Run /wiki-setup to create one.",
                "status": "critical",
            })
        else:
            print(wikilib.DISCOVERY_FAILURE_MESSAGE, file=sys.stderr)
        return wikilib.EXIT_CRITICAL

    if args.json:
        wikilib.emit_json({
            "found": True,
            "config_path": path,
            "method": method,
            "status": "ok",
        })
    else:
        print(path)
        print("(discovered via: %s)" % method, file=sys.stderr)
    return wikilib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
