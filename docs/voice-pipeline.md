# Voice capture and transcription pipeline (macOS)

Maintainer-run plumbing for the personal pipeline (v3.0, Phase 0-1 of
[`prompts/llm-wiki-setup-plan.md`](../prompts/llm-wiki-setup-plan.md)): get a
spoken memo from the phone into `archive.db` as a transcribed `voice_notes`
row, ready for ingestion. Everything here runs on one MacBook Pro and is
copy-paste; the repo documents it but does not ship or test it (premortem
revision 12 in
[`docs/roadmap-glossary-personal-pipeline.md`](roadmap-glossary-personal-pipeline.md):
the repo stays a generic tool).

> **Scope.** This guide covers capture, sync, transcription, and storage.
> The synthesis step (transcript to journal summary and wiki updates) is the
> `wiki-ingest-voice` skill, tracked in
> [#57](https://github.com/larnsce/llm-wiki/issues/57) and specified in
> [`openspec/specs/ingest.md`](../openspec/specs/ingest.md) (Voice Sources,
> REQ-080..087). The skill ships with the personal tier
> (`setup.sh --with-personal`, setup REQ-803); the manual Claude session in
> section 8 remains the Phase 0 exit test and the fallback when the skill
> is not installed. The storage contract this guide implements is
> [`openspec/specs/storage.md`](../openspec/specs/storage.md)
> (REQ-1100..1141); where this guide and the spec disagree, the spec wins.

## 1. What this is

The whole loop:

```
Phone recorder --sync--> ~/voice-inbox/ --nightly watcher--> whisper.cpp
                                                                 |
                                                       archive.db (voice_notes)
                                                                 |
                                              /wiki-ingest-voice skill (or a
                                              manual Claude run, section 8)
                                                                 |
                                                      journal summary (Logseq)
```

One split shapes every step: **transcription is deterministic and free to
re-run; synthesis costs tokens.** Transcription (audio to text) happens on
your machine with whisper.cpp and can be repeated at zero cost if anything
goes wrong. Synthesis (text to journal summary and wiki updates) is a Claude
run. Keep them as separate steps, always: the transcript lands in
`archive.db` first, and synthesis starts from the stored transcript
(ingest REQ-080).

Sections below are in adoption order. Do them top to bottom; in particular,
do section 2 before any real memo exists.

## 2. Before anything: archive.db durability

archive.db is source data and irreplaceable (storage REQ-1101). Per
storage REQ-1120, the nightly off-machine copy must exist BEFORE any real
(non-test) data enters the database. So backups come first, capture second.

> **Warning: archive.db is gitignored AND irreplaceable.** It is outside
> git by construction (storage REQ-1103), which means git cannot save it and
> ignored-file cleanup can destroy it. Per storage REQ-1122, add a line to
> your vault's CLAUDE.md (or equivalent agent guidance) forbidding
> `git clean -xfd` and any command that removes ignored or untracked files
> inside the vault or the database location. Agents are the likeliest
> executor of the deletion; the ban has to live where agents read it.
> Suggested wording:
>
> ```
> Never run `git clean -xfd`, `git clean -xdf`, or any other command that
> deletes ignored or untracked files anywhere in this vault or under
> ~/archive/. archive.db and index.db are kept out of git on purpose;
> deleting archive.db destroys irreplaceable source data.
> ```

### 2.1 Create archive.db

Pick a home outside the vault's git tree (storage REQ-1103). This guide uses
`~/archive/`:

```bash
mkdir -p ~/archive
sqlite3 ~/archive/archive.db < /dev/null   # creates an empty database file
```

The `voice_notes` table is created in section 5.

### 2.2 Nightly off-machine copy

"Off-machine" means a target that survives loss of the MacBook
(storage REQ-1120): Time Machine plus one cloud or offsite copy. Time Machine
covers `~/archive/` already if the disk is not excluded; verify with:

```bash
tmutil isexcluded ~/archive
```

For the cloud leg, the snippet below snapshots the database safely (SQLite's
`.backup`, consistent even while a writer is active) and pushes the snapshot
with [rclone](https://rclone.org) (`brew install rclone`, then
`rclone config` once for your provider). Any offsite target works; substitute
your own copy command if you prefer.

Save as `~/bin/archive-backup.sh` and `chmod +x` it:

```bash
#!/bin/bash
set -euo pipefail

DB="$HOME/archive/archive.db"
SNAPDIR="$HOME/archive/backups"
SNAP="$SNAPDIR/archive-$(date +%F).db"

mkdir -p "$SNAPDIR"
sqlite3 "$DB" ".backup '$SNAP'"
rclone copy "$SNAP" remote:archive-backups/

# keep the last 14 local snapshots
ls -t "$SNAPDIR"/archive-*.db | tail -n +15 | while read -r old; do
  rm -- "$old"
done
```

Schedule it nightly with launchd. Save as
`~/Library/LaunchAgents/local.archive-backup.plist`, replacing `YOU` with
your username (launchd does not expand `$HOME` in paths):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.archive-backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/YOU/bin/archive-backup.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/YOU/archive/backup.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOU/archive/backup.log</string>
</dict>
</plist>
```

Load it and run it once now:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.archive-backup.plist
launchctl kickstart -k gui/$(id -u)/local.archive-backup
```

If you prefer cron over launchd, the equivalent crontab line is
`0 3 * * * /bin/bash $HOME/bin/archive-backup.sh >> $HOME/archive/backup.log 2>&1`;
note that cron jobs missed while the machine sleeps are skipped, while
launchd runs a missed `StartCalendarInterval` job once on wake. Prefer
launchd on a laptop.

### 2.3 Restore drill: run one NOW and record the date

A backup that has never been restored is a hypothesis, not a backup
(storage REQ-1121). Run the drill now, then quarterly:

```bash
mkdir -p /tmp/restore-drill
rclone copy remote:archive-backups/archive-$(date +%F).db /tmp/restore-drill/
sqlite3 /tmp/restore-drill/archive-$(date +%F).db "SELECT count(*) FROM voice_notes;"
sqlite3 ~/archive/archive.db "SELECT count(*) FROM voice_notes;"
```

The two counts must match (both zero is a valid first drill, once the table
from section 5 exists). Record the date and result in today's journal, per
REQ-1121. Do not insert a real voice note until one drill has passed.

## 3. whisper.cpp setup

[whisper.cpp](https://github.com/ggml-org/whisper.cpp) runs Whisper locally;
on Apple Silicon the Metal backend transcribes faster than real time.

### 3.1 Clone and build with Metal

Requires the Xcode Command Line Tools (`xcode-select --install`) and cmake
(`brew install cmake`):

```bash
mkdir -p ~/src
git clone https://github.com/ggml-org/whisper.cpp ~/src/whisper.cpp
cd ~/src/whisper.cpp
cmake -B build -DGGML_METAL=ON
cmake --build build -j --config Release
```

The binary lands at `~/src/whisper.cpp/build/bin/whisper-cli`.

### 3.2 Download large-v3-turbo

```bash
cd ~/src/whisper.cpp
sh ./models/download-ggml-model.sh large-v3-turbo
```

This fetches `models/ggml-large-v3-turbo.bin` (about 1.6 GB).

### 3.3 Transcribe one test file

whisper-cli wants 16 kHz mono WAV. Voice Memos and most phone recorders
produce `.m4a`; convert with `afconvert` (ships with macOS, no extra
install):

```bash
afconvert -f WAVE -d LEI16@16000 -c 1 test-memo.m4a /tmp/test-memo.wav
~/src/whisper.cpp/build/bin/whisper-cli \
  -m ~/src/whisper.cpp/models/ggml-large-v3-turbo.bin \
  -f /tmp/test-memo.wav --no-timestamps
```

Keep the test file; the troubleshooting check in section 9 reuses it.

### 3.4 The context-prompt trick

Whisper accepts a text prompt that biases decoding, and it is the difference
between "log seek" and "Logseq" in your transcripts. Pass the proper nouns
you actually say (active people, projects, tools) via `--prompt`:

```bash
~/src/whisper.cpp/build/bin/whisper-cli \
  -m ~/src/whisper.cpp/models/ggml-large-v3-turbo.bin \
  -f /tmp/test-memo.wav --no-timestamps \
  --prompt "Lars, Logseq, llm-wiki, whisper.cpp, Zotero, PARA, Syncthing"
```

Maintain the name list where the insert script reads it (section 5 keeps it
in a constant; edit it as projects and people change). Update it when
transcripts start mangling a name; that is the signal.

## 4. Phone to Mac sync

Goal: every memo you speak on the phone appears as an audio file in
`~/voice-inbox/` on the Mac, with no manual step per memo. Pick the path for
your phone OS.

### 4.1 iPhone: Voice Memos + Shortcuts + iCloud Drive

1. In the Files app on the phone, create a folder `voice-inbox` at the top
   level of iCloud Drive.
2. On the Mac, confirm iCloud Drive syncs full files: System Settings >
   your Apple ID > iCloud > Drive, and turn OFF "Optimize Mac Storage".
   With optimization on, files can be dataless stubs that the watcher
   cannot read.
3. On the Mac, link the synced folder to the expected path:

   ```bash
   ln -s "$HOME/Library/Mobile Documents/com~apple~CloudDocs/voice-inbox" "$HOME/voice-inbox"
   ```

4. On the phone, open Shortcuts > Automation > "+" > "Time of Day". Pick a
   time you are usually online (for example 21:00, daily) and set it to
   "Run Immediately" (not "Ask Before Running").
5. Add the Voice Memos search action (named "Find Recordings" or "Search
   Voice Memos" depending on iOS version) with the filter "Date Created is
   today".
6. Add a "Repeat with Each" over the results containing one "Save File"
   action: destination iCloud Drive > `voice-inbox`, "Ask Where to Save"
   off.
7. Test it: record a short memo, run the automation manually once from the
   Shortcuts app, and confirm the file appears in `~/voice-inbox/` on the
   Mac (allow a minute for iCloud to sync).

> **Gotcha: re-confirm after every iOS update.** iOS updates can disable
> personal automations or reset their permission prompts, and the failure is
> silent: memos keep recording, nothing syncs. After every iOS update, open
> Shortcuts > Automation, confirm the automation is still enabled and set to
> run immediately, and run it once manually. The weekly canary memo
> (section 7) exists to catch the times you forget.

### 4.2 Android: Fossify Voice Recorder + Syncthing

1. Install [Fossify Voice Recorder](https://f-droid.org/packages/org.fossify.voicerecorder/)
   (or any recorder that writes files to a folder you can pick) and note its
   recordings folder.
2. Install [Syncthing](https://syncthing.net) on the phone (F-Droid) and on
   the Mac:

   ```bash
   brew install syncthing
   brew services start syncthing
   ```

3. In the Syncthing web UI on the Mac (http://localhost:8384), pair the two
   devices, then share the phone's recordings folder to the Mac with local
   path `~/voice-inbox` (create the directory first: `mkdir -p ~/voice-inbox`).
   Set the share to "Send Only" on the phone side.
4. Test it: record a memo and confirm the file appears in `~/voice-inbox/`.

## 5. archive.db insert

### 5.1 The voice_notes table

The schema is normative in storage REQ-1110/1111 (six columns, exactly).
As DDL:

```sql
CREATE TABLE IF NOT EXISTS voice_notes (
    id          INTEGER PRIMARY KEY,  -- provenance id: archive.db:voice_notes/<id>
    recorded_at TEXT,                 -- ISO 8601
    duration    REAL,                 -- seconds
    transcript  TEXT,                 -- the full transcript (the ingest input)
    audio_path  TEXT,                 -- audio file path (cold storage after transcription)
    processed   INTEGER DEFAULT 0     -- 0/1, lifecycle owned by ingest REQ-080
);
```

Create it:

```bash
sqlite3 ~/archive/archive.db "CREATE TABLE IF NOT EXISTS voice_notes (
    id          INTEGER PRIMARY KEY,
    recorded_at TEXT,
    duration    REAL,
    transcript  TEXT,
    audio_path  TEXT,
    processed   INTEGER DEFAULT 0
);"
```

Rows are append-only: captured fields are never edited or deleted, and the
only sanctioned mutation is the `processed` flag (storage REQ-1110, lifecycle
per ingest REQ-080).

### 5.2 The insert script

One script does the deterministic leg for one file: transcribe, insert the
row, move the audio to cold storage. python3 stdlib only, plus the macOS
built-ins `afconvert`/`afinfo` and the whisper-cli binary from section 3.

Save as `~/bin/voice_note_insert.py`:

```python
#!/usr/bin/env python3
"""Transcribe ONE audio file, insert a voice_notes row, move audio to cold storage.

Usage: python3 voice_note_insert.py /path/to/memo.m4a
Idempotent: if a row for this file's cold-storage path already exists,
no second row is inserted.
"""
import datetime
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

DB = pathlib.Path.home() / "archive" / "archive.db"
COLD = pathlib.Path.home() / "archive" / "voice-audio"
WHISPER = pathlib.Path.home() / "src" / "whisper.cpp"
MODEL = WHISPER / "models" / "ggml-large-v3-turbo.bin"
# The context prompt (section 3.4): active people, projects, tools.
CONTEXT_PROMPT = "Lars, Logseq, llm-wiki, whisper.cpp, Zotero, PARA, Syncthing"


def duration_seconds(path):
    out = subprocess.run(["afinfo", str(path)], capture_output=True,
                         text=True, check=True).stdout
    for line in out.splitlines():
        if "estimated duration" in line:
            return round(float(line.split(":")[1].split()[0]), 2)
    return 0.0


def transcribe(path):
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "audio.wav"
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000",
                        "-c", "1", str(path), str(wav)], check=True)
        result = subprocess.run(
            [str(WHISPER / "build" / "bin" / "whisper-cli"),
             "-m", str(MODEL), "-f", str(wav),
             "--no-timestamps", "--prompt", CONTEXT_PROMPT],
            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main():
    src = pathlib.Path(sys.argv[1]).expanduser()
    COLD.mkdir(parents=True, exist_ok=True)
    dest = COLD / src.name
    con = sqlite3.connect(DB)
    try:
        row = con.execute("SELECT id FROM voice_notes WHERE audio_path = ?",
                          (str(dest),)).fetchone()
        if row:
            # A previous run inserted the row but died before the move:
            # finish the move, insert nothing.
            shutil.move(str(src), str(dest))
            print(f"row {row[0]} already exists for {dest.name}; audio moved")
            return
        recorded_at = datetime.datetime.fromtimestamp(
            src.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        dur = duration_seconds(src)
        transcript = transcribe(src)
        cur = con.execute(
            "INSERT INTO voice_notes"
            " (recorded_at, duration, transcript, audio_path, processed)"
            " VALUES (?, ?, ?, ?, 0)",
            (recorded_at, dur, transcript, str(dest)))
        con.commit()
        shutil.move(str(src), str(dest))
        print(f"voice_notes/{cur.lastrowid}: {dur}s, audio moved to cold storage")
    finally:
        con.close()


if __name__ == "__main__":
    main()
```

Run it by hand on one synced memo to prove the leg:

```bash
python3 ~/bin/voice_note_insert.py ~/voice-inbox/<some-memo>.m4a
sqlite3 ~/archive/archive.db "SELECT id, recorded_at, duration, substr(transcript, 1, 80) FROM voice_notes;"
```

The insert happens before the move, and the script checks for an existing
row by cold-storage path first, so a crash at any point is safe to re-run:
the file either stays in the inbox (retried next run) or the leftover move
is completed without a duplicate row.

## 6. The watcher (Phase 1)

Nightly, pull-based, idempotent: the script processes whatever is in
`~/voice-inbox/` and exits. If the lid was closed for three days, three
days of memos queue in the sync folder and the next run drains the whole
backlog. Nothing is lost to intermittency; the worst case is delay.

Save as `~/bin/voice-watcher.sh` and `chmod +x` it:

```bash
#!/bin/bash
set -euo pipefail

INBOX="$HOME/voice-inbox"
LOG="$HOME/archive/voice-watcher.log"

shopt -s nullglob
for f in "$INBOX"/*.m4a "$INBOX"/*.wav "$INBOX"/*.mp3; do
  echo "$(date '+%Y-%m-%dT%H:%M:%S') processing: $f" >> "$LOG"
  if python3 "$HOME/bin/voice_note_insert.py" "$f" >> "$LOG" 2>&1; then
    echo "$(date '+%Y-%m-%dT%H:%M:%S') done: $f" >> "$LOG"
  else
    echo "$(date '+%Y-%m-%dT%H:%M:%S') FAILED, left in inbox for next run: $f" >> "$LOG"
  fi
done
```

A failed file stays in the inbox and is retried on the next run; a processed
file has been moved to cold storage, so re-running the watcher is always
safe.

Schedule it with launchd. Save as
`~/Library/LaunchAgents/local.voice-watcher.plist`, replacing `YOU`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.voice-watcher</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/YOU/bin/voice-watcher.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>15</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/YOU/archive/voice-watcher.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOU/archive/voice-watcher.log</string>
</dict>
</plist>
```

Load it, then force one run to verify:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.voice-watcher.plist
launchctl kickstart -k gui/$(id -u)/local.voice-watcher
tail ~/archive/voice-watcher.log
```

launchd runs a missed `StartCalendarInterval` job once on the next wake, so
a closed lid at 02:15 delays the run rather than skipping it. The first run
may prompt for file access (Terminal or bash needing access to iCloud
Drive); grant it once and see section 9 for what happens when macOS resets
such permissions.

## 7. Tripwires

Both tripwires exist because this pipeline fails silently: a dead automation
records nothing anywhere. See storage REQ-1140/1141.

### 7.1 The dead-man status line

Per storage REQ-1140, every daily journal summary the voice skill (#57)
writes begins with a one-line pipeline status: newest inbox file age,
unprocessed `voice_notes` count, last index rebuild age (example in the
REQ). Silence becomes visible in the one place you already look every
morning.

When the skill is not installed, run the check manually once a week:

```bash
newest=$(ls -t "$HOME/voice-inbox" 2>/dev/null | head -n 1)
if [ -n "$newest" ]; then
  age_h=$(( ( $(date +%s) - $(stat -f %m "$HOME/voice-inbox/$newest") ) / 3600 ))
  echo "pipeline: inbox newest ${age_h}h ($newest)"
else
  echo "pipeline: inbox empty"
fi
sqlite3 "$HOME/archive/archive.db" \
  "SELECT 'unprocessed ' || count(*) FROM voice_notes WHERE processed = 0;"
echo "index rebuilt: n/a (index.db lands with P-4)"
```

Read it the way storage.md scenario 5 does: an old newest-file age with
nothing unprocessed means capture has stalled upstream, on the phone side.

### 7.2 The weekly canary memo

Per storage REQ-1141: once a week, speak one test memo on the phone
("canary, <today's date>") and expect it in tomorrow's journal (when the
skill is not installed: expect the transcribed row, checked with the query
below).

```bash
sqlite3 ~/archive/archive.db \
  "SELECT id, recorded_at FROM voice_notes WHERE transcript LIKE '%canary%' ORDER BY id DESC LIMIT 1;"
```

If the canary is absent, **check the phone-side leg FIRST**: it fails
invisibly, and Mac-side monitoring cannot see it. Is the audio file in
`~/voice-inbox/` (or already in `~/archive/voice-audio/`)? If the file never
arrived, the problem is the Shortcuts automation or Syncthing (section 9,
leg 1). Only if the file arrived and no row exists do you look at the
watcher and whisper.cpp (legs 2 and 3).

## 8. Phase 0 exit test

This was the merge gate for the `wiki-ingest-voice` skill (premortem
revision 3); the maintainer waived the gate on 2026-07-05 (recorded on
[#57](https://github.com/larnsce/llm-wiki/issues/57)) and the skill shipped
ahead of it. The test remains the recommended FIRST run of the voice loop:
it proves every leg with no automation you have not built yet, and step 1
(backup plus restore drill before any real note) still binds per storage
REQ-1120/1121.

1. Confirm section 2 is done: the nightly copy job exists, and one restore
   drill has passed and is recorded (storage REQ-1120/1121 forbid real data
   before this).
2. Speak a real memo on the phone (a sentence or two about an actual
   project, naming at least one person or project you track).
3. Confirm the audio file lands in `~/voice-inbox/` on the Mac.
4. Transcribe it and insert the row:
   `python3 ~/bin/voice_note_insert.py ~/voice-inbox/<file>`. Confirm the
   row with the sqlite3 query from section 5.2 and confirm the audio moved
   to `~/archive/voice-audio/`.
5. Run ONE manual Claude session following ingest REQ-080..087. Journal
   summary only in Phase 0. Concretely: give Claude the transcript and the
   row id; ask for a 2-4 line summary for today's journal page with
   `[[links]]` and the provenance id `archive.db:voice_notes/<id>`
   (ingest REQ-082/086); confirm interactively before anything is written
   (REQ-081); any line naming a person gets shown in full and confirmed
   individually (REQ-084); assessments of people (health, family, grades,
   conflicts, performance) stay in the transcript and are never promoted
   (REQ-085); TODOs in the transcript are offered for you to place, not
   auto-written (REQ-087). No wiki page is touched in this test (wiki
   writes are per-row opt-in anyway, REQ-083); do not mark the row
   processed until the journal write is committed (REQ-080).
6. The next morning, read the summary on yesterday's journal page as part
   of the daily review. That reading is the actual test: the loop produced
   something you used.
7. Record the result (date, what worked, what needed a retry) as a comment
   on [#57](https://github.com/larnsce/llm-wiki/issues/57).

Kill criterion (from the premortem): if this test has not passed within two
weekends of this guide landing, stop filing v3.0 issues; the plumbing does
not deserve a skill yet.

## 9. Troubleshooting: the three silent failure legs

Each leg fails without an error you would see. The canary memo (section 7.2)
tells you THAT something died; this table tells you WHERE.

| Leg | What kills it | One check |
|---|---|---|
| 1. Phone sync | iOS updates disable Shortcuts personal automations or reset their permissions (Syncthing: battery optimization kills the background sync) | Speak a memo, run the automation manually once, then on the Mac: `ls -lt ~/voice-inbox \| head` |
| 2. The watcher | macOS permission changes (TCC resets, OS upgrades) stop launchd jobs from reading iCloud Drive or the inbox | `launchctl print gui/$(id -u)/local.voice-watcher \| grep -E 'state\|last exit code'` and `tail ~/archive/voice-watcher.log` |
| 3. whisper.cpp | Xcode / Command Line Tools updates break the built binary or its Metal shaders | `~/src/whisper.cpp/build/bin/whisper-cli -m ~/src/whisper.cpp/models/ggml-large-v3-turbo.bin -f /tmp/test-memo.wav --no-timestamps` (the kept test file from section 3.3) |

Fixes, in the same order: re-enable the automation and re-run it once
(section 4.1, gotcha box); reload the agent
(`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.voice-watcher.plist`)
and re-grant file access when prompted; rebuild whisper.cpp (section 3.1,
the model file survives a rebuild).

## Related

- [`openspec/specs/storage.md`](../openspec/specs/storage.md): the two-plane
  contract, `voice_notes` schema, durability and dead-man REQs (normative)
- [`openspec/specs/ingest.md`](../openspec/specs/ingest.md): Voice Sources,
  REQ-080..087 (the synthesis contract this pipeline feeds)
- [`prompts/llm-wiki-setup-plan.md`](../prompts/llm-wiki-setup-plan.md): the
  adoption plan and phases this guide serves
- [`docs/roadmap-glossary-personal-pipeline.md`](roadmap-glossary-personal-pipeline.md):
  the v3.0 issue plan and the binding premortem revisions
