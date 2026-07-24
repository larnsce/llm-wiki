---
title: wiki-maintain in plain language
description: Reports how the wiki is doing, and on request retires pages nobody reads from the search index without deleting anything.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-maintain skill in plain language. The model itself runs
the [standard version](../skills/wiki-maintain/SKILL.md), which the site
publishes word for word.
:::

## What it does

wiki-maintain keeps the wiki fast to search as it grows. It has two modes.
Status is the default and only reads. It reports how many pages exist in
each section, how healthy they are, which pages are read most, which pages
have not been read in months, and what changed in the last weeks. Prune runs
only when you ask for it. It collects the pages nobody has read for six
months (you can change the period) and, page by page and with your
confirmation, moves their routing lines out of the live search index into an
archive list, so that searches stop considering them.

## When to use it

Use status whenever you wonder how the wiki is doing. Use prune a few times
a year to keep the search index small and precise.

## What it never does

Prune never deletes, renames, or moves a page file, so every link to the
page keeps working. The only change is that the page leaves the live search
index, and the query skill offers to bring it back the moment a search hits
it again. Hub pages, the Schema page, the Dashboard, and projects that are
still active are never pruned, even when nobody has read them.
