# Supersede marking convention

Spec: openspec/specs/update.md REQ-953; block syntax per
openspec/specs/citations.md REQ-900 and the tool modes in
[formats](../../wiki-core/references/formats.md)

When new information contradicts an existing cited claim, the old claim is
never silently deleted (REQ-953). It stays on the page, struck through, with a
`superseded::` property naming the date and pointing at the replacement. The
replacement claim is a new block with its own `cite::`. Git holds the literal
prior text; the page holds the legible belief history.

## The marking

- Strike through the old claim text (`~~...~~`); do not otherwise reword it.
- Attach `superseded:: YYYY-MM-DD -- <pointer>` to the old claim block, in the
  same block-property shape as `cite::` (Logseq: block property line; Obsidian:
  indented child bullet). The pointer is one short phrase locating the
  replacement, e.g. `replaced by the next block`.
- The old claim KEEPS its original `cite::`: the record of what supported the
  old belief is part of the history.
- Place the replacement claim directly after the superseded block whenever the
  page structure allows, so the pointer stays trivial to follow.

## Logseq mode

```
- ~~Solar capacity grew 12% in 2024.~~
  cite:: ingested/papers/old-report.md#p3
  superseded:: 2026-07-04 -- replaced by the next block
- Solar capacity grew 24% in 2024.
  cite:: ingested/papers/iea-2024.md#p12
```

## Obsidian mode

```
- ~~Solar capacity grew 12% in 2024.~~
  - cite:: ingested/papers/old-report.md#p3
  - superseded:: 2026-07-04 -- replaced by the next block
- Solar capacity grew 24% in 2024.
  - cite:: ingested/papers/iea-2024.md#p12
```

## Rules

- `superseded::` uses one grep shape in both tool modes, mirroring `cite::`
  (citations.md acceptance criteria).
- The date is ISO 8601, zero-padded (schema REQ-560/561).
- Superseded claims do NOT count toward the page's `reliability::` roll-up;
  only live claims do (schema REQ-586). Their sources normally remain in the
  page's `source-file::` union because the superseded block still cites them
  (citations.md REQ-904 counts every `cite::` on the page).
- A superseded claim is not an audit failure: wiki-audit verifies live claims;
  a struck-through block with `superseded::` is skipped as marked history.
- Only wiki-update may apply this marking; every other write path is
  append-only (update.md REQ-950, ingest.md REQ-032).
