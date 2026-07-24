---
title: wiki-paper in plain language
description: Keeps one anchor page per manuscript that links everything the wiki holds for that paper, and that page later becomes the public site's table of contents.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-paper skill in plain language. The model itself runs the
[standard version](../skills/wiki-paper/SKILL.md), which the site publishes
word for word.
:::

## What it does

wiki-paper gives each manuscript one anchor page in the wiki. The anchor
page holds six sections: the manuscript's working title and status, the
literature it draws on, its datasets, the open questions, the dated
decisions taken while drafting, and a note on how AI was used. Everything
appears as links. The literature notes, concept pages, and data pages stay
where they already live; the anchor page only points at them. When you
start a paper, the skill creates the anchor page after showing you exactly
what it will write. When you want to add a source or a dataset, it appends
a link to the right section, again shown as a change first. A read-only
status mode reports how complete the anchor page is, including any page in
the paper's folder that the anchor does not link yet.

Each paper also gets a log page, created together with the anchor page.
Every time a skill touches the paper's material, one row is added: the
date, which skill ran, which model the user confirmed, what was read, what
was written, and what the user approved. Journals increasingly ask authors
to disclose how AI was used, and the disclosure statement for submission
can be generated from these rows instead of being reconstructed from
memory. The rows are never edited or deleted.

The anchor page matters beyond the wiki. When a paper is published as a
public site, the anchor page becomes the site's homepage and table of
contents, and only pages reachable from it are exported. A link missing
from the anchor means a page missing from the public record, so the health
check warns about unlinked pages.

## When to use it

Use it when you start writing a paper, when you want to attach a source or
dataset you just ingested, or when you want to know how a paper's material
stands, e.g., before an export.

## What it never does

The skill never rewrites, moves, or copies the pages a paper draws on;
they are linked in place. It never writes outside the paper's own folder
and the papers index. It never touches your personal project notes; the
anchor page may link to them, but their content stays yours. And a
finished paper is not special: its pages age out of the live search index
like any other cold pages, and come back when something hits them again.
