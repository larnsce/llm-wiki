# The documentation website

The repo publishes its markdown tree as a Quarto website on GitHub Pages,
structured like a pkgdown site: Home (the README), a Skills reference, a
Specs reference, an Agents reference, Articles (this `docs/` directory),
and News (the CHANGELOG). Nothing is duplicated for the site; the pages
ARE the repo files, rendered in place.

The Skills navbar entry is a dropdown with two entries. "Standard
(SKILL.md)" lists the skills' own SKILL.md files, the instructions the
model runs, published word for word. "In plain language" lists the
`plain/<skill>.md` companion pages, which explain each skill in everyday
words for human readers, written to the plain-writing skill's rules. The
two generated indexes cross-link each pair, and every plain page opens
with a pointer to its standard page.

## How it fits together

- `_quarto.yml` at the repo root defines the website project. Its
  `render:` list is an allowlist: only the README-derived homepage,
  CHANGELOG, CONTRIBUTING, `docs/*.md`, `plain/*.md`, `openspec/specs/*.md`,
  `skills/*/SKILL.md`, `skills/*/references/*.md`, `agents/*.md`, and the
  generated `reference/*.md` index pages are rendered. `templates/`,
  `tests/`, `prompts/`, and `examples/` are deliberately excluded
  (Logseq-syntax templates and fixture content are not human docs).
- `tools/build_doc_indexes.py` runs as the Quarto pre-render step and
  generates the pkgdown-style index pages from metadata that already
  lives in the sources: `reference/skills.md` and `reference/agents.md`
  from SKILL.md / agent frontmatter (`name`, `description`, `model`),
  `reference/plain-language.md` from the `plain/*.md` frontmatter
  (`title`, `description`), `reference/specs.md` from each spec's h1 and
  Description paragraph, `reference/articles.md` from the `docs/*.md`
  h1s, and `index.md` as a copy of the README. All six outputs plus
  `_site/` and `.quarto/` are gitignored: edit the sources, never the
  generated files.
- `.github/workflows/publish-site.yml` renders and publishes to the
  `gh-pages` branch on every push to `main` (and on manual dispatch),
  via `quarto-dev/quarto-actions`. GitHub Pages serves that branch. The
  site URL is `https://larnsce.github.io/llm-wiki/`.

## Local preview

Quarto is a self-contained CLI (no npm, no pip; the pre-render script is
stdlib python3). If `quarto` is not on PATH, RStudio and Positron bundle
it:

```
export PATH="/Applications/Positron.app/Contents/Resources/app/quarto/bin:$PATH"
quarto preview        # live-reload preview
quarto render         # full build into _site/
```

## Conventions the site relies on

- Every rendered page derives its title from YAML frontmatter or its
  first `# h1`; all docs, specs, and SKILL.md files carry one.
- Frontmatter must be strict YAML: a `description:` value containing
  `": "` needs quoting (Claude Code's reader is tolerant, Quarto's is
  not; the agent definitions are quoted for this reason).
- Relative `.md` links between rendered files are rewritten to `.html`
  automatically. Links INTO unrendered directories (`prompts/`,
  `templates/`) stay raw `.md` and 404 on the site while still working
  on GitHub; they only occur in archival roadmap docs, which is the
  accepted trade-off.

## First-time publishing checklist

1. Merge the site config to `main`; the workflow creates `gh-pages` on
   its first run.
2. In the repo settings, set Pages to serve from the `gh-pages` branch
   (root). One-time step;
   `gh api repos/larnsce/llm-wiki/pages -X POST -f 'source[branch]=gh-pages' -f 'source[path]=/'`
   does the same from the CLI once the branch exists.
3. Check the rendered site against this page's conventions after
   structural changes (new top-level directories need a `render:`
   entry; a new skill or spec appears in its index automatically).
4. Every skill ships with a `plain/<skill>.md` companion page. A new
   skill without one still renders and is still indexed, but its
   plain-language cell stays empty and the pre-render script prints a
   warning; write the plain page (following the plain-writing skill's
   rules) to clear it.
