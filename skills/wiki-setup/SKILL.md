---
name: wiki-setup
description: Initialize a new llm-wiki (Logseq or Obsidian), write llm-wiki.yml and the global pointer file, seed the Schema/Dashboard/hub templates, and migrate a v1 single-command install. Not yet implemented.
---

# wiki-setup

STUB. This skill will initialize a wiki from scratch: prompt for the tool (Logseq
or Obsidian) and paths, write `llm-wiki.yml` and the global pointer file
`~/.config/llm-wiki/config.yml`, seed the Schema, Dashboard, Access-Log, and hub
pages from `templates/`, optionally run `git init`, verify the install (calling the
planned `init_wiki.py` and `check_config.py` from wiki-core/scripts), and detect a
legacy v1 `.claude/commands/wiki.md` install, offering removal. Implementation
lands with issue #13.

Spec: openspec/specs/setup.md REQ-700..780
