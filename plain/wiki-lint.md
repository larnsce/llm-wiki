---
title: wiki-lint in plain language
description: Checks the health of the wiki, reports every finding with a suggested fix, and changes nothing without your confirmation.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-lint skill in plain language. The model itself runs the
[standard version](../skills/wiki-lint/SKILL.md), which the site publishes
word for word.
:::

## What it does

wiki-lint checks the health of the wiki in two layers. The first layer is
mechanical. Scripts check the rules a program can verify, such as missing
page properties, malformed dates, broken source links, and leaked
credentials. The second layer needs judgment, so the model reviews it. It
looks for pages that claim to be current but have not been touched in
months, for wiki content that duplicates the separate memory files, and for
weak page names and routing descriptions. All findings land in one report,
grouped from critical to informational, each with the page, the broken
rule, and a suggested fix.

## When to use it

Use it when you want to know what is wrong with the wiki, and as a periodic
cleanup, e.g., after a large ingest session.

## What it never does

By default the skill only reports and modifies nothing. With the --fix
option it proposes a concrete fix per finding and applies it only after you
confirm. A leaked credential is never fixed automatically. The skill asks
you to move it out of the wiki yourself, because deciding where a secret
belongs is not the tool's call.
