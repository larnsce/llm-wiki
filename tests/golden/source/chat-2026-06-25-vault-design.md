# Vault architecture - curated claude.ai export, 2026-06-25

Curated at export time per the transcript route (ingest REQ-1305): decisions,
the questions that drove them, and enough surrounding text to stay honest.
Tool noise and dead ends dropped. FAKE conversation written for this test
suite; every claim in it is fictional.

---

**Lars:** I keep going back and forth on whether the teaching materials
should live in the same Logseq graph as the wiki. Give me the strongest case
for each side.

**Claude:** The case for one graph is friction: one search box, one journal,
links across the boundary. The case for splitting is that the two collections
differ on the axes that actually hurt later: sharing boundary (the wiki is
private; course material is handed to students every semester) and lifecycle
(course repos get archived each semester; the wiki never does). There is also
a performance angle: Logseq's Datalog queries degrade noticeably once a graph
grows past roughly 20,000 pages, so merging collections buys you the ceiling
of both.

**Lars:** The sharing-boundary point settles it. Decision: one graph per
sharing boundary. The wiki stays private and personal; teaching materials get
their own graph because they are shared with students and archived every
semester. The lifecycle difference alone would justify it.

**Claude:** Noted. Related question while you are here: your cross-cutting
concepts (reproducibility, data ethics) currently sit as ever-deeper
namespace pages. Namespaces encode ownership and routing; concepts that cut
across hubs fight that structure.

**Lars:** Agreed, second decision: cross-cutting concepts get tags, not
deeper namespaces. We cap namespace depth at three anyway; a concept that
wants to live in two hubs is a tag by definition.

**Lars:** Side note - Jana said her graph got slow after she imported ten
years of notes. I should ask her what size it actually reached before I
believe the 20,000-page figure.

**Lars:** The setup.sh flag bug we hit this morning is already fixed - the
repo has the issue and the commit, so nothing to record here.

**Claude:** Decision log for this session, as requested:

1. One graph per sharing boundary: the wiki stays private; teaching
   materials get their own graph (shared with students, archived every
   semester).
2. Cross-cutting concepts are tags, not namespaces; namespace depth stays
   capped at three.

Open follow-up: ask Jana for her graph's actual page count before treating
the 20,000-page degradation figure as real.
