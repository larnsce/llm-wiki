# Model tiering: route wiki work by task value

Once model usage costs real money, wiki work should run on the cheapest
model whose output survives the regression net, with deliberate
escalation where reasoning quality changes durable wiki truth. This page
is the operating manual for that routing (issue #108, premortem-revised):
the tier map, the agent definitions that implement it, the escalation
triggers, the observability story, and the review checklist that decides
whether it stays.

## How the routing works

Routing lives in the `agents/` subagent definitions that `setup.sh`
installs to `~/.claude/agents/` (or `<project>/.claude/agents/` with
`--project`), per setup REQ-807. Shipped SKILL.md files stay
model-neutral on purpose: llm-wiki is a public tool, and a `model:` key
in a skill would silently change cost behavior for every user. Skills
NAME the agents in their dispatch steps and degrade gracefully to
generic subagents when the definitions are absent, so a user who never
installs them gets exactly the old behavior.

Do NOT set `CLAUDE_CODE_SUBAGENT_MODEL`: the resolution order puts that
env var above per-agent frontmatter, so it would silently override every
`model:` this design relies on.

The four agents:

| Agent | Model | Used by | Job |
|---|---|---|---|
| `wiki-triage` | haiku | `/wiki-ingest` queue drains (ingest REQ-076) | slugs, types, priority, complexity flag; queue-decidable triggers only; never writes |
| `wiki-audit-verify` | sonnet | `/wiki-audit` Phase 2 (audit REQ-922) | per-source claim verification, isolated |
| `wiki-audit-judge` | opus | `/wiki-audit` Phase 3 (audit REQ-924) | corroboration independence, reliability deltas, Pending Review resolutions |
| `wiki-synthesize` | opus | `/wiki-ingest` flagged items (REQ-076) | deep Phase 1-2 analysis for dense or high-stakes sources |

## Tier map

| Tier | Tasks |
|---|---|
| haiku | `/wiki-lint` and `/wiki-maintain status` runs, `raw/` queue triage, intake slugging, file moves, index and log updates, grep-style lookups, git hygiene |
| sonnet (default) | routine ingest (clippings, short articles, promoted notes), `/wiki-query`, `/wiki-import`, glossary maintenance, journal promotion, audit verification subagents, non-final drafting |
| opus | audit final judgment, `/wiki-update` supersessions, dense or high-stakes ingest synthesis, corroboration reasoning; every escalation trigger lands here first |
| fable (batched, deliberate sessions) | schema/namespace/convention evolution, review-level cross-source synthesis pages, contested Pending-Review resolution batches; each task only after opus demonstrably falls short on the goldens |

Opus, not Fable, is the escalation default: half the price, none of the
API-side caveats. Fable is reserved for deliberate batched sessions, and
promotion of a task from opus to fable happens per-task, only on
evidence from the golden comparison below.

## Escalation triggers

Two kinds, and keeping them apart is what makes triage cheap
(issue #108 premortem):

Queue-decidable (the `wiki-triage` flag; decided WITHOUT reading wiki
pages, from the queue files plus the hub index and Schema list handed to
the agent):

1. long source (real reading required);
2. dense paper (many findings/methods/limitations);
3. another queue item or `ingested/` source on the same topic
   (corroboration/contradiction decisions likely);
4. the topic maps to a hub or Schema page itself (high blast radius);
5. the triage agent's own low confidence.

Checkpoint-decided (needs wiki state, so the SESSION decides at the
batch checkpoint, never triage):

6. the change would SUPERSEDE existing wiki content rather than append
   (`/wiki-update` territory);
7. a genuine conflict with existing claims, or a corroboration decision
   that would change a `reliability::` value;
8. a cheaper model's output failed lint or audit twice on this task, or
   it self-reports low confidence.

Any trigger means: run that item's synthesis one tier up (sonnet ->
opus). Fable enters only through the per-task promotion rule above.

Early warning: a sustained weekly triage flag rate below 5% or above 40%
means the triggers are mis-tuned; re-check them against
`tests/golden/triage.golden.md`.

## Observability: the run log, not self-report

Every ingest and audit run-log entry on the Dashboard carries an
`agents <names|none>` field (ingest REQ-053, audit REQ-926): the agent
definitions actually DISPATCHED, or `none`. This is deliberately not a
model name: the executing model cannot introspect its own id, and a
silent fallback (agents not installed, org allowlist, `inherit`) would
log the plan instead of the execution. `/wiki-maintain status` reports
the agent mix over the last 10 runs. At review time, reconcile the log
against the billing/usage dashboard; treat a log with no `none` entries
at all as an anomaly, not a success.

## Golden comparison protocol

`tests/golden/fable-baseline/` holds the frozen reference checkpoints
recorded on `claude-fable-5` (2026-07-08). To evaluate a cheaper model
for a task: stage the fixture per `tests/golden/README.md`, run the
skill to the checkpoint on the candidate model, and diff against the
baseline under the scoring rubric (a divergence fails iff it changes a
`reliability::` value, gets `## Pending Review` wrong, or accepts false
corroboration; cosmetics never fail). Each task defaults to the cheapest
model whose output passes. NEVER regenerate a baseline on the model
being evaluated. Record verdicts in the golden headers and on issue
#108.

## Session discipline

- Daily driver: a sonnet session. Escalation happens per-task through
  the agents (a subagent MAY run a stronger model than the session).
- Batch the fable-tier work into deliberate sessions (weekly synthesis
  or audit blocks); never make fable the default `/model`.
- Single-source interactive ingests skip triage entirely; the two-pass
  shape exists for queue drains.

## Vault-side CLAUDE.md template

Copy this block into the vault's CLAUDE.md so the orchestrating session
delegates without being asked each time:

```markdown
# Model routing (llm-wiki)

- Default session model: sonnet. Do not change /model for wiki work.
- /wiki-ingest with a multi-file queue: dispatch wiki-triage first
  (haiku), route complexity-flagged items through wiki-synthesize
  (opus), handle routine items in the session.
- /wiki-audit: dispatch per-source verification to wiki-audit-verify
  (sonnet) and the final reconciliation to wiki-audit-judge (opus).
- Escalate a single task to opus when it supersedes existing wiki
  content, changes a reliability:: value, touches a hub or the Schema
  page, or a cheaper attempt failed lint/audit twice.
- Log honestly: the run-log agents field records what was actually
  dispatched; write "none" when no agent ran.
```

## Two-week review (due date 2026-07-21)

Checklist, posted as a comment on issue #108:

- [ ] Pull the last two weeks of run-log entries; compute the agent mix
      and the triage flag rate.
- [ ] Reconcile against the billing/usage dashboard: does the model mix
      match what the log implies? A contradiction means the routing is
      fiction somewhere; find the silent fallback.
- [ ] Which opus/fable runs could sonnet have done? Re-run one or two on
      the cheaper tier against the baselines and check with the rubric.
- [ ] Flag rate outside 5-40% weekly? Re-tune the triage triggers.
- [ ] Post the adjusted tier map (or "unchanged") on issue #108.

Kill criteria (from the premortem, binding): if the billing model-mix
contradicts the run-log counts, or the review does not happen by the due
date, remove the agents and freeze at "sonnet default plus manual
`/model` escalation".
