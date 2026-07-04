# Configuration: llm-wiki.yml

Spec: openspec/specs/config.md REQ-600..654

Every skill reads `llm-wiki.yml` as its FIRST operation, before any wiki page
operation (REQ-601). All downstream behavior (tool mode, paths, namespaces) depends
on this file.

## Discovery

Locate `llm-wiki.yml` in this order, first hit wins (REQ-652):

1. the path in the `LLM_WIKI_CONFIG` environment variable, if set;
2. walking up from the current working directory to `$HOME` (inclusive);
3. the global pointer file `~/.config/llm-wiki/config.yml`, whose `wiki_path` names
   the wiki root containing the real `llm-wiki.yml`. The pointer file is written by
   wiki-setup so skills work from any project directory (REQ-653); it contains only
   `wiki_path`.

When all three steps fail, report "llm-wiki.yml not found. Run /wiki-setup to create
one." and abort (REQ-602, REQ-654).

Planned scripts (issue #12): `find_config.py` implements this discovery;
`check_config.py` validates a discovered config. Until they land, perform the steps
manually.

## Keys

Required (REQ-610..613):

- `tool`: `logseq` or `obsidian`; no other values.
- `wiki_path`: absolute or tilde-expandable path to the wiki root.
- `pages_dir`: path relative to `wiki_path` (typically `pages` for Logseq, empty
  string for Obsidian).
- `namespaces`: non-empty array of top-level namespace names.

Optional (REQ-620..624):

- `memory_path`: path to the L1 memory directory. Absent means L1 Memory features
  (query supplementation, L1/L2 duplicate detection) are disabled; this is a
  graceful degradation, not an error.
- Source pipeline: `raw_dir` (default `raw`), `ingested_dir` (default `ingested`),
  `source_types` (default `papers, clippings, articles, data, notes, assets`),
  `default_source_type`. Absent keys disable the source pipeline.
- `sensitive_source_types`: source types whose archived bytes must not enter git
  history (see openspec/specs/ingest.md REQ-046).

## Validation

Per REQ-630..634: an invalid `tool` value, a non-existent `wiki_path`, or an empty
`namespaces` array aborts with the spec's error message; a missing `pages_dir`
directory or a non-Title-Case namespace name warns but continues.

## Path handling

Expand `~` to `$HOME` in `wiki_path` and `memory_path` before use (REQ-640). Resolve
the pages path as `wiki_path + "/" + pages_dir` (REQ-641); for Obsidian with empty
`pages_dir`, the pages path equals `wiki_path` (REQ-642).

## Tool mode propagation

The `tool` value determines ALL downstream format decisions (property syntax, file
naming, content format, hub file naming; REQ-650) and must stay consistent for the
whole session (REQ-651). The format rules themselves live in
[formats.md](formats.md).
