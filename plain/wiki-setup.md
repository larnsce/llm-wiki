---
title: wiki-setup in plain language
description: Creates a new wiki or upgrades an old one, and never overwrites your content.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-setup skill in plain language. The model itself runs the
[standard version](../skills/wiki-setup/SKILL.md), which the site publishes
word for word.
:::

## What it does

wiki-setup takes you from nothing to a working wiki, or from an old install
to the current one. It finds your configuration file and checks it. It
reports every problem it finds, together with a suggested fix. If no wiki
exists yet, it asks a few questions about which tool you use, where the wiki
should live, and which sections it should have, and then it creates the
starting pages. It can also write a small pointer file in your home folder,
so the other skills find the wiki from any directory. For an old wiki it
upgrades the Schema page by adding the sections that are missing.

## When to use it

Use it when you set up a wiki for the first time, and when an existing wiki
needs repair or an upgrade. It also recognizes the old version 1 install and
offers to remove the outdated command file.

## What it never does

The skill never overwrites your content. When it creates starting pages, it
skips every file that already exists. The Schema upgrade only appends missing
sections and leaves the sections you wrote untouched. Every step that removes
or replaces something asks you first.
