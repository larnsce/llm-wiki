---
title: wiki-glossary in plain language
description: Collects your open terminology questions into one review table and writes only the rows you confirm. You decide every rule.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-glossary skill in plain language. The model itself runs
the [standard version](../skills/wiki-glossary/SKILL.md), which the site
publishes word for word.
:::

## What it does

wiki-glossary maintains a personal glossary for writing in two languages,
English and German. While you write, you mark a term you were unsure about
with a #glossary-todo tag and move on. The skill later collects all open
captures into one review table, with a suggested translation rule for each
term. You decide every rule. The skill writes only the rows you confirm,
exactly as you confirmed them, onto the glossary page you chose. It can
also pull matching entries from an external terminology file onto a staging
page for you to decide later, and it can load your decided glossary pages
as context for a writing session, so a draft follows your conventions.

## When to use it

Use it when captures have piled up and you want to decide them in one
sitting, when you want to import terms from a terminology file, or when a
draft should follow your decided terminology.

## What it never does

The tool never decides a translation rule, because the rules are the
product and they are yours. An import never fills in a rule. The skill
writes only under the glossary folder, and the other wiki skills never
write there.
