#!/usr/bin/env python3
"""secret_scan.py - pre-archive secret and PII gate (specs/ingest.md REQ-045/046).

Scans raw SOURCE bytes (Zotero exports, clipped HTML, extracted PDF text,
notes, datasets) BEFORE a source file is moved into the git-tracked
`ingested/` tree, where exposure is sticky. The pattern set is tuned to raw
source formats, NOT to Logseq `property::` page syntax; the page-oriented
credential rule lives in lint.py (REQ-163) and is deliberately not reused
here.

Two passes:

- text pass: decodable content is scanned line by line
- strings pass: binary files are scanned via extracted printable-ASCII runs
  (8+ chars), so a key embedded in a PDF or other binary is still caught

Severities:

- blocking (exit 2): credentials and key material (AWS keys, private key
  blocks, vendor token prefixes, JWTs, credential assignments, connection
  strings with embedded credentials, scoped high-entropy tokens). A blocking
  finding means: do NOT archive, do NOT commit; the file stays in raw_dir
  until redacted (or the user gives an explicit --allow-secret override at
  the ingest level).
- advisory (exit 1): governed personal data (email addresses, national-ID
  shapes, IBANs, phone-number-dense content). Advisory findings need explicit
  human confirmation before the bytes enter git history.

High-entropy/base64 detection is scoped: text files only, tokens of 20-64
chars in assignment-like contexts, never inside binary object streams and
never in data: URIs or integrity/hash attributes, so embedded media does not
false-positive.

A clean scan is an assist, not a certification: the tool prints an explicit
not-a-guarantee disclaimer.

Modes:

  secret_scan.py FILE [FILE ...]          scan files (directories recurse)
  secret_scan.py --staged                 scan git-staged files (pre-commit)
  secret_scan.py --gitignore-check ROOT PATH
                                          verify PATH is git-ignored under
                                          the vault ROOT (REQ-046 helper)
  secret_scan.py --list-patterns          print the pattern inventory

Exit codes: 0 = clean, 1 = advisory findings, 2 = blocking findings (or a
usage/IO error, or --gitignore-check failure: the path would enter history).
"""

import argparse
import math
import os
import re
import subprocess
import sys

import wikilib

MAX_BYTES = 32 * 1024 * 1024  # cap per file; a truncated scan is flagged
PHONE_DENSE_THRESHOLD = 5
ENTROPY_MIN_BITS = 4.5
ENTROPY_TOKEN_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_.\-]{1,40})\s*[:=]\s*[\"'`]?"
    r"([A-Za-z0-9+/=_\-]{20,64})[\"'`]?")
# Keys whose values are legitimately high-entropy in raw web/source formats
# (subresource integrity, content hashes, cache tags): never entropy-flag.
ENTROPY_KEY_ALLOWLIST = {
    "integrity", "hash", "checksum", "digest", "etag", "nonce",
    "sha", "sha1", "sha256", "sha384", "sha512", "md5",
    "srcset", "sizes", "class", "id", "style", "content", "href", "src",
    "d", "points", "viewbox", "transform", "commit", "rev", "revision",
    "blob", "tree", "oid", "signature-hash",
}
BINARY_RUN_RE = re.compile(rb"[\x20-\x7e]{8,}")
PHONE_RE = re.compile(
    r"(?:\+|\b00)\d{1,3}[\s./-]?\(?\d{1,4}\)?(?:[\s./-]?\d{2,4}){2,4}"
    r"|\(\d{3}\)\s?\d{3}[-.\s]\d{4}"
    r"|\b\d{3,4}[-./]\d{3}[-./]\d{4}\b")

PLACEHOLDER_VALUE_RE = re.compile(r"^(?:\$\{|\{\{|<|%[({]?|\$\()|^[xX*.#_\-]+$")
PLACEHOLDER_WORDS = (
    "example", "changeme", "change-me", "placeholder", "redacted",
    "your-", "your_", "dummy", "sample", "xxxx", "insert", "value-here",
)
TRIVIAL_VALUES = {
    "password", "passwort", "secret", "true", "false", "none", "null",
    "undefined", "required", "optional", "string",
}


def _nontrivial_assignment(match):
    """Heuristic: is the assigned value plausibly a real secret?"""
    value = match.group(2).strip("\"'`,;")
    if len(value) < 8:
        return False
    if PLACEHOLDER_VALUE_RE.match(value):
        return False
    low = value.lower()
    if low in TRIVIAL_VALUES:
        return False
    if any(word in low for word in PLACEHOLDER_WORDS):
        return False
    # a single lowercase/Titlecase dictionary-style word is prose, not a key
    if value.isalpha() and (value.islower() or value.istitle()):
        return False
    return True


def _iban_valid(match):
    """ISO 13616 mod-97 check; kills most random letter-digit runs."""
    candidate = re.sub(r"\s", "", match.group(0))
    if not 15 <= len(candidate) <= 34:
        return False
    rearranged = candidate[4:] + candidate[:4]
    digits = []
    for char in rearranged:
        if char.isdigit():
            digits.append(char)
        elif char.isalpha():
            digits.append(str(ord(char.upper()) - 55))
        else:
            return False
    return int("".join(digits)) % 97 == 1


# (name, severity, compiled regex, description, validator-or-None,
#  scan-binary-strings-too)
POINT_PATTERNS = [
    ("aws-access-key", "blocking",
     re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
     "AWS access key id", None, True),
    ("private-key-block", "blocking",
     re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
     "PEM/OpenSSH private key block", None, True),
    ("github-token", "blocking",
     re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b"
                r"|\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
     "GitHub token", None, True),
    ("gitlab-token", "blocking",
     re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}\b"),
     "GitLab personal access token", None, True),
    ("slack-token", "blocking",
     re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}\b"),
     "Slack token", None, True),
    ("stripe-key", "blocking",
     re.compile(r"\b[sr]k[-_]live[-_][A-Za-z0-9]{16,}\b"),
     "Stripe live secret/restricted key", None, True),
    ("api-secret-key", "blocking",
     re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
     "sk- prefixed API secret key (OpenAI/Anthropic style)", None, True),
    ("jwt", "blocking",
     re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}"
                r"\.[A-Za-z0-9_\-]{8,}\b"),
     "JSON Web Token (header.payload.signature)", None, True),
    ("credential-assignment", "blocking",
     re.compile(r"(?i)\b(password|passwd|pwd|api[_-]?key|apikey|secret"
                r"|secret[_-]?key|client[_-]?secret|auth[_-]?token"
                r"|access[_-]?token|access[_-]?key|private[_-]?key|token"
                r"|credentials?)\b\s*[:=]>?\s*[\"'`]?([^\s\"'`,;]{8,})"),
     "credential assignment with a non-trivial value",
     _nontrivial_assignment, True),
    ("connection-string", "blocking",
     re.compile(r"\b[a-z][a-z0-9+.\-]{1,15}://[^\s:/@\"'`]{1,64}"
                r":[^\s/@\"'`]{3,64}@[A-Za-z0-9.\-]"),
     "connection string with embedded credentials (scheme://user:pass@host)",
     None, True),
    ("email-address", "advisory",
     re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
     "email address (governed personal data)", None, True),
    ("us-ssn", "advisory",
     re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
     "US Social Security number shape (with SSA sanity constraints)",
     None, True),
    ("de-steuer-id", "advisory",
     re.compile(r"(?i)\b(?:steuer(?:liche)?[-\s]?id(?:entifikationsnummer)?"
                r"|steuer[-\s]?identnummer|idnr|tax\s?id)\b\D{0,10}"
                r"([1-9]\d(?:\s?\d){9})\b"),
     "German Steuer-ID (11 digits in keyword context)", None, True),
    ("de-svnr", "advisory",
     re.compile(r"\b\d{2}\s?[0-3]\d[01]\d\d{2}\s?[A-Z]\s?\d{2}\s?\d\b"),
     "German Sozialversicherungsnummer shape", None, True),
    ("iban", "advisory",
     re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b"),
     "IBAN (mod-97 validated)", _iban_valid, True),
]

# Procedural rules, counted in the inventory alongside the point patterns.
PROCEDURAL_PATTERNS = [
    ("high-entropy-token", "blocking",
     "high-entropy token (20-64 chars, assignment context, text files only; "
     "never binary streams, data: URIs, or integrity/hash attributes)"),
    ("phone-dense", "advisory",
     "phone-number-dense content (%d+ phone-shaped numbers in one file)"
     % PHONE_DENSE_THRESHOLD),
]

PATTERN_COUNT = len(POINT_PATTERNS) + len(PROCEDURAL_PATTERNS)

DISCLAIMER = ("a clean result is NOT a guarantee, eyeball sensitive "
              "sources before committing.")

REMEDIATION = (
    "BLOCKED: do NOT archive, do NOT commit. The file stays in raw_dir.\n"
    "Redact the matched content at the locations above, or re-run the\n"
    "ingest with an explicit --allow-secret override, before re-ingest.\n"
    "Rationale: ingested/ is committed git history; exposure there is sticky.")

ADVISORY_NOTE = (
    "ADVISORY: possible governed personal data (PII). Review the findings\n"
    "above and confirm explicitly before the bytes enter git history. In\n"
    "--auto ingest runs advisory findings block, unless the source type is\n"
    "listed in sensitive_source_types (those bytes stay out of git anyway).")


def shannon_entropy(text):
    counts = {}
    for char in text:
        counts[char] = counts.get(char, 0) + 1
    total = len(text)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def redact(text):
    """Mask the middle of a matched excerpt; never print the full match."""
    text = " ".join(text.split())
    if len(text) <= 8:
        return text[:1] + "***" + text[-1:]
    keep = 4 if len(text) >= 12 else 2
    return text[:keep] + "******" + text[-keep:]


def make_finding(path, pattern_name, severity, description, excerpt,
                 line=None, byte=None):
    return {
        "file": path,
        "line": line,
        "byte": byte,
        "pattern": pattern_name,
        "severity": severity,
        "description": description,
        "excerpt": redact(excerpt),
    }


def _scan_chunk(path, text, findings, seen, line=None, byte_base=None,
                binary=False):
    """Run the point patterns over one text chunk (a line or an ASCII run)."""
    for name, severity, regex, description, validator, binary_ok in POINT_PATTERNS:
        if binary and not binary_ok:
            continue
        for match in regex.finditer(text):
            if validator and not validator(match):
                continue
            key = (line, byte_base, match.start())
            if key in seen:
                continue
            seen.add(key)
            byte = None if byte_base is None else byte_base + match.start()
            findings.append(make_finding(
                path, name, severity, description, match.group(0),
                line=line, byte=byte))


def _scan_entropy_line(path, line_text, line_no, findings, seen):
    """Scoped high-entropy detection (text files, assignment contexts only)."""
    for match in ENTROPY_TOKEN_RE.finditer(line_text):
        key_name, value = match.group(1), match.group(2)
        if key_name.lower().strip("_-.") in ENTROPY_KEY_ALLOWLIST:
            continue
        # never fire inside data: URIs / base64 media payloads
        context = line_text[max(0, match.start() - 48):match.start()]
        if "data:" in context or "base64," in context:
            continue
        if shannon_entropy(value) < ENTROPY_MIN_BITS:
            continue
        dedupe = (line_no, None, match.start())
        if dedupe in seen:
            continue
        seen.add(dedupe)
        findings.append(make_finding(
            path, "high-entropy-token", "blocking",
            "high-entropy token in assignment context", match.group(0),
            line=line_no))


def scan_text(path, text, findings):
    seen = set()
    for line_no, line_text in enumerate(text.splitlines(), start=1):
        _scan_chunk(path, line_text, findings, seen, line=line_no)
        _scan_entropy_line(path, line_text, line_no, findings, seen)
    phone_hits = PHONE_RE.findall(text)
    if len(phone_hits) >= PHONE_DENSE_THRESHOLD:
        findings.append(make_finding(
            path, "phone-dense", "advisory",
            "%d phone-shaped numbers in one file" % len(phone_hits),
            phone_hits[0], line=None))


def scan_binary(path, data, findings):
    """Strings-style pass: printable-ASCII runs of 8+ chars.

    No entropy and no phone-density rules here: binary object streams
    (images, compressed PDF streams) must never false-positive on
    base64-looking noise.
    """
    seen = set()
    for run in BINARY_RUN_RE.finditer(data):
        chunk = run.group(0).decode("ascii")
        _scan_chunk(path, chunk, findings, seen,
                    byte_base=run.start(), binary=True)


def scan_file(path, findings):
    """Scan one file; appends findings. Returns True if scanned."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    except OSError as error:
        print("ERROR: cannot read %s: %s" % (path, error), file=sys.stderr)
        return False
    truncated = len(data) > MAX_BYTES
    if truncated:
        data = data[:MAX_BYTES]
        findings.append(make_finding(
            path, "scan-truncated", "advisory",
            "file larger than %d bytes; only the first %d bytes were "
            "scanned" % (MAX_BYTES, MAX_BYTES), "truncated scan"))
    if b"\x00" in data[:8192] or b"\x00" in data:
        scan_binary(path, data, findings)
        return True
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    scan_text(path, text, findings)
    return True


def collect_paths(arguments):
    """Expand file and directory arguments into a flat file list."""
    paths = []
    for arg in arguments:
        if os.path.isdir(arg):
            for dirpath, dirnames, filenames in os.walk(arg):
                dirnames[:] = sorted(
                    d for d in dirnames if d not in (".git",))
                for filename in sorted(filenames):
                    paths.append(os.path.join(dirpath, filename))
        elif os.path.isfile(arg):
            paths.append(arg)
        else:
            print("ERROR: no such file: %s" % arg, file=sys.stderr)
            return None
    return paths


def staged_paths():
    """Paths staged in the current git repo (pre-commit usage)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z",
             "--diff-filter=ACMR"],
            capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print("ERROR: git diff --cached failed: %s" % error, file=sys.stderr)
        return None
    names = [n for n in result.stdout.decode("utf-8").split("\0") if n]
    return [n for n in names if os.path.isfile(n)]


def gitignore_check(vault_root, path, as_json):
    """REQ-046 helper: verify `path` stays out of git under `vault_root`.

    Exit 0: the path is ignored (or the vault is not a git repo, so nothing
    enters history). Exit 2: the path would enter git history (not ignored,
    or already tracked so .gitignore does not apply).
    """
    vault_root = os.path.expanduser(vault_root)
    if not os.path.isdir(vault_root):
        print("ERROR: vault root '%s' is not a directory." % vault_root,
              file=sys.stderr)
        return wikilib.EXIT_CRITICAL

    def emit(status, message, exit_code):
        if as_json:
            wikilib.emit_json({"mode": "gitignore-check", "vault": vault_root,
                               "path": path, "status": status,
                               "message": message})
        else:
            print(message)
        return exit_code

    tracked = subprocess.run(
        ["git", "-C", vault_root, "ls-files", "--error-unmatch", "--", path],
        capture_output=True)
    if tracked.returncode == 0:
        return emit("tracked",
                    "BLOCKED: '%s' is already TRACKED in git; .gitignore "
                    "does not apply to tracked files. Run 'git rm --cached "
                    "-- %s' (the bytes remain in past history; consider "
                    "history rewriting if they are sensitive)."
                    % (path, path), wikilib.EXIT_CRITICAL)

    ignored = subprocess.run(
        ["git", "-C", vault_root, "check-ignore", "-q", "--", path],
        capture_output=True)
    if ignored.returncode == 0:
        return emit("ignored",
                    "OK: '%s' is git-ignored under %s; its bytes will not "
                    "enter git history." % (path, vault_root),
                    wikilib.EXIT_OK)
    if ignored.returncode == 1:
        return emit("not-ignored",
                    "BLOCKED: '%s' is NOT git-ignored under %s. Add the "
                    "path (or its directory) to the vault .gitignore before "
                    "moving a sensitive source there (specs/ingest.md "
                    "REQ-046)." % (path, vault_root), wikilib.EXIT_CRITICAL)
    return emit("no-repo",
                "OK: %s is not a git repository; no bytes enter git "
                "history." % vault_root, wikilib.EXIT_OK)


def list_patterns(as_json):
    inventory = [
        {"name": name, "severity": severity, "description": description}
        for name, severity, _regex, description, _v, _b in POINT_PATTERNS
    ] + [
        {"name": name, "severity": severity, "description": description}
        for name, severity, description in PROCEDURAL_PATTERNS
    ]
    if as_json:
        wikilib.emit_json({"mode": "list-patterns", "patterns": inventory,
                           "pattern_count": PATTERN_COUNT})
        return wikilib.EXIT_OK
    width = max(len(entry["name"]) for entry in inventory)
    for entry in inventory:
        print("%-*s  %-8s  %s" % (width, entry["name"], entry["severity"],
                                  entry["description"]))
    print("\n%d patterns (%d blocking, %d advisory)" % (
        PATTERN_COUNT,
        sum(1 for e in inventory if e["severity"] == "blocking"),
        sum(1 for e in inventory if e["severity"] == "advisory")))
    return wikilib.EXIT_OK


def location(finding):
    if finding["line"] is not None:
        return "%s:%d" % (finding["file"], finding["line"])
    if finding["byte"] is not None:
        return "%s @byte %d" % (finding["file"], finding["byte"])
    return finding["file"]


def print_report(findings, files_scanned, status):
    for finding in sorted(findings,
                          key=lambda f: (f["severity"] != "blocking",
                                         f["file"], f["line"] or 0,
                                         f["byte"] or 0)):
        print("%-8s  %-22s  %s  %s  (%s)" % (
            finding["severity"].upper(), finding["pattern"],
            location(finding), finding["excerpt"], finding["description"]))
    if findings:
        print()
    print("scanned %d files against %d patterns; %s"
          % (files_scanned, PATTERN_COUNT, DISCLAIMER))
    if status == "blocking":
        print("\n" + REMEDIATION)
    elif status == "advisory":
        print("\n" + ADVISORY_NOTE)


def main():
    parser = argparse.ArgumentParser(
        description="Pre-archive secret and PII gate for raw source bytes "
                    "(specs/ingest.md REQ-045/046). Blocking findings mean: "
                    "no archive, no commit; the file stays in raw_dir until "
                    "redacted.")
    parser.add_argument("paths", nargs="*",
                        help="files (or directories, walked recursively) to "
                             "scan; with --gitignore-check: the ONE path to "
                             "verify")
    parser.add_argument("--staged", action="store_true",
                        help="scan git-staged files instead of path "
                             "arguments (manual pre-commit use)")
    parser.add_argument("--gitignore-check", metavar="VAULT_ROOT",
                        default=None,
                        help="verify that the given path argument is "
                             "git-ignored under VAULT_ROOT (sensitive-source "
                             "flow, REQ-046); exit 0 ignored, exit 2 "
                             "otherwise")
    parser.add_argument("--list-patterns", action="store_true",
                        help="print the pattern inventory and exit")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    args = parser.parse_args()

    if args.list_patterns:
        return list_patterns(args.json)

    if args.gitignore_check is not None:
        if len(args.paths) != 1:
            print("ERROR: --gitignore-check takes exactly one path argument.",
                  file=sys.stderr)
            return wikilib.EXIT_CRITICAL
        return gitignore_check(args.gitignore_check, args.paths[0], args.json)

    if args.staged:
        if args.paths:
            print("ERROR: --staged takes no path arguments.", file=sys.stderr)
            return wikilib.EXIT_CRITICAL
        paths = staged_paths()
    else:
        if not args.paths:
            parser.print_usage(sys.stderr)
            print("ERROR: give file paths, --staged, --gitignore-check, or "
                  "--list-patterns.", file=sys.stderr)
            return wikilib.EXIT_CRITICAL
        paths = collect_paths(args.paths)
    if paths is None:
        return wikilib.EXIT_CRITICAL

    findings = []
    files_scanned = 0
    for path in paths:
        if scan_file(path, findings):
            files_scanned += 1
        else:
            return wikilib.EXIT_CRITICAL

    blocking = [f for f in findings if f["severity"] == "blocking"]
    advisory = [f for f in findings if f["severity"] == "advisory"]
    if blocking:
        status, exit_code = "blocking", wikilib.EXIT_CRITICAL
    elif advisory:
        status, exit_code = "advisory", wikilib.EXIT_WARNINGS
    else:
        status, exit_code = "ok", wikilib.EXIT_OK

    if args.json:
        wikilib.emit_json({
            "mode": "staged" if args.staged else "files",
            "files_scanned": files_scanned,
            "pattern_count": PATTERN_COUNT,
            "findings": findings,
            "totals": {"blocking": len(blocking), "advisory": len(advisory)},
            "status": status,
            "disclaimer": DISCLAIMER,
        })
    else:
        print_report(findings, files_scanned, status)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
