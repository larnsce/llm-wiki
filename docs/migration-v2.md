# Migrating from the v1 Single Command

Through v1.5.0, this tool shipped as one file: `wiki.md`, installed as the `/wiki` slash command in `.claude/commands/`. Version 2.0.0 replaces it with the skill suite in `skills/`. This guide covers the command-level migration. For migrating a pre-v2 page corpus (properties, dates, schema stamping), see [migration.md](migration.md); that is a separate, one-time step driven by the `wiki-migrate` skill.

## Verb-to-skill map

Every workflow the v1 command provided has a skill home. The left column lists the verbs of the old `/wiki` command:

| v1 verb | v2 home |
|---------|---------|
| `ingest <source>` | `/wiki-ingest` (interactive by default; `--auto` to drain the `raw/` queue without a checkpoint) |
| `query <question>` | `/wiki-query` |
| `lint [--fix]` | `/wiki-lint` (fixes proposed per finding, applied on confirmation) |
| `status` | `/wiki-maintain` (status is the default, read-only mode) |
| `prune [--months N]` | `/wiki-maintain prune` |
| `import` | `/wiki-ingest --import` |
| `setup.sh` (v1 installer) | `setup.sh` (v2, installs the suite) plus the `/wiki-setup` skill |

The shared context the v1 file carried inline (config reading, tool-specific format rules, the L1/L2 boundary, hub-index routing, the Access-Log, provenance and trust conventions) lives in `skills/wiki-core/references/`, which every skill reads before executing.

## What happens to the legacy install

- **It keeps working.** The v1 `wiki.md` was self-contained: it embedded its own workflow text and reads `llm-wiki.yml` directly. Deleting the file from this repository does not break an installed copy.
- **It is unsupported.** No further fixes or spec updates target the single-command form. New features (interactive checkpoint, secret gate, two-layer lint, migration tooling) exist only in the skills.
- **wiki-setup detects it and offers removal.** The setup skill (and `setup.sh`) checks `~/.claude/commands/wiki.md` and `<project>/.claude/commands/wiki.md`, explains the situation, and removes the file only on explicit confirmation (openspec/specs/setup.md REQ-806).

Running both side by side is possible but not recommended: the v1 command predates the v2 conventions (interactive checkpoint, secret gate, `schema-spec-version::` stamping), so pages it writes will show up as findings in `/wiki-lint`.

## Your wiki data

No data migration is required for the switch itself. The v2 properties (`schema-spec-version::`, `source-file::`, `reliability::`, `canonical-url::`) are additive; existing pages keep working and are grandfathered by lint at reduced severity until you migrate them. When you want the corpus itself on v2 conventions, follow [migration.md](migration.md).

## Recommended sequence

1. `git pull` (or re-clone) the repository and run `./setup.sh`. It installs the suite and offers to remove a detected legacy `wiki.md`.
2. Run `/wiki-setup` once. It validates `llm-wiki.yml` (new optional keys: source pipeline, `sensitive_source_types`), offers the append-only Schema-page upgrade, and can write the global pointer file.
3. Use the new skills. When lint's grandfathered findings get noisy, run `/wiki-migrate` for the one-time corpus migration.
