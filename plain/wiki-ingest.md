---
title: wiki-ingest in plain language
description: Reads a source, shows you a plan, and writes what it learned onto wiki pages with a note saying where each fact came from.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-ingest skill in plain language. The model itself runs the
[standard version](../skills/wiki-ingest/SKILL.md), which the site publishes
word for word.
:::

## What it does

wiki-ingest is the main way knowledge enters the wiki. You give it a source,
which can be a web address, a file, pasted text, or the queue of files
waiting in the raw folder. The skill reads the source and works out which
facts, people, and decisions it contains. It then plans which wiki pages to
create or update. Before it writes anything, it shows you one review table
for the whole run and asks what to emphasize, skip, or keep out of the wiki.
Only after you answer does it write. Every factual statement it writes
carries a note saying which source backs it, so you can check the fact later.
When it is done, it moves the processed file into the archive folder and
records the whole run in one git commit.

## When to use it

Use it whenever you have something new the wiki should know, e.g., an
article you read, a paper, a meeting note, or the files you collected during
the week.

## What it never does

The skill never rewrites existing text on a page. It only adds new blocks,
so nothing you wrote can be lost. It never writes before you have answered
the review table, unless you passed the --auto option to drain the queue
without questions, and even then the safety checks still apply. A file that
contains a password or another secret is never archived. The skill stops and
asks you to redact the secret first.
