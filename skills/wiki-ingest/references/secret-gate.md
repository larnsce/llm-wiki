# Pre-archive secret gate

Reference for the wiki-ingest secret gate (`secret_scan.py`, specs/ingest.md
REQ-045/046, specs/config.md REQ-624). Implements issues #15 and #6.

## The invariant

`ingested/` is committed git history: **keep it secret-free.** Once a source
file's bytes are committed there, exposure is sticky; removing the file later
does not remove it from history. So every source file is scanned BEFORE the
move from `raw_dir` into `ingested/`, and a blocking finding means the move
and the commit do not happen. The file stays in `raw_dir` until it is
redacted (or the user gives an explicit `--allow-secret` override).

The gate scans the raw SOURCE bytes, not the synthesized wiki pages. The
pattern set is tuned to raw source formats (Zotero exports, clipped HTML,
extracted PDF text, notes, datasets), not to Logseq `property::` syntax; the
page-oriented credential rule is lint.py's REQ-163 and is a separate check.

## Blocking vs advisory

Run `python3 skills/wiki-core/scripts/secret_scan.py --list-patterns` for the
full inventory. Two severities, kept clearly separated in the output:

- **Blocking (exit 2), credentials and key material:** AWS access keys,
  private key blocks, GitHub/GitLab/Slack/Stripe/OpenAI-style token prefixes,
  JWTs, credential assignments with non-trivial values, connection strings
  with embedded credentials, and scoped high-entropy tokens. Consequence: no
  archive, no commit; the file stays in `raw_dir` with a remediation message
  naming each match location.
- **Advisory (exit 1), governed personal data (PII):** email addresses,
  national-ID shapes (US SSN, German Steuer-ID and
  Sozialversicherungsnummer, IBAN), phone-number-dense content. Consequence:
  the findings are shown and explicit human confirmation is required before
  the bytes enter git history. In `--auto` mode advisory findings block,
  unless the source's type is in `sensitive_source_types` (see below), whose
  flow keeps the bytes out of git anyway.

Binary files (PDFs, images) get a strings-style pass over printable-ASCII
runs, so an embedded key inside a PDF is still caught. High-entropy/base64
detection is scoped to assignment-like contexts in text files and never runs
on binary object streams, `data:` URIs, or integrity/hash attributes, so
embedded media does not false-positive.

## Sensitive source types (REQ-046)

`sensitive_source_types` in `llm-wiki.yml` (specs/config.md REQ-624) lists
source types (typically `notes`, `data`) whose bytes must NEVER enter git,
even when the scan is clean. The flow:

1. The source is scanned like any other (a blocking finding still blocks).
2. Ingest writes the wiki pages as normal; `source-file::` records
   `ingested/<type>/<filename>`.
3. Ensure the vault `.gitignore` covers `ingested/<type>/`. Add the entry if
   it is missing; the `.gitignore` change is committed, the source bytes are
   not.
4. Verify BEFORE the move that the destination is ignored:

   ```
   python3 skills/wiki-core/scripts/secret_scan.py \
     --gitignore-check <vault-root> ingested/<type>/<filename>
   ```

   Exit 0: the path is ignored, the move is safe. Exit 2: the path would
   enter history (not ignored, or already tracked so `.gitignore` does not
   apply); fix that before moving the file.
5. Move the file to `ingested/<type>/` UNTRACKED. The atomic ingest commit
   contains the page edits (and the `.gitignore` addition), never the file.

The provenance path stays valid locally; only the bytes are excluded from
history. Note the trade-off: an untracked source is not backed up by the git
remote, so it needs its own backup channel.

## Not a guarantee

A passing scan prints: scanned N files against M patterns; a clean result is
NOT a guarantee, eyeball sensitive sources before committing. Treat the gate
as an assist, not a certification. Pattern-based scanning cannot recognize
every secret shape (novel token formats, secrets in prose, PII without a
canonical shape), so a green result never replaces looking at a sensitive
source before its bytes become permanent history.

## Manual pre-commit usage

The gate also works as a manual pre-commit check on whatever is staged, in
any git repo (the vault included):

```
cd <vault-root>
git add .
python3 <path-to>/skills/wiki-core/scripts/secret_scan.py --staged
# exit 0: clean (disclaimer applies)  1: advisory findings  2: blocking
git commit -m "..."   # only after the scan is acceptable
```

Use `--json` for machine-readable output of the same result.
