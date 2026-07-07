# Premortem: Issues #107 (transcript route) + #108 (model tiering)

Session transcript, 2026-07-07. Premortem run over the two issues filed
earlier today — #107 (source-gap triage + AI-conversation-transcript
ingest route) and #108 (model tiering) — both scoped for implementation
on 2026-07-08, the last day of free Fable 5 access.
Method: Klein premortem; 8 parallel investigators + 1 adversarial
counter-check + synthesis. Rendered report:
`docs/premortem-report-20260707.html`.

## Gathered context

- **What:** two issues to implement in one high-capability session
  tomorrow. #107: a decision table for 11 source gaps
  (docs/source-routes.md) plus a full new ingest route for AI
  conversation transcripts (sensitive source type `transcripts`,
  raw/chat-*.md capture, capture-backed reliability:: low, interactive
  decision-extraction checkpoint, spec REQ block modeled on voice,
  golden test, one PR). #108: model tiering (Sonnet 5 default session;
  four agent definitions installed by setup.sh — wiki-triage haiku,
  wiki-audit-verify sonnet, wiki-audit-judge + wiki-synthesize opus;
  self-written `| model <alias>` run-log field; 2-week review;
  Opus-vs-Fable golden comparison as the evidence basis for the map).
- **Who:** Lars, solo maintainer, daily personal wiki use; public repo
  with strict discipline (canon-first specs, one PR per issue, harness
  in both tool modes, golden transcripts, check_canon); standing
  premortem rules gate expansion behind a daily review habit (#65,
  several gates still unticked).
- **Success (3 months):** both merged tomorrow; the transcript route
  routinely captures design decisions; the tier map holds quality while
  cutting cost, validated by logged data.

## Frame

It is 2026-10-07 (3 months later). Both issues shipped on the last free
Fable day. Both have failed. We look back and explain why.

## Raw failure reasons

1. **Deadline-driven scope blowout** — two canon-first spec PRs plus a
   two-model trial in one day vs. the repo's per-PR verification bar.
2. **Formalized before done by hand** — the transcript route ships full
   machinery with zero manual reps; real export artifacts don't match
   the design.
3. **Capture friction kills the habit** — five manual steps to
   re-process a conversation that feels already done; no export
   trigger moment; base habit gates unticked.
4. **Gitignored provenance rots** — sensitive transcript bytes live on
   one machine outside git-as-backup; audit breaks on machine
   migration; no archive.db-style backup requirement.
5. **Triage agent structurally blind** — escalation triggers defined in
   terms of wiki state cannot be evaluated by a haiku agent that only
   reads the raw/ queue; no golden pins triage.
6. **Self-reported model log is fiction** — the executing model cannot
   introspect its ID; silent agent fallbacks mean the `| model` column
   records the plan, not the execution.
7. **Silent quality erosion** — regenerating goldens on Sonnet
   re-baselines the regression net to Sonnet's own calibration;
   same-tier verification confirms its own tier's errors.
8. **Opus-vs-Fable trial undoable as specified** — scheduled behind two
   implementations; golden diffs are re-review signals, not verdicts;
   no scoring rubric, no dense-paper fixture chosen.

Counter-check added:

9. **The scarce resource is misidentified** — the last Fable day is
   spent writing code any model can write next week, while the only
   thing that expires at midnight (Fable's judgment applied to real
   content) is never banked.

## Deep dives

### 1. Deadline-driven scope blowout

**Story.** The tell was already in the CHANGELOG: 3.4.0 *and* 3.4.1 both
shipped 2026-07-07 — the queue was being force-drained toward the
deadline. On 2026-07-08, #107's decision table was done by 09:00; the
transcript route wasn't. The `transcripts` entry in
sensitive_source_types broke fresh-scaffold `--strict` lint at 13:40
(scaffold gitignore template didn't know `raw/chat-*.md`); the fix
rippled into setup.sh, storage.md, check_canon.py. The golden — the part
that pins LLM judgment and can't be rushed — was still unwritten at
16:00. First tip: the harness ran in only one tool mode "to save time."
Second tip, 19:15: the PR body's e2e transcript was written from memory
of a partial run. #108 got ninety minutes: two of four agents, no
`| model` field, trial verdicts pasted from a single unrepeated run.
Three months later the transcripts golden drifts on the first real chat
export and the route is abandoned.

**Assumption.** A higher-capability model compresses the *verification*
bar the way it compresses the writing — but harness, goldens, and e2e
transcripts cost wall-clock time regardless of who types.

**Early warnings.** (1) Two releases tagged the day before the deadline
(already visible). (2) Any PR body whose e2e transcript timestamp
predates the final commit on the branch.

### 2. Formalized before done by hand

**Story.** Every artifact assumed "a transcript is a markdown file you
rename to raw/chat-*.md." The golden fixture was a hand-written 200-line
idealized dialogue — nothing real existed to fixture from, because no
transcript had ever been ingested by hand. First real attempt
(2026-07-12): Claude Code `/export` produced a 41,000-line file of tool
calls, diffs, permission prompts; the checkpoint blew context before
reaching the design discussion. Second attempt: claude.ai has no clean
per-conversation markdown export, so copy-paste lost the structure the
REQ block assumed. The real workflow required an undocumented pre-trim
step the spec had no verb for; the golden kept passing against its
fictional fixture. By October: zero ingests in three months and an open
issue calling for a breaking spec change. The voice pipeline had a
Phase 0 exit test before its skill existed; #107 skipped exactly that
gate to catch the deadline.

**Assumption.** "Transcript" names an artifact like a voice memo — a
small, clean, self-contained markdown file — rather than an export
format problem never actually touched.

**Early warnings.** (1) The golden fixture was authored, not captured —
no real `/export` file ever committed to tests/. (2) No Phase 0
manual-exit issue (the #57/#65 pattern) existed before the spec PR.

### 3. Capture friction kills the habit

**Story.** Week one was novelty, not habit: two exports on July 9 and
11. The second checkpoint was the tip — re-litigating a decision made
three days earlier, approve-then-opt-in, felt like being deposed about
one's own conversation; twelve minutes to re-process something the
brain had filed as *done*. The existing loop is one motion (drop, run,
read); the chat route is five, and the first — noticing mid-conversation
that this chat matters — has no trigger. Issue #65's gate A (10 of 14
days of the *base* review habit) was unticked when #107 shipped: a
second habit stacked on an unformed first one. The `--auto` prohibition,
correct for sensitive content, removed the low-ceremony fallback. Zero
transcripts after July 11; decisions from ~40 subsequent sessions
evaporated exactly as before.

**Assumption.** Valuing captured decisions would generate the five-step
capture behavior — motivation substituting for a trigger.

**Early warnings.** (1) Zero new ingested transcripts in any 14-day
window after week one. (2) Median lag between a chat's timestamp and
its ingest exceeding 48 hours.

### 4. Gitignored provenance rots

**Story.** Transcripts instantly became the most-cited source type —
40+ pages by September, many carrying reliability:: low claims only a
re-read could raise. The tip was invisible: from the first ingest, the
bytes existed in exactly one place, and nothing complained. The vault's
durability story is "git is the backup," and the gitignore surgically
removed transcripts from it. Voice notes had REQ-1120 (off-machine
archive.db copy before first real data, restore drills); transcripts
got the gitignore pattern and nothing else — the file-move-as-provenance
model *felt* durable because it rides a git commit, but the commit
records the move, not the bytes. Late September: laptop migration,
fresh clone, old disk wiped after `git status` came back clean. October
audit: per-source subagents get ENOENT on every transcript citation —
60+ claims unverifiable exactly where decisions live.

**Assumption.** "In git history" and "durable" are the same property —
so excluding bytes from git needs no replacement durability plan.

**Early warnings.** (1) `git ls-files ingested/` diverging from
`ls ingested/**/*` — cited paths untracked. (2) A fresh clone on any
second machine immediately emitting source-missing for all transcript
citations.

### 5. Triage agent structurally blind

**Story.** Week one it under-flagged: a preprint contradicting figures
on an existing hub page hit triggers 1 and 2 — but Haiku could only see
the queue file, not the wiki, so nothing looked like a conflict. Sonnet
appended the new figure alongside the old; the contradiction hardened
and three later ingests cited it as settled. Trigger 3 ("is the target
a hub?") was equally blind; trigger 4 required history the pass doesn't
carry. Mid-August the prompt was "tightened" — *when in doubt, flag* —
and an agent that could never evaluate its triggers was always in
doubt: flag rate went ~4% → ~70%, Opus ran on grocery-list-grade
captures, and September's bill exceeded pre-tiering. Nobody caught
either phase because no golden ever asserted "this fixture must flag,
this one must not."

**Assumption.** Escalation triggers defined in terms of existing wiki
state can be evaluated by an agent whose inputs contain no wiki state.

**Early warnings.** (1) Sustained flag rate <5% or >40% in a week.
(2) Any Sonnet-processed item later editing a hub/Schema page or
changing a reliability:: value.

### 6. Self-reported model log is fiction

**Story.** Day one: the run-log spec told the executing LLM to write
`model <alias>`, but a model can't introspect its ID — the skill text
effectively said "write the alias from the tier map."
~/.claude/agents/wiki-triage.md wasn't installed (setup.sh never
re-run; scope mismatch), so the Agent tool silently fell back to the
session model — and the Dashboard line read `model haiku` anyway.
Fiction from run one. July 21: `/wiki-maintain status` counted 31
haiku / 9 sonnet / 4 opus, the review concluded haiku triage had "zero
regressions" (the session model had been doing haiku's job), and
demoted two more tasks. The instrument measured the plan, so it
validated the plan. The only cross-check — the billing dashboard — was
never in the loop; October's invoice showed premium spend flat against
a log claiming 78% haiku.

**Assumption.** The model executing a skill knows — or can be trusted to
report — which model it actually is.

**Early warnings.** (1) Billing model-mix diverging from run-log counts
(checkable in week one). (2) A 100%-clean model column with zero
fallback/inherit entries ever logged — from self-report, itself the
anomaly.

### 7. Silent quality erosion

**Story.** It tipped at the golden re-review. Sonnet's re-run diffed
against Fable-era transcripts and the diffs looked *reasonable* —
reliability:: high where Fable had said medium-with-Pending-Review. The
maintainer judged the new output defensible and regenerated the goldens,
re-baselining the regression net to Sonnet's calibration: from then on
the tests could only confirm Sonnet agreed with Sonnet. Structurally,
audit verification ran on Sonnet subagents making the same
characteristic errors as Sonnet ingest — treating two sources from one
origin as independent corroboration, reading hedges as assertions — so
audits returned clean verdicts on pages ingested with those same
errors; Opus judgment only reconciled verdicts it was handed. Pending
Review sections quietly emptied. Because pages take the minimum across
claims and later pages cite earlier ones, inflated ratings laundered
upward through the graph. October spot-check: a drifted claim under
reliability:: high, and no way to tell which stratum to trust.

**Assumption.** Verification is a cheaper task than generation — a
checker of the same tier as the worker adds independent signal.

**Early warnings.** (1) Rate of ## Pending Review sections created per
ingest drops after the switch. (2) Golden re-run diffs clustering in
reliability:: values, all in the generous direction.

### 8. Opus-vs-Fable trial undoable as specified

**Story.** The trial was task 5 of 7 in #108, behind the
implementation, where it died. By evening, "re-run goldens once on
sonnet" became the whole trial: no opus run, no fable run, no dense
paper (none was ever picked — "genuinely dense" was never defined). The
deeper tip was scoring: the golden README's own rule — a diff is a
re-review signal, not automatically a failure — means a diff can't
produce a verdict. The one hasty comparison that ran produced two
defensible checkpoint tables differing on a hub cross-link and one
reliability rationale; adjudication was deferred to the July 21 review,
which never happened. Weekly Fable sessions were never scheduled —
nothing in #108 creates a trigger, only "session discipline" prose.
October: golden headers say validated-on-sonnet; the fable tier rows
shipped with zero demonstrations, and re-running now costs $10/$50 per
MTok.

**Assumption.** A regression net built to flag one model's drift can
double, unchanged and unscored, as a cross-model benchmark squeezed
into implementation leftovers.

**Early warnings.** (1) End of 07-08: no Fable verdict line in any
golden header, no verdict comment on #108. (2) No dense-paper fixture
committed before the trial day started.

### 9. The scarce resource is misidentified (counter-check)

**Story.** All eight reasons critique *how* the two issues get built;
none questions whether building them is what a final frontier-model day
is *for*. The repo's own premortem states the governing insight: the
plan engineers the free part (code) and assumes the expensive part
follows. Specs, configs, skills, setup.sh edits are the free part —
Sonnet can produce them next week at no urgency. What becomes expensive
at midnight is Fable *output*: Fable-generated golden baselines, the
comparison corpus, a Fable pass over the real source gaps, Fable
adjudicating the wiki's actual contested claims. That is precisely the
data #108's map needs to be "validated by real data" — and the plan
schedules it last, guaranteeing it gets cut. The plan burns the
expiring asset to manufacture durable ones and lets the expiring one
lapse.

**Assumption.** "Maximize the last free day" = "merge maximum PRs
before the clock," when it should mean "bank maximum irreplaceable
model judgment."

**Early warnings.** (1) By midday, the session transcript shows only
scaffolding and spec-writing — zero Fable invocations against real
wiki or transcript content. (2) Nothing in either merged PR is an
artifact only Fable could have produced.

## Synthesis

**Most likely failure:** the composite of 1+8+9 — the implementable
crowds out the expiring. Implementation eats the day (the repo *can*
ship 11 PRs in a day, but the verification bar plus a two-model trial
cannot coexist with it), the trial gets cut, and the one workload with
a hard deadline is the one that doesn't happen.

**Most dangerous failure:** 7, silent quality erosion. Regenerating
goldens on the new default model destroys the only instrument that
could detect the downgrade; same-tier verification then confirms its
own tier's errors, and inflated reliability compounds through the
citation graph into durable wiki truth. Cheap to prevent tomorrow,
nearly impossible to undo in October.

**Likelihood × impact (2×2):**
- High P / High D: 9 (misallocated Fable day), 3 (capture friction),
  7 (quality erosion).
- High P / Medium D: 1 (scope blowout), 8 (trial yields no verdicts),
  2 (formalized before hand-use), 6 (model log fiction).
- Low-Med P / High D: 4 (provenance rot — fires on machine migration).
- Medium P / Medium D: 5 (triage blindness).

**The hidden assumption:** *"Maximizing the last free Fable day means
merging maximum tooling before midnight."* Inverted: code is the free
part — Sonnet can write all of it on Thursday. The only thing that
expires is Fable's judgment applied to real content: frozen baselines,
a comparison corpus, hand-run transcript ingests, adjudicated Pending
Review items. Sub-assumptions the issues never questioned: that a
transcript is a small clean file; that a same-tier checker adds
independent signal; that a self-report log measures execution.

**Revised plan:**

*Tonight (~30 min prep):*
1. Pick and commit the dense-paper fixture for the comparison corpus.
2. Save one real Claude Code `/export` file and one claude.ai
   conversation as raw material — real artifacts, not authored ones.
3. Write the one-paragraph comparison scoring rubric BEFORE any run:
   a divergence counts as failure iff it changes a reliability:: value,
   misses a required ## Pending Review, or accepts false corroboration;
   page-plan cosmetics don't count.

*Tomorrow (Fable day) — bank judgment, build nothing:*
4. Run Fable over the 3 existing goldens + the dense paper; commit the
   outputs as frozen `fable-baseline` reference files. These are never
   regenerated; future models are diffed against them. (Opus/Sonnet
   sides of the comparison are repeatable any day — only the Fable side
   expires.)
5. Do the transcript verb BY HAND twice (the real /export + the
   claude.ai chat), Fable driving, using existing ingest/import — no
   new machinery. This is #107's missing Phase-0 exit test and yields
   the real golden fixture.
6. Spend the rest of the day on the work the tier map itself reserves
   for Fable: adjudicate contested ## Pending Review items, audit the
   most-cited pages, sanity-pass the 11-gap decision table.

*Later, on Sonnet/Opus (no deadline) — implement descoped:*
7. #107 descope: ship docs/source-routes.md + a documented manual
   transcript protocol. The spec REQ block waits for 5 hand ingests
   (the done-by-hand gate). Design adds the pre-digest/trim verb the
   real artifacts require, and evaluates capture-at-source (an
   end-of-session "write the decision log" instruction) as the primary
   mechanism over post-hoc export.
8. #107 provenance fix: sensitive transcripts get an explicit backup
   REQ mirroring archive.db's REQ-1120 (named off-machine copy before
   first real ingest) and an audit tripwire distinguishing
   source-missing from low-reliability.
9. #108 descope: triage triggers rewritten to queue-decidable inputs —
   give wiki-triage the hub index and Schema page list as explicit
   context; use length/type/multiple-sources-on-one-topic proxies;
   move the "supersedes" check to the Sonnet ingest checkpoint (which
   does read the wiki). Add a triage golden (must-flag / must-not-flag
   fixtures).
10. #108 logging fix: log the dispatched agent *name* (observable),
    not a model alias (not observable); reconcile against the billing
    dashboard at the 2-week review; treat a fallback-free log as an
    anomaly.
11. #108 golden rule: never regenerate goldens on the new model — diff
    against the frozen Fable baselines; a generous-direction
    reliability:: diff means escalate the task, not re-baseline the
    test.

**Kill criteria:**
1. 2026-07-08 12:00 — if the Fable baselines (goldens + dense paper)
   and both hand transcript ingests are not done by noon, cancel all
   implementation for the day and bank Fable artifacts until midnight.
2. Transcript route — if fewer than 5 transcripts have been
   hand-ingested by 2026-07-22, the spec REQ block does not get
   written; the route stays a manual protocol in source-routes.md.
3. Tiering — at the 2026-07-21 review, if the billing model-mix
   contradicts the run-log counts, or the review does not happen,
   remove the agents and freeze at "Sonnet default + manual /model
   escalation."

**Pre-launch checklist:**
1. Dense-paper fixture committed (tonight).
2. One real /export + one claude.ai conversation saved raw (tonight).
3. Comparison scoring rubric written and committed before any run.
4. Backup path for sensitive transcript bytes named BEFORE the first
   sensitive ingest ever happens.
5. Honest #65 check: the base-habit gate is still unticked and both
   issues are "expansion" under the standing premortem rules — tick the
   gate or explicitly accept the exception in writing.
