# Glossary System (EN ↔ DE)

## Purpose

Make terminology decisions once and record them permanently, so blog posts, teaching material, and AI-generated drafts stay consistent. Modeled on the termbases professional translators maintain.

## Core principles

1. **Separate structure from content.** Tags, page titles, and links in the vault use exactly one canonical language. Note content and quotes stay in their original language.
2. **Draft in the output language, don't translate.** Write German blog posts and teaching content directly in German — notes are raw material, not draft text.
3. **A glossary is not ingest.** Ingest processes external sources once. A glossary is a curated, permanently maintained evergreen reference page — part of the wiki layer, conceptually an "L1 cache": small, always relevant, loaded whenever you write.

## Placement in Logseq

- **Not in journals.** Journals are chronological capture; a glossary is timeless reference.
- **Namespace per domain:** `Glossary/Tech`, `Glossary/Teaching`, `Glossary/Marketing`. The parent page `Glossary` automatically serves as the index.
- **Split by domain, not by language pair.** All glossaries are EN↔DE anyway; what differs is subject area and audience.
- **Aliases for bridge terms:** key concepts get the other-language term as an alias, so `[[Decision]]` and `[[Entscheidung]]` resolve to the same page.

## Page format

```markdown
# Glossary/Tech

| EN | DE | Rule | Note |
|----|----|----|----|
| prompt | der Prompt | keep EN | naturalized, don't translate |
| note-taking | Zettelarbeit | translate | "Notizen machen" only colloquially |
| link | die Verknüpfung / der Link | context | blog: Link, teaching: Verknüpfung |
```

The **Rule** column is the crucial one — it records the *decision*, not just the translation. Three rule types cover almost everything:

- `keep EN` — term stays English (record gender: der Prompt, das Feature)
- `translate` — fixed German equivalent
- `context` — depends on domain/audience, with a note on when to use which

## Workflow

1. **Capture:** Hesitating on a term while writing = the signal. Mark it inline with `#glossary-todo` and keep writing.
2. **Curate:** Periodically review all `#glossary-todo` hits, make the decision, move it to the right `Glossary/...` page.
3. **Use:** When drafting with Claude, reference the relevant glossary as context ("use the conventions from Glossary/Teaching") → consistent terminology in generated German text.

## Term pages and `[[ ]]` linking

The glossary table is the index; **core terms additionally get their own page**. That makes definitions findable everywhere: hover-preview on any `[[Repository]]` link shows your adopted definition, and both language variants resolve to one page via alias.

Term page template:

```markdown
# Repository

alias:: Repositorium
domain:: [[Glossary/Tech]]
rule:: keep EN (der/das Repository)

Adopted definition: a place where a version control system stores
a project's files and their history.

conflicts:: Turing Way defines it broadly (any storage location for
data/software/publications); Glosario restricts it to VCS. I use the
narrow VCS sense; for data archives I say [[Data Repository]].
```

Rules of thumb:

- **Promote selectively.** Only terms that are load-bearing in your writing or teaching get a page. The rest live as table rows.
- **Link on first mention or where precision matters** — not every occurrence. Logseq's *Unlinked references* catches unmarked mentions automatically, so over-linking only adds noise.
- **The `conflicts::` property is the payoff.** External glossaries genuinely contradict each other (e.g., Turing Way vs. Glosario on *continuous integration*, *bug*, *repository*, *Markdown*). A term page records which definition you adopted and why — one decision, applied everywhere.
- Table cells in the domain glossaries link to the term pages: `| [[repository]] | das Repository | keep EN | ... |`

## Importing external glossaries

External multilingual glossaries can seed your pages, as long as they are structured data. Example: Glosario (The Carpentries, CC-BY) publishes its entire glossary as one YAML file with per-language `term` and `def` fields.

**Pattern:**

1. Fetch the source data (`glossary.yml` from the GitHub repo, not the website).
2. Filter to entries that have both `en` and `de`.
3. Convert to your table format, into a dedicated **staging page** (e.g., `Glossary/Imported/Glosario`) with `source::` and `status:: unreviewed` properties.
4. **Promote, don't merge.** Move individual terms into your own domain pages only when you actually adopt them — filling in the Rule column is your decision, not the source's. Imported entries have translations but no rules yet.

Reference script (Python, ~20 lines):

```python
import yaml

entries = yaml.safe_load(open("glossary.yml"))
rows = [
    (e["en"]["term"], e["de"]["term"], e["slug"])
    for e in entries
    if e.get("en", {}).get("term") and e.get("de", {}).get("term")
]
rows.sort(key=lambda r: r[0].lower())

with open("glossary-glosario-import.md", "w") as f:
    f.write("# Glossary/Imported/Glosario\n\n")
    f.write("source:: Glosario (The Carpentries), CC-BY\n")
    f.write("status:: unreviewed\n\n")
    f.write("| EN | DE | Rule | Note |\n|----|----|----|----|\n")
    for en, de, slug in rows:
        f.write(f"| {en} | {de} | | [src](https://glosario.carpentries.org/en/#{slug}) |\n")
```

Keep the attribution line — Glosario is CC-BY. The same pattern works for any structured termbase (TBX, CSV, or Microsoft's terminology collection).
