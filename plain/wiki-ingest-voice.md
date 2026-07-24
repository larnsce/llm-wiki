---
title: wiki-ingest-voice in plain language
description: Turns your recorded voice notes into short journal summaries and offers wiki updates one at a time, with strict protection for what you said about other people.
---

::: {.callout-note}
A skill is a set of instructions the model follows. The page you are reading
explains the wiki-ingest-voice skill in plain language. The model itself
runs the [standard version](../skills/wiki-ingest-voice/SKILL.md), which
the site publishes word for word.
:::

## What it does

wiki-ingest-voice processes your recorded voice notes. It belongs to the
personal tier, so a default install does not include it. The skill first
transcribes any audio waiting in the inbox into the archive database. It
then takes each transcript that has not been processed yet and drafts a
short summary of it, two to four lines, for today's journal page. When a
note contains something that belongs on a wiki page, the skill offers that
update separately and shows you the exact sentences it would write. Each
offer needs its own yes. A voice note only records what you said, not what
is true, so claims from voice notes enter the wiki with the lowest
trust rating until a real source confirms them.

## When to use it

Use it to drain the queue after you have recorded notes on your phone,
e.g., once a day.

## What it never does

The skill never runs unattended, and it has no automatic mode. Anything you
said about another person's health, family, grades, conflicts, or
performance is never copied to a wiki page, even if you answer yes. It
stays in the transcript. The stored transcripts are never edited or
deleted. The only change the skill makes to the database is marking a note
as processed, and it does so only after the writes are safely committed.
