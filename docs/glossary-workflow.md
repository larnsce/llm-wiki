# Glossary workflow: EN-DE terminology decisions, made once

How to run a hand-maintained EN-DE terminology layer (`glossary/`) in the same graph as the
wiki, so blog posts, teaching material, and AI-generated drafts stay consistent. Modeled on the
termbases professional translators maintain.

> **Status (v2.3, 2026-07-06).** The hand-run layer (G-0, 2026-07-04) plus the tooling layer
> ([#54](https://github.com/larnsce/llm-wiki/issues/54), shipped 2026-07-06 under the gate
> waiver): spec ([`openspec/specs/glossary.md`](../openspec/specs/glossary.md)), lint rule 15,
> `--with-glossary` scaffold, and the `/wiki-glossary` skill; see
> [The tooling layer](#the-tooling-layer) below. Concept note:
> [`prompts/glossary-concept.md`](../prompts/glossary-concept.md).

> **Scope.** This is a **vault-side workflow guide**, not a skill reference. The wiki toolchain
> does not manage `glossary/` pages; you create and maintain them by hand from the templates.
> The tool's only involvement today is reading a domain page when you load it as drafting
> context, and (on request) transforming an external termbase at import time.

## The idea

A glossary is not ingest and not notes. It is a curated, permanently maintained evergreen
reference: you make each terminology decision once and record it forever, instead of re-deciding
it in every draft. Conceptually an L1 cache: small, always relevant, loaded whenever you write.

The **Rule column IS the product**. It records the decision, not just the translation. Three
values cover almost everything:

- `keep-en` - the term stays English; record the German article (der Prompt, das Feature).
- `translate` - a fixed German equivalent.
- `context` - depends on domain or audience, with a note on when to use which.

A row without a Rule value is not a glossary entry; it is raw material waiting for a decision.

## Placement

- **Domain pages, not language-pair pages:** `glossary/tech`, `glossary/teaching`,
  `glossary/marketing`. Every domain glossary is EN-DE; what differs is subject area and
  audience. Structural names stay lowercase with hyphens (schema REQ-580..581).
- **The parent `glossary` page is the index.** Give it hub-style routing lines, one per domain:
  `[[glossary/tech]] -- software, git, and computing terms #glossary`
- **Term pages live under their domain:** `glossary/tech/repository`, never at the vault root.
  Root-level term pages pollute the root and trip namespace hygiene for no benefit.
- **Aliases carry both language forms.** A term page with `alias:: Repository, Repositorium`
  makes `[[Repository]]` and `[[Repositorium]]` resolve to the same page, and hover-preview
  shows your adopted definition wherever the term is linked.
- **Not in journals.** Journals are chronological capture; a glossary is timeless reference.

Start from the templates:
[`templates/logseq/glossary-domain.md`](../templates/logseq/glossary-domain.md),
[`templates/logseq/glossary-term.md`](../templates/logseq/glossary-term.md), and the Obsidian
counterparts
([domain](../templates/obsidian/glossary-domain.md), [term](../templates/obsidian/glossary-term.md)).

## Capture

Hesitating on a term while writing IS the signal. Mark it inline with `#glossary-todo` and keep
writing:

```
- Der #glossary-todo Pull Request wird nach dem Review gemerged.
```

Do not stop to decide; deciding mid-draft is how drafts die. The tag costs one word and
preserves the exact sentence that triggered the hesitation, which is the context you will want
when you decide later.

## Curate

A periodic hand pass, suggested cadence weekly while you are drafting regularly:

1. **Collect:** search for `#glossary-todo` (Logseq: the tag's linked references; Obsidian:
   search for the tag).
2. **Decide:** for each hit, pick the Rule value and the German form. This is the human step;
   nothing decides for you.
3. **Write the row:** add `| EN | DE | Rule | Note |` to the right domain page. Create the
   domain page from the template if it does not exist yet, and add its routing line to the
   `glossary` index.
4. **Mark done:** mark the captured block `DONE` or replace the tag with a link to the decided
   term, so the next pass starts clean. Aim to drain the tag to zero.

## Use as drafting context

When drafting with Claude, load the relevant domain page as context: "use the conventions from
`glossary/teaching`". One small page buys consistent terminology in the generated German text.

**Never load a staging or import page (`glossary/imported/...`) as drafting context.** Staging
rows are unreviewed and carry no Rule values; loading them would feed undecided terminology into
your drafts and silently outvote the 12 rows you actually decided. Curated domain pages are the
only glossary pages that belong in a drafting prompt.

## Promote selectively

- **Table rows are the default.** Only load-bearing terms, the ones your writing or teaching
  leans on, get their own page under the domain (`glossary/tech/repository`).
- **`conflicts::` is the payoff of a term page.** External glossaries genuinely contradict each
  other (The Turing Way and Glosario disagree on repository, continuous integration, bug). The
  property records which definition you adopted and why: one decision, applied everywhere.
- **Link on first mention** or where precision matters, not on every occurrence. Logseq's
  unlinked references catch unmarked mentions; over-linking only adds noise.
- On the domain page, turn a promoted term's EN cell into a link to its term page.

## Import is a pull, not a dump

External termbases (for example [Glosario](https://glosario.carpentries.org/) by The
Carpentries, CC-BY, published as one `glossary.yml`) can seed rows, under three rules:

1. **Pull only what you captured or requested.** Import brings in ONLY terms matching your open
   `#glossary-todo` captures, plus terms you explicitly ask for. Never the full termbase: a
   400-row unreviewed staging page next to a 12-row curated page is how the Rule column dies.
2. **Import is an agent transformation, not a script.** There is no importer script in this
   repo, by design: have Claude read the downloaded source file and write only the matching
   rows. A hand-rolled parser would be permanent code for an occasional pull (and PyYAML is not
   stdlib, so it stays out).
3. **Staging, then promote; never merge.** Imported rows land on `glossary/imported/<source>`
   (for example `glossary/imported/glosario`) with `source::` attribution and
   `status:: unreviewed`, and the Rule column EMPTY: the source has translations, not your
   decisions. Move a row to a domain page only when you adopt it and fill in the Rule yourself.
   Keep the `source::` attribution line on the staging page; Glosario is CC-BY, so attribution
   is a license condition, not a courtesy.

A working import prompt:

```
Read ~/Downloads/glossary.yml (Glosario, The Carpentries, CC-BY).
Find the entries for: repository, commit, continuous integration.
Write ONLY those rows to the page glossary/imported/glosario, table
| EN | DE | Rule | Note |, Rule cell empty, a link to the Glosario
entry in the Note cell. Page properties:
source:: Glosario (The Carpentries), CC-BY, https://glosario.carpentries.org
status:: unreviewed
Report the row count, and confirm each requested term against the
source file (it must appear as a slug in glossary.yml); tell me which
requested terms have no de entry.
```

Three requested terms must produce at most three rows; verify the count before moving on. The
same pattern works for any structured termbase (TBX, CSV, or a terminology collection export).

## The tooling layer

The formal layer originally gated behind 20-plus hand-decided rows shipped under the 2026-07-05
gate waiver ([#54](https://github.com/larnsce/llm-wiki/issues/54)):

- `glossary/` is the fourth namespace of the contract
  ([`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) REQ-960); its ownership
  model (human-DECIDED, tool-READABLE, structure-LINTED) is normative in
  [`openspec/specs/glossary.md`](../openspec/specs/glossary.md).
- Lint recognizes glossary pages: no more rule 14 strays, no wiki-only findings
  (source-file, reliability, cite, routing). **Rule 15 (glossary hygiene)** checks structure
  only: the exact `| EN | DE | Rule | Note |` header, the rule enum, empty-Rule rows on
  domain pages, and `source::`/`status::` on `glossary/imported/` staging pages. It never
  judges or auto-fixes a decision.
- `init_wiki.py --with-glossary` (or `setup.sh --init ... --with-glossary`) scaffolds the
  `glossary` index and a seed domain page from the templates; the `glossary_dir` config key
  (default `glossary`) names the namespace.
- The `/wiki-glossary` skill automates the mechanical parts of this guide: it drains
  `#glossary-todo` captures into a curation checkpoint, writes ONLY the rows you confirm,
  runs the promote flow (staging row to domain page to optional term page), and loads domain
  pages as drafting context. Everything it writes lands under `glossary/` and nothing is
  written without your confirmation at the checkpoint.

The hand-run loop in this guide remains the core of the workflow; the skill only removes the
copying and collecting. The standing rules bind the skill exactly as they bind you: import is
pull not bulk, staging pages are never drafting context, and the Rule column stays a human
decision.

## Related

- [`prompts/glossary-concept.md`](../prompts/glossary-concept.md) - the concept note this layer implements
- [`docs/roadmap-glossary-personal-pipeline.md`](roadmap-glossary-personal-pipeline.md) - the plan and the premortem revisions that gated the tooling
- [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) - the namespace contract; glossary/ is its fourth namespace
- [`openspec/specs/glossary.md`](../openspec/specs/glossary.md) - the normative glossary spec (REQ-1000..1014)
- [Schema Reference](schema-reference.md) - naming, properties, lint rules
- [PARA + Zettelkasten workflow](para-notes-workflow.md) - the other human-owned layers in the graph
