# Getting started with Zotero

This guide walks you through installing and configuring Zotero, the free and open-source reference manager. At the end you will have a working library that you can save papers into from your browser, read and highlight PDFs in, and pull stable citation keys out of. The guide assumes no prior experience with Zotero.

It is also the baseline setup we use at Global Health Engineering (GHE). The citation-key settings in Step 7 are the group convention; configure them exactly as written so your keys match everyone else's. The guide is self-contained: it does not depend on any other tooling, and you can stop after the final checklist with a complete, working reference manager.

Written against Zotero 9 and the current Better BibTeX release (July 2026). Menu names may differ slightly in other versions.

## What you are setting up

You will install and configure five pieces:

- **Zotero**, the desktop app. It stores your references, the PDFs attached to them, and your reading highlights.
- **A zotero.org account with sync**, so your library is backed up and available on other devices.
- **The Zotero Connector**, a browser extension that saves papers into your library with one click.
- **Better BibTeX**, a Zotero plugin that gives every item a stable short ID called a citation key (for example `forte2022building`). Citation keys are how plain-text tools such as LaTeX, Quarto, R Markdown, Obsidian, and Logseq refer to the items in your library.
- **Two settings inside Zotero**: local API access, which lets other apps on your computer read your library, and Quick Copy, which puts a citation key on your clipboard with one keystroke.

## Step 1: Install Zotero

1. Go to [zotero.org/download](https://www.zotero.org/download/).
2. Download the installer for your platform (macOS, Windows, or Linux) and install it like any other app.
3. Open Zotero once so it can create its data folder.

If Zotero is already installed, update it before you continue. On macOS, use **Zotero → Check for Updates**. On Windows and Linux, use **Help → Check for Updates**. The steps below need Zotero 7 or newer.

Throughout this guide, "Settings" means the window you open with **Zotero → Settings** on macOS or **Edit → Settings** on Windows and Linux (older versions call it Preferences).

## Step 2: Create an account and turn on sync

A zotero.org account backs up your library and lets you use Zotero on more than one device. It is also how you join shared group libraries.

1. Create a free account at [zotero.org/user/register](https://www.zotero.org/user/register) and confirm the email it sends you.
2. In Zotero, open **Settings → Sync**.
3. Sign in with your new account.
4. Leave the data syncing defaults as they are. Data syncing covers your references, notes, tags, and highlights. It is free and has no size limit.

File syncing is a separate switch on the same tab. It covers the attached PDFs themselves. Zotero gives every account 300 MB of file storage for free; beyond that you either pay for a larger Zotero Storage plan or point Zotero at your own WebDAV server. If you plan to read your PDFs on a second device, keep file syncing on with the "Zotero" option selected; Zotero Storage is the option that works without further setup. If your library outgrows the free tier, you can decide later between paying and WebDAV.

Once you are signed in, any group libraries you have been invited to sync down automatically and appear in the left pane under **Group Libraries**. If you are at GHE and do not see the group library, ask to be invited with the email address on your zotero.org account.

## Step 3: Install the browser connector

The connector is the browser extension that saves what you are reading into Zotero.

1. In the browser you normally use, go to [zotero.org/download](https://www.zotero.org/download/). The page detects your browser and offers the matching connector (Firefox, Chrome, Edge, and Safari are supported).
2. Install the extension and pin its button to the toolbar so you can see it.
3. Keep the Zotero desktop app open while you save. The connector hands items to the desktop app; with the app closed it falls back to saving into your online library, which you then have to sync down.

To save an item, open the paper's page (the journal landing page, an arXiv abstract page, a book's publisher page) and click the connector button. The button's icon shows what Zotero detected: a paper, a book, a webpage. Zotero saves the reference metadata and, when it has access, downloads the PDF as an attachment.

Two other ways to add items, both inside Zotero:

- Click the magic wand button ("Add Item by Identifier") in the toolbar and paste a DOI, ISBN, PMID, or arXiv ID. Zotero fetches the full record.
- Drag a PDF file into the Zotero window. Zotero reads the metadata out of the PDF and creates the item around it. Check the result; metadata pulled from a bare PDF is sometimes incomplete.

## Step 4: Know your way around the library

Ten minutes of orientation before the configuration steps.

- The left pane lists your **collections**. A collection is a folder you assign items to; one item can sit in several collections at once without being duplicated.
- The middle pane lists the **items** in the selected collection. An item is the reference record: title, authors, year, journal, DOI, and so on.
- Attachments (the PDF), notes, and tags hang off an item. Click the arrow next to an item to see them.
- The right pane shows the selected item's fields. You can edit any field here; fix obvious metadata errors (wrong year, missing author) as you notice them, because everything downstream builds on these fields.
- Double-click an item to open its PDF in Zotero's built-in reader. Select text to highlight it, pick highlight colors, and add comments to a highlight. Your highlights are stored in Zotero's database, not written into the PDF file, and they sync across devices like any other data.

Save two or three real papers now so you have something to test with in the later steps.

## Step 5: Allow other apps to talk to Zotero

Some tools read your Zotero library through a local connection on your own computer, for example reference pickers in text editors and note-taking apps. One checkbox enables this.

1. Open **Settings → Advanced**.
2. Check **Allow other applications on this computer to communicate with Zotero**.

The connection only works for apps running on the same computer. Nothing is exposed to the internet, and nothing leaves your machine. You may not need it today; turning it on now means tools you add later work without a trip back to this menu.

## Step 6: Install Better BibTeX

Better BibTeX is not in a built-in plugin store; you install it from a downloaded file.

1. In your browser, go to the [Better BibTeX releases page](https://github.com/retorquere/zotero-better-bibtex/releases) and download the latest `.xpi` file. If the browser asks whether to open or save it, save it. Firefox may try to install it as a browser extension; right-click the link and choose "Save Link As" instead.
2. In Zotero, go to **Tools → Plugins** (older versions call it Add-ons).
3. Click the gear icon, choose **Install Plugin From File**, and select the `.xpi` you downloaded.
4. Restart Zotero when prompted.

After the restart, the Settings window has a new **Better BibTeX** tab.

## Step 7: Configure the citation keys

A citation key is a short, human-readable ID for one item, like `forte2022building`. Once other tools refer to your items by these keys, a key must never change, because every reference to it would break. The settings in this step make keys predictable and stable.

At GHE, the formula below is the harmonized citation key for everyone. Because every member generates keys the same way, a reference shared through the group library carries the same key in each member's library, and `forte2022building` means the same paper in everyone's manuscripts. Drafts, Quarto documents, and bibliography files can then move between people without rekeying citations.

Open **Settings → Better BibTeX**. Under **Citation keys**:

1. Set the citation key formula to:

   ```
   auth.lower + year + veryshorttitle(1, 0).lower
   ```

   Reading the formula left to right: the last name of the first author, lowercased; then the publication year; then the first meaningful word of the title (leading words like "a" and "the" are skipped), lowercased. For example, Tiago Forte's 2022 book "Building a Second Brain" gets the key `forte2022building`.

2. Set **Automatically fill citation key after** to `2` seconds. Filling writes the generated key into Zotero's own Citation Key field on the item, where it is saved permanently and synced across your devices. Two seconds after you save or edit an item, its key is fixed; you can see it in the item's right-hand pane.

3. Keep **Force citation key to plain text** checked. It keeps TeX markup and escape sequences out of the keys.

4. Keep **Regenerate citation key when item changes** unchecked. With the box unchecked, a filled key stays as it is even when you later fix a typo in the author or title. That is what you want: metadata corrections should not silently rename the key that other tools already use.

5. The defaults under **Keeping citation keys unique** are fine: the comparison ignores upper and lower case, and keys are kept unique within each library. When two items would get the same key, Better BibTeX appends a letter (`forte2022building`, `forte2022buildinga`) so no two items collide. Those suffixes depend on what else is in a given library, so they are the one place where two members' keys can differ; when a key with a trailing letter shows up in shared work, check the group library for the authoritative one.

A note on "pinning", in case you read older guides: earlier Better BibTeX versions called a stored key "pinned", and the setting in point 2 was named *Automatically pin citation key after*. The mechanism is the same, only the wording changed.

Items that were already in your library before this step may carry keys from the old default formula. To recompute them, select the items, right-click, and choose **Better BibTeX → Regenerate citation key**. Do this now, before anything else refers to the old keys; regenerating later breaks every reference to them.

## Step 8: Set up Quick Copy

Quick Copy defines what lands on your clipboard when you copy an item. Set it to the citation key, since that is what you will paste into plain-text documents and notes.

1. Open **Settings → Export**.
2. Under **Quick Copy**, set **Item Format** to **Better BibTeX Citation Key Quick Copy**.
3. Set **Note Format** to **Markdown + Rich Text**, and check **Include Zotero Links** on the Markdown line (leave the Rich Text/HTML line unchecked). A Zotero note copied out as Markdown then keeps a link back to the item it came from.

From now on, selecting an item and pressing **Cmd+Shift+C** (macOS) or **Ctrl+Shift+C** (Windows/Linux) copies its citation key. Dragging an item into any text field pastes the key. If you need a formatted citation instead of the key, **Cmd+Shift+A** (**Ctrl+Shift+A**) copies one in the citation style selected on the same settings tab.

## Optional: Zotero on an iPad or phone

The mobile app is good for reading and highlighting; everything else stays on the desktop.

1. Install Zotero from the App Store (iOS) or Play Store (Android) and sign in with your zotero.org account. That is the whole mobile setup: no API keys, no plugins. Better BibTeX does not exist on mobile, so citation keys are assigned when the desktop app next syncs.
2. Reading PDFs on the device requires file syncing (Step 2), because the device has to download the attachments.
3. Highlights made on the device sync to zotero.org and from there to your desktop, like highlights made anywhere else.

## Check your setup

Run through this list with one real paper. If every point works, the setup is complete.

1. Click the connector button on a paper's webpage; the item appears in Zotero with its metadata and, where available, the PDF.
2. Within a few seconds of saving, the item shows a citation key in the right-hand pane, in the shape `authorYEARword`, all lowercase.
3. Select the item and press Cmd+Shift+C (Ctrl+Shift+C on Windows/Linux); pasting into any text editor produces that key.
4. Edit the item's title, wait, and confirm the key did not change.
5. Open the PDF, add a highlight, and (if you use a second device) confirm the highlight shows up there after a sync.

## Where to go from here

You now have a library with stable citation keys, one-keystroke access to them, and a local connection other tools can use. On top of this foundation you can point a citation plugin in your text editor at Zotero, cite from Quarto or LaTeX documents by key, or connect a note-taking system that files your reading notes under the same keys.

If you are continuing into the llm-wiki literature workflow, the [Zotero setup walkthrough](zotero-setup-walkthrough.md) builds directly on this setup; everything you configured here is its prerequisite.
