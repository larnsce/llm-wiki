# wiki-core

Shared foundation for the llm-wiki skill suite. This directory is NOT a user-facing
skill; it carries no SKILL.md and is never invoked directly. Every `wiki-*` skill
loads the reference files here instead of restating shared conventions.

## Why this exists

The openspec requirements (`openspec/specs/`) are the single source of truth. Skills
give operational instructions and cite REQ IDs; they do not restate normative
requirements. Conventions that more than one skill needs (config discovery, tool
formats, the trust layer, the cache architecture) live exactly once, in
`references/`, so no normative rule is stated in more than one place across
`skills/`.

## Contents

### references/

- [config.md](references/config.md) - how `llm-wiki.yml` is discovered, loaded, and
  validated, and what its keys mean.
- [formats.md](references/formats.md) - Logseq vs Obsidian file formats, page and
  hub naming, property syntax, routing-line and Access-Log formats.
- [trust.md](references/trust.md) - provenance and trust layer: `source-file::`,
  `reliability::`, `confidence::`, `s2-metrics::`, Pending Review, the
  `raw/` to `ingested/` lifecycle.
- [architecture.md](references/architecture.md) - the L1/L2 cache hierarchy,
  hub-index routing, LRU-Demote, the Access-Log, retrieval and commit discipline,
  and the namespace scope rule.

### scripts/

Not present yet. Executable helpers land with issue #12: `wikilib.py`,
`find_config.py`, `check_config.py`, `init_wiki.py` (python3 stdlib + bash only, no
package manager). Skills reference these by name where they will call them.
