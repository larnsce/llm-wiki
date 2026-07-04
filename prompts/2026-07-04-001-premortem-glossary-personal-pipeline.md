# Premortem: Glossary (v2.3) + Personal Pipeline (v3.0) plan

Session transcript, 2026-07-04. Premortem run over the draft plan in
`docs/roadmap-glossary-personal-pipeline.md` (the two concepts in
`prompts/glossary-concept.md` and `prompts/llm-wiki-setup-plan.md`).
Method: Klein premortem; 9 parallel investigators + 1 adversarial
counter-check + synthesis. Rendered report:
`docs/premortem-report-20260704.html`.

## Gathered context

- **What:** two milestones on top of the shipped v2.0-v2.2 suite. v2.3
  Glossary: a glossary/ namespace, EN|DE|Rule|Note domain tables, term pages,
  #glossary-todo capture + curation skill, Glosario import, lint rule 15.
  v3.0 Personal pipeline: storage-plane spec (index.db derived/disposable,
  archive.db irreplaceable, both gitignored), voice pipeline
  (whisper.cpp -> archive.db -> wiki-ingest-voice skill -> journal summary +
  wiki updates), rebuild_index.py, two-plane query routing, docs-only guides
  for the personal plumbing.
- **Who:** Lars, solo maintainer, German/English educator + data scientist,
  fresh empty Logseq graph, one MacBook, public repo, implementation via
  Claude Code agents (v2.0-v2.2 was 11 PRs in one day).
- **Success (6 months):** glossary decisions recorded once and referenced in
  German drafting; voice memos reliably become journal summaries + wiki
  updates; daily 5-10 min review habit alive; maintenance within 1-2 h/month.

## Frame

It is January 2027 (6 months later). Both additions have failed. We look
back and explain why.

## Raw failure reasons (9 + 1 from the counter-check)

1. Glossary curation loop dies (capture frictionless, curation untriggered)
2. Fourth-namespace spec churn erodes the just-shipped three-namespace canon
3. Glosario import flood outcompetes curation; Rule column stays empty
4. Silent plumbing decay kills trust (capture leg breaks invisibly)
5. Synthesis quality rot (transcripts are not sources; audit launders noise)
6. The second plane eats the architecture (index.db stops being derived)
7. Privacy leak through the promotion seam (candid sentence about a named person)
8. Tooling outruns behavior; five simultaneous habits crush the cold start
9. Hand-rolled YAML parser is the wrong hill
10. (Counter-check) archive.db loss: irreplaceable yet gitignored, no backup REQ

## Deep dives

### 1. Glossary curation loop dies

THE FAILURE STORY: July 2026: G-1 through G-6 ship on schedule. Lint rule 15
passes, init --with-glossary scaffolds three domain pages, the Glosario
import lands 400 staging rows with empty Rule columns. It looks alive.
Capture works immediately because it costs nothing: typing #glossary-todo
mid-sentence takes two seconds. By September the fresh graph holds 60+ todos
scattered across journals and post drafts. Curation is where it dies, and it
dies quietly. The wiki-glossary skill is pull-only: Lars must open Claude
Code, invoke it, and sit through a checkpoint deciding keep-en vs translate
vs context for each term. The first pass, in August, drains 20 todos in 40
minutes; it feels like grading, not writing. The second pass never gets
scheduled because nothing schedules it: no lint failure fires on aging todos
(rule 15 checks table structure, not queue depth), no journal reminder, no
exit test like v3.0's Phase 0 has. Skipping costs zero that day. The tipping
moment: October, drafting a German teaching post, Lars needs the "pipeline"
decision, finds the domain page holding 12 rows and 400 unreviewed staging
entries, decides faster from memory, and stops loading glossary context at
all. Published posts in November use three different renderings of
"notebook". The glossary froze at roughly 15 decided rows.

UNDERLYING ASSUMPTION: That a friction-free capture mechanism implies the
downstream curation pass will happen, when capture and curation have opposite
cost profiles and only capture was engineered.

EARLY WARNING SIGNS: (a) count of open #glossary-todo tags rises for 3+
consecutive weeks while decided domain-table rows stay flat; (b) zero
wiki-glossary invocations in a calendar month.

### 2. Fourth-namespace spec churn

THE FAILURE STORY: The tip came at G-1, days after v2.2 shipped. The agent
amended REQ-960 from "exactly three" to "exactly four" and patched rule 14's
allowlist, but the contract was never one requirement; it was a phrase
repeated everywhere. The spec's own title ("wiki/ | para/ | notes/ Contract
and Scope"), Scenario 7 ("stray page outside the three namespaces"), the
acceptance checklist, the scope-guard reference, two roadmap docs, and
templates all narrated "three" in prose. check_canon stayed green because,
by its own docstring, such phrases are narration, not structure: it verifies
rule counts and marker phrases, not the namespace count. Green light,
rotting canon. The second tip was G-3: the glossary ownership model is
genuinely novel (human-decided, tool-readable, structure-linted), and G-3's
issue text already says both things at once: glossary pages are "exempt from
wiki-only rules" AND linted under rule 15. One doc copied the para/notes
framing and called glossary/ exempt; another called it enforced. After the
one-day v2 sprint, in which namespaces.md was renumbered three times, Lars
had stopped reading amendment diffs line by line. By January the honest
answer to "is glossary/ in scope for prune?" differed by which file you
opened, and check_canon's green checkmark stopped meaning anything.

UNDERLYING ASSUMPTION: That check_canon's green status covers every surface
where the namespace contract is narrated, when it only covers counted
structure.

EARLY WARNING SIGNS: (a) `grep -ril "three namespaces|exactly three"`
returns more than zero files after the G-1 PR merges while check_canon
reports all surfaces aligned; (b) the G-1 diff touches fewer files than a
grep for "namespace" across specs, references, templates, and docs returns.

### 3. Import flood

THE FAILURE STORY: Week one, Lars ran glossary_import.py against the fresh
graph. The Glosario YAML, EN+DE filtered, landed roughly 400 rows on
glossary/imported/glosario with source:: attribution, status:: unreviewed,
Rule empty. That page was instantly the largest, most complete-looking page
in an otherwise empty graph. The three domain pages held maybe eight
hand-entered terms combined. The first tipping moment came in week two,
drafting a German blog post: he needed "cache" and "pipeline", neither was
in glossary/tech, both were on the staging page. Loading the staging page as
drafting context worked. The translation was right, the post shipped, and no
Rule was ever recorded. The second tip was structural: promotion cost three
edits per term while lookup cost zero. The wiki-glossary skill automated the
mechanics but still demanded the one thing that cannot be automated, the
human Rule decision, so promotion sessions felt like data entry and got
deferred. By January 2027 the staging page is the glossary. Domain pages: 19
terms, 14 with a Rule. Staging: 400 rows, unreviewed, Rule empty at scale.
Drafting context is a CC-BY dictionary dump, and it silently answers keep-en
versus translate questions Lars never actually decided, so his published
texts now encode Glosario's choices, not his.

UNDERLYING ASSUMPTION: That a complete third-party lookup table sitting next
to an empty curated one would motivate curation rather than substitute for
it.

EARLY WARNING SIGNS: (a) staging page appears in drafting-session context
loads more often than any domain page within the first month; (b)
promoted-terms count flat across two consecutive weekly reviews.

### 4. Silent plumbing decay

THE FAILURE STORY: It tipped on September 15, 2026, when iOS 20.1 landed.
The Voice Memos Shortcuts automation, the plan's capture leg, needed a
one-time re-confirmation after the update; the prompt appeared once on the
lock screen and was swiped away. From that day, memos stayed on the phone.
Nothing errored. The iCloud Drive folder just stopped receiving files, and
~/voice-inbox/ stayed empty, which the launchd job correctly interpreted as
nothing to drain. The plan's core comfort, "worst case is delay, nothing is
lost", assumed queuing happens on the Mac side where the drain loop can see
it. It queued on the phone instead, invisible to every component that runs
nightly. Lars kept speaking memos for about two weeks; journal summaries
kept appearing at first, drawn from the pre-update backlog archive.db
already held, so the loop looked alive while it was dead. When summaries
thinned out in early October, he attributed it to travel and a sleeping
laptop, exactly the intermittency his own plan had normalized. The plan
trained him to ignore gaps. He noticed in late October: 40-plus memos
stranded on the phone. He fixed the Shortcut in ten minutes and whisper.cpp
drained everything in one night, but summaries of six-week-old ramblings
referenced stale contexts and dead decisions; he skipped reviewing them. By
December he had stopped recording. The habit died not from the outage but
from the worthless catch-up batch.

UNDERLYING ASSUMPTION: Every failure mode queues data where the drain loop
can see it, so silence means empty, never broken.

EARLY WARNING SIGNS: (a) days since the newest file arrived in
~/voice-inbox/ exceeds 3 while the phone shows recent memos; (b) the daily
journal summary is absent or covers zero new voice_notes rows for 5
consecutive days.

### 5. Synthesis quality rot

THE FAILURE STORY: August 2026: the pipeline launches and works, in the
sense that pages change. The first tip comes in September, when a walking
memo mentions a collaborator; whisper.cpp renders "Marek" as "Mark", the
context prompt lists neither, and wiki-ingest-voice appends a plausible line
to the wrong person page. The checkpoint does not catch it because Lars is
approving 15 summaries in a batch and the line reads fine. Second tip,
October: a driving memo containing "I should maybe pitch this to the
sanitation group" becomes "Planned: pitch to sanitation group" on a project
page, reliability-rated as if it were a decision. The quality gate passes
it; the gate checks structure and secrets, not epistemic status. The
provenance property reads archive.db:voice_notes/482, which satisfies
wiki-audit mechanically: the claim matches the transcript, so audit stays
green. But the transcript itself is noise; the audit verifies mush against
mush. The v2 value proposition (source-backed, auditable) is now laundering
half-formed speech into cited fact. November: Lars quotes his own wiki in an
email to the real Marek and gets corrected. He greps the page history, finds
three more voice-sourced errors, and cannot tell from provenance alone which
claims are trustworthy. The checkpoint flips to reject-by-default; by
December he rejects everything unread. In January 2027 he comments out the
voice leg. archive.db keeps accumulating unprocessed transcripts.

UNDERLYING ASSUMPTION: That a transcript row is a source in the v2 sense,
when it is actually unvetted raw capture, so citation and audit confer trust
the material never earned.

EARLY WARNING SIGNS: (a) checkpoint approval rate above roughly 90 percent
with median review time under 10 seconds per item; (b) zero instances of
anyone opening a voice_notes provenance link in the first month.

### 6. The second plane eats the architecture

THE FAILURE STORY: August 2026: the rebuild hook moved from ingest to
pre-commit because ingest sessions sometimes skipped it. By September,
rebuild_index.py took 40+ seconds on the grown vault, so the maintainer
added --no-verify to his muscle memory during quick fixes. The hook never
errored; it just stopped running. index.db was three weeks stale before
anyone noticed, and the staleness warning fired constantly, got annoying,
and was downgraded to a silent log line in October. The tipping point was
the schema. The maintainer is a data scientist fluent in SQL; in November a
meeting-frequency question was awkward against the page_properties table, so
he added a projects table, then an importer that pulled calendar exports
directly into index.db, bypassing the vault entirely. That was the moment
index.db stopped being derived. Rebuild now destroyed data that existed
nowhere in markdown, so rebuilds got scarier and rarer, which made staleness
worse. By December, wiki-query routed aggregate questions to SQL that
contradicted the pages ("7 meetings with Anna" vs 9 in the hub index), and
the answers stated their plane confidently, so wrong aggregates looked
authoritative. Debugging ate 4-6 hours/month. The text-first guarantee was
gone: some facts lived only in a gitignored binary file.

UNDERLYING ASSUMPTION: That derived-and-disposable is a property a database
keeps by design, rather than a discipline a SQL-fluent solo maintainer must
actively re-earn every time extending the schema is cheaper than editing
markdown.

EARLY WARNING SIGNS: (a) any commit made with --no-verify, or rebuild
wall-time exceeding ~10 seconds; (b) the first table or importer whose data
has no markdown source; measurable as rebuild + diff no longer reproducing
index.db.

### 7. Privacy leak through the promotion seam

THE FAILURE STORY: It tipped in October 2026, three weeks after the pipeline
went daily. Lars recorded a voice memo walking home from a thesis meeting:
"Check in on [[Student M]], she basically admitted she's failing the
semester because of the situation at home, don't push the deadline."
wiki-ingest-voice did its job perfectly: it recognized Student M as an
active relationship, updated her people page with a provenance-stamped
bullet, and linked it from the journal summary. secret_scan ran clean; there
was no key, no IBAN, no phone block. The sentence was just German prose
about a named person. The interactive checkpoint fired at 6:58am as row 7 of
12 in a summary table, truncated to 80 characters, between two harmless
project updates. Lars had confirmed 11 or 12 rows every morning for three
weeks. He pressed y. The second tip was structural: the vault is where blog
and teaching drafts are born, so two months later a draft post about
supervision workflows pulled context from people pages, and a paraphrase of
the "situation at home" line survived into a shared preview link. A
colleague recognized the student. Even after the apology, the damage was
fixed in git history: 60 days of commits, synced to two machines and GitHub;
purging meant history rewrites Lars could not fully verify. The gate was
aimed at the wrong threat: both defenses matched shape, not meaning.
Confidential prose about people looks exactly like the wanted content,
because people pages are the product.

UNDERLYING ASSUMPTION: That dangerous content is pattern-detectable and a
daily human confirm step constitutes review, when the actual hazard is
ordinary sentences approved on habit.

EARLY WARNING SIGNS: (a) checkpoint approval time trends under 30 seconds
for 10+ row batches, with zero rejections in 14 consecutive days; (b) git
log on any people page shows bullets naming health, family, grades, or
conflict that never triggered even an advisory flag.

### 8. Tooling outruns behavior

THE FAILURE STORY: It tipped in the first week of July 2026. The roadmap
said P-3 lands during week 2 and P-4/P-5 around week 5, but nothing enforced
that except restraint, and building cost one prompt. By July 8 all 13 issues
were merged: a fourth namespace, lint rule 15, glossary_import.py,
rebuild_index.py, two-plane query routing, the voice skill. The Phase 0 exit
test never ran because there was no reason to gate anything; the gated thing
already existed. The second tip came the first real morning. The graph was
empty. To write three notes about a paper, the maintainer faced the full
ceremony built for a mature corpus: namespace placement across four
namespaces; source-file:: provenance; the interactive ingest checkpoint; the
secret gate; #glossary-todo tagging with a curation pass owed later; and the
daily review itself. Five habits demanded on day one, each designed assuming
the others were already routine. The repo's own rule ("do not formalize a
verb until it has been done by hand enough to know the ceremony pays off")
had been violated thirteen times in one week. Morning review took 25
minutes, not 5-10, mostly spent operating tooling rather than reading notes.
By day 9 the review was skipped once, then twice. The setup document had
named the stakes: the habit decides whether the system lives. It died at
week two. January 2027: 108 green assertions, 15 lint rules, 11 skills, 14
pages.

UNDERLYING ASSUMPTION: That shipping capacity and adoption pacing are
independent, so free implementation cannot hurt a habit plan.

EARLY WARNING SIGNS: (a) commits-to-tooling versus pages-added ratio: any
week where merged PRs outnumber new graph pages; (b) P-4/P-5 merged before
the Phase 0 exit test has a recorded pass.

### 9. Hand-rolled YAML parser

THE FAILURE STORY: The parser shipped in June 2026 after one afternoon
against a snapshot of glossary.yml. It handled term: and def: lines and
two-space indentation, and the first import produced 640 staging rows. What
Lars did not notice: Glosario's multi-line definitions use both folded
blocks and quoted strings containing colons. The parser treated the colon as
a key separator and silently skipped those entries; roughly 80 terms never
made it into staging, including most German entries, whose def strings carry
umlauts that one byte-level split mangled into mojibake in three rows.
Because the import worked (rows appeared, no errors), the gaps went
undetected for weeks, until a wiki page cited a glossary term that did not
exist. The tipping point came in October 2026, when Glosario's maintainers
reordered keys and added a ref: field. The parser failed loudly mid-file.
Lars spent an evening patching it, then another in November after a quoting
change. The one-command import was now a recurring parsing chore against a
third party's format drift. In December, tired of it, he added import yaml
behind a try/except just for this one script. The zero-dependency rule, held
through 9 validator scripts, was now a rule with one exception, and the next
script's PyYAML question had a precedent instead of an answer.

UNDERLYING ASSUMPTION: That Glosario's YAML is a stable flat subset a
hand-rolled parser can cover, rather than real YAML maintained by someone
else.

EARLY WARNING SIGNS: (a) imported row count below Glosario's published term
count on day one (parsed entries vs grep -c 'term:'); (b) any commit
touching glossary_import.py after ship day.

### 10. archive.db loss (from the adversarial counter-check)

THE FAILURE STORY: Everything else in the repo is protected by git or
rebuildable by design: markdown is committed, index.db is declared derived
and disposable. archive.db inherits gitignored from the never-merge/privacy
rationale and silently inherits the property "not backed up", because git is
the plan's only backup story and no milestone contains a backup, restore, or
export requirement for it. Months of voice notes accumulate on one MacBook.
Then a routine event deletes it: a fresh clone of the graph, a disk failure,
or, most likely given the workflow, a Claude Code agent fixing a messy
working tree with git clean -xfd, which removes ignored files. index.db
regenerates on the next rebuild, which reads as recovery worked, masking
that archive.db did not. The damage is permanent and radiates: every
committed wiki page carrying provenance archive.db:voice_notes/<id> now
dangles forever, so the loss also poisons the audit and provenance layer,
the trust foundation for failure modes 5 and 7.

UNDERLYING ASSUMPTION: "Gitignored plus irreplaceable" was written as a
merge-safety rule, and nobody asked what durability mechanism replaces git
for the one file git refuses to cover.

EARLY WARNING SIGNS: (a) the v3.0 spec ships with no REQ for archive.db
backup/restore and no check that provenance ids resolve; (b) the first
agent-driven cleanup or machine migration where index.db rebuilds cleanly
and the session is declared healthy without verifying archive.db row counts.

## Synthesis

See the report (docs/premortem-report-20260704.html) and the revised plan
section appended to docs/roadmap-glossary-personal-pipeline.md. Summary:

- Most likely failure: #8 (tooling outruns behavior), which also amplifies
  #1, #3, and #5.
- Most dangerous: #7 (privacy leak, harms a third party, git history makes
  it sticky); most irreversible: #10 (archive.db loss).
- Hidden assumption across the plan: because implementation is free,
  shipping the tool is progress. The system's real products are habits and
  decisions; the plan engineers the free part (code) and assumes the
  expensive part (behavior) follows. Corollary: raw capture (transcripts,
  imported termbases) keeps getting treated as if it had the trust status of
  curated sources.
- The revised plan re-gates code on demonstrated behavior, adds mechanical
  tripwires for the silent failures, and removes the two highest-risk
  build-items (hand-rolled YAML parser, batch-confirmed people-page writes)
  by design rather than by mitigation.
