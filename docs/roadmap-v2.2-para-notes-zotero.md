# Roadmap: v2.2 — `para/` + `notes/` + Zotero

Assessment of the "Patch 3" proposal (para/notes namespaces, naming convention, Zotero wiring) and
how it folds into the release roadmap. Companion to the v2.0.0 / v2.1 milestones (issues #9–#21).

## Why this exists

Patch 3 was drafted as copy-paste blocks in the **pre-v2 idiom**: sentinel-wrapped edits to
`wiki.md`, additions to `pages/wiki___schema.md`, a `sed` rename, and Logseq plugin/query-page
setup. Three facts reshape it from a patch-to-apply into a roadmap item:

1. **This is the tooling repo, not a graph.** It ships the wiki skill suite, `openspec/specs/`,
   `templates/`, `setup.sh`, `docs/`. It has no `pages/`, `raw/`, `ingested/`, `journals/` — those
   are scaffolded into your vault by `setup.sh`. So Patch 3 splits into **tool changes** (specs,
   lint, seams, templates, docs — here) and **your-graph operations** (the rename, task conversion,
   the Zotero plugin, the query pages — documented here, run in your vault).
2. **The v2 pivot deletes Patch 3's idiom.** #9 removes the provenance regions (sentinel comments, removed in 2.0.0); #20
   deletes `wiki.md`; #11 splits it into a `skills/` suite, canon-first. #13 bans `sed`/heredoc
   python. Patch 3's "paste this sentinel block" and its `sed` one-liners target things being
   removed or forbidden.
3. **v2.0.0 was scoped minimal on purpose.** Patch 3 depends on the finished skill suite (#11),
   spec canon (#10), lint (#16), the migration converter (#21), and — for the notes→wiki seam —
   block-native citations (#17, v2.1). It is a **later milestone**, not core.

## Design decisions

- **New v2.2 milestone**, after v2.0.0 + v2.1. Not stacked on an unfinished base.
- **Adopt lowercase `wiki/` everywhere** (change REQ-580), via the migration converter — not a
  naked `sed`.
- **No `/para` or `/notes` command skills.** The tool recognizes and protects those namespaces and
  provides the two ingest seams; the PARA/Zettelkasten mechanics stay human-run in the vault
  (documented in [para-notes-workflow.md](para-notes-workflow.md)). This follows the repo's own
  rule — don't formalize a verb until you've done it by hand enough to know the ceremony pays off.

## What to keep, fix, drop

**Keep (strong):** the three-namespace contract (`wiki/` machine-written; `para/` + `notes/`
human-owned, machine-exempt) and the single seam — the only path in is through `raw/` with
provenance. A clean extension of the existing "sources enter via `raw/`" invariant (REQ-589). This
is now [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md).

**Drop:** the command suite (`/para archive`, `/notes promote`, live-list/fleeting-inbox as tool
features). Logseq is already native for tasks, queries, and the Zettelkasten flow. These become a
vault-setup guide, not skills.

**Fix (re-home to v2 idiom):**

- Schema/naming additions → `specs/schema.md` REQs + both `templates/{logseq,obsidian}/Schema.md`.
- Scope guard → `skills/wiki-core` shared reference (stated once, `check_canon.py`-enforced).
- Lint extensions → `lint.py` (mechanical naming/namespace hygiene) + `wiki-lint` skill
  (proper-noun-leaf judgment exemption), matching #16's two-layer split.
- Seams → steps in the existing `wiki-ingest` skill, not new skills.
- Casing → `migrate_wiki.py` (#21) with dry-run + grandfather mode.
- Roam task conversion → a step in the python import path (per #13's no-`sed` rule).

**Already covered — don't rebuild:** the `notes/` PII risk is #6/#15's pre-archive secret gate +
`sensitive_source_types`. The `para/resources` "waiting room / stub" idea overlaps #7's
`canonical-url::` stubs. Reference, don't duplicate.

**Depends on v2.1:** the "one archived source, two readings" seam is only fully auditable once
block-native `cite::` (#17) exists.

## Premortem (frame: 6 months on, v2.2 failed)

- **Most likely — stacked-dependency stall.** v2.2 depends on the whole solo backlog. *Mitigation:*
  v2.2 does not open until v2.0.0 + v2.1 ship and lint runs clean on the real vault (#21 gate); file
  only Tier-1 fully, rest as stubs so they don't drift against a skill suite that doesn't exist yet.
- **Most dangerous (now avoided) — building unused commands.** *Mitigation:* the command suite is
  dropped; only boundary + seams remain in the tool.
- **Lowercase migration is cosmetic but corpus-wide.** *Mitigation:* ride #21 dry-run + grandfather
  mode; reversible.
- **Zotero docs rot.** *Mitigation:* verify-once, version-pinned, "known-good as of <date>".
- **check_canon noise** from new enums. *Mitigation:* add "personal synthesis = medium" inside #9's
  reliability rework so it's one statement, not two.

**Hidden assumption surfaced:** that para/notes/Zotero is a *tool feature set*. It's mostly a
*personal workflow* your existing tools already run; the tool's real contribution is a thin
protective boundary plus two seams.

**Kill criteria:**

- v2.0.0 + v2.1 not both shipped and lint-clean on the real vault → do not open v2.2.
- Lowercase dry-run reports a non-trivial broken-link/orphan count with no clean remediation →
  defer the rename; keep `wiki/`/`para/`/`notes/` as new-content-only.
- After Tier 1, if the manual PARA/notes flow works fine by hand → never revisit the command suite.

## Issue breakdown (v2.2 label)

**Tier 1 — file fully:**

1. spec: v2.2 REQs — namespaces contract + naming (depends #10)
2. lint: naming-hygiene + namespace-hygiene rules (+ proper-noun exemption in wiki-lint) (#16)
3. wiki-ingest: para/notes promotion seams (raw/ at `reliability:: medium`) (#14; #17 for the
   literature "one source, two readings" variant)
4. lowercase migration: `Wiki/` → `wiki/` via converter dry-run + REQ-580 + templates (#21, #9, #16)
5. test: fixtures for naming, namespace-scope, and the two seams (#19)

**Tier 2 — stubs until v2.1 is near done:**

6. docs: para + notes vault-setup workflow *(this file's companion — draft already on branch)*
7. docs + schema: Zotero literature notes born as `notes/literature/@citekey` *(draft on branch)*
8. config + setup: `para_dir`/`notes_dir` + `init_wiki` scaffold
9. v2.2 release rollup (mirrors #20)

## Delivered on this branch now

- [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) — the normative contract
- [`docs/para-notes-workflow.md`](para-notes-workflow.md) — the vault-side PARA/Zettelkasten guide
- [`docs/zotero-setup.md`](zotero-setup.md) — the Zotero wiring guide
- This roadmap

The code changes (lint rules, migration pass, seam steps, template edits) are described in the
Tier-1 issues and land once the v2.0.0 skill suite + v2.1 citations exist — building them now would
target a skill suite that isn't there yet.
