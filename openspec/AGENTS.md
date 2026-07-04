# AI Agent Instructions — llm-wiki

## Role

You are implementing or extending the llm-wiki system. This is an open-source project
that provides a structured knowledge management system for LLM assistants.

## Before Writing Code

1. Read `openspec/project.md` for architecture, constraints, and tech stack
2. Read the relevant `openspec/specs/*.md` file for the feature you are working on
3. Understand ALL SHALL/MUST requirements before making changes
4. Review BDD scenarios — these are your acceptance criteria

## Key Architectural Rules

- **Tool-agnostic:** Every feature MUST work in both Logseq and Obsidian modes
- **Zero dependencies:** Only bash, python3, and git. No npm, no pip, no Docker
- **Append-only wiki:** Never overwrite existing content blocks in wiki pages
- **L1/L2 separation:** Credentials in L1 only. Wiki (L2) is git-tracked
- **JIT retrieval:** Max 3 wiki pages loaded at once

## Format Rules

- **Logseq:** Every line prefixed with `- `, properties as `property:: value`
- **Obsidian:** Standard markdown, properties as YAML frontmatter
- **Both:** `[[Wiki/Namespace/Page]]` link syntax, ISO 8601 dates

## Implementation Rules

- Each feature branch maps to one spec file
- Commit messages reference the spec: `feat: implement ingest phase 3 (ingest.md REQ-030-039)`
- SHALL/MUST requirements are non-negotiable
- SHOULD requirements: implement unless there is a documented reason not to
- Test both Logseq and Obsidian modes before merging

## Testing

- Mechanical harness: `bash skills/wiki-core/scripts/test_pipeline.sh` (stdlib
  bash + python3 only, both tool modes; see `docs/testing.md`)
- BDD scenarios from specs serve as manual test scripts for the LLM-side
  behaviors the harness cannot cover (golden transcripts in `tests/golden/`)
- Each scenario describes: precondition, action, expected result
- Verify both tool modes for every change

## File Map

| File | Purpose |
|------|---------|
| `skills/` | The wiki skill suite (SKILL.md per skill; shared scripts and references in `skills/wiki-core/`) |
| `setup.sh` | Installer for the skill suite |
| `config.example.yml` | Configuration template |
| `docs/` | Architecture docs, schema reference, migration guides |
| `templates/logseq/` | Logseq page templates (Schema, Hub, Dashboard) |
| `templates/obsidian/` | Obsidian page templates |
| `examples/` | Before/after examples, L1 memory samples |
| `diagrams/` | Mermaid architecture diagrams |
| `tests/` | Harness fixtures and golden transcripts |
