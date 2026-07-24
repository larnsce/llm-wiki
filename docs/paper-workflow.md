# Writing a paper on the wiki

How the wiki supports writing a scientific article, from the first
source to the public supplementary site. The tooling behind each step
is the wiki-paper skill, the agent-use log, and the export bundle
(issues #146, #147, #148); the exact rules live in
`openspec/specs/paper.md`. You do not need to know the rules to use
the workflow, and every command below is a sentence you say in a
Claude Code session inside your vault.

## The problem the workflow solves

While you write an article, the material behind it piles up in the
wiki. The literature notes arrive through Zotero, the concept pages
grow during ingest sessions, a dataset gets its own page, and the
decisions you take while drafting end up in journal entries. The wiki
holds all of it, but spread out, with no view that belongs to the
paper. Two outside pressures meet that pile. Journals increasingly ask
authors to state how AI was used in preparing a manuscript, and
reviewers or readers may want to inspect the knowledge base behind a
paper. Without a per-paper view, you would answer both questions from
memory.

## The anchor page

Each manuscript gets one anchor page in the wiki, at
`wiki/papers/<slug>` (the spec calls it the paper hub). The anchor
page has six sections:

- Manuscript (working title and status)
- Literature drawn on
- Data
- Open questions
- Draft decisions (dated, and never deleted; a changed decision is
  marked as superseded so the history stays readable)
- AI use

Everything in the anchor page is a link to pages you already have.
Nothing moves and nothing is copied. A literature note stays at
`notes/literature/@<citekey>`, a dataset page stays under `wiki/data/`,
and the anchor page points at them. The health check warns when a page
in the paper's own folder is not linked from the anchor, because an
unlinked page would silently miss the public export later.

## The log and the disclosure statement

Alongside the anchor page lives a log page, created together with it.
Whenever a skill touches the paper's material, one row lands in the
log with the date, the skill, the model you confirmed, what was read,
what was written, and what you approved. The rows are never edited or
deleted. When you submit the paper, the disclosure statement that
journals ask for is generated from the rows, so you never reconstruct
your AI use from memory. The model column deserves one note. The
executing model cannot report its own name honestly, so the column
records what you confirmed at the checkpoint, and "session" when
nothing was stated.

## Making the material public

When you want the material public, say so and the export runs. The
export starts at the anchor page and follows its links. Only pages the
walk can reach are included, so the anchor page is also the table of
contents of the public artifact. Before a single file is written,
every included page is scanned for secrets, and one blocking finding
stops the whole export with nothing on disk. The result is a folder
that is a complete small website with no build step. A reviewer reads
the rendered pages in a browser, and an AI tool fetches the identical
raw markdown at the same addresses. Publishing is pushing the folder
to a public GitHub repository and turning on Pages.

The folder also contains a manifest. The manifest lists every included
page with its source, every linked page that was kept out and the
reason, and every link that pointed at a page that does not exist.
Nothing leaves your vault silently, and nothing is dropped silently
either.

## What never leaves the vault

The export refuses your personal tiers. Pages under `para/`, journal
pages, glossary pages, and notes outside `notes/literature/` are never
included, even when the anchor page links them. Source files under
`ingested/` never ship either, because they may be copyrighted PDFs or
sensitive captures; the citations on the exported pages remain as
written provenance. When a page deliberately keeps something private,
say so in the page itself, e.g., "the household microdata stays
private, consent covers aggregates only". A stated exclusion reads as
provenance. A bare gap reads as an oversight.

## How you use it

You talk to a Claude Code session in your vault, and you confirm
diffs. The session runs the scripts.

1. "Start a paper hub for <manuscript>". The skill shows you the
   anchor page and the log page before writing, and you say yes.
2. "Attach @<citekey> and the survey dataset to it". Links are
   appended to the right sections, again shown first.
3. Keep working normally. Ingest sources, query while drafting,
   correct claims. The log fills itself as a side effect.
4. "Export it and start a preview". The session runs the export,
   relays the manifest, and hands you a local address to click
   through.
5. Read the included pages once with the privacy question in mind.
   Ratings and open review sections publish as they stand, and that is
   the point, but claims about people deserve a deliberate look before
   they leave the vault.
6. "Publish it". The session creates the public repository and turns
   on Pages.

Step 5 is the only step that is genuinely yours. Everything else is
one sentence and a confirmation.

## A worked example

The repo ships a complete fictional example at `examples/paper-site/`,
a made-up sanitation paper with an anchor page, a filled agent log
with a generated disclosure statement, literature notes, concept
pages, and a data page. Serve it locally to see what a published
paper site looks and feels like:

```
cd examples/paper-site
python3 -m http.server 8123
# open http://localhost:8123/
```

## Where the details live

- `openspec/specs/paper.md` holds the normative rules (REQ-1500..1526)
- `docs/publish-wiki.md` covers the viewer, the publish boundary, and
  the gate for publishing wiki content in general
- the wiki-paper skill page and its plain-language twin describe the
  skill itself
