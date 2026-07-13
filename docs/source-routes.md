# Source routes: how each kind of source gets into the wiki

One page answering "I have a thing I want in the wiki; which route does it
take?" This is the durable decision record from the 2026-07-07 source
inventory triage (issue #107, premortem-revised): every known source kind,
its capture mechanism, where it enters the pipeline, and the trust and
model-tier defaults that apply. Routes that deliberately do not exist are
listed at the end so the backlog stops resurfacing.

The model-tier column follows the tier map in issue #108. Until that ships,
read it as guidance for which sessions to batch the work into, not as
installed tooling.

## The route table

| Source | Capture mechanism | Pipeline entry | Source type | Reliability default | Model tier |
|---|---|---|---|---|---|
| Papers, preprints | Zotero, then `/lit-sync` (see `docs/literature-research.md` and `docs/zotero-setup.md`); or drop the PDF/markdown into `raw/` | `raw/<file>` | `papers` | rubric: `high` peer-reviewed, `medium` preprint (schema REQ-586) | sonnet; opus for dense or high-stakes synthesis |
| Web clippings | MarkDownload in Firefox (`docs/web-clipper-firefox.md`); a symlinked funnel folder into `raw/` works well | `raw/<file>` | `clippings` | rubric: `medium` expert post, `low` anecdotal | sonnet |
| News, blog articles | same clipping funnel | `raw/<file>` | `articles` | rubric: `medium` or `low` | sonnet |
| R data packages | `data_packages:` in `llm-wiki.yml`, then `/data-sync` (`docs/data-package-workflow.md`) | none: managed dataset pages plus `ingested/data/` snapshots | `data` | managed by `data_pkg_sync.R` (dataset provenance, schema REQ-585d) | haiku for sync runs; sonnet when annotating |
| Own voice memos | voice pipeline into archive.db (`docs/voice-pipeline.md`), then `/wiki-ingest-voice` | `archive.db:voice_notes/<id>` | capture, not a source | `low`, capture-backed (schema REQ-586b) | sonnet |
| Voice memos, revisited in conversation | `/wiki-chat-voice` (issue #117): browse archive.db read-only, converse in-session, one closing ingest | `archive.db:voice_notes/<id>`; the conversation is never a cite target (ingest REQ-1204) | capture, not a source | `low`, capture-backed; discussion adds no evidence | session model for the conversation; haiku for picker digests |
| Promoted personal notes | copy the note to `raw/note-<name>.md` (promotion seam, `docs/para-notes-workflow.md`) | `raw/note-*.md` | `notes` | `medium`, personal synthesis (schema REQ-586) | sonnet |
| Own published outputs (blog, papers, talks) | none: stub, do not ingest | none | none | n/a | haiku (stubbing is mechanical) |
| Book and e-reader highlights (Kindle, KOReader, Readwise) | import the export into Zotero, then the normal paper route | via Zotero | `papers` | per rubric | sonnet |
| Audio and video actually listened to (podcasts, YouTube, lectures) | obtain or make a transcript, treat it as an article with `canonical-url::` | `raw/<file>` | `articles` | per rubric | sonnet |
| Newsletters and RSS actually read | clip the read item like any web page | `raw/<file>` | `clippings` | per rubric | sonnet |
| AI conversation transcripts | manual protocol below; gated until five hand ingests | `raw/chat-*.md` | `notes` (classified by hand at the checkpoint) | `low`; the user's own decisions `medium` once confirmed at the checkpoint | opus/fable class while the protocol is manual |
| Teaching feedback | manual capture as `raw/note-*.md`; anything with student names needs `sensitive_source_types` handling first | `raw/note-*.md` | `notes` | `medium` | sonnet |
| Handwritten and physical notes | photo, OCR by hand, then `raw/note-*.md` | `raw/note-*.md` | `notes` | `medium` | haiku intake, sonnet synthesis |

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
`/wiki-ingest --auto` (the checkpoint table still lands in the report). Bulk
triage of a LARGE backlog waits for the queue-triage agent planned in issue
#108; until then, drain in small batches you can actually review.

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

## AI conversation transcripts: the manual protocol

Status: MANUAL protocol, not spec'd machinery. The Phase-0 evaluation
(issue #107, 2026-07-08) found that spec work before real usage would repeat
the voice pipeline's early mistake, so the machinery (a `transcripts` source
type, `chat-` filename inference, checkpoint variant, golden) is gated: if
fewer than five transcripts have been hand-ingested by 2026-07-22, the spec
REQ block does not get written and this stays a manual protocol.

What the Phase-0 hand ingests established:

- Claude Code sessions on a repository are usually NOT worth ingesting: the
  repo itself absorbs the decisions (issues, CHANGELOG, commit messages). A
  raw export of one working day measured 4,637 lines and 254 tool calls and
  yielded zero net-new wiki content after trimming.
- The value concentrates in conversations with no repository behind them
  (claude.ai chats, cross-project design discussions), and in the trim: a
  hand-curated export was ingestable as-is; the raw dump was not. Curate at
  export time (or end the session by asking the model for a decision log)
  rather than trimming dumps afterwards.

The protocol, per transcript:

1. Export and curate. Keep the decisions ("we chose X because Y"), the
   questions that drove them, and enough surrounding text to stay honest;
   drop tool noise and dead ends. Aim for something a stranger could read.
2. Name it `chat-YYYY-MM-DD-<topic-slug>.md` and drop it into `raw/`. The
   `chat-` prefix is not machinery yet (type inference will fall back to
   your `default_source_type` or ask); it keeps transcripts recognizable in
   the queue and is the prefix the future inference rule would use.
3. Run `/wiki-ingest` and classify as `notes` at the checkpoint when asked.
4. Trust calls at the checkpoint: a transcript is capture, not a vetted
   source. Model-asserted analysis rates `low` with a `## Pending Review`
   entry (corroborate later from real sources); your own decisions recorded
   in the chat rate `medium` once you confirm them at the checkpoint, the
   same standing as promoted personal notes. A transcript can never
   corroborate itself (schema REQ-586b applies in spirit).
5. Skip what another system already records: repo decisions live in the
   repo; ecosystem trivia goes stale; install mechanics are in the docs.
   If the checkpoint proposes nothing durable, the correct outcome is no
   wiki writes.

## What deliberately has no route

- Automated subscription or feed ingestion (violates the funnel rule).
- Bulk import of unread backlogs (same rule; drain read material in
  reviewable batches).
- Messaging and calendar data (blocked on the people/meetings/email
  question, see above).
- Automated AI-transcript capture into archive.db (revisit only if the
  manual protocol survives its gate and volume demands it).
