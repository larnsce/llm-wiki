# Zotero setup walkthrough (novice-friendly)

A step-by-step companion to [Zotero setup](zotero-setup.md). That doc states the design and the
settings; this one walks through the installation for someone doing it for the first time,
including the end-to-end verification run that [#28](https://github.com/larnsce/llm-wiki/issues/28)
tracks.

## What you are building

At the end of this setup, every paper you save in Zotero can become a page in Logseq named like
`notes/literature/@Forte2022`, pre-filled with the paper's metadata, and your PDF highlights can be
synced onto that page with one click. Four pieces need to cooperate:

- **Zotero** (the desktop app), which stores your papers and PDF annotations.
- **Better BibTeX**, a Zotero plugin whose job here is to give every paper a stable short ID called
  a *citekey* (for example `Forte2022`). The Logseq page names are built from these citekeys.
- **Zotero's local API**, a setting that lets other apps on the same computer read your Zotero
  library. Nothing leaves your machine.
- **logseq-zoterolocal-plugin**, a Logseq plugin that reads your library through that local API and
  creates or updates the pages.

## Step 1: Let other apps talk to Zotero (TODO: Add a another step to actually download the latest version of Zotero)

1. Open the Zotero desktop app.
2. Go to **Zotero → Settings** (on macOS; **Edit → Preferences** on Windows/Linux).
3. Open the **Advanced** tab.
4. Check the box **Allow other applications on this computer to communicate with Zotero**.

This switch is what "local API access" means. Without it, the Logseq plugin cannot see your
library at all. It only allows apps on your own computer; it does not expose anything to the
internet.

## Step 2: Install Better BibTeX and set the citation key formula

Better BibTeX is not in a built-in plugin store; you install it from a downloaded file.

1. In your browser, go to the
   [Better BibTeX releases page](https://github.com/retorquere/zotero-better-bibtex/releases) and
   download the latest `.xpi` file. (If the browser asks whether to open or save it, save it.
   Firefox may try to install it as a browser extension; right-click the link and choose "Save
   Link As" instead.)
2. In Zotero, go to **Tools → Plugins** (older versions call it Add-ons).
3. Click the gear icon, choose **Install Plugin From File**, and select the `.xpi` you downloaded.
4. Restart Zotero when prompted.

Now configure the one setting that matters here:

1. Go back to **Zotero → Settings** and open the **Better BibTeX** tab.
2. Under **Citation keys**, set the citation key formula to:

   ```
   auth.lower + year + veryshorttitle(1, 0).lower
   ```

A note on "pinning", in case you read older guides: Better BibTeX used to compute citekeys on
the fly (so they could silently change, for example if you fixed a typo in an author name), and
you had to "pin" a key to freeze it - older versions of this walkthrough said to set
*Automatically pin citation key after* to 1 second. That setting is gone: since Better BibTeX 8
(Zotero 8/9), every key is written into Zotero's native citation-key field as soon as it is
generated, and that field syncs across your devices. You never have to think about pinning.

Since your Logseq page names are built from citekeys, a key must never change once its page
exists. For papers already in your library that you want recomputed with the formula above, do
it **before** creating their pages: select them, right-click, and choose
**Better BibTeX → Regenerate citation key**.

TODO: I have old instructions here: https://ds4owd-002.github.io/website/content/guide/#zotero-reference-management find guidance on all steps and add them
TODO: This guide is more up to date, but still doesn't get there fully: https://unlimited.ethz.ch/spaces/ghestudents/pages/182077770/Reference+management the export quick copy step is still there.

## Step 3: Install the Logseq plugin

1. In Logseq, first make sure plugins are enabled: **Settings → Advanced → Plug-in system** must
   be on (restart Logseq if you just turned it on). TODO: hard to find. point out it's at the three dot menu in the top-right. Also: don't have that option under advanced. plug-ins are already there
2. Click the three-dot menu (top right) → **Plugins** → **Marketplace** tab.
3. Search for **zoterolocal** and install **logseq-zoterolocal-plugin** (author: benjypng).
4. Open the plugin's settings (gear icon on its card in the Plugins list) and confirm the
   **connection to Zotero** check passes. Zotero must be running for this to work; it must also be
   running any time you import or sync later.

One caution (see the status note in [Zotero setup](zotero-setup.md)): community plugins change
over time. Note down which plugin version you installed, and avoid blind updates; if the
marketplace offers an update, check its changelog before accepting. Your provenance chain depends
on the plugin producing the same properties it produces today.

## Step 4: Set the page-name template

In the plugin's settings, find the page-name template field and set it to exactly:

```
notes/literature/@<% citeKey %>
```

Reading this template left to right: every imported item becomes a page inside the
`notes/literature/` namespace, and the page's own name is `@` followed by the citekey. So the
paper with citekey `Forte2022` becomes the page `notes/literature/@Forte2022`.

This matters for the vault's rules: `notes/` is the human-owned namespace that the wiki toolchain
never writes to, and the `@citekey` leaf is explicitly recognized by lint as a proper noun
([`namespaces.md`](../openspec/specs/namespaces.md) REQ-976), so these pages will not show up as
naming violations.

## Step 5: Set the page template

The plugin also has a template for the page *content* (what gets pre-filled when an item is
imported). Run its **Insert Zotero template** command once to see the default, then replace the
generated block with this trimmed version:

```markdown
type:: literature
citekey:: <% citeKey %>
authors:: <% creators %>
year:: <% date %>
item-type:: <% itemType %>
doi:: <% DOI %>
zotero:: <% libraryLink %>
source-file::

- ## my reading
	-
- ## annotations
	- (synced from Zotero below this line)
```

What each part is for:

- The `key:: value` lines at the top are Logseq page properties; they hold just enough metadata to
  identify the paper. The full record stays in Zotero, and the archived full text lives in
  `ingested/`, so copying every metadata field here would only add noise.
- `source-file::` is deliberately left empty at import time. You fill it in later, only when the
  paper actually goes through the wiki pipeline: after `/wiki-ingest` archives the paper to
  `ingested/papers/<file>.md`, you paste that path here by hand. That shared path is what makes
  your reading auditable against the same source the wiki cites ("one archived source, two
  readings", REQ-973). The tool never writes this for you.
- `## my reading` is where your own words go. Nothing automated ever touches it.
- `## annotations` is where the plugin appends your synced PDF highlights. The sync is incremental
  (tracked via a `zotero-last-sync` property), so re-syncing adds only new highlights and never
  clobbers what is already on the page.

## Step 6: Run the loop once, end to end

This is the verification [#28](https://github.com/larnsce/llm-wiki/issues/28) asks for. Pick one
real paper and walk it through:

1. In Zotero, open the paper's PDF and add at least one highlight.
2. In Logseq, import the item via the plugin and confirm the page appears as
   `notes/literature/@<citekey>` with the properties filled in.
3. Right-click the page title → **Zotero: Sync annotations** (or use the command palette →
   *Sync all annotations*) and confirm your highlight appears under `## annotations`.
4. Write a sentence or two under `## my reading`.
5. Export or flatten the paper to markdown into `raw/`, run `/wiki-ingest`, and when the ingest
   report shows the `ingested/papers/...` path, paste it into `source-file::` on the literature
   note.

If all five steps work, the setup is done and #28 can be closed with a note recording the plugin
version you pinned.

## Related

- [Zotero setup](zotero-setup.md) - the design rationale, page-name contract, and status;
  includes the **iPad / iOS** section if you also read and annotate on a tablet
- [Literature Research](literature-research.md) - the full discovery→Zotero→ingest funnel
- [PARA + Zettelkasten workflow](para-notes-workflow.md) - the `notes/` layer this feeds
