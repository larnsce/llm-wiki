# /lit-sync - Zotero to Logseq literature sync

Sync the Zotero library into `notes/literature/@<citekey>` pages via the
local HTTP API. Plugin-free: this replaces the logseq-zoterolocal-plugin
(issue #90). Guide: `docs/zotero-setup.md`.

## Preconditions (tell the user and stop if unmet)

1. Zotero is running, with Settings -> Advanced -> "Allow other
   applications on this computer to communicate with Zotero" enabled.
2. Better BibTeX is installed with citekeys auto-pinned. Items without a
   pinned citekey are skipped with a warning, never guessed.
3. The vault path: resolve the Logseq graph root from `llm-wiki.yml`
   (`wiki_path`), or ask if no config is discoverable.

## Workflow

1. **Dry-run first, always:**

   ```
   python3 scripts/lit_sync.py --vault <wiki_path> --dry-run
   ```

   Show the user the planned creates/updates/appends and the skipped-item
   titles. If the local connection fails (exit 2), STOP and relay the
   script's message. Do NOT work around it with the Zotero cloud API.

2. **Real run only after the user confirms the dry-run output:**

   ```
   python3 scripts/lit_sync.py --vault <wiki_path>
   ```

3. **Review and commit** (in the vault repo, not this repo): show
   `git status` of the touched `pages/notes___literature___*` files, then
   commit as `lit: sync Zotero library (<n> created, <n> updated)`.

## Guarantees the script keeps (do not break them by hand-editing output)

- Only managed properties are rewritten (`type`, `citekey`, `authors`,
  `year`, `item-type`, `doi`, `zotero`); `source-file::` and user-added
  properties survive every run.
- The reading section (`## literature`; `## my reading` on pages created
  before the #101 rename) is never touched: it is human-written `notes/`
  content. Notes there are LITERATURE notes in the user's Zettelkasten
  typing; the user adds the `#literature` tag by hand. The tooling never
  writes a `#tag`.
- Annotations append incrementally: only Zotero versions newer than the
  page's `zotero-last-sync::` stamp, sorted by position in the PDF.
- `source-file::` stays blank at creation; it is filled by hand when the
  paper goes through `/wiki-ingest` (the "one source, two readings" seam).
