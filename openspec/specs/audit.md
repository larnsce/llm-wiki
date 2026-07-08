# Spec: /wiki-audit - Claim Verification

## Description

Verify a single page against its cited sources: detect uncited factual claims, then
check that each citation actually SUPPORTS the specific claim that cites it.
`reliability::` answers "how good are the sources"; audit answers "does the source
actually say this". Read-only by default.

---

## Requirements

### Invocation

- REQ-920: `/wiki-audit <page>` SHALL be read-only by default. `--fix` MAY write, and
  only after explicit user confirmation of the proposed changes.

### Phase 1: Claim Map

- REQ-921: The system SHALL build the claim-to-source map mechanically (via
  check_citations.py per citations.md), then classify every remaining factual,
  non-common-knowledge claim that carries no `cite::` as UNCITED, listing each
  verbatim with its block location.

### Phase 2: Verification (parallel)

- REQ-922: The system SHALL dispatch ONE verification subagent per cited source, in
  parallel. Each subagent sees ONLY its own claim(s) and source; verdicts from one
  source MUST NOT leak into another's judgment. When the `wiki-audit-verify`
  agent definition is installed (specs/setup.md REQ-807), dispatch SHOULD use
  it (it pins the verification model tier, issue #108); a missing definition
  degrades to a generic subagent with the same prompt and isolation rules.
- REQ-923: Each subagent SHALL resolve its source (an `ingested/` path is read from
  disk; a `url:` ref is fetched) and judge ONLY whether the source supports the
  specific claim(s) citing it: verdict is one of `supported | partial | unsupported`,
  or `source-missing` when the target does not resolve. The verdict carries a
  one-line paraphrased justification, not long quotes.

### Phase 3: Reconciliation

- REQ-924: The system SHALL reconcile verdicts with the trust layer per schema
  REQ-586/588: all cited claims `supported` with independent corroboration MAY raise
  claim ratings (and thus the page minimum); any `unsupported`, `source-missing`, or
  UNCITED claim caps the page at `medium` (`low` when central claims fail) and MUST
  appear under `## Pending Review`. When the `wiki-audit-judge` agent
  definition is installed (specs/setup.md REQ-807), the reconciliation
  judgment (corroboration independence, `reliability::` deltas, Pending
  Review resolutions) SHOULD be dispatched to it; a missing definition
  degrades to reconciling in the session (issue #108).

### Phase 4: Report

- REQ-925: The system SHALL output a table (claim, citation, verdict) plus explicit
  lists of uncited claims, unsupported claims, and missing sources, and the proposed
  `reliability::` and Pending Review deltas. In default mode it SHALL NOT write.

### Capture-Backed Claims (v3.0)

- REQ-927: A claim whose ref is a capture ref (`archive.db:voice_notes/<id>`,
  specs/ingest.md Voice Sources) SHALL receive the distinct verdict
  `capture-backed` instead of being judged supported/partial/unsupported against
  the transcript: the transcript is raw capture, not a vetted source, and
  verifying against it would launder spoken speculation into green-checked fact.
  When the ref does not resolve against archive.db (dangling id), the verdict is
  `source-missing` (broken capture provenance); this resolution check is the
  audit-side durability tripwire for archive.db (specs/storage.md). During
  reconciliation (REQ-924), capture-backed claims keep the `reliability:: low`
  default of schema REQ-586b and MUST NOT raise any rating; the only upgrade
  path is a real source through normal ingest (per REQ-586b). STAGING: takes
  effect with the voice pipeline implementation (v3.0, P-3); until then no
  capture ref exists and the REQ-923 verdict set is unchanged.

### Fix Mode

- REQ-926: With `--fix` and after confirmation, the system SHALL: add `cite::` stubs
  to uncited claims (ref left for the user to fill), move unsupported/uncited claims
  under `## Pending Review` (NEVER silently delete prose), update `reliability::` and
  `updated::`, append a log entry
  (`## [YYYY-MM-DD] audit | <page> | <n> verified, <n> flagged | agents <names|none>`),
  and git commit. The `agents` field mirrors specs/ingest.md REQ-053: the
  agent definitions actually dispatched this run, or `none`; additive,
  never a self-reported model id.

---

## Scenarios

### Scenario 1: Unsupported claim flagged

```
GIVEN a page with three cited claims
AND the fixture source for claim 2 does not contain the fact claim 2 states
WHEN /wiki-audit runs on the page
THEN claim 2's verdict is unsupported and claims 1 and 3 are supported
AND the report proposes capping reliability:: at medium and adding claim 2 to Pending Review
AND no file is modified
```

### Scenario 2: Missing source

```
GIVEN a claim citing ingested/papers/gone.md which does not exist on disk
WHEN /wiki-audit runs
THEN that claim's verdict is source-missing
AND the report flags the broken provenance chain
```

### Scenario 3: Capture-backed claim is not verified against its transcript

```
GIVEN a page claim citing archive.db:voice_notes/17
AND the row exists in archive.db
WHEN /wiki-audit runs
THEN that claim's verdict is capture-backed (no subagent judges it against the
    transcript)
AND the report keeps its reliability at low per schema REQ-586b, noting that
    upgrading requires a real source through normal ingest
AND if the row did not exist, the verdict would be source-missing (dangling
    capture provenance)
```

---

## Acceptance Criteria

- Default run writes nothing
- Each verification subagent is isolated to its own claim and source
- Verdict set is exactly supported | partial | unsupported | source-missing;
  capture refs additionally yield capture-backed (REQ-927, v3.0)
