# wiki-lint judgment layer and --fix playbook

Spec: openspec/specs/lint.md. The mechanical subset of the 14 rules runs in
`skills/wiki-core/scripts/lint.py` (report-only). This file defines what
the agent adds on top and how fixes are applied.

## Division of labor

Mechanical (lint.py): rules 1, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14 plus
the schema-level checks (date format, enums, provenance, format mixing).
For rule 13 (naming hygiene) only the structural part is mechanical: leaf
segments are flagged by lint.py only for separator violations (underscore,
en/em dash, REQ-231); leaf casing and spaces are this layer's judgment.

Judgment (agent, this layer):

- Rule 2 Stale Detection (REQ-120..123). The trigger is mechanical
  (`updated::` older than 90 days AND `confidence:: high`) but the fix is
  editorial: read the page and judge whether the content is actually
  outdated before downgrading `confidence::` to `stale`. The `updated::`
  date is NEVER changed by this fix (REQ-123): the content did not change,
  only the confidence assessment.
- Rule 9 L1/L2 Duplicates (REQ-190..192). Compare wiki pages against the L1
  memory files at `memory_path`. "Substantially the same information" is a
  semantic call, not a string match. Severity info; no auto-fix, the user
  decides which location is authoritative.
- Proper-noun-leaf review (rule 13, REQ-231): lint.py flags structural
  (non-leaf) segments for spaces, uppercase, underscores, and en/em dashes
  (REQ-230), but a leaf is only flagged mechanically for separator
  violations. Review the leaf findings and DISMISS proper-noun leaves
  (REQ-580b, namespaces REQ-976): a capitalized or `@`-prefixed leaf naming
  a person, tool, paper, or citekey (`wiki/tools/Claude Code`,
  `notes/literature/@forte2022building`) keeps natural casing and is NOT a
  violation. Flag the inverse case the mechanical layer skips: an uppercase
  or spaced leaf that is NOT a proper noun (`wiki/tech/My Notes`).
- Naming quality: lowercase structural segments, hyphens for multi-word
  names, depth of at most 3 (REQ-580..582); flag names that are technically
  valid but unclear or misleading.
- Routing-description quality: hub `### Index` descriptions must be
  distinctive routing keys, at most 120 chars, no filler like "Info
  about ..." (REQ-555, REQ-557). lint.py only catches EMPTY descriptions
  (REQ-195); weak ones are a judgment call.
- Misfiled namespace: a page whose content belongs in a different
  namespace (e.g. a client profile under wiki/tech). Propose a NEW page in
  the right namespace and demote or merge the old one; never move or
  rename the file itself (links are by page name, see the architecture
  reference).
- Entity mentions that should be links (REQ-572) and missing
  `## Cross-References` sections (REQ-573, info level).
- Summary quality: empty-ish pages that technically pass REQ-171 but say
  nothing useful; propose ingest or deletion.

## --fix playbook (agent-side, always confirmed)

lint.py never writes. For each finding, propose the concrete edit, get
user confirmation, apply, then git commit (REQ-203). Never auto-fix
critical findings silently. Fix recipes per rule:

- Rule 1 orphan (REQ-112): add the orphan page link to its namespace hub.
- Rule 2 stale (REQ-123): downgrade `confidence::` from high to stale;
  never touch `updated::`.
- Rule 4 broken ref (REQ-142/143): create a stub page (type:: knowledge,
  domain:: tech, confidence:: low, created/updated today, "To be filled
  via /wiki-ingest") with a cross-reference back to the linking page.
- Rule 5 hub completeness (REQ-152): append the missing child link to the
  hub.
- Rule 8 cross-ref minimum (REQ-181): add a link to the page's namespace
  hub.
- Rule 10 index drift (REQ-196): backfill a routing line for an unroutable
  page (description from title + first content block, copy the page's
  existing #tags); remove orphaned routing lines.
- Rule 11 archived-in-live-index (REQ-198): move the routing line from
  `### Index` to `### Archive`; NEVER rename or move the page file.

No auto-fix, ever: rule 3 missing properties (REQ-133), rule 6 credential
leak (REQ-164; move the credential to L1 memory manually and scrub git
history if needed), rule 7 empty pages (REQ-172), rule 9 L1/L2 duplicates
(REQ-192), rule 12 link rot (REQ-222; update the URL, ingest a snapshot,
or archive the stub), rule 13 naming hygiene (REQ-232; a rename changes
page identity and runs through the migration converter or by hand), rule
14 namespace hygiene (REQ-242; moving content between namespaces is the
human's call, and content enters wiki/ only through the promotion seam).

## Grandfather mode (issue #21)

Pages without the current `schema-spec-version::` are pre-v2: lint.py
floors their findings one severity tier (credential leaks excepted). Do
not propose page-by-page hand fixes for a large unmigrated corpus; point
the user to the wiki-migrate path instead. `--strict` shows full
severities when the user wants the real total.
