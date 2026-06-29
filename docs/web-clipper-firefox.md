# Setting up a Firefox web-clipper for the LLM Wiki (MarkDownload on macOS)

Setup notes for clipping web pages into the Logseq-based LLM Wiki's `raw/` folder, where `/wiki ingest` picks them up. Companion to the provenance/audit work in the [Schema Reference](schema-reference.md) and [Literature Research](literature-research.md) guides.

This covers choosing a Firefox extension to turn web pages into `.md` files, configuring it to drop clips into the wiki's raw-input folder on macOS, and fixing the symlink so the hand-off is automatic.

## 1. Which Firefox extension fits the pipeline

Goal: turn web pages into `.md` files that feed the existing file-based `/wiki ingest` workflow, ideally carrying source metadata that maps onto the wiki's provenance fields (`source-file::`, `reliability::`).

Shortlist, sorted by fit:

- **MarkDownload (deathau)** is the best fit. It uses Mozilla Readability + Turndown, downloads a `.md` file, and is open-source and mature. Its front/back template system stamps each clip with source URL, title, author, and date, exactly the fields the ingest step needs to populate provenance. It supports selection-only clipping and right-click context menus.
- **Get Markdown** is a close second, more turnkey. Readability-based, it emits rich metadata (title, author, source, URL, save date) automatically with a one-click `.md` download. Newer and less battle-tested.
- **LLMFeeder** is open-source (Readability + Turndown), with customizable metadata templates, download/ZIP/merge options, and a token counter. Clipboard-first by design, so slightly less aligned with a file-based ingest.
- **Page to Markdown** is a simple one-click download with a plain-text mode that strips links and images for minimal-noise context.
- **Page to Markdown Exporter** bundles images into a ZIP alongside the markdown; useful for image-heavy pages.

**Integration note:** these emit standard markdown / YAML front matter, not Logseq block syntax. Treat a clip as *raw* input: it lands in the raw side of the raw/ingested split, and `/wiki ingest` transforms it into a proper Logseq page with provenance and claim-level citations. Do not drop clipper output straight into the vault as a finished page; that bypasses the provenance and audit machinery.

## 2. Can MarkDownload save to a dedicated folder?

Yes, with one boundary: it can only write **inside the browser's Downloads folder**, because a browser security limit prevents saving to an arbitrary path. Within that limit:

- The **Subfolder** option (Options page) routes clips to a subfolder of Downloads. It requires **Download Mode = Downloads API**.
- The **title template** also accepts a forward slash to nest files (e.g. `wiki-raw/{title}`), but the dedicated Subfolder field is cleaner.

To land clips directly in the vault (which lives outside Downloads), bridge the last hop with either:

- **A symlink.** Point `~/Downloads/wiki-raw` at the vault's `raw/` folder. This is the standard macOS solution.
- **A watch/move step.** A script that watches `~/Downloads/wiki-raw/`, moves new `.md` files into the vault's raw folder, and optionally triggers `/wiki ingest`.

The symlink is the tidiest for a git-versioned vault: the clip writes to Downloads, the symlink lands it in `raw/`, and ingest does the transform.

## 3. Step-by-step setup (macOS)

### Part A - Install and set the download mode

1. In Firefox, add MarkDownload from addons.mozilla.org.
2. Open the extension's **Options** (puzzle-piece icon, then MarkDownload, then Manage/Options).
3. Set **Download Mode** to **Downloads API** (the Subfolder feature only works in this mode).

### Part B - Point it at a `wiki-raw` subfolder

4. In the **Subfolder** field, type exactly: `wiki-raw`
5. Leave **Title Template** as the default `{title}`.

### Part C - Stamp each clip with its source (provenance)

6. In **Front/Back Templates**, set the front template to:

```
---
title: {pageTitle}
source: {baseURI}
author: {byline}
clipped: {date:YYYY-MM-DD}
---
```

`{baseURI}` is the page URL and `{byline}` is the author. The `source:` line is the anchor `/wiki ingest` reads to fill `source-file::`, giving web clips the same provenance as Zotero papers.

### Part D - Create the symlink (one-time Terminal step)

First confirm the vault's `raw/` folder exists in Finder (create it if not).

7. Open **Terminal**.
8. Type `ln -s ` (with a trailing space); do not press Enter.
9. Drag the vault's **raw** folder from Finder into Terminal (this pastes its path).
10. Type a space, then `~/Downloads/wiki-raw`.
11. Press **Enter**. The finished line looks like:

```
ln -s "/Users/yourname/logseq-notes/raw" ~/Downloads/wiki-raw
```

12. Verify with `ls -la ~/Downloads/`; look for `wiki-raw -> /Users/.../raw` (the arrow proves it is a shortcut, not a folder).

### Part E - Test

13. Clip any page with MarkDownload, then Download.
14. Confirm the new `.md` appears directly in the vault's `raw/` folder, with the source URL in its front matter.

## 4. Troubleshooting: nested symlink

**Symptom:** after running the link command, `Downloads/wiki-raw/raw` appears instead of `wiki-raw` itself being the shortcut.

**Cause:** a `wiki-raw` folder already existed in Downloads (from an earlier test clip). When the target name already exists as a directory, `ln -s` places the link *inside* it (named `raw`) rather than turning `wiki-raw` into the link.

**Fix:**

1. In Finder, open `Downloads/wiki-raw` and move any `.md` test clips into the vault's `raw/` folder so they are not lost.
2. Drag the whole `wiki-raw` folder to the Trash. (Deleting a shortcut never deletes its target, so the vault's real `raw/` folder stays safe.)
3. Re-run the `ln -s` command from Part D. With `wiki-raw` gone, the command now makes `wiki-raw` *itself* the shortcut.
4. Verify with `ls -la ~/Downloads/`; the `wiki-raw -> /Users/.../raw` arrow should now appear.
5. Test-clip a page; the `.md` lands directly in the vault's `raw/` folder.

MarkDownload settings do not change: **Subfolder** stays `wiki-raw`.

**Result:** working. Clips now flow Firefox to `~/Downloads/wiki-raw` (symlink) to vault `raw/` to `/wiki ingest`.
