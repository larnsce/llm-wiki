# Before & After: Wiki Page Synthesis

This example shows how `llm-wiki ingest` transforms a raw placeholder page into a
well-structured, cross-referenced wiki page.

---

## Example: "Newsletter" topic

### BEFORE (placeholder page, no synthesis)

#### Logseq format

```markdown
- type:: knowledge
- created:: 2025-03-10
- updated:: 2025-03-10
- ## Newsletter
	- We send a newsletter.
```

#### Obsidian format

```markdown
---
type: knowledge
created: 2025-03-10
updated: 2025-03-10
---

# Newsletter

We send a newsletter.
```

---

### AFTER (synthesized by `llm-wiki ingest`)

#### Logseq format

```markdown
- type:: knowledge
- domain:: content
- created:: 2025-03-10
- updated:: 2025-06-15
- confidence:: high
- ## Newsletter
	- Monthly email newsletter sent to subscribers with project updates, technical insights, and community highlights.
- ## Workflow
	- Draft content in [[wiki/content/writing-process]] using the standard template
	- Review with at least one team member before sending
	- Send via the newsletter platform on the first Monday of each month
	- Archive the issue in [[wiki/content/newsletter-archive]]
- ## Audience
	- Primary: existing clients and partners
	- Secondary: developer community and tech leads
	- Current subscriber count tracked in [[wiki/business/metrics]]
- ## Tools
	- [[wiki/tech/email-platform]] -- delivery and analytics
	- [[wiki/tech/markdown-editor]] -- drafting and formatting
- ## Lessons Learned
	- Plain-text subject lines outperform emoji-heavy ones (tested Q1 2025)
	- Sending on Monday mornings yields ~20% higher open rates than Fridays
	- See [[wiki/reference/newsletter-gotchas]] for common pitfalls
```

#### Obsidian format

```markdown
---
type: knowledge
domain: content
created: 2025-03-10
updated: 2025-06-15
confidence: high
---

# Newsletter

Monthly email newsletter sent to subscribers with project updates, technical
insights, and community highlights.

## Workflow

- Draft content in [[wiki/content/writing-process]] using the standard template
- Review with at least one team member before sending
- Send via the newsletter platform on the first Monday of each month
- Archive the issue in [[wiki/content/newsletter-archive]]

## Audience

- Primary: existing clients and partners
- Secondary: developer community and tech leads
- Current subscriber count tracked in [[wiki/business/metrics]]

## Tools

- [[wiki/tech/email-platform]] -- delivery and analytics
- [[wiki/tech/markdown-editor]] -- drafting and formatting

## Lessons Learned

- Plain-text subject lines outperform emoji-heavy ones (tested Q1 2025)
- Sending on Monday mornings yields ~20% higher open rates than Fridays
- See [[wiki/reference/newsletter-gotchas]] for common pitfalls
```

---

## What changed?

| Aspect              | Before                | After                                    |
|---------------------|-----------------------|------------------------------------------|
| Properties          | Missing `domain`, `confidence` | All required properties present  |
| Content depth       | 1 vague sentence      | Workflow, audience, tools, lessons        |
| Cross-references    | 0 links               | 6 `[[wiki/...]]` links                   |
| Actionable insight  | None                  | Timing tips, testing results              |
| Hub page updated    | No                    | Yes (`[[wiki/content]]` now lists this page) |
