# Migrating an Existing Wiki to v2

If your wiki predates schema-spec-version 2.0.0, its pages were authored under v1 conventions: no `schema-spec-version::` property, free-form dates, mixed-case property keys and enum values, prose citations. The v2 lint rules would fire a wall of violations against that corpus. Two mechanisms keep it usable:

1. **Grandfather lint mode** (on by default) keeps the unmigrated corpus legible.
2. **The one-time converter** `migrate_wiki.py` upgrades pages mechanically; the `/wiki-migrate` skill drives it interactively.

## Grandfather mode

`lint.py` treats any page without `schema-spec-version:: 2.0.0` as pre-v2 and reports its findings one severity tier lower: critical becomes warning, warning becomes info. Two exceptions:

- **Credential leaks (REQ-163) always stay critical.** The wiki is git-tracked; a leaked secret is dangerous whatever the page's schema vintage.
- **`--strict` disables the floor** and shows the true violation count the corpus would face at full severity.

Grandfathered findings carry a `grandfathered: true` flag and a message suffix, so the report always tells you why a finding was floored. Once a page carries the current `schema-spec-version::`, it is held to the full rule set. Migration is therefore also a commitment: stamp a page only when you are ready to keep it lint-clean.

## The dry-run / apply / verify loop

The converter lives at `skills/wiki-core/scripts/migrate_wiki.py`. It is stdlib-only, dry-run by default, idempotent, and append-only (it never deletes or rewrites content lines).

```bash
# 1. Baseline: how bad is it really?
python3 skills/wiki-core/scripts/lint.py --json            # grandfathered counts
python3 skills/wiki-core/scripts/lint.py --strict --json   # full-severity counts

# 2. Dry run: report only, nothing is written
python3 skills/wiki-core/scripts/migrate_wiki.py

# 3. Apply: requires a clean git tree in the vault, refuses otherwise
python3 skills/wiki-core/scripts/migrate_wiki.py --apply

# 4. Idempotence check: a second run reports zero mechanical changes
python3 skills/wiki-core/scripts/migrate_wiki.py

# 5. Verify: migrated pages are now held to full severity
python3 skills/wiki-core/scripts/lint.py --json
```

Useful flags: `--page wiki/tech/Docker` restricts the run to one page (works with and without `--apply`), `--json` emits a machine-readable report, `--config` points at a specific `llm-wiki.yml`, `--date` pins the date stamp used in Schema-template placeholders.

Exit codes follow the suite convention: 0 = nothing to migrate and no follow-ups, 1 = changes pending/applied or manual follow-ups remain, 2 = critical (no config, dirty tree on `--apply`, unknown `--page`).

Run the loop via the `/wiki-migrate` skill to get diff previews and confirmations instead of raw script output.

## What the converter does

Per v1-authored page (any page without `schema-spec-version::`), in both tool modes:

- adds `schema-spec-version:: 2.0.0` (this ends grandfather mode for the page)
- normalizes property spacing (`key::value` to `key:: value`) and lowercases known property keys (`Updated::` to `updated::`)
- normalizes date property values to `YYYY-MM-DD` where unambiguously parseable (`03/15/2024` to `2024-03-15`)
- normalizes enum values that are a case-variant of a valid member (`Confidence:: Medium` to `confidence:: medium`)
- adds ONE `needs-review::` marker naming the required properties that are missing, so a human can fill them in
- Schema page: appends v2 template sections that are missing (append-only, per the wiki-setup skill Phase 5); if the page diverges too far from the template it is reported and skipped, never rewritten

## What the converter does NOT do

- **It never fabricates ratings.** `confidence::` and `reliability::` are judgments a human (or a sourced ingest) must make; a missing rating becomes a `needs-review::` marker, not a guessed value.
- **It never deletes or rewrites content lines.** Prose stays prose; only the property block is touched.
- **It never guesses ambiguous dates.** `03/04/2024` could be March 4 or April 3; it is reported as a manual follow-up.
- **It does not restructure prose citations** into the cited-claim format (openspec/specs/citations.md); it only reports where they are.
- **It does not add Logseq `- ` block prefixes** to free-form lines (REQ-590); restructuring content is editorial work.
- **It does not fix format mixing** (YAML frontmatter in a Logseq wiki or outliner properties in an Obsidian wiki, REQ-595); such pages are reported and skipped.
- **It does not create hub routing lines or cross-references**; run `/wiki-lint --fix` for those after migration.

## Manual follow-up checklist

After `--apply`, work through this list (the converter's report and the `needs-review::` markers tell you which pages are affected):

- [ ] Fill in the properties named by each `needs-review::` marker, then delete the marker
- [ ] Set `confidence::` / `reliability::` by hand where missing (independent axes; see the Trust Axes section of the Schema page)
- [ ] Fix dates the converter reported as ambiguous or unparseable
- [ ] Restructure prose citations into cited claims (openspec/specs/citations.md)
- [ ] Add `- ` block prefixes to reported free-form lines (Logseq mode)
- [ ] Convert format-mixed pages to the configured tool's property syntax
- [ ] Reconcile a skipped Schema page by hand (wiki-setup skill, Phase 5)
- [ ] Run `/wiki-lint --fix` for orphans, hub completeness, and routing lines
- [ ] Re-run `lint.py --strict` and confirm the remaining count is the work you have consciously deferred, not a surprise

## The lowercase rename pass (v2.2)

Since v2.2 the structural namespace casing is lowercase (`wiki/tech`, not `Wiki/Tech`; specs/schema.md REQ-580). The corpus rename is a second converter pass, never a hand-run `sed`:

```bash
# Dry run: full rename list + broken-link/orphan count after a simulated rename
python3 skills/wiki-core/scripts/migrate_wiki.py --lowercase

# Apply: requires a clean git tree; renames go through git mv
python3 skills/wiki-core/scripts/migrate_wiki.py --lowercase --apply

# Idempotence check: a second run reports zero changes
python3 skills/wiki-core/scripts/migrate_wiki.py --lowercase
```

What the pass does:

- renames files (`Wiki___Tech.md` to `wiki___tech.md`) and directories (`Wiki/Tech/` to `wiki/tech/`); renames are git-aware (`git mv`) so case-only renames land in the git index, not only on a case-insensitive filesystem
- rewrites `[[Wiki/...]]` link targets everywhere, which covers the hub `### Index` and `### Archive` routing lines
- lowercases `namespace::` property values and the `namespaces:` values in `llm-wiki.yml`
- converts Roam task markers: `{{[[TODO]]}}` to `TODO` (plus the DOING/DONE/NOW/LATER/WAITING/CANCELED variants)

Leaf casing follows the documented heuristic (REQ-580b): hub pages, the system leaves (schema, dashboard, access-log), and leaves matching a namespace segment are structural and are lowercased; entity pages name proper nouns and keep their leaf casing; anything else with uppercase letters is AMBIGUOUS, kept unchanged, and reported as a manual follow-up. The converter never guesses.

The dry-run report ends with the broken-link and orphan counts after a simulated rename. That is the kill criterion: a non-trivial count with no clean remediation means the rename is deferred and the lowercase names are adopted new-content-only (pre-migration pages stay legible under the lint grandfather floor, REQ-580c).

## Release gate

v2.0.0 is tagged only after a real-vault (non-fixture) `wiki-lint` run returns a manageable violation count with a documented remediation path for every remaining finding. The synthetic test corpus proves the machinery; the real corpus proves the release.
