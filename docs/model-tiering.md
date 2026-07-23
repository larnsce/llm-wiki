# Model tiering: route wiki work by task value

Wiki work should run on the cheapest model whose output survives the
regression net, with deliberate escalation where reasoning quality
changes durable wiki truth. Fable is available on demand (not a scarce
or expiring resource), so the deepest-reasoning automated work runs on
Fable where it earns its keep, and mechanical or routine work stays on
the cheaper tiers where Fable adds nothing. This page is the operating
manual for that routing (issue #108): the tier map, the agent
definitions that implement it, the escalation triggers, the
observability story, and the review checklist that decides whether it
stays.

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
| `wiki-audit-judge` | fable | `/wiki-audit` Phase 3 (audit REQ-924) | corroboration independence, reliability deltas, Pending Review resolutions |
| `wiki-synthesize` | fable | `/wiki-ingest` flagged items (REQ-076) | deep Phase 1-2 analysis for dense or high-stakes sources |

The two deep-reasoning agents run on Fable: their job is exactly the
durable-truth work (final trust judgment, dense-source synthesis) where
the strongest reasoning is worth the cost. Verification (`wiki-audit-verify`)
stays on sonnet and triage stays on haiku, because volume-per-source
isolated checks and mechanical classification do not improve on the
cheaper model.

## Tier map

| Tier | Tasks |
|---|---|
| haiku | `/wiki-lint` and `/wiki-maintain status` runs, `raw/` queue triage, intake slugging, file moves, index and log updates, grep-style lookups, git hygiene |
| sonnet (default) | routine ingest (clippings, short articles, promoted notes), `/wiki-query`, `/wiki-import`, glossary maintenance, journal promotion, audit verification subagents, non-final drafting |
| opus | `/wiki-update` supersessions and the middle escalation step: a routine task that trips a trigger but is not durable-truth reasoning lands here first (sonnet -> opus) |
| fable | audit final judgment, dense or high-stakes ingest synthesis, corroboration reasoning, contested Pending-Review resolution; plus the deliberate batched sessions - schema/namespace/convention evolution and review-level cross-source synthesis pages |

Route by where the reasoning changes durable wiki truth, not by scarcity.
Fable carries the deepest automated work (the two deep agents above) and
the batched evolution sessions, because that is where the strongest
reasoning pays off. Opus is the middle escalation tier for routine tasks
that trip a trigger without being trust-level judgment. Sonnet is the
default session and the verification tier; haiku does the mechanical
work. Use the golden comparison below to confirm a cheaper tier is
enough before demoting a task.

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

Any trigger means: run that item's synthesis one tier up. A routine task
that trips a trigger goes sonnet -> opus. Durable-truth reasoning (final
audit judgment, dense or high-stakes synthesis, corroboration decisions
that move a `reliability::` value) is handled by the Fable agents
directly - that is what `wiki-audit-judge` and `wiki-synthesize` are for.

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
recorded on `claude-fable-5` (2026-07-08). These are the regression net
for tiering decisions: they capture what the strongest reasoning
produces on the judgment calls that matter, so a cheaper model's output
can be measured against them. They no longer exist because Fable output
was scarce (Fable is available on demand now); they exist because a
frozen reference is what lets a demotion be checked rather than assumed.

To evaluate a cheaper model for a task: stage the fixture per
`tests/golden/README.md`, run the skill to the checkpoint on the
candidate model, and diff against the baseline under the scoring rubric
(a divergence fails iff it changes a `reliability::` value, gets
`## Pending Review` wrong, or accepts false corroboration; cosmetics
never fail). A task may be demoted to the cheapest model whose output
passes. NEVER regenerate a baseline on the model being evaluated - that
re-baselines the net to the cheaper model's own calibration. Record
verdicts in the golden headers and on issue #108.

## Session discipline

- Daily driver: a sonnet session. Escalation happens per-task through
  the agents (a subagent MAY run a stronger model than the session), so
  the deep work reaches Fable without the session itself switching.
- The two deep agents already run on Fable per task, so most
  durable-truth reasoning needs no session change. Reserve a deliberate
  Fable `/model` session for the batched evolution work (schema or
  convention changes, review-level cross-source synthesis blocks) where
  the whole session is that kind of reasoning.
- Single-source interactive ingests skip triage entirely; the two-pass
  shape exists for queue drains.

## Vault-side CLAUDE.md template

Copy this block into the vault's CLAUDE.md so the orchestrating session
delegates without being asked each time:

```markdown
# Model routing (llm-wiki)

- Default session model: sonnet. Do not change /model for routine wiki
  work; the agents escalate per task on their own.
- /wiki-ingest with a multi-file queue: dispatch wiki-triage first
  (haiku), route complexity-flagged items through wiki-synthesize
  (fable), handle routine items in the session.
- /wiki-audit: dispatch per-source verification to wiki-audit-verify
  (sonnet) and the final reconciliation to wiki-audit-judge (fable).
- Escalate a routine task to opus when it supersedes existing wiki
  content or a cheaper attempt failed lint/audit twice. Durable-truth
  reasoning (reliability:: changes, corroboration judgment, dense or
  hub/Schema-touching synthesis) is already carried by the fable agents.
- Log honestly: the run-log agents field records what was actually
  dispatched; write "none" when no agent ran.
```

## Periodic review

The first review was due 2026-07-21 (issue #108). Run this checklist
periodically thereafter, posting the result as a comment on issue #108:

- [ ] Pull the last two weeks of run-log entries; compute the agent mix
      and the triage flag rate.
- [ ] Reconcile against the billing/usage dashboard: does the model mix
      match what the log implies? A contradiction means the routing is
      fiction somewhere; find the silent fallback.
- [ ] Which fable/opus runs could a cheaper tier have done? Re-run one or
      two on the cheaper tier against the baselines and check with the
      rubric; demote any task whose cheaper output passes.
- [ ] Flag rate outside 5-40% weekly? Re-tune the triage triggers.
- [ ] Post the adjusted tier map (or "unchanged") on issue #108.

Kill criterion: if the billing model-mix contradicts the run-log counts,
the routing is fiction somewhere - find the silent fallback before
trusting any tiering claim. (The original premortem also tied a hard
kill to Fable output expiring at a due date; Fable is available on
demand now, so that clock no longer applies. The regression net and the
honest run-log remain the guardrails.)
