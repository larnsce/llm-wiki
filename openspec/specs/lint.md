# Spec: /wiki-lint - Automated Health Checks

## Description

The lint command scans all wiki pages for structural issues, data quality problems,
and security concerns. It reports findings grouped by severity and can auto-fix
certain issues when run with the `--fix` flag. There are 15 lint rules.

---

## Requirements

### Scanning

- REQ-100: The system SHALL scan ALL files matching the wiki page pattern
  (Logseq: `Wiki___*.md`, Obsidian: `Wiki/**/*.md`).
- REQ-101: The system SHALL read page properties, count outgoing `[[Wiki/...]]`
  links, and check the `updated::` date for every scanned page.
- REQ-102: The system SHALL build an incoming-link graph (page -> pages that
  reference it) to detect orphans.
- REQ-103: The system SHALL read `llm-wiki.yml` first to determine tool mode
  and paths.

### Rule 1: Orphan Detection

- REQ-110: The system SHALL flag pages with 0 incoming `[[Wiki/...]]` links
  from other wiki pages.
- REQ-111: Hub pages (type:: hub) SHALL be exempt from orphan detection.
- REQ-112: Auto-fix (--fix): The system SHALL add the orphan page to its
  namespace's hub page.

### Rule 2: Stale Detection

- REQ-120: The system SHALL flag pages where `updated::` is older than 90 days
  AND `confidence::` is `high`.
- REQ-121: Pages without a `confidence::` property SHALL be exempt from stale
  detection (the rule only applies to knowledge-type pages).
- REQ-122: The 90-day threshold SHALL be calculated as: today minus the
  `updated::` date value.
- REQ-123: Auto-fix (--fix): The system SHALL downgrade `confidence::` from
  `high` to `stale`. The `updated::` date SHALL NOT be changed by this
  operation (the page content has not changed, only the confidence assessment).

### Rule 3: Missing Properties

- REQ-130: The system SHALL check each page against the required properties for
  its declared `type::` value (per Schema page).
- REQ-131: Required properties per type:
  - Entity: type, entity-type, created, updated, status, source
  - Project: type, status, created, updated, started
  - Knowledge: type, domain, created, updated, confidence
  - Feedback: type, severity, created, verified, applies-to
  - Hub: type, namespace
- REQ-132: A page with a missing required property SHALL be flagged as a warning.
- REQ-133: No auto-fix for missing properties (requires human judgment).

### Rule 4: Broken References

- REQ-140: The system SHALL identify all `[[Wiki/...]]` links in every page and
  verify that the target page exists on disk.
- REQ-141: A link to a non-existent page SHALL be flagged as a warning.
- REQ-141a (pending person pages): A link to a non-existent
  `wiki/people/` target SHALL be reported at INFO severity with a
  "pending person page" reason instead of the REQ-141 warning. Rationale:
  ingest writes person-name links wherever names appear (ingest
  REQ-036a) but creates the person page only at the second-source
  threshold (ingest REQ-024a), so a person link legitimately precedes
  its page. The `--fix` stub creation (REQ-142) SHALL NOT apply to these
  targets: person pages are born through ingest with their citation
  shape, not as knowledge stubs.
- REQ-142: Auto-fix (--fix): The system SHALL create a stub page for each broken
  reference with: type:: knowledge, domain:: tech, confidence:: low,
  created:: [today], updated:: [today], and a placeholder note
  "To be filled via /wiki-ingest".
- REQ-143: Stub pages SHALL include a cross-reference back to the page that
  contained the broken link.

### Rule 5: Hub Completeness

- REQ-150: The system SHALL verify that every hub page lists ALL pages that exist
  in its namespace.
- REQ-151: A hub page missing a child page SHALL be flagged as a warning.
- REQ-152: Auto-fix (--fix): The system SHALL append the missing child page link
  to the hub page.

### Rule 6: Credential Leak

- REQ-160: The system SHALL scan all wiki page content for credential patterns:
  `token::`, `password::`, `secret::`, `api-key::`, `api.key::`, and base64
  strings matching `[A-Za-z0-9+/]{40,}`. A base64 candidate SHALL count only
  when it shows credential-shaped character diversity (both letter cases AND
  at least one digit), and text inside `[[...]]` link spans SHALL be excluded
  before the base64 pass: a long lowercase namespace path (for example a
  routing line's `wiki/data/<pkg>/<dataset>` target) is link syntax, not a
  credential candidate (issue #104). The named property patterns and the
  specific key shapes (AWS, GitHub, `sk-`) keep scanning the full text.
- REQ-161: Pattern matching SHALL be case-insensitive.
- REQ-162: In Obsidian mode, the system SHALL also scan YAML frontmatter for
  credential patterns.
- REQ-163: Any credential match SHALL be flagged as severity `critical`.
- REQ-164: No auto-fix for credential leaks (requires manual intervention to
  move the credential to L1 memory).

### Rule 7: Empty Pages

- REQ-170: The system SHALL flag pages that contain only properties and no
  substantive content below the properties section.
- REQ-171: A page with only type/date properties and no knowledge blocks SHALL
  be flagged as a warning.
- REQ-172: No auto-fix (page should be filled via /wiki-ingest or deleted).

### Rule 8: Cross-Reference Minimum

- REQ-180: The system SHALL flag pages with fewer than 1 outgoing `[[Wiki/...]]`
  link.
- REQ-181: Auto-fix (--fix): The system SHALL add a link to the page's namespace
  hub page (e.g., a page in Wiki/Tech/ gets a link to [[Wiki/Tech]]).

### Rule 9: L1/L2 Duplicates

- REQ-190: The system SHALL compare wiki page content against L1 memory files
  (at the path specified in `llm-wiki.yml` `memory_path`).
- REQ-191: The system SHALL flag cases where substantially the same information
  exists in both L1 memory and L2 wiki.
- REQ-192: No auto-fix (requires human decision on which location is authoritative).

### Rule 10: Index Drift

- REQ-193: The system SHALL flag a routing line in a hub `### Index` whose target
  page does not exist on disk (orphaned routing line).
- REQ-194: The system SHALL flag an active (non-archived) page that has no routing
  line in its namespace hub `### Index` (unroutable - only findable via L3 grep).
- REQ-195: The system SHALL flag a routing line that has no description text after
  the `--` separator (a routing key cannot be empty).
- REQ-196: Auto-fix (--fix): for an unroutable page, the system SHALL backfill a
  routing line into the hub `### Index`, deriving the description from the page
  title and first content block and copying the page's existing `#tags`. For an
  orphaned routing line, the system SHALL remove it.

### Rule 11: Archived-in-Live-Index

- REQ-197: The system SHALL flag a demoted page (marked `archived::`, see specs/schema.md
  REQ-565) whose routing line is still in the hub `### Index` instead of `### Archive`
  (an unclean prune).
- REQ-198: Auto-fix (--fix): the system SHALL move the routing line from `### Index`
  to `### Archive`. It MUST NOT rename or move the page file (links are by page name).

### Rule 12: External Link Rot (canonical-url)

- REQ-220: The system SHALL check every page carrying `canonical-url::` (schema
  REQ-584) and verify the URL still resolves. When an HTTP client is available
  (e.g. `curl`), resolution means a 2xx/3xx status; otherwise the check degrades to
  URL-shape validation and reports itself as degraded.
- REQ-221: An unreachable `canonical-url::` target SHALL be flagged as a warning
  (info when the check ran degraded). A page with `canonical-url::` SHALL NOT be
  flagged for missing `source-file::` or other ingested-page properties: it is a
  deliberate stub, not an ingested page missing provenance.
- REQ-222: No auto-fix: link rot requires human judgment (update the URL, ingest a
  snapshot, or archive the stub).

### Rule 13: Naming Hygiene (structural names)

- REQ-230: The system SHALL flag any page whose STRUCTURAL (non-leaf) name
  segments contain spaces, uppercase characters, underscores, en dashes
  (`U+2013`), or em dashes (`U+2014`); the only word separator inside a
  structural segment is the ASCII hyphen `U+002D` (specs/schema.md
  REQ-580/580a/581). Severity: warning on `wiki/` pages; info on `para/` and
  `notes/` pages, whose content is human-owned and exempt from the wiki
  conventions but whose namespace STRUCTURE is shared graph territory
  (specs/namespaces.md REQ-961).
- REQ-231: A LEAF segment SHALL be flagged mechanically ONLY when it violates
  the hyphen rule (underscore, en dash, or em dash). Uppercase characters,
  `@` prefixes, or spaces in a leaf MAY be a proper noun
  (`wiki/tools/Claude Code`, `notes/literature/@Forte2022`, specs/schema.md
  REQ-580b) and that judgment stays in the wiki-lint skill: it reviews
  naming-hygiene leaf findings and dismisses proper-noun leaves
  (specs/namespaces.md REQ-976).
- REQ-232: No auto-fix: a rename changes page identity (links are by page
  name) and runs through the migration converter (specs/schema.md REQ-580c)
  or by hand, never by lint.

### Rule 14: Namespace Hygiene (pages outside the contract)

- REQ-240: The system SHALL flag any page outside `wiki/`, the configured
  `para_dir`, `notes_dir`, and `glossary_dir` namespaces (specs/config.md
  REQ-625/628, specs/namespaces.md REQ-980), the configured `journals_dir`
  (specs/config.md REQ-629), and the recognized
  deliberate root pages, as a stray outside the namespace contract
  (specs/namespaces.md REQ-960/962). Severity: warning (the grandfather floor reports it as info
  on pages without the current `schema-spec-version::`).
- REQ-241: Recognized deliberate root pages SHALL NOT be flagged: Schema,
  Dashboard, Access-Log, Contents, hub pages (`type:: hub`), and query pages
  (`type:: query` or `#+BEGIN_QUERY` content), per specs/namespaces.md
  REQ-962/977.
- REQ-241a: In logseq mode, the built-in `contents` page (`pages/contents.md`,
  the sidebar Contents) SHALL additionally be treated as a SYSTEM page: exempt
  from the wiki-only rules (orphan REQ-110, required properties REQ-132,
  provenance, empty page REQ-171, cross-reference minimum REQ-180,
  canonical-url), the same treatment as Schema, Dashboard, and the Access-Log.
  Adding wiki properties or forced links to a Logseq system page is wrong
  (issue #105).
- REQ-242: Pages under `para_dir` and `notes_dir` are IN-contract for this
  rule and EXEMPT from all wiki-only rules (specs/namespaces.md REQ-961/966):
  the system SHALL NOT run any other rule against them (rule 13 reports its
  advisory info-level structural findings only). Pages under `glossary_dir`
  are IN-contract, exempt from the wiki-only rules (specs/glossary.md
  REQ-1002), and checked by rules 13 (advisory) and 15 (glossary
  structure). No auto-fix: moving a page between namespaces is a human
  decision; content enters `wiki/` only through the promotion seam
  (specs/namespaces.md REQ-970).

### Rule 15: Glossary Hygiene (structure only, never the decisions)

Mechanical enforcement of specs/glossary.md; runs only on pages under
`glossary_dir` (config REQ-628). The decisions themselves (which Rule, which
DE form) are human and never judged.

- REQ-250 (table shape): In a terms table under a `## Terms` heading on a
  glossary page, the header SHALL be exactly `| EN | DE | Rule | Note |`;
  a deviating header or a data row with a different column count SHALL be
  flagged as a warning.
- REQ-251 (rule enum): A non-empty Rule cell SHALL be one of
  `keep-en | translate | context`; any other value is a warning. An EMPTY
  Rule cell is a warning on a domain page (an undecided row belongs on
  staging) and accepted on a `glossary/imported/` staging page
  (specs/glossary.md REQ-1010).
- REQ-252 (staging hygiene): A page under `glossary/imported/` SHALL carry
  `source::` (attribution) and `status::`; a missing property is a warning.
- REQ-253 (term pages): A term page (`glossary/<domain>/<term>`, not under
  `glossary/imported/`) SHALL carry `rule::` with a REQ-251 enum value; a
  missing or invalid value is a warning. No auto-fix anywhere in rule 15:
  every fix is a terminology decision, and those are human
  (specs/glossary.md REQ-1000).

### Reporting

- REQ-200: The system SHALL group findings by severity: critical, warning, info.
- REQ-201: The system SHALL output totals: total pages scanned, healthy pages,
  issues found (by rule and severity).
- REQ-202: For each finding, the system SHALL report: page name, rule violated,
  severity, and suggested fix.
- REQ-203: After auto-fix (--fix), the system SHALL output what was changed and
  recommend a git commit.

### Dashboard

- REQ-210: After lint completes, the system SHOULD update the Dashboard page
  (Wiki/Dashboard or Wiki___Dashboard.md) with current health metrics.
- REQ-211: The Dashboard SHALL include: last lint date, total pages, issues by
  severity, and pages needing attention.

---

## Scenarios

### Scenario 1: Clean wiki - no issues

```
GIVEN a wiki with 10 pages, all with required properties, cross-references,
    and current updated:: dates
AND all hub pages list their children
AND no credential patterns exist in any page
WHEN the user runs /wiki-lint
THEN the report SHALL show: 10 pages scanned, 0 issues found
AND no pages SHALL be modified
```

### Scenario 2: Orphan page detected

```
GIVEN a page Wiki___Tech___Redis.md exists
AND no other wiki page contains a [[Wiki/Tech/Redis]] link
AND Redis is NOT a hub page
WHEN the user runs /wiki-lint
THEN the system SHALL flag Wiki/Tech/Redis as "orphan" (warning)
AND suggest: "Add [[Wiki/Tech/Redis]] to the Wiki/Tech hub page"
```

### Scenario 3: Orphan auto-fix

```
GIVEN the same orphan condition as Scenario 2
WHEN the user runs /wiki-lint --fix
THEN the system SHALL append [[Wiki/Tech/Redis]] to Wiki___Tech.md
AND the report SHALL show: "Fixed: Added Wiki/Tech/Redis to hub Wiki/Tech"
```

### Scenario 4: Stale page with high confidence

```
GIVEN a page Wiki___Tech___Strapi.md with updated:: 2026-01-01
AND the page has confidence:: high
AND today is 2026-04-10 (100 days later, exceeds 90-day threshold)
WHEN the user runs /wiki-lint
THEN the system SHALL flag the page as "stale" (warning)
AND suggest: "Confidence is 'high' but page is 100 days old. Review or downgrade."
```

### Scenario 5: Stale auto-fix - confidence downgraded

```
GIVEN the same stale condition as Scenario 4
WHEN the user runs /wiki-lint --fix
THEN the system SHALL change confidence:: from high to stale
AND the updated:: property SHALL remain 2026-01-01 (NOT changed)
AND the report SHALL show: "Fixed: Downgraded confidence from high to stale"
```

### Scenario 6: Credential leak detected

```
GIVEN a page Wiki___Tech___Deployment.md contains the text
    "api-key:: sk-ant-abc123def456ghi789jkl012mno345pqr678"
WHEN the user runs /wiki-lint
THEN the system SHALL flag the page as "credential leak" (critical)
AND suggest: "Move credential to L1 memory. Wiki pages are git-tracked."
AND the finding SHALL be listed first in the report (critical severity)
```

### Scenario 7: Broken reference with auto-fix

```
GIVEN a page Wiki___Projects___MyProject.md contains [[Wiki/Tech/NewTool]]
AND no file Wiki___Tech___NewTool.md exists
WHEN the user runs /wiki-lint --fix
THEN the system SHALL create a stub page Wiki___Tech___NewTool.md with:
    type:: knowledge, domain:: tech, confidence:: low, created:: [today],
    updated:: [today], and content "To be filled via /wiki-ingest"
AND the stub SHALL contain [[Wiki/Projects/MyProject]] as a cross-reference
AND the Wiki___Tech.md hub SHALL be updated to list the new page
```

### Scenario 8: Hub missing child pages

```
GIVEN Wiki___Tech.md (hub) lists: [[Wiki/Tech/Strapi]], [[Wiki/Tech/Stack]]
AND Wiki___Tech___Deployment.md also exists in the pages directory
WHEN the user runs /wiki-lint
THEN the system SHALL flag Wiki/Tech hub as "incomplete" (warning)
AND suggest: "Hub Wiki/Tech is missing child: [[Wiki/Tech/Deployment]]"
```

### Scenario 9: Empty page detected

```
GIVEN a page Wiki___Learning___Rust.md contains only:
    type:: knowledge
    domain:: tech
    created:: 2026-03-15
    updated:: 2026-03-15
    confidence:: low
AND no content blocks exist below the properties
WHEN the user runs /wiki-lint
THEN the system SHALL flag the page as "empty" (warning)
AND suggest: "Page has properties but no content. Fill via /wiki-ingest or delete."
```

### Scenario 10: L1/L2 duplicate detected

```
GIVEN L1 memory file feedback_deploy_ram.md contains "Stop ClamAV before deploy"
AND wiki page Wiki___Tech___Deployment.md also contains "Stop ClamAV before deploy"
WHEN the user runs /wiki-lint
THEN the system SHALL flag as "L1/L2 duplicate" (info)
AND suggest: "Same info in L1 memory and L2 wiki. Decide which is authoritative."
```

### Scenario 11: Index drift - unroutable page backfilled

```
GIVEN a page Wiki___Tech___Redis.md exists and is active (not archived)
AND the Wiki/Tech hub `### Index` has no routing line for [[Wiki/Tech/Redis]]
WHEN the user runs /wiki-lint --fix
THEN the system SHALL flag Wiki/Tech/Redis as "index drift: unroutable" (warning)
AND backfill a routing line into the Wiki/Tech hub `### Index`:
    "[[Wiki/Tech/Redis]] -- <description from title + first block> #<existing tags>"
```

### Scenario 12: Archived page still in the live index

```
GIVEN Wiki___Tech___Legacy-Foo.md has archived:: 2026-06-07 (and status:: archived, an entity page)
AND its routing line still sits in the Wiki/Tech hub `### Index`
WHEN the user runs /wiki-lint --fix
THEN the system SHALL flag it as "archived-in-live-index" (warning)
AND move the routing line from `### Index` to `### Archive`
AND NOT rename or move the Legacy-Foo page file
```

---

### Scenario 13: Stub page with rotten canonical-url

```
GIVEN a reference page with canonical-url:: https://example.org/moved-course
AND the URL returns HTTP 404
WHEN /wiki-lint runs
THEN the page is flagged: rule 12, warning, "canonical-url target unreachable"
AND the page is NOT flagged for missing source-file::
```

### Scenario 14: Naming hygiene - structural vs leaf

```
GIVEN pages Wiki/Foo, wiki/tech/my_note, and wiki/tools/Claude Code
WHEN /wiki-lint runs the naming-hygiene check
THEN Wiki/Foo is flagged (REQ-230: uppercase structural segment)
AND wiki/tech/my_note is flagged (REQ-231: underscore in the leaf)
AND wiki/tools/Claude Code is NOT flagged mechanically (leaf casing and
    spaces are the wiki-lint skill's proper-noun judgment, REQ-231)
```

### Scenario 15: Namespace hygiene - stray root page, exempt human page

```
GIVEN a page "Scratchpad" outside wiki/, para/, notes/, journals, and the
    recognized root pages
AND a page para/projects/secret-plan carrying no wiki properties
WHEN /wiki-lint runs
THEN Scratchpad is flagged (REQ-240, warning)
AND para/projects/secret-plan is NOT flagged by namespace hygiene
AND para/projects/secret-plan is NOT flagged by any wiki-only rule (REQ-242)
```

## Acceptance Criteria

- [ ] All 15 rules execute during a lint run
- [ ] Findings grouped by severity: critical > warning > info
- [ ] Report includes totals (pages scanned, healthy, issues by rule)
- [ ] Auto-fix (--fix) only modifies rules 1, 2, 4, 5, 8, 10, 11 (the 7 auto-fixable rules)
- [ ] Rules 3, 6, 7, 9, 12, 13, 14 never auto-fix (require human judgment)
- [ ] Index Drift (rule 10) backfills unroutable pages and removes orphaned routing lines
- [ ] Archived-in-Live-Index (rule 11) moves routing lines but never renames/moves page files
- [ ] Naming Hygiene (rule 13) flags structural segments mechanically; leaf proper-noun judgment stays in the wiki-lint skill
- [ ] Namespace Hygiene (rule 14) flags strays, accepts the recognized root pages, and exempts para/ and notes/ from all wiki-only rules
- [ ] Glossary Hygiene (rule 15) checks table shape, the rule enum, and staging hygiene on glossary/ pages, and never auto-fixes a decision
- [ ] Credential detection is case-insensitive and scans both content and frontmatter
- [ ] Stale detection uses exact 90-day threshold from updated:: to today
- [ ] Hub completeness checks ALL child pages, not just recently created ones
- [ ] Works correctly in both Logseq and Obsidian page naming conventions
- [ ] Dashboard page updated after lint completes
