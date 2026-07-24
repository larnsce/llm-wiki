---
title: wiki-audit in plain language
description: Fact-checks one page against the sources it cites and reports which claims are supported, doubtful, or missing their source.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-audit skill in plain language. The model itself runs the
[standard version](../skills/wiki-audit/SKILL.md), which the site publishes
word for word.
:::

## What it does

wiki-audit fact-checks one page against the sources it cites. It first
builds a map from every claim on the page to the source the claim cites.
Each cited source is then checked by its own separate helper. A helper sees
only its own source and the claims citing it, never the rest of the page,
so one source's verdict cannot influence another's. Every claim gets one of
four verdicts. Supported means the source says what the claim says. Partial
means the source covers only part of it. Unsupported means the source does
not back the claim. Source-missing means the cited file cannot be found.
The report lists the verdicts, the claims that cite nothing at all, and the
changes the skill would suggest to the page's trust ratings.

## When to use it

Use it when a page needs to be trustworthy, e.g., before you rely on it for
a decision, or after importing a large batch of notes.

## What it never does

By default the skill writes nothing. With the --fix option it updates the
page's ratings and moves doubtful claims into a review section, and only
after you confirm. It never rewrites the text of a claim. Correcting a
wrong claim is the job of wiki-update, the one skill allowed to change
existing content.
