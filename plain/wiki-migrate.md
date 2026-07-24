---
title: wiki-migrate in plain language
description: Upgrades an old wiki to the current page format, one time, with a preview of every change and nothing applied without your confirmation.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-migrate skill in plain language. The model itself runs
the [standard version](../skills/wiki-migrate/SKILL.md), which the site
publishes word for word.
:::

## What it does

wiki-migrate upgrades an old wiki to the current page format, one time. It
runs a converter in preview mode first and shows you a report of every
change it would make, page by page. Nothing is applied until you confirm,
and you can apply everything at once, go page by page, or stop. After
applying, the skill commits the changes in git and compares the health
check results from before and after, so you can see what the migration
fixed and what is left for you to decide. A second pass renames the old
capitalized folder names, e.g. Wiki/, to lowercase and repairs every link
the rename touches.

## When to use it

Use it once, when your wiki was built before the version 2 page format, or
when it still uses the old capitalized folder names.

## What it never does

The converter never deletes or rewrites your content lines. It only adds
and normalizes page properties. Where a quality rating is missing, it never
guesses one. It marks the page for your review instead, because ratings are
a human call. It also refuses to run while the wiki has uncommitted
changes, so a bad run can always be undone with git.
