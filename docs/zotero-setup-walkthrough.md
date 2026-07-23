# Zotero setup walkthrough (novice-friendly)

A step-by-step companion to [Zotero setup](zotero-setup.md). That doc states the design and the
settings; this one walks through the installation for someone doing it for the first time,
including the end-to-end verification run that [#28](https://github.com/larnsce/llm-wiki/issues/28)
tracks.

If you are entirely new to Zotero, start with
[Getting started with Zotero](zotero-getting-started.md) instead. It covers the same install
and settings without assuming llm-wiki, plus the account, sync, and browser-connector basics;
Steps 1 to 5 below overlap with it, and Step 6 onward is the llm-wiki-specific part.

## What you are building

At the end of this setup, every paper you save in Zotero can become a page in Logseq named like
`notes/literature/@forte2022building`, pre-filled with the paper's metadata, and your PDF
highlights can be synced onto that page with one command. Four pieces need to cooperate:

- **Zotero** (the desktop app), which stores your papers and PDF annotations.
- **Better BibTeX**, a Zotero plugin whose job here is to give every paper a stable short ID called
  a *citekey* (for example `forte2022building`). The Logseq page names are built from these
  citekeys.
- **Zotero's local API**, a setting that lets other apps on the same computer read your Zotero
  library. Nothing leaves your machine.
- **`scripts/lit_sync.py`**, the sync script in this repository, run through the `/lit-sync`
  command. It reads your library through the local API and creates or updates the pages. No
  Logseq plugin is involved; the plugin that earlier versions of this walkthrough recommended
  did not work in practice and was abandoned (issue
  [#90](https://github.com/larnsce/llm-wiki/issues/90), see the status note in
  [Zotero setup](zotero-setup.md)).

## Step 1: Install Zotero

1. Download the installer for your platform from
   [zotero.org/download](https://www.zotero.org/download/) and install it.
2. If Zotero is already installed, update it first: **Zotero → Check for Updates** on macOS,
   **Help → Check for Updates** on Windows/Linux. The local API used below needs Zotero 7 or
   newer; this guide is written against Zotero 9.

## Step 2: Let other apps talk to Zotero

1. Open the Zotero desktop app.
2. Go to **Zotero → Settings** (on macOS; **Edit → Preferences** on Windows/Linux).
3. Open the **Advanced** tab.
4. Check the box **Allow other applications on this computer to communicate with Zotero**.

This switch is what "local API access" means. Without it, the sync script cannot see your
library at all. It only allows apps on your own computer; it does not expose anything to the
internet.

## Step 3: Install Better BibTeX

Better BibTeX is not in a built-in plugin store; you install it from a downloaded file.

1. In your browser, go to the
   [Better BibTeX releases page](https://github.com/retorquere/zotero-better-bibtex/releases) and
   download the latest `.xpi` file. (If the browser asks whether to open or save it, save it.
   Firefox may try to install it as a browser extension; right-click the link and choose "Save
   Link As" instead.)
2. In Zotero, go to **Tools → Plugins** (older versions call it Add-ons).
3. Click the gear icon, choose **Install Plugin From File**, and select the `.xpi` you downloaded.
4. Restart Zotero when prompted.

## Step 4: Configure the citation keys

Go back to **Zotero → Settings**, open the **Better BibTeX** tab, and work through the
**Citation keys** section:

1. Set the citation key formula to:

   ```
   auth.lower + year + veryshorttitle(1, 0).lower
   ```

   The formula builds lowercase keys from the first author, the year, and the first meaningful
   word of the title. For example, Tiago Forte's 2022 book "Building a Second Brain" gets the
   key `forte2022building`.

2. Set **Automatically fill citation key after** to `2` seconds. Filling writes the generated
   key into Zotero's native citation-key field, which syncs across your devices. The sync
   script reads exactly this field, and it skips any item whose key is not filled yet.
3. Keep **Force citation key to plain text** checked.
4. Keep **Regenerate citation key when item changes** unchecked. Your Logseq page names are
   built from citekeys, so a key must never change once its page exists. With the box
   unchecked, a filled key stays put even when you later fix a typo in the item's metadata.
5. The defaults under **Keeping citation keys unique** are fine: comparison ignores
   upper/lowercase, and keys are kept unique within each library.

A note on "pinning", in case you read older guides: earlier Better BibTeX versions called a
stored key "pinned", and the setting in point 2 was named *Automatically pin citation key
after*. The mechanism is the same, only the wording changed.

For papers already in your library that you want recomputed with the formula above, do it
**before** creating their pages: select them, right-click, and choose
**Better BibTeX → Regenerate citation key**.

## Step 5: Set up Quick Copy

Quick Copy is how you get a citekey out of Zotero while you write, so you can link
`[[notes/literature/@<citekey>]]` from any other page. Go to **Zotero → Settings**, open the
**Export** tab, and under **Quick Copy**:

1. Set **Item Format** to **Better BibTeX Citation Key Quick Copy**.
2. Set **Note Format** to **Markdown + Rich Text**, and check **Include Zotero Links** on the
   Markdown line (leave the Rich Text/HTML line unchecked). A Zotero note copied out as
   markdown then keeps a link back to the item it came from.

With that in place, selecting an item and pressing **Cmd+Shift+C** (**Ctrl+Shift+C** on
Windows/Linux) copies its citekey, and dragging an item into a text field pastes it.

## Step 6: Run the sync

Zotero must be running, now and any time you sync later. Run `/lit-sync` in Claude Code. It
resolves your graph location from `llm-wiki.yml`, shows a dry-run for review, then does the real
run and the commit. To run the script by hand instead:

```
python3 scripts/lit_sync.py --vault <logseq-graph-root> --dry-run   # review first
python3 scripts/lit_sync.py --vault <logseq-graph-root>            # then for real
```

Every item with a filled citekey gets a page named `notes/literature/@<citekey>`, created from
this template:

```markdown
type:: literature
citekey:: forte2022building
authors:: Tiago Forte
year:: 2022
item-type:: book
doi::
zotero:: zotero://select/library/items/<KEY>
source-file::
zotero-last-sync:: <library version>

- ## literature
	-
- ## annotations
	- (synced from Zotero below this line)
```

What each part is for:

- The `key:: value` lines at the top are Logseq page properties; they hold just enough metadata
  to identify the paper. The full record stays in Zotero, and the archived full text lives in
  `ingested/`, so copying every metadata field here would only add noise. On later runs the
  script rewrites only these managed properties; `source-file::` and anything you add yourself
  survive.
- `source-file::` starts empty. It gets filled when the paper goes through the wiki pipeline:
  after `/wiki-ingest` archives the paper to `ingested/papers/<file>.md`, it offers at its
  checkpoint to set the property to that path, and you confirm the write (REQ-974). That shared
  path is what makes your reading auditable against the same source the wiki cites ("one
  archived source, two readings", REQ-973).
- `## literature` is where your own words go - your literature note in the Zettelkasten sense.
  Nothing automated ever touches it. Add the `#literature` tag by hand when you write the note;
  the tooling never writes tags.
- `## annotations` is where the script appends your synced PDF highlights, sorted by their
  position in the PDF. The sync is incremental (tracked through the `zotero-last-sync::`
  property), so re-syncing adds only new highlights and never clobbers what is already on the
  page.

Items whose citekey is not filled yet are skipped with a warning and picked up on a later run;
nothing is guessed. If the script cannot reach Zotero, fix the Zotero side (is Zotero running,
is the Step 2 box checked); do not work around it with the Zotero cloud API.

The page name also fits the vault's rules: `notes/` is the human-owned namespace, and lint
recognizes the `@citekey` leaf ([`namespaces.md`](../openspec/specs/namespaces.md) REQ-976), so
these pages will not show up as naming violations.

## Step 7: Run the loop once, end to end

This is the verification [#28](https://github.com/larnsce/llm-wiki/issues/28) asks for. Pick one
real paper and walk it through:

1. In Zotero, open the paper's PDF and add at least one highlight.
2. Run `/lit-sync`; confirm the dry-run lists the item, then let the real run create the page.
3. In Logseq, confirm the page appears as `notes/literature/@<citekey>` with the properties
   filled in and your highlight under `## annotations`.
4. Write a sentence or two under `## literature`.
5. Export or flatten the paper to markdown into `raw/`, run `/wiki-ingest`, and confirm at the
   checkpoint when it offers to set `source-file::` on the literature note to the
   `ingested/papers/...` path it produced.

If all five steps work, the setup is done. Close #28 and stamp [Zotero setup](zotero-setup.md)
with the Zotero and Better BibTeX versions the run used.

## Related

- [Getting started with Zotero](zotero-getting-started.md) - the standalone Zotero guide for
  first-time users (install, sync, connector, GHE-harmonized citation keys)
- [Zotero setup](zotero-setup.md) - the design rationale, page-name contract, and status;
  includes the **iPad / iOS** section if you also read and annotate on a tablet
- [Literature Research](literature-research.md) - the full discovery→Zotero→ingest funnel
- [PARA + Zettelkasten workflow](para-notes-workflow.md) - the `notes/` layer this feeds
