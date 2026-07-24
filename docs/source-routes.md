# Source routes: how each kind of source gets into the wiki

One page answering "I have a thing I want in the wiki; which route does it
take?" This is the durable decision record from the 2026-07-07 source
inventory triage (issue #107, premortem-revised): every known source kind,
its capture mechanism, where it enters the pipeline, and the trust
defaults that apply. Routes that deliberately do not exist are
listed at the end so the backlog stops resurfacing.

(The former model-tier column was removed with the model-tiering
machinery, issue #108; sessions run one model, escalated manually with
`/model` for judgment-heavy work.)

## The route table

| Source | Capture mechanism | Pipeline entry | Source type | Reliability default |
|---|---|---|---|---|
| Papers, preprints | Zotero, then `/lit-sync` (see `docs/literature-research.md` and `docs/zotero-setup.md`); or drop the PDF/markdown into `raw/` | `raw/<file>` | `papers` | rubric: `high` peer-reviewed, `medium` preprint (schema REQ-586) |
| Web clippings | MarkDownload in Firefox (`docs/web-clipper-firefox.md`); funnel via symlink or the launchd sweep (`scripts/wiki-sweep.sh`) | `raw/<file>` | `clippings` | rubric: `medium` expert post, `low` anecdotal |
| News, blog articles | same clipping funnel | `raw/<file>` | `articles` | rubric: `medium` or `low` |
| R data packages | `data_packages:` in `llm-wiki.yml`, then `/data-sync` (`docs/data-package-workflow.md`) | none: managed dataset pages plus `ingested/data/` snapshots | `data` | managed by `data_pkg_sync.R` (dataset provenance, schema REQ-585d) |
| Own voice memos | voice pipeline into archive.db (`docs/voice-pipeline.md`), then `/wiki-ingest-voice` | `archive.db:voice_notes/<id>` | capture, not a source | `low`, capture-backed (schema REQ-586b) |
| Voice memos, revisited in conversation | `/wiki-chat-voice` (issue #117): browse archive.db read-only, converse in-session, one closing ingest | `archive.db:voice_notes/<id>`; the conversation is never a cite target (ingest REQ-1204) | capture, not a source | `low`, capture-backed; discussion adds no evidence |
| Promoted personal notes | copy the note to `raw/note-<name>.md` (promotion seam, `docs/para-notes-workflow.md`) | `raw/note-*.md` | `notes` | `medium`, personal synthesis (schema REQ-586) |
| Own published outputs (blog, papers, talks) | none: stub, do not ingest | none | none | n/a |
| Book and e-reader highlights (Kindle, KOReader, Readwise) | import the export into Zotero, then the normal paper route | via Zotero | `papers` | per rubric |
| Audio and video actually listened to (podcasts, YouTube, lectures) | obtain or make a transcript, treat it as an article with `canonical-url::` | `raw/<file>` | `articles` | per rubric |
| Newsletters and RSS actually read | clip the read item like any web page | `raw/<file>` | `clippings` | per rubric |
| AI conversation transcripts | curate at export (best: end the session by asking for a decision log), name it `chat-YYYY-MM-DD-<slug>.md`, drop into `raw/` (ingest REQ-1300..1305) | `raw/chat-*.md` | `transcripts` (sensitive by default, REQ-1301: bytes never enter git) | `low`, capture-backed (schema REQ-586b); the user's own decisions `medium` once confirmed per decision (REQ-1302) |
| Teaching feedback | manual capture as `raw/note-*.md`; anything with student names needs `sensitive_source_types` handling first | `raw/note-*.md` | `notes` | `medium` |
| Handwritten and physical notes | photo, OCR by hand, then `raw/note-*.md` | `raw/note-*.md` | `notes` | `medium` |

## Route notes

### Own published outputs and code repositories: stub, do not ingest

A copy of your own blog post, paper, package README, or teaching repo goes
stale the moment the original changes, and lint then flags it as an L1/L2
duplicate. The standing answer (see `docs/literature-research.md`, section
"Your own published material") is a thin `reference` page with
`canonical-url::` (schema REQ-584) pointing at the living original. Stub the
back catalog by hand when a page earns a link; there is no bulk tooling on
purpose. Package data is different: that has the data-package route above.

### Book and e-reader highlights: Zotero is the system of record

Per-passage highlights live in Zotero, not in wiki pages (annotation table in
`docs/literature-research.md`). Kindle, KOReader, and Readwise exports enter
Zotero through its import paths; from there `/lit-sync` carries annotations
to `notes/literature/@<citekey>` like any paper. No separate wiki route.

### Audio, video, newsletters: the funnel rule

Only material you actually listened to or read crosses the line into `raw/`.
A transcript of a podcast episode you heard is just a text source; route it
as `articles` with `canonical-url::`. Automated subscription ingestion
(pulling a feed or inbox into the wiki unread) is rejected: it violates the
funnel rule and buries the queue.

### Read-it-later and bookmark backlogs

Batch-export what you have read into `raw/` as `clippings` and drain with
`/wiki-ingest --auto` (the checkpoint table still lands in the report).
Drain a LARGE backlog in small batches you can actually review.

### Teaching feedback and handwritten notes: deliberately informal

Both work today with zero new tooling (manual capture into `raw/note-*.md`).
They stay informal until doing them by hand a few times shows the ceremony
pays off; the repo rule is not to formalize a verb prematurely. For teaching
feedback, put the source type into `sensitive_source_types` before the first
ingest that contains student names, so the bytes stay out of git history
(ingest REQ-046).

### Messaging threads and calendar: no route

Blocked on the unresolved people/meetings/email design question. The staging
ground is the archive layer (`docs/archive-layer.md`); nothing enters the
wiki from there until that question is decided. Adding a route here without
that decision would hard-code an answer to the harder question by accident.

Update 2026-07-16 (issues #123/#124/#125): the staging half is now decided
and running -- email is captured daily into archive.db by a deterministic
IMAP job (`docs/mail-pipeline.md`, capture only), and the sent-mail
overview is a review-time SQL query with zero journal writes (#125,
Option B). The wiki half stays blocked exactly as above: nothing enters
pages or the journal from mail. Interactive triage uses the official
Infomaniak Mail MCP server (#124) and promotes only by hand through the
normal `raw/note-*.md` seam.

## AI conversation transcripts: the spec'd route

Status: SPEC'D machinery (ingest REQ-1300..1305, issue #107 Part 2). The
Phase-0 evaluation (2026-07-08) descoped this to a manual protocol behind a
five-hand-ingest gate; the maintainer waived the gate on 2026-07-16 after
the route proved itself in use, and the machinery shipped: `transcripts`
source type (sensitive by default, REQ-1301), `chat-` filename inference
(REQ-1300), the per-decision checkpoint variant (REQ-1302/1303), and the
golden (`tests/golden/ingest-transcript.golden.md`).

What the Phase-0 hand ingests established (now encoded in the REQs):

- Claude Code sessions on a repository are usually NOT worth ingesting: the
  repo itself absorbs the decisions (issues, CHANGELOG, commit messages). A
  raw export of one working day measured 4,637 lines and 254 tool calls and
  yielded zero net-new wiki content after trimming (REQ-1304).
- The value concentrates in conversations with no repository behind them
  (claude.ai chats, cross-project design discussions), and in the trim: a
  hand-curated export was ingestable as-is; the raw dump was not. Curate at
  export time (or end the session by asking the model for a decision log)
  rather than trimming dumps afterwards (REQ-1305).

Using the route, per transcript:

1. Export and curate. Keep the decisions ("we chose X because Y"), the
   questions that drove them, and enough surrounding text to stay honest;
   drop tool noise and dead ends. Aim for something a stranger could read.
2. Name it `chat-YYYY-MM-DD-<topic-slug>.md` and drop it into `raw/`; the
   `chat-` prefix infers type `transcripts` (REQ-1300).
3. Run `/wiki-ingest`. Transcripts are interactive-only: `--auto` states
   that and runs the checkpoint anyway (REQ-1303). The default outcome is a
   short journal decision-log entry; wiki writes are offered per extracted
   decision, individually (never on a batch yes).
4. Trust calls are made for you but overridable: model-asserted analysis
   rates `low` with a `## Pending Review` entry (a transcript is capture,
   schema REQ-586b, and can never corroborate itself); your own decisions
   rate `medium` once you confirm them at the checkpoint, the same standing
   as promoted personal notes (REQ-1302).
5. Expect skips: repo decisions live in the repo; ecosystem trivia goes
   stale; install mechanics are in the docs. A checkpoint proposing no wiki
   writes is the route working, not failing (REQ-1304).

Durability note, applies to EVERY sensitive source type: gitignored
`ingested/<type>/` bytes sit outside git-as-backup, so an off-machine copy
of those subtrees must exist before the first sensitive ingest (REQ-1301,
mirroring the archive.db rule, storage REQ-1120). If the bytes are lost,
`/wiki-audit` reports the affected claims as `source-missing` - broken
provenance, deliberately distinct from `reliability:: low` (audit REQ-927).

## What deliberately has no route

- Automated subscription or feed ingestion (violates the funnel rule).
- Bulk import of unread backlogs (same rule; drain read material in
  reviewable batches).
- Messaging and calendar data (blocked on the people/meetings/email
  question, see above; the daily archive.db mail capture of
  `docs/mail-pipeline.md` is staging, not a route).
- Automated AI-transcript capture into archive.db (the file route,
  ingest REQ-1300, is deliberately manual and selective; revisit only if
  its volume demands bulk capture).
