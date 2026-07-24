type:: agent-log
paper:: cbs-adoption
entries:: 8
updated:: 2026-07-22

- # Agent-use log — cbs-adoption
- Structured record of every agent interaction that touched this paper's namespace. One entry per invocation, append-only. The journal AI-disclosure statement is generated from this log rather than reconstructed from memory.
	- | Date | Skill | Model tier | Sources touched | Pages written | Human confirmations |
	  |------|-------|-----------|-----------------|---------------|---------------------|
	  | 2026-06-02 | `wiki-paper` | standard | — | hub scaffold | scaffold approved |
	  | 2026-06-11 | `wiki-ingest` | standard | Tilley et al. 2024 (PDF) | [[notes/literature/@tilley2024]], [[wiki/concept/container-based-sanitation]] | 2 page writes confirmed |
	  | 2026-06-17 | `wiki-ingest` | standard | Russel et al. 2023 (DOI) | [[notes/literature/@russel2023]] | 1 page write confirmed |
	  | 2026-07-03 | `wiki-query` | fast | hub + 4 linked pages | — (read-only) | — |
	  | 2026-07-08 | `wiki-ingest` | standard | WHO 2025 guidelines (PDF) | [[notes/literature/@who2025]] | 1 page write confirmed |
	  | 2026-07-15 | `wiki-update` | standard | WHO 2025 (cited) | revision on [[wiki/concept/container-based-sanitation]] — superseded claim kept legible | diff approved |
	  | 2026-07-21 | `wiki-audit` | thorough | 3 cited sources | audit notes on [[wiki/concept/container-based-sanitation]] | fix declined, flag kept |
	  | 2026-07-22 | `wiki-query` | fast | hub + 6 linked pages | — (read-only, drafting session) | — |
- ## Disclosure statement (generated)
- > Portions of the literature synthesis for this manuscript were prepared with an LLM agent (Claude Code) operating the llm-wiki skill suite. The agent ingested 3 sources and wrote 5 wiki pages under human confirmation, made one sanctioned source-backed revision (the superseded claim remains legible on the page), and ran two read-only query sessions and one citation audit. All agent interactions are logged above; raw markdown of every touched page is published on this site. No agent-generated text was pasted into the manuscript without review.
