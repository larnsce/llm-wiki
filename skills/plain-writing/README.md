# plain-writing (vendored)

A writing-style skill by Shreya Shankar, vendored from
https://github.com/shreyashankar/plain-writing-skill
(commit `25a5393`, 2026-07-16, MIT license; see `LICENSE`).

It makes the agent write prose in a plain style: simple everyday words,
complete sentences, no dashes, no jargon, no analogies, no filler. The rules
live in `SKILL.md`; `assets/revision_template.html` is the template for the
optional HTML diff view the skill builds when it revises a text.

The skill is not part of the wiki suite and has no dependency on
`wiki-core`; it is installed alongside the `wiki-*` skills by `setup.sh`
because wiki pages are prose. To update it, re-copy `SKILL.md`,
`assets/revision_template.html`, and `LICENSE` from upstream and bump the
commit reference above.
