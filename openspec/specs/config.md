# Spec: Configuration - llm-wiki.yml Loading & Validation

## Description

Every wiki skill reads `llm-wiki.yml` before doing anything else. This config
file determines tool mode (Logseq vs Obsidian), file paths, and namespace structure.
All downstream behavior depends on this file being valid.

---

## Requirements

### Config File Location

- REQ-600: The config file MUST be named `llm-wiki.yml` and located in the wiki
  root directory (the path specified as `wiki_path` in the config itself).
- REQ-601: Every wiki skill (ingest, query, lint, maintain) MUST read the config
  file as its first operation, before any wiki page operations.
- REQ-602: If no config file can be discovered (REQ-652), the system SHALL display
  an error: "llm-wiki.yml not found. Run /wiki-setup to create one." and abort.

### Config Discovery

- REQ-652: Commands SHALL locate `llm-wiki.yml` in this order, first hit wins:
  1. the path in the `LLM_WIKI_CONFIG` environment variable, if set;
  2. walking up from the current working directory to `$HOME` (inclusive);
  3. the global pointer file `~/.config/llm-wiki/config.yml`, whose `wiki_path`
     names the wiki root containing the real `llm-wiki.yml`.
- REQ-653: The global pointer file is written by /wiki-setup so that the wiki skills
  work from any project directory. It contains only `wiki_path`.
- REQ-654: When discovery fails at all three steps, the REQ-602 error applies.

### Required Keys

- REQ-610: The config MUST contain the key `tool` with value `logseq` or `obsidian`.
  No other values are allowed.
- REQ-611: The config MUST contain the key `wiki_path` with an absolute or
  tilde-expandable path to the wiki root directory.
- REQ-612: The config MUST contain the key `pages_dir` with a path relative to
  `wiki_path`. For Logseq this is typically `pages`. For Obsidian this is
  typically an empty string.
- REQ-613: The config MUST contain the key `namespaces` with a non-empty array
  of namespace names.

### Optional Keys

- REQ-620: The config MAY contain the key `memory_path` with a path to the L1
  memory directory. If absent, L1 Memory features (query supplementation,
  L1/L2 duplicate detection) are disabled.
- REQ-623: The config MAY configure the source pipeline with the keys `raw_dir`
  (default `raw`), `ingested_dir` (default `ingested`), `source_types` (array;
  default `papers, clippings, articles, data, notes, assets`), and
  `default_source_type` (one of `source_types`). When these keys are absent the
  source pipeline (specs/ingest.md Source Pipeline section) is disabled and ingest
  behaves as the base workflow.
- REQ-624: The config MAY contain `sensitive_source_types`: an array of source
  types (subset of `source_types`) whose archived bytes MUST NOT enter git history
  (specs/ingest.md REQ-046). Typical values: `notes`, `data`. This key already
  covers PII in promoted `para/`/`notes/` content (specs/namespaces.md REQ-981);
  no additional key is needed for the human namespaces.
- REQ-625: The config MAY contain the keys `para_dir` (default `para`) and
  `notes_dir` (default `notes`): paths relative to the pages directory naming the
  human-owned namespaces (specs/namespaces.md). They are recognized by the
  namespace scope rule and the namespace-hygiene lint check; when absent, the
  defaults apply and the namespaces are still recognized.
- REQ-626: The config MAY contain the key `archive_db` (default
  `~/archive/archive.db`, the convention of `docs/voice-pipeline.md`): the path
  to the archive.db capture database consumed by the voice ingest workflow
  (specs/ingest.md Voice Sources; specs/storage.md). The path is expanded like
  `wiki_path` (tilde to `$HOME`) and is NOT required to exist: absence of the
  file means the voice queue is empty, not a config error. The placement
  invariants of specs/storage.md REQ-1103 (outside git, or gitignored) bind
  whatever value is configured; validation is shape-only.
- REQ-627: The config MAY contain the key `index_db` (default
  `~/archive/index.db`): the path where `rebuild_index.py` writes the derived,
  disposable index database (specs/storage.md REQ-1130..1133). Expanded like
  `wiki_path`; not required to exist (the first rebuild creates it). The
  REQ-1103 placement invariants bind the value: when the path resolves inside
  the vault's git-tracked tree and is not gitignored, the rebuild SHALL refuse
  to write.
- REQ-628: The config MAY contain the key `glossary_dir` (default
  `glossary`): the path, relative to the pages directory, naming the
  human-decided glossary namespace (`specs/glossary.md`,
  `specs/namespaces.md` REQ-960/980). Recognized by namespace-hygiene
  (lint rule 14) and the glossary structure check (rule 15); when absent,
  the default applies and the namespace is still recognized. Shape rules as
  for `para_dir`/`notes_dir` (REQ-625).
- REQ-629: The config MAY contain the key `journals_dir` (default
  `journals`): the path, relative to `wiki_path`, naming the journal
  (daily notes) directory. For Logseq this is the native `journals/`
  directory, a sibling of `pages/`; for Obsidian it is the daily-notes
  folder relative to the vault root. Consumed by the journal seam
  (specs/ingest.md REQ-090..095), page enumeration pruning, and the
  namespace classification in lint. When absent, the default applies and
  journal pages are still recognized. Shape rules as for
  `para_dir`/`notes_dir` (REQ-625). The journal namespace stays
  human-owned; the journal seam's daily Ingested block is the single
  sanctioned machine write into it.

### Validation Rules

- REQ-630: If `tool` is not `logseq` or `obsidian`, the system SHALL display:
  "Invalid tool '{value}'. Must be 'logseq' or 'obsidian'." and abort.
- REQ-631: If `wiki_path` does not exist on disk (after tilde expansion), the
  system SHALL display: "Wiki path '{path}' does not exist." and abort.
- REQ-632: If `pages_dir` is non-empty and the resolved directory
  (`wiki_path/pages_dir`) does not exist, the system SHALL display a warning
  but continue (the directory may be created during setup).
- REQ-633: If `namespaces` is empty or missing, the system SHALL display:
  "No namespaces configured in llm-wiki.yml." and abort.
- REQ-634: Namespace names SHOULD follow the structural naming rules in
  specs/schema.md (REQ-580..581: lowercase, hyphenated; e.g. `tech`, not `Tech`).
  A non-conforming name SHALL trigger a warning but not abort. The mechanical
  advisory in code flips from the old Title Case check with the lowercase
  migration (issue #25); pre-migration Title Case corpora warn under the
  grandfather floor.

### Path Handling

- REQ-640: The system SHALL expand `~` to `$HOME` in `wiki_path` and
  `memory_path` before use.
- REQ-641: The system SHALL resolve `pages_dir` relative to `wiki_path`:
  `full_pages_path = wiki_path + "/" + pages_dir`.
- REQ-642: For Obsidian with empty `pages_dir`, `full_pages_path` equals
  `wiki_path`.

### Tool Mode Propagation

- REQ-650: The `tool` value determines ALL downstream format decisions:
  - Property syntax (inline vs YAML frontmatter)
  - File naming (triple-underscore vs directory hierarchy)
  - Content format (outliner blocks vs flat markdown)
  - Hub file naming (`Wiki___Namespace.md` vs `Wiki/Namespace/_index.md`)
- REQ-651: The tool mode MUST be consistent across ALL wiki operations in a
  single session. Switching tools mid-session is not supported.

---

## Scenarios

### Scenario 1: Valid Logseq config

```
GIVEN llm-wiki.yml contains:
    tool: logseq
    wiki_path: /home/user/Documents/Logseq
    pages_dir: pages
    memory_path: ~/.claude/projects/myproject/memory/
    namespaces:
      - Business
      - Tech
      - Projects
AND /home/user/Documents/Logseq/pages/ exists on disk
WHEN any wiki skill starts
THEN the system SHALL load the config successfully
AND set tool mode to Logseq (outliner format, triple-underscore files)
AND resolve pages path to /home/user/Documents/Logseq/pages/
```

### Scenario 2: Valid Obsidian config

```
GIVEN llm-wiki.yml contains:
    tool: obsidian
    wiki_path: ~/Documents/ObsidianVault
    pages_dir: ""
    namespaces:
      - Business
      - Tech
AND ~/Documents/ObsidianVault/ exists on disk
WHEN any wiki skill starts
THEN the system SHALL load the config successfully
AND set tool mode to Obsidian (flat markdown, directory hierarchy)
AND resolve pages path to /home/user/Documents/ObsidianVault/
```

### Scenario 3: Config file missing

```
GIVEN no llm-wiki.yml file exists in the wiki root
WHEN the user runs /wiki-ingest "some source"
THEN the system SHALL display: "llm-wiki.yml not found. Run setup.sh to create one."
AND abort without modifying any files
```

### Scenario 4: Invalid tool value

```
GIVEN llm-wiki.yml contains tool: notion
WHEN the user runs any wiki skill
THEN the system SHALL display: "Invalid tool 'notion'. Must be 'logseq' or 'obsidian'."
AND abort without modifying any files
```

### Scenario 5: Wiki path does not exist

```
GIVEN llm-wiki.yml contains wiki_path: /home/user/nonexistent/path
AND that path does not exist on disk
WHEN the user runs any wiki skill
THEN the system SHALL display: "Wiki path '/home/user/nonexistent/path' does not exist."
AND abort without modifying any files
```

### Scenario 6: Empty namespaces

```
GIVEN llm-wiki.yml contains namespaces: []
WHEN the user runs any wiki skill
THEN the system SHALL display: "No namespaces configured in llm-wiki.yml."
AND abort
```

### Scenario 7: Memory path missing - features degraded

```
GIVEN llm-wiki.yml has no memory_path key
WHEN the user runs /wiki-query "some question"
THEN the system SHALL proceed without L1 Memory consultation
AND NOT display an error (memory_path is optional)
AND the answer SHALL be based on wiki pages only
```

### Scenario 8: Tilde expansion in paths

```
GIVEN llm-wiki.yml contains:
    wiki_path: ~/Documents/MyWiki
    memory_path: ~/.claude/projects/x/memory/
AND the user's HOME is /home/user
WHEN the system loads the config
THEN wiki_path SHALL resolve to /home/user/Documents/MyWiki
AND memory_path SHALL resolve to /home/user/.claude/projects/x/memory/
```

---

### Scenario 9: Discovery from a project directory

```
GIVEN the wiki lives at ~/notes with ~/notes/llm-wiki.yml
AND ~/.config/llm-wiki/config.yml contains wiki_path: ~/notes
AND the user runs a wiki skill from ~/projects/some-repo (no config in the walk-up)
WHEN config discovery runs (REQ-652)
THEN LLM_WIKI_CONFIG is unset, the walk-up finds nothing, and the pointer file
    resolves the config at ~/notes/llm-wiki.yml
```

## Acceptance Criteria

- [ ] Config read as first operation of every wiki skill
- [ ] Missing config file produces clear error with setup.sh hint
- [ ] tool value strictly validated (logseq or obsidian only)
- [ ] wiki_path validated (must exist on disk)
- [ ] namespaces validated (must be non-empty)
- [ ] memory_path is optional (features degrade gracefully)
- [ ] Tilde expansion works in all path fields
- [ ] Tool mode propagates to all downstream operations
- [ ] Invalid config values produce clear, specific error messages

---

## Dependencies

- setup.sh creates this config file (see specs/setup.md)
- All other specs (ingest, query, lint) depend on config being loaded first
