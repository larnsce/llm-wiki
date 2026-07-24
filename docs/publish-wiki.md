# Publishing a wiki as a static site

How to publish a wiki (or an exported subset of one) as a public,
markdown-first website (issue #145). The pattern follows the
Karpathy-style setup: the server hosts nothing but raw `.md` files plus
one static `index.html`. Everything after `#/` in the URL names a real
markdown file; a small script fetches it and renders it client-side.
Humans read the rendering; agents fetch the identical `.md` at the same
path. No build step, no framework, no dependencies.

This is distinct from the Quarto documentation site (`docs/website.md`),
which publishes this tool's own documentation. This page is about
publishing wiki content.

## The viewer template

The canonical viewer lives at `templates/site/index.html` in this repo:
one self-contained file (hash router plus an embedded markdown
renderer). It renders both page flavors per file: Obsidian (YAML
frontmatter plus flat markdown) and Logseq (`property::` lines plus
outline blocks, flattened for reading). Page properties render as a
small metadata strip under the title. `[[wikilinks]]` become hash
routes, so `[[wiki/concept/foo]]` links to `#/wiki/concept/foo.md`.

For a Logseq graph published as-is, namespaced pages live flat under
`pages/` with `___` separators. The viewer resolves that automatically:
a route like `wiki/concept/foo.md` with no file at that path falls back
to `pages/wiki___concept___foo.md`.

A working example is `examples/paper-site/` (the #145-#148 exploration
fixture): a fictional paper wiki with a hub homepage, an AI-transparency
agent log, literature and concept pages, and a visible publish-boundary
404 page.

## Install

1. Create the publish directory and copy in the markdown you are
   publishing (see the boundary section below).
2. Copy `templates/site/index.html` into its root.
3. Edit the `SITE` block at the top of the script (marked
   `>>> EDIT THIS <<<`): site title, tagline, default route, and the
   header navigation links. The default route should be a hub or index
   page, so the L1 hub doubles as the site's navigation root.
4. Preview locally:

   ```
   cd <publish-dir>
   python3 -m http.server 8123
   # open http://localhost:8123/#/index.md
   ```

5. Publish: push the directory to a GitHub repository and enable Pages
   on it (serve from the branch root). Deploying is copying files; there
   is no build.

## The publish boundary

The boundary is the file set you copy. The viewer renders whatever
markdown is present and shows a "not part of the published set" page
for anything else, so an unpublished page fails visibly and gracefully.
Two boundary models, from issues #145 and #148:

- **Whole-wiki publishing**: copy the wiki tiers you consider public
  (for example `wiki/` and its hub pages). Personal tiers stay out by
  default: journals, voice material, `para/`, `notes/` are never copied
  unless you decide otherwise deliberately.
- **Paper bundles** (#148, planned): the export walks a paper hub's
  link graph and collects only reachable pages, with this viewer
  vendored into the bundle root. The boundary is the walk.

## The publish gate

Nothing goes public without a secret scan. Before the first push, and
after any content update, run the scanner over every file in the
publish directory:

```
find <publish-dir> -name "*.md" -print0 | \
  xargs -0 -n1 python3 skills/wiki-core/scripts/secret_scan.py
```

A blocking finding (exit 2) means the file does not get published until
the secret is redacted. This is the same gate the ingest pipeline uses
before archiving sources (ingest REQ-045/046), applied at the publish
seam.

Also review the content itself before publishing: reliability ratings,
`## Pending Review` sections, and provenance notes are published as
they stand, which is the point (the trust layer is part of the public
record), but claims about other people deserve a deliberate read before
they leave the vault.

## Privacy model

- The publish directory is a copy, never a symlink into the vault; the
  vault itself stays private.
- The viewer has no search index, no analytics, and fetches nothing
  from outside the site's own origin.
- The raw `.md` behind any rendered page is public at the same path
  the viewer uses. Publish only what may be read raw.

## Install path status

There is deliberately no `wiki-publish` skill yet: the manual path
above is the install path until the #148 export bundle exists, which
will own the mechanical walk-and-copy (the repo rule is not to
formalize a verb prematurely). The cognee front end that motivated the
prior-art check (see #145) was evaluated 2026-07-24 and rejected for
reuse: the demo site is a built React bundle, not a vendorable static
file, and cognee's frontend (Apache-2.0) is a full application
entangled with its backend. The from-scratch single-file viewer is the
implementation.
