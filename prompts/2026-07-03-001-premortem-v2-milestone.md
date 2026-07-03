# Premortem Transcript — llm-wiki v2.0.0 Milestone

**Date:** 2026-07-03
**Method:** Gary Klein prospective hindsight — assume the plan has already failed, work backward.
**Fan-out:** 10 investigators (one per failure mode) + 1 adversarial counter-check, run in parallel.

---

## Context gathered

- **What it is:** The v2.0.0 milestone — dissolving the 469-line `wiki.md` monolith into a canon-first, agentskills.io-style multi-skill suite via 12 sequenced, dependency-chained GitHub issues (I-1…I-12). Spec foundation (#9/#10) already committed on the `dev` branch; ten implementation issues remain (scaffold + port; core scripts; setup v2; interactive ingest w/ checkpoint + `--auto` + `--import`; pre-archive secret scan; lint.py + wiki-lint; block-native `cite::` citations; wiki-audit + wiki-update; test harness; delete monolith + rewrite README + tag). Zero-dependency (python3 stdlib + bash). Both Logseq and Obsidian modes throughout.
- **Who it affects:** `larnsce` as effectively the sole maintainer; a handful of Logseq/Obsidian + Claude Code users; public repo; literature-research / data-steward use case (governed personal data possible).
- **Success criterion:** v2.0.0 tagged — monolith gone, human back in the ingest loop, all 6 original issues (#2,#4,#5,#6,#7,#8) resolved, every doc claim traceable to a spec REQ, tests green, and the tool **still used daily**.

**Frame:** It is 3 months later (bounded engineering milestone). v2.0.0 has failed. Why?

---

## Raw premortem — 9 failure reasons (before deep dives)

1. **Byte-identical trap (I-4/#12).** "init_wiki.py byte-identical to setup.sh" is a tar pit across two modes; #12 is the shared import, so a stall there stalls the whole critical path.
2. **Unenforceable DRY-canon.** "No rule stated in more than one place" is an acceptance criterion backed by nothing that runs; conventions narrated in specs + references + 7 SKILL.md + 2 Schema pages drift and contradict.
3. **Scope collapse / half-migrated limbo.** A solo maintainer can't finish 12 chained two-mode issues; the repo ends worse than v1 with two competing sources of truth.
4. **Spec-implementation drift.** 20+ REQs written before code; designs prove wrong on contact with Logseq's block model and subagent economics; specs rot into fiction.
5. **Checkpoint friction.** The mandatory pre-write ingest checkpoint is bypassed via `--auto`; the feature that answered #4 goes behaviorally dead.
6. **Test net covers only the mechanical shell.** LLM synthesis/citation/audit quality has no automated regression net — only a one-time manual protocol.
7. **Secret gate ~70% effective.** Stdlib regex misses PDFs/PII/novel tokens and false-positives; false confidence lands sensitive bytes in git history — #6's exact gap.
8. **Two-tool-mode tax.** Every script/skill forks Logseq vs Obsidian; the maintainer dogfoods one; the other silently breaks.
9. **Over-engineering for an audience of one.** v2's architecture is heavier to maintain than v1's single file; the project stalls under its own weight.

**Lens coverage:** demand/market (#9), execution/ops (#1,#3,#8), people (#3), timing/sequencing (#3,#4), competition/alternatives (upstream dormancy folded into #9), hidden assumption (#2,#4,#6). Finance/unit-economics N/A (open source, no revenue) — not forced.

---

## Deep dives

### 01 — Byte-identical trap stalls the critical path *(Prob Med · Impact Med)*

**Story.** wikilib.py's parser lands fast, but init_wiki.py stalls the moment "byte-identical to setup.sh for the default answers" meets reality: setup.sh's Python heredocs emit a trailing newline `open().write()` doesn't; a `sed` patch inserts a tab where the port uses four spaces; Obsidian mode drifts on frontmatter key ordering (string-concat vs dict). Each is a one-line fix that surfaces another. The tip is the decision to keep byte-identical a *hard* gate rather than semantically-equivalent — four evenings diffing `xxd` output instead of writing REQs — then "just one more mode," a combinatorial pit across every default-answer permutation × two editors that no REQ scoped. Because #12 is the shared import for every downstream script, I-5…I-11 can't scaffold against it. Momentum dies; the monolith keeps shipping because it still works; v2.0.0 stays untagged.

**Assumption.** That "byte-identical" was a cheap mechanical equivalence check, rather than a spec of every incidental artifact of a shell script — whitespace, ordering, newlines — that no one had canonized.

**Early signs.** init_wiki.py acceptance test red >~3 days while its diff shrinks to whitespace/newline/key-order deltas only; downstream issues (I-5+) have zero commits because nothing can import a not-yet-frozen wikilib.py.

### 02 — Unenforceable DRY-canon → rule drift *(Prob High · Impact Med)*

**Story.** The invariant "no normative rule in more than one place" is an acceptance criterion backed by nothing that runs. It tips first at wiki-ingest when the reliability-aggregation rule must appear in `schema.md`, in wiki-core references, and in *both* template Schema pages (which already diverge line-for-line today). "Load by reference" solves code duplication, not prose: a Logseq user's Schema page can't `@import` a reference, so the convention is narrated locally as designed. It tips irreversibly ~I-8 when a property enum gains a value — updated in spec and reference, missed in obsidian/Schema.md — with no linter comparing the five narrations; the only check was the maintainer re-reading everything each PR, which a solo dev stops by week three. The "12 lint rules" count drifts to "13 stated, 12 enforced." By tag, the MAY-vs-SHALL contradictions v2 existed to kill are respread across more files.

**Assumption.** A convention can live in exactly one place while five audiences each need to read it in situ, absent any tool that detects when the copies disagree.

**Early signs.** `diff` of logseq vs obsidian Schema.md shows normative divergence (already true today); the stated lint-rule count differs across SKILL.md, spec, and docs.

### 03 — Scope collapse into half-migrated limbo *(Prob High · Impact High)*

**Story.** The tip comes at I-4: extracting core scripts is billed as the foundation "gating almost everything," so it's done carefully and slowly. Waves 1–2 feel like progress on weekends, but I-4 forces the deferred decision that every script behave identically in both modes — silently doubling every downstream issue. By I-6 each "one issue" is two implementations plus a diff test, and a day-job crunch swallows three weekends. Momentum dies exactly where the chain fans out: I-6 gates I-7, I-9, I-10, so four issues freeze at once. The repo is already bimodal — `wiki.md` still works and is used daily, while `skills/` holds half-ported workflows the merged specs describe as finished. A README-follower hits a citation feature (I-9) documented but never built. Bad-options fork: finish six more chained two-mode issues nights-and-weekends, or revert and admit the specs lied. Neither happens; `dev` diverges from `main`; the canon-first specs become fiction; one clean source of truth becomes two competing ones with no fallback.

**Assumption.** A solo maintainer's spare-time velocity is roughly constant across 12 issues, when per-issue cost silently compounds through the two-mode requirement and the dependency chain.

**Early signs.** >~3 weeks between merged implementation PRs after I-4; `main` still ships `wiki.md` while `dev` has a non-empty `skills/` tree — both present past the I-6 mark.

### 04 — Spec-implementation drift, canon-first in the breach *(Prob High · Impact High)*

**Story.** REQ-904 ("source-file:: = union of the page's cite:: refs") is mechanically checkable on paper, but in Logseq source-file:: is page-level while cite:: lives on blocks, and the outliner reorders/merges blocks — constant invariant violations on legitimate edits, so the gate is downgraded from enforce to warn; REQ-904 becomes fiction the day it ships. REQ-922 ("one verification subagent per cited source, in parallel") fans a 30-cite page into 30 subagents — slow, expensive, rate-limited — so sources get batched "temporarily," breaking the isolation guarantee, and the verdict set drifts. REQ-951/952's mandatory source + before/after diff fight batch/scripted ingest, so an `--auto` path grows that skips the confirmation the spec makes unconditional. By the tag, #20's "every doc claim traceable to a REQ" is true only textually — claims trace to REQs the code no longer honors.

**Assumption.** A design's correctness can be established on paper against Logseq's block model and subagent economics before a single line of code tests it.

**Early signs.** Any REQ enforcement downgraded from SHALL/gate to "warn"/skipped in commit messages or config flags; citations/audit/update specs with zero edits after implementation commits touch the same behavior.

### 05 — The mandatory checkpoint reintroduces the friction it replaced *(Prob High · Impact Med)*

**Story.** The first few ingests, the maintainer actually stops at the checkpoint — reads the planned page touches, reliability ratings, contradiction flags, answers "what to emphasize / skip / route to L1." It feels like the gist restored. Then a conference dump lands: eighteen papers. Stopping eighteen times to read near-identical analysis blocks is unbearable, so `--auto` "just for this batch." It works fine — that's the poison: a skipped checkpoint's cost (a bad reliability call, a missed contradiction) is silent and deferred, while the checkpoint's cost is immediate and certain. Every rational ingest optimizes toward `--auto`. By month two it's muscle memory; #14 shipped as specified and #4 is behaviorally reopened, now with a flag that launders the autonomy as a deliberate choice. The other branch is worse: those who don't reach for `--auto` simply ingest less, and the wiki stops growing — failing "used daily" from the other direction.

**Assumption.** That a checkpoint made mandatory in code is also mandatory in behavior — that an always-available skip won't become the default when review cost is immediate and skip cost is invisible.

**Early signs.** `--auto` in >50% of ingest invocations within the first month; median checkpoint dwell time trending toward zero (displayed and dismissed in <~3s with no input entered).

### 06 — The test harness covers only the mechanical shell *(Prob Med · Impact High)*

**Story.** A line gets drawn — "the LLM-in-the-loop part cannot be asserted by a script" — and everything past it (synthesis quality, cite:: correctness, the supported/partial/unsupported verdict) is demoted to `docs/testing.md`, "a manual protocol executed once," on clean fixtures, by the person who wrote it. That single run is the entire regression net for the tool's only real value. `test_pipeline.sh` goes green on orphans, broken refs, uncited-claim detection, the fake secret — all true, all cheap, all beside the point. Then routine maintenance: a prompt tweak plus a model bump, both green, because nothing reads whether a cite:: points at a claim the source actually makes, or whether audit now calls a partial match "supported." Three months on it surfaces in the maintainer's own wiki — pages synthesized from unsupporting sources, citations on the wrong claim, inflated reliability — discovered by hand, in the one place trusted by definition, where wrong content reads as fact and compounds across links.

**Assumption.** Because the LLM behaviors can't be asserted mechanically, they don't need a regression net at all — a one-time manual protocol substitutes for continuous testing.

**Early signs.** A commit touching prompts / ingest / audit merges with only `test_pipeline.sh` green and no re-run of the manual protocol logged; a golden-transcript check on a fixed source (expected cite:: targets + audit verdicts) drifts after a prompt/model change.

### 07 — The secret gate is ~70% effective — worse than none *(Prob Med · Impact Critical)*

**Story.** secret_scan.py reuses REQ-042's regex, written for synthesized pages: `token::`, `password::`, `secret::`, `api-key::`, plus 40+ char base64. The `::` are Logseq delimiters that never appear in a Zotero export, a clipped web page, or extracted PDF text — so on real source bytes it matches almost nothing except the base64 rule, which fires on every embedded image, font subset, and PDF object stream. Week two, five false positives on innocuous PDFs; the maintainer routes them into `sensitive_source_types` and internalizes "it cries wolf." Then the case the data-steward actually cares about: a Zotero library exported with author emails and a scanned consent form (national IDs inside binary PDF text the strings pass fragments across object boundaries) sails through clean. The gate's reassuring silence retires the manual eyeballing REQ-014 assumed; the source moves verbatim into git-tracked `ingested/` and is committed. #6's sticky-exposure gap is realized — worse, because a green check certified it safe.

**Assumption.** A partial regex that catches some credentials is a net safety gain — when any automated pass that returns "clean" transfers responsibility off the human without earning it.

**Early signs.** `sensitive_source_types` grows entries added right after a blocked-ingest event (bypasses tracking false positives, not policy); zero true-positive blocks over many ingests while sources demonstrably contain emails/IDs.

### 08 — The two-tool-mode tax — the non-dogfooded mode silently breaks *(Prob High · Impact Med)*

**Story.** The two template Schema pages aren't one file with a variable — they're two hand-maintained files with different structure (block properties + `- ##` headings vs YAML frontmatter + bare `##`). That's four template pairs plus init_wiki.py instantiation plus wikilib.py parsing plus every script carrying an `if mode == logseq` branch. The maintainer dogfoods Logseq. The tip is the I-9 cite:: work ("Logseq block property; Obsidian indented child bullet"): the Logseq path runs daily; the Obsidian child-bullet path is written once, eyeballed against a hand-made fixture, never round-tripped through a real vault. "Verified in both modes" collapses to "the Logseq run passed and the Obsidian test I also wrote passed" — same author, same blind spot. Lint globs `Wiki___*.md` vs `Wiki/**/*.md`; the Obsidian nested glob matches zero files in some layouts, so lint reports green by finding nothing. v2.0.0 tags. Three months later the first Obsidian user hits byte-wrong pages, cite:: children that don't parse, lint false-passing on an empty set.

**Assumption.** A solo maintainer can keep two divergent format implementations equally correct when they only ever run one of them.

**Early signs.** Logseq commits outnumber Obsidian ~5:1 with near-zero Obsidian fixtures and no CI job instantiating a real Obsidian vault to byte-diff; lint on an Obsidian vault exits 0 while processing 0 files (empty glob).

### 09 — Over-engineering for an audience of one *(Prob Med–High · Impact High)*

**Story.** Building the openspec canon means every real change — a citation format, a cache-eviction tweak — now requires editing a REQ, reconciling it against wiki-core references, and keeping 8 skills consistent: a three-surface change where v1 was a single-file edit. The maintainer notices he spends Saturdays servicing the spec instead of writing notes. The audit subsystem with parallel subagents and the L1/L2 hub-index cache with LRU-demote are built for scale and adversarial trust a single-user personal wiki never experiences — provenance/trust guards a threat model of one trusted person. By month two, adding a note sometimes trips a stale REQ or a skill assuming the old cache contract; capturing a thought costs a debugging detour. The daily-use metric — the actual success criterion — inverts: the wiki gets opened to fix the wiki, not to think. Upstream Karpathy dormancy removes the external pull. With no second user to justify the abstraction and no one to share maintenance, he drifts back to plain Obsidian. v2.0.0 gets tagged; it just isn't used.

**Assumption.** Robustness machinery justified by multi-user/adversarial scale (trust layer, audit subagents, spec canon, LRU cache) pays off for a single-author personal wiki, when its only cost — maintenance — is borne by that same single person.

**Early signs.** Ratio of commits touching skills/specs/scripts vs commits adding actual wiki content trends above ~1:1 over a month; days-since-last-note grows while days-since-last-architecture-edit stays near zero.

---

## Adversarial counter-check — what did we miss?

### 10 — No migration path for the EXISTING corpus *(Prob High · Impact High)*

**Missing failure (headline).** Nothing in the 12 issues migrates the maintainer's existing wiki corpus, so v2's new schema, block-native cite:: format, and 12 lint rules land on a body of v1-authored pages that instantly become non-conforming — and "used daily" dies on day one against its own data.

**Story.** Every issue builds the machinery that *processes* a wiki, never the hundreds of pages already edited every day. Those were authored under v1 conventions: prose citations, old block structure, no schema discipline. The moment v2 ships, wiki-lint's 12 rules fire against real content and return a wall of violations; wiki-query and wiki-audit assume block-native cite:: the existing corpus doesn't have; wiki-maintain expects a schema no old page satisfies. There is no migration issue, no converter, no grandfather escape hatch, and the harness runs on `tests/fixtures` — clean synthetic data — so this never surfaces before tag. The maintainer, whose entire reason for v2 was to keep using his own knowledge base, now faces a manual reformatting slog across the whole vault. Realistically he reverts to v1 on the real wiki (v2 becomes shelfware validated only against fixtures) or the daily-use loop breaks — monolith gone, but the actual wiki left behind.

**Why overlooked.** The list scrutinized the code-and-spec pipeline exhaustively but treated the wiki as an abstraction, never as a concrete pre-existing pile of the maintainer's own bytes that must survive the cutover.

**Assumption.** That building a correct v2 engine is the whole job — silently assuming existing content will conform, or that a green run on synthetic fixtures means the real vault works.

**Early signs.** No issue, script, or REQ mentions converting/migrating existing pages; all fixtures are freshly authored. The first `wiki-lint` run against the real vault (not tests/) returns dozens-to-hundreds of violations.

---

## Synthesis

**① Most likely failure.** Scope collapse into half-migrated limbo (#3), compounded by the un-migrated real corpus (#10). Neither needs an adversarial condition — they're the base-rate outcome of a solo maintainer running 12 chained, two-mode issues, and the guaranteed result of shipping onto a v1 vault. The repo ends worse than v1: two competing sources of truth, no clean fallback.

**② Most dangerous failure.** The secret gate certifies a false "clean" and governed PII lands, sticky, in git history (#7). Lower probability than scope collapse but the highest-severity, hardest-to-reverse damage — and it directly re-opens the very issue (#6) it was built to close, now with a green check laundering the exposure. Insure against this regardless of likelihood.

**③ Likelihood × Impact.** Top-right (priority): #3, #10, #4, #9. High-impact / lower-prob: #6, #7. High-prob / lower-impact: #2, #5, #8. Lower/lower: #1.

**④ Hidden assumption.** That the job is building a correct v2 *engine*, when the success criterion is a knowledge base *still used daily*. Nearly every mode traces to treating the wiki as an abstraction (fixtures, specs, byte-diffs, dual-mode promises) instead of the maintainer's concrete corpus and habit. "Correct engine" and "still used daily" are different targets; the plan aims at the first.

**⑤ Revised plan.**
1. Add a one-time corpus-migration issue + a grandfather lint mode; release gate = wiki-lint on the *real* vault, not just fixtures. (→#10)
2. Demote "byte-identical" to "semantically equivalent" via a defined normalization; never block on `xxd`. (→#1)
3. Add a spec-consistency check (rule counts, enums, reliability rule agree across all narrations) in CI. (→#2)
4. Batch the ingest checkpoint (one review per queue, per-source expand); log `--auto` share. (→#5)
5. Golden-transcript tests for cite:: targets and audit verdicts, re-run on prompt/model change. (→#6)
6. Reframe the secret gate as an assist: source-byte regex (drop `::`), add email/national-ID PII patterns, "clean" output disclaims guarantee, track bypass-driven `sensitive_source_types` additions. (→#7)
7. Pick Logseq as tier-1; label Obsidian experimental unless CI byte-diffs a real Obsidian vault. (→#8)
8. Define a minimal coherent v2.0.0; defer audit/update/citations to v2.1 if momentum flags. (→#3,#9)

**⑥ Kill criteria.**
- >3 weeks between merged implementation PRs after I-4 → freeze scope, ship what's coherent, defer the rest.
- init_wiki.py byte-identical test red >3 days on whitespace/ordering deltas → switch to semantic-equivalent that day.
- First wiki-lint on the real vault returns >~20 violations with no grandfather path → do not tag; build migration first.
- `--auto` in >50% of ingests in month 1 → checkpoint design failed; redesign to batch review before claiming #4 is closed.

**⑦ Pre-launch checklist.**
1. Run wiki-lint against the actual production vault; confirm migration path + manageable violation count.
2. Instantiate a real Obsidian vault from init_wiki.py; byte-diff + round-trip a cite:: — or downgrade Obsidian to experimental.
3. Wire the spec-consistency check into CI.
4. Add ≥1 golden-transcript test for ingest citations and audit verdicts.
5. Confirm secret_scan.py catches a planted email / national-ID / PDF-embedded secret and disclaims guarantee on "clean."
6. Verify the cutover is atomic — `main` never ships wiki.md deleted with a workflow only half-ported.
