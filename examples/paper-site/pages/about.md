type:: meta
updated:: 2026-07-21

- # About this site
- This is a **minimal example** of a public paper wiki: the open side product of writing a scientific article, published as plain markdown files plus one static `index.html` viewer. It is fixture content for [llm-wiki](https://github.com/larnsce/llm-wiki) issues #145–#148 — every fact on it is fictional.
- ## How it works
	- The server hosts nothing but raw `.md` files and one `index.html`.
	- Everything after `#/` in the URL names a real markdown file. The viewer fetches it and renders it client-side. No build step, no framework.
	- The raw file behind any page is available at the same path: humans read the rendered page, agents fetch the identical markdown.
	- `[[wikilinks]]` are rewritten to hash routes, so the wiki's internal graph survives publication.
- ## What gets published
- The pages here are the subgraph reachable from the paper hub — literature notes, concept pages, data pages, and the [[agent-log|agent-use log]] — collected by the export walk, gated by a secret scan, with personal tiers excluded. The working wiki behind it is larger and private; this site is a derived view.
- ## Two flavors, one viewer
- The wiki suite supports Obsidian serialization (flat markdown + YAML frontmatter, used by most pages here) and Logseq serialization (outline blocks + `property::` lines). The viewer renders both — compare the [[index|paper hub]] with its [[pages/wiki___papers___cbs-adoption|Logseq-flavor twin]].
