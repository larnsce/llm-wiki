# Glossary workflow: EN-DE terminology decisions, made once

How to run a hand-maintained EN-DE terminology layer (`glossary/`) in the same graph as the
wiki, so blog posts, teaching material, and AI-generated drafts stay consistent. Modeled on the
termbases professional translators maintain.

> **Status (v2.3 G-0, 2026-07-04).** This is the hand-run layer: two page templates and this
> guide, nothing else. Capture, curation, and promotion run manually for at least 4 weeks. The
> tooling layer (spec, lint rule, scaffold flag, skill) is gated behind
> [#54](https://github.com/larnsce/llm-wiki/issues/54); see [The tooling gate](#the-tooling-gate)
> below. Concept note: [`prompts/glossary-concept.md`](../prompts/glossary-concept.md).

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

## The tooling gate

The formal layer - a glossary spec, lint rule 15 (glossary hygiene), an
`init_wiki.py --with-glossary` scaffold flag, and a wiki-glossary skill - is stubbed and gated
in [#54](https://github.com/larnsce/llm-wiki/issues/54). It gets built only after **20 or more
hand-decided Rule rows** exist. If 4 weeks of hand-running produce fewer, the tooling is not
built and the glossary stays a manual convention (the kill criterion). No verb gets formalized
before it has been done by hand enough to know the ceremony pays off.

Until that layer lands, `glossary/` sits outside the three-namespace contract
([`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) REQ-960), so `lint.py`
reports a **namespace-hygiene warning (rule 14, REQ-240)** on every glossary page. This is
expected and harmless during the hand-run period. Because the glossary page types and links
are not registered either, lint may also report unknown-type, orphan, and cross-ref findings on
the same pages; same story. On fresh pages (no `schema-spec-version::`) all of these are floored
to info severity and lint still exits clean. The gated layer recognizes `glossary/` and retires
these findings.

## Related

- [`prompts/glossary-concept.md`](../prompts/glossary-concept.md) - the concept note this layer implements
- [`docs/roadmap-glossary-personal-pipeline.md`](roadmap-glossary-personal-pipeline.md) - the plan and the premortem revisions that gated the tooling
- [`openspec/specs/namespaces.md`](../openspec/specs/namespaces.md) - the namespace contract glossary pages currently sit outside of
- [Schema Reference](schema-reference.md) - naming, properties, lint rules
- [PARA + Zettelkasten workflow](para-notes-workflow.md) - the other human-owned layers in the graph
