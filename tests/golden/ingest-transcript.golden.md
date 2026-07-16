# Golden transcript: wiki-ingest checkpoint for a fixture AI-chat export

Pinned source: `tests/golden/source/chat-2026-06-25-vault-design.md`, a FAKE
curated claude.ai export written for this suite. It enters the queue as
`raw/chat-2026-06-25-vault-design.md`, so the `chat-` prefix triggers the
transcript route (ingest REQ-1300).

Conditions of the recorded run: freshly scaffolded logseq-mode vault
(init_wiki.py defaults), `llm-wiki.yml` with the config.example.yml source
pipeline (`transcripts` in `source_types` AND in `sensitive_source_types`),
interactive mode, run date 2026-07-16. Pinned 2026-07-16 for the transcript
route (issue #107 Part 2, gate waived by maintainer decision) against ingest
REQ-1300..1305.

model: claude-fable-5 (recorded at pinning, issue #107; there is no
separate fable-baseline copy - this golden IS the Fable recording).

A diff against this file after a prompt or model change is a re-review
signal, not automatically a failure. See `tests/golden/README.md`.

The six behaviors this golden pins: `chat-` prefix type inference, the
per-decision opt-in table (batch confirmation never covers wiki writes from
a transcript), the confirmed-decision `medium` vs model-analysis `low` split
(REQ-1302 / schema REQ-586b), the repo-absorbed-content skip (REQ-1304), the
individual confirmation for the row naming a person (REQ-084), and the
sensitive-type flow (bytes move to gitignored `ingested/transcripts/`,
REQ-1301/REQ-046).

---

## Checkpoint table (verbatim format from SKILL.md)

| # | Source | Proposed page touches | Reliability (one-line rationale) | Contradictions |
|---|--------|-----------------------|----------------------------------|----------------|
| 1 | chat-2026-06-25-vault-design.md (transcripts) | 2 touches: create `wiki/tech/vault-architecture` (both confirmed decisions plus the flagged model claim); update hub `wiki/tech` (routing line) | split per REQ-1302: the two decisions `medium` once individually confirmed (user's own conclusions); the 20,000-page degradation claim `low` (model-asserted, capture-backed, schema REQ-586b) | none (fresh vault scan) |

Journal: journals/2026_07_16 <- 1 decision-log block (2-4 lines)

Transcript variant: wiki writes are opt-in PER DECISION below; only the
journal decision-log entry is batch-confirmable (REQ-1303).

## Decision table (per-decision opt-in, REQ-1302/1303)

| # | Decision (full sentence to be written) | Target | cite | reliability |
|---|----------------------------------------|--------|------|-------------|
| 1 | One graph per sharing boundary: the wiki stays private and personal; teaching materials live in their own graph because they are shared with students and archived every semester - sharing boundary and lifecycle, not topic, decide graph membership. | create `wiki/tech/vault-architecture` | ingested/transcripts/chat-2026-06-25-vault-design.md | medium once confirmed (the user's own recorded decision; the confirmation makes the user the source) |
| 2 | Cross-cutting concepts (reproducibility, data ethics) are tags, not namespaces: namespace depth stays capped at three, and a concept that belongs to two hubs is a tag by definition. | same page, second claim block | ingested/transcripts/chat-2026-06-25-vault-design.md | medium once confirmed |

## Model-asserted analysis (stays low, Pending Review, REQ-1302/REQ-074)

- Claim: Logseq Datalog queries degrade noticeably past roughly 20,000
  pages.
- Written only if the user opts in, at `reliability:: low` (capture-backed:
  the chat is where it was said, not a source for it being true), with a
  `## Pending Review` entry: corroborate from a real source through normal
  ingest before relying on it. The transcript cannot corroborate itself
  (schema REQ-586b). Page roll-up: if this claim is included,
  `wiki/tech/vault-architecture` carries `reliability:: low` (page minimum
  across claims, REQ-073).

## Skipped as another system's record (REQ-1304, not offers)

- The setup.sh flag bug: the repository's issue and commit already record
  it; the transcript adds nothing. Skipping content is a valid outcome; the
  file still completes the lifecycle move.

## Row naming a person (individual confirmation, REQ-084)

- The Jana graph-slowdown remark names a person. It is NOT proposed as a
  wiki claim (anecdote, no durable content); it surfaces only in the TODO
  hand-over below. Anything from it that the user asks to write would be
  confirmed individually, full sentence shown, never on a batch yes.

## TODO hand-over (REQ-087)

Offered for the human to place (today's journal on request, or a `para/`
page the human edits themself):

1. Ask Jana for her graph's actual page count before treating the
   20,000-page degradation figure as real.

## Journal decision-log block to be written on confirmation (REQ-1303)

```
- Vault design decisions from a claude.ai chat (2026-06-25): one graph per
  sharing boundary - the wiki stays private, teaching materials get their
  own per-semester graph ([[wiki/tech/vault-architecture]]); cross-cutting
  concepts become tags, not namespaces.
  ingested/transcripts/chat-2026-06-25-vault-design.md
```

## Sensitive-type flow (REQ-1301, REQ-046)

After confirmation: the secret gate scans the file (clean), the vault
`.gitignore` covers `ingested/transcripts/`, and the move target verifies
ignored (`secret_scan.py --gitignore-check`). The wiki page, hub line, and
journal block enter the atomic commit; the transcript bytes do not. Page
properties record `source-file:: ingested/transcripts/chat-2026-06-25-vault-design.md`
- the provenance path stays valid locally, only the bytes stay out of
history.

With `--auto`: the system states that transcript sources are interactive-only
(REQ-1303) and presents this same checkpoint anyway.
