# llm-wiki

[![License: MIT](https://img.shields.io/github/license/larnsce/llm-wiki)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/larnsce/llm-wiki)](https://github.com/larnsce/llm-wiki/commits)

Build [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) with Claude Code: a suite of eight skills that maintain a structured, cross-referenced knowledge base in Logseq or Obsidian, on a two-layer cache architecture (L1/L2) with a source-provenance and trust layer.

## What is this?

![Wiki graph view after setup](docs/graph-view.png)
*Your wiki after a few ingests: interconnected knowledge pages in Logseq's graph view.*

In April 2026, Andrej Karpathy published a gist called "LLM Wiki". The idea: let an LLM maintain a structured, cross-referenced wiki for you. Feed it raw sources, it extracts facts, links them together, and keeps everything consistent. The wiki becomes a persistent, compounding artifact instead of a graveyard of stale notes.

llm-wiki is an implementation of that idea. Claude Code is the LLM brain; Logseq or Obsidian is the wiki UI. Version 2 replaces the original single `/wiki` command with a suite of focused skills backed by a spec canon (`openspec/specs/`), shared scripts, and a mechanical test harness. For how the design compares against the original gist, in both directions, see [docs/design-vs-karpathy.md](docs/design-vs-karpathy.md).

## The skill suite

| Skill | What it does |
|-------|--------------|
| `wiki-setup` | Initialize or upgrade a wiki: config discovery and validation, fresh scaffolding, legacy v1 detection, Schema-page upgrade |
| `wiki-ingest` | The write path: process a source (URL, file, text, or the `raw/` queue), update pages append-only with provenance; interactive by default, `--auto` for queue draining, `--import` for existing notes |
| `wiki-query` | The read path: two-stage retrieval via hub indexes, targeted page reads, Access-Log update, synthesized answer with sources |
| `wiki-lint` | Two-layer health check: mechanical rules via `lint.py` and `check_canon.py`, judgment rules on top; fixes only with confirmation |
| `wiki-maintain` | Status report (read-only metrics, hot/cold cache profile) and prune (LRU-Demote eviction of cold pages from the live index) |
| `wiki-migrate` | One-time, interactive v1-to-v2 corpus migration driving `migrate_wiki.py` |
| `wiki-audit` | Stub, ships in v2.1: verify a page claim by claim against its cited sources |
| `wiki-update` | Stub, ships in v2.1: the sanctioned non-append edit path for cited content |

`skills/wiki-core/` is not a skill; it is the shared library the suite runs on: the scripts (`init_wiki.py`, `lint.py`, `check_canon.py`, `secret_scan.py`, `migrate_wiki.py`, config discovery) and the shared reference docs (config, architecture, formats, trust).

## Install

```bash
git clone https://github.com/larnsce/llm-wiki.git
cd llm-wiki
./setup.sh
```

`setup.sh` copies (or, with `--symlink`, links) the skills into `~/.claude/skills/` (or `<project>/.claude/skills/` with `--project`), optionally scaffolds a wiki via `init_wiki.py` (`--init --tool logseq --wiki-path ~/notes`), and optionally writes a global pointer file so the skills find your wiki from any directory. It patches no files; config is discovered at runtime. Run `./setup.sh --help` for all options.

Requirements: bash, python3, git. No npm, no pip.

## Quickstart

```
/wiki-setup                        # scaffold or validate the wiki
/wiki-ingest "your first source"   # write path: source -> pages
/wiki-query "what do I know about X?"
/wiki-lint                         # health check, fixes on confirmation
/wiki-maintain                     # status report; "prune" to evict cold pages
```

The wiki starts sparse and gets denser with every ingest. Ingest is interactive by default: it presents a consolidated plan (pages to create and update, reliability ratings) and waits for your approval before writing anything.

## Support tiering

- **Logseq is tier-1.** It is the mode the maintainer uses daily; the outliner format is what the ingest write discipline was designed around.
- **Obsidian is experimental.** The scripts and the test harness exercise obsidian mode mechanically (scaffolding, lint, fixtures), but no CI currently instantiates a real Obsidian vault and diffs the rendered output. Treat obsidian mode as functional but less proven until that gate exists.

## The L1/L2 architecture

Some knowledge must be available in every session, before you ask a question ("always use ISO 8601 dates"). If the LLM has to query the wiki to learn these rules, it has already made the mistake. Other knowledge only matters in specific contexts, and loading it every session wastes the context window. The design maps onto a CPU cache hierarchy:

| Layer | What | Loading | Contains |
|-------|------|---------|----------|
| **L1** | Claude Code Memory (~10-20 files) | Auto-loaded every session | Rules, gotchas, identity, credentials |
| **L2** | Wiki (~50-200 pages) | On demand via `/wiki-query` | Projects, workflows, research, deep knowledge |

The routing rule: would a mistake without this knowledge be dangerous or embarrassing? L1. Merely inconvenient? L2. Credentials must live in L1: the wiki is git-tracked, the L1 memory directory is not.

Two cache mechanisms keep L2 precise as it grows:

- **Hub-index routing.** Every hub page carries an `### Index` of routing lines (`[[page]] -- description #tags`). Query reads the cheap indexes first, picks the best 3-5 pages, and reads only those; full-text grep is the L3 fallback. Every full-page read lands in an append-only Access-Log together with the reason it was picked.
- **LRU-Demote.** `/wiki-maintain prune` evicts pages with no access in N months (default 6) from the live index. Eviction is not deletion: the file stays, links stay valid, and the page is re-promoted on a re-hit.

For the deep-dive, see [docs/l1-l2-architecture.md](docs/l1-l2-architecture.md).

## Source provenance and trust

With the source pipeline configured, ingest is reproducible: a source dropped in `raw/` is synthesized into pages, then moved to `ingested/<type>/` in the same git commit as the page edits. The move is the provenance record. Pages carry `source-file::` (which file they rest on) and `reliability:: high | medium | low` (how good the sources are; the page takes the minimum across its claims). Weakly-supported pages get a `## Pending Review` section until corroborated. `reliability::` and `confidence::` (is this current and verified) are separate axes and never cross-derived.

Before any source file is archived into the git-tracked `ingested/` tree, a pre-archive secret gate (`secret_scan.py`) scans its bytes for credential patterns; blocking findings stop the move. Source types listed in `sensitive_source_types` never enter git history at all.

## The schema

The schema is the contract between you and the LLM: page types (Entity, Project, Knowledge, Feedback, Hub) with required properties, namespaces, lint rules, and the provenance conventions. Pages are stamped with `schema-spec-version::` so lint can distinguish a v2 page from a grandfathered v1 page. The canonical rules live in `openspec/specs/`, mirrored into the vault's Schema page by the templates; `check_canon.py` keeps those surfaces from drifting. See [docs/schema-reference.md](docs/schema-reference.md).

## Migrating from v1

- **From the single `/wiki` command:** see [docs/migration-v2.md](docs/migration-v2.md). The legacy `.claude/commands/wiki.md` file keeps working but is unsupported; `wiki-setup` detects it and offers removal.
- **An existing pre-v2 page corpus:** see [docs/migration.md](docs/migration.md). Lint grandfathers unmigrated pages by default; `wiki-migrate` drives the one-time converter.

## Testing

`bash skills/wiki-core/scripts/test_pipeline.sh` runs the mechanical harness (both tool modes, fixtures generated at runtime), golden transcripts in `tests/golden/` pin the LLM-side behaviors, and [docs/testing.md](docs/testing.md) describes the manual end-to-end protocol.

## Documentation

- [FAQ](docs/faq.md) - Common questions before you run `setup.sh`
- [Troubleshooting](docs/troubleshooting.md) - Setup, integration, and runtime issues
- [L1/L2 Architecture](docs/l1-l2-architecture.md) - Why two layers, how to route knowledge
- [Schema Reference](docs/schema-reference.md) - Page types, properties, lint rules
- [Logseq vs. Obsidian](docs/logseq-vs-obsidian.md) - Detailed comparison and migration notes
- [Design vs. the Karpathy gist](docs/design-vs-karpathy.md) - What the gist wanted, what v2 restores, what this tool adds
- [Migration from v1 (command)](docs/migration-v2.md) - Single command to skill suite
- [Migration from v1 (corpus)](docs/migration.md) - Grandfather mode and the converter
- [Testing](docs/testing.md) - Harness, golden transcripts, manual protocol
- [Literature Research](docs/literature-research.md) - Pipeline (Connected Papers, Semantic Scholar, Elicit, Zotero) and how the wiki skills fit
- [Firefox Web-Clipper](docs/web-clipper-firefox.md) - Clip web pages into the `raw/` queue with MarkDownload on macOS
- [PARA + Zettelkasten workflow](docs/para-notes-workflow.md) - Run `para/` and `notes/` in the same graph; the promotion seam into `wiki/`
- [Zotero setup](docs/zotero-setup.md) - Wire Zotero so literature notes are born as `notes/literature/@citekey`
- [Roadmap: v2.2](docs/roadmap-v2.2-para-notes-zotero.md) - The para/notes/Zotero assessment and issue breakdown

## Credits

- Inspired by [Andrej Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Built with [Claude Code](https://claude.ai/code)
- Works with [Logseq](https://logseq.com/) and [Obsidian](https://obsidian.md/)

## License

MIT - see [LICENSE](LICENSE) for details.
