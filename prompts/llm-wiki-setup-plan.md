# Personal Knowledge System — Setup Plan & Summary

**Hardware decision:** current phone + MacBook Pro. No new purchases. Server question deferred until the pipeline proves itself (revisit if the laptop's intermittency starts dropping notes).

---

## 1. Architecture Summary

Three layers, one rule: **markdown is for what a human writes; SQLite is for what a machine accumulates.**

| Layer | Lives in | Contents | In git? |
|---|---|---|---|
| **Wiki (synthesis)** | Logseq vault — `wiki/` | Curated entity pages: people who matter (~50–150, not everyone), projects, orgs. L1/L2 cache architecture per llm-wiki. | Yes |
| **Working notes** | Logseq vault — PARA + journals | Daily journal, active project notes, TODOs, voice-note summaries. | Yes |
| **index.db** | Outside vault, gitignored | Derived from vault: `people`, `meetings`, `meeting_attendees` tables + FTS5. **Disposable — rebuilt from markdown anytime.** | No |
| **archive.db** | Outside vault, outside git, backed up | Raw personal corpus: emails, calendar, contacts, voice transcripts. **Source data — irreplaceable.** | No (backed up separately) |

Key principles settled during design:

- **SQLite over DuckDB/Parquet** — workload is point lookups + FTS + incremental appends (OLTP-shaped); FTS5 is decisive; format has archival-grade longevity. DuckDB can attach the SQLite file later for analytics if ever needed.
- **Never merge index.db and archive.db** — one is disposable, one is not; separate files make the distinction impossible to get wrong.
- **Emails: keep as archive, don't ingest wholesale.** Lazy ingestion — pull a person's threads through the pipeline only when a query reveals a gap.
- **People pages:** synthesized wiki entities only for active relationships. Completeness lives in archive.db; the wiki hub index stays small so Stage-1 routing keeps working.
- **Meetings:** dated records (notes-layer or archive.db rows), feeding synthesized updates onto people/project pages with provenance.
- **Provenance:** every wiki update generated from a source records where it came from (source-file:: property or a `page_updates → sources` row once raw/ingested moves to SQLite).
- **Dogsheep importers** (google-takeout-to-sqlite etc.) instead of hand-written email/calendar importers. Watch Simon Willison's Datasette Agent / "Claw" work — same problem, solved in public.

---

## 2. Voice Pipeline (MacBook Pro)

```
Phone recorder ──sync──▶ ~/voice-inbox/ ──watcher──▶ whisper.cpp
                                                        │
                                              archive.db (voice_notes)
                                                        │
                                            Claude Code `ingest-voice`
                                                   │            │
                                        journal summary    wiki page updates
                                        (Logseq, linked)   (with provenance)
```

- **Capture (pick per phone OS):**
  - iPhone: Voice Memos + Shortcuts automation → iCloud Drive folder.
  - Android: any recorder (e.g. Fossify) + Syncthing → MacBook folder.
- **Transcribe:** whisper.cpp with `large-v3-turbo` (Metal — faster than real time on Apple Silicon). Pass a context prompt of active people/project names so proper nouns transcribe correctly.
- **Archive:** `voice_notes(id, recorded_at, duration, transcript, audio_path, processed)`. Audio moved to cold storage after transcription.
- **Ingest (Claude Code skill):** per unprocessed note — 2–4 line summary onto today's journal page with `[[links]]` + provenance id; substantive content routed to wiki pages; TODOs extracted; row marked processed.
- **Scheduling on a laptop:** nightly launchd job, **pull-based and idempotent** — if the lid was closed, notes queue in the sync folder and the next run drains the backlog. Nothing is lost to intermittency; worst case is delay.
- **Keep transcription and synthesis as separate steps** — transcription is deterministic and free to re-run; synthesis costs Claude tokens.

---

## 3. Setup Plan (phased, ~20–30 h total over 4–8 weeks)

### Phase 0 — Prove the loop (weekend 1, ~4–6 h)
- [ ] Install whisper.cpp, download large-v3-turbo, transcribe one test memo (1 h)
- [ ] Phone → Mac sync of recordings (Shortcuts/iCloud or Syncthing) (1–2 h)
- [ ] Create archive.db with `voice_notes` table; manual insert script (1–2 h)
- [ ] Manually run one Claude Code ingest: transcript → journal summary (1 h)
- **Exit test:** speak a memo on the phone, read a summary in tomorrow's journal.

### Phase 1 — Automate (week 2, ~5–8 h)
- [ ] Watcher script (launchd) → transcribe → insert → archive audio (3–5 h)
- [ ] `ingest-voice` skill: SKILL.md + prompt, provenance property, TODO extraction (2–3 h)
- [ ] Start the **daily habit:** 5–10 min morning review of journal summaries + pending wiki changes

### Phase 2 — Prompt iteration (weeks 2–4, ~2–4 h spread)
- [ ] 2–3 revision passes on the summarization prompt against real rambling transcripts
- [ ] Tune what goes to journal vs. wiki pages vs. gets dropped

### Phase 3 — Archive layer (weeks 3–5, ~4–8 h + Takeout wait)
- [ ] Request Google Takeout early (multi-day wait)
- [ ] google-takeout-to-sqlite → email into archive.db; add FTS5
- [ ] Calendar (.ics) → `meetings` / `meeting_attendees`; contacts → `people` seed
- [ ] Begin alias resolution table — **do this lazily**, per person, as they surface (5–15 h over months; do not front-load)

### Phase 4 — Index + query layer (weeks 5–6, ~3–5 h)
- [ ] `rebuild-index` script: vault → index.db (people, meetings, properties)
- [ ] `query` skill: Claude routes aggregate/temporal/full-text questions to SQL, entity lookups to wiki pages
- [ ] Hook rebuild into ingest workflow or pre-commit

### Phase 5 — Optional refactor (later, ~5–10 h)
- [ ] After v2.2 lands: migrate `raw/`/`ingested/` provenance into SQLite (`sources`, `page_updates` tables)
- [ ] Pilot the people/meetings expansion with ~20 people + one year of meetings **before** committing the full corpus; check that hub routing holds

### Deliberately deferred
- Server purchase (Mac mini / Linux box) — only if laptop intermittency hurts
- New phone — pipeline is phone-agnostic; a future de-Googled phone (e.g. Punkt MC03) only changes the capture leg (Syncthing instead of iCloud)
- OpenClaw / Datasette Agent — reassess once the basic loop is habitual

---

## 4. Maintenance Budget

| Item | Cost |
|---|---|
| Plumbing (sync hiccups, dependency updates, importer re-runs) | 1–2 h/month |
| Prompt/skill tweaks | ~1 h/month, declining |
| Alias resolution (lazy, per person) | minutes/week |
| Backups: archive.db nightly off-machine (Time Machine + one cloud/offsite copy); vault via git | set up once, verify quarterly |
| **Daily review habit** | **5–10 min/morning — this is the product working, and the thing that decides whether the system lives** |

## 5. Risks & Guardrails

- **Scale mismatch:** wiki tuned for 50–200 pages. Guardrail: completeness in archive.db, curation in wiki; pilot before bulk expansion.
- **Privacy:** emails/transcripts contain other people's PII. Guardrail: archive.db never enters git; vault repo stays private; credential lint on anything promoted to pages.
- **Data loss:** archive.db is irreplaceable. Guardrail: keep original exports (Takeout, .ics) so it's re-derivable; automated backups from day one.
- **Abandonment:** the real failure mode. Guardrail: Phase 0 exit test before any further investment; three weeks of habit before expanding scope.
