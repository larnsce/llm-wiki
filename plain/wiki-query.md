---
title: wiki-query in plain language
description: Answers a question from what the wiki knows, names its sources, and says so plainly when the wiki has no answer.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-query skill in plain language. The model itself runs the
[standard version](../skills/wiki-query/SKILL.md), which the site publishes
word for word.
:::

## What it does

wiki-query answers a question from what the wiki already knows. It does not
read every page. Each section of the wiki has a hub page with one routing
line per page, and the skill reads those lines first to pick the three to
five pages most likely to hold the answer. It reads only the pages it
picked and then writes an answer that names its sources. The answer always
comes in two versions. The first is precise and keeps the technical
vocabulary. The second, under the heading "In plain terms", carries the same
facts and the same warnings in everyday words. The skill also notes which
pages it read in an access log, and the maintenance skill later uses that
log to tell busy pages from cold ones.

The skill has a second mode for starting a work session. With the --prime
option you describe what you are about to work on instead of asking a
question, and the skill returns a short briefing: the few pages that bear
on the work, pointers to further candidates it did not open, each read
page's linked neighbors, and any standing rules from memory. If you give
no description, it derives one from the conversation and shows you exactly
what it primed on. The briefing reads at most three pages, changes
nothing, and never runs by itself; you invoke it when you want it.

## When to use it

Use it when you want to know what the wiki says about a topic, e.g., "what
do we know about deployment" or "who works on the parser". Use --prime at
the start of a work session, before you have a precise question.

## What it never does

The skill never invents an answer. If the wiki holds nothing on the topic,
it says so plainly and offers to save what you tell it instead. Answering
is a read activity, so apart from the access log line it writes to the wiki
only when you ask it to.
