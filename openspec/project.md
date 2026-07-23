# Project: llm-wiki

## Context

llm-wiki implements Andrej Karpathy's "LLM Wiki" concept — a persistent, structured
knowledge base maintained by an LLM (Claude Code) using a dual-layer cache architecture
inspired by CPU memory hierarchies.

- **Owner:** Mehmet Goekce / MEMOTECH
- **License:** MIT (open-source)
- **Repository:** github.com/larnsce/llm-wiki
- **Status:** Initial release (v1.0), actively developed

## Architecture

- **L1 (Fast, auto-loaded):** Claude Code memory directory (~10-20 files). Rules, gotchas,
  credentials, identity. Loaded every session. Git-excluded.
- **L2 (On-demand):** Logseq or Obsidian wiki (~50-200 pages). Projects, workflows,
  research, deep knowledge. Queried via the wiki skill suite (`/wiki-query` etc.).
  Git-tracked.

## Tech Stack

- **Runtime:** Claude Code (CLI)
- **Dependencies:** bash, python3, git (no npm, no pip)
- **Wiki tools:** Logseq (outliner) or Obsidian (flat markdown)
- **Config:** `llm-wiki.yml` (YAML)
- **Format:** Markdown with tool-specific conventions

## Stakeholders

| Role | Who | Responsibility |
|------|-----|---------------|
| Maintainer | Mehmet Goekce | Architecture, releases, specs |
| Contributors | Open-source community | Features, bug fixes, templates |
| Users | Claude Code users | Install, configure, use the wiki skills |

## Constraints

- Zero external dependencies beyond bash, python3, git
- Must work on macOS, Linux, WSL
- Must support both Logseq and Obsidian (identical capabilities, different format)
- Config always reads from `llm-wiki.yml`
- Max 3 wiki pages loaded simultaneously (LLM context budget)
- Credentials MUST stay in L1 (L2 is git-tracked)
- Append-only updates (never overwrite existing wiki content)

## Specs

| Spec | Covers |
|------|--------|
| specs/ingest.md | /wiki-ingest - source processing pipeline, interactive checkpoint, source pipeline, secret gate |
| specs/query.md | /wiki-query - two-stage retrieval, synthesis, write-back, Access-Log; one-hop neighbor section (v3.7, not yet implemented) |
| specs/lint.md | /wiki-lint - 12 automated health checks with auto-fix |
| specs/prune.md | /wiki-maintain prune - LRU-Demote index eviction |
| specs/schema.md | Page types, properties, validation, format rules, provenance |
| specs/config.md | llm-wiki.yml loading, validation, error handling |
| specs/setup.md | wiki-setup and installer behavior |
| specs/l1-l2-routing.md | L1/L2 boundary decision logic |
| specs/namespaces.md | Namespace scope rules (wiki/ vs para/ and notes/) |
| specs/citations.md | Block-native citations (v2.1, not yet implemented) |
| specs/audit.md | wiki-audit claim verification (v2.1, not yet implemented) |
| specs/update.md | wiki-update sanctioned non-append edits (v2.1, not yet implemented) |
| specs/prime.md | /wiki-query --prime context priming / auto-associative recall (v3.7, not yet implemented) |
