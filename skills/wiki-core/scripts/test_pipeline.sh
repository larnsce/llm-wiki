#!/usr/bin/env bash
# test_pipeline.sh - mechanical test harness for the llm-wiki validators.
#
# Builds temporary wikis (clean fixtures are generated at runtime via
# init_wiki.py to avoid fixture rot; only defect deltas are checked in under
# tests/fixtures/), runs every validator (find_config, check_config, lint.py
# including --strict and the grandfather floor, check_canon.py,
# secret_scan.py), and asserts GREEN on clean fixtures and RED on each
# planted defect (exit code AND, for lint, the expected REQ id in the --json
# findings).
#
# Usage: bash skills/wiki-core/scripts/test_pipeline.sh [--verbose]
# Dependencies: bash, python3, git. Exit: 0 all assertions pass, 1 otherwise.
#
# The LLM-side behaviors (ingest planning, reliability rating) are NOT
# covered here; see tests/golden/README.md and docs/testing.md.

set -euo pipefail

VERBOSE=0
if [[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]]; then
  VERBOSE=1
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--verbose]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIXTURES="$REPO_ROOT/tests/fixtures"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/llm-wiki-tests.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
FAILED_NAMES=()

OUT="$WORK/last-stdout"
ERR="$WORK/last-stderr"
RC=0

# run <cmd...>: execute, capture stdout/stderr and exit code without
# tripping set -e.
run() {
  RC=0
  "$@" >"$OUT" 2>"$ERR" || RC=$?
  if [[ $VERBOSE -eq 1 ]]; then
    echo "+ $*  (exit $RC)"
    sed 's/^/    /' "$OUT"
    sed 's/^/    ERR /' "$ERR"
  fi
}

report() {
  local status="$1" name="$2" detail="${3:-}"
  if [[ "$status" == PASS ]]; then
    PASS=$((PASS + 1))
    [[ $VERBOSE -eq 1 ]] && echo "PASS  $name"
  else
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("$name")
    echo "FAIL  $name${detail:+ - $detail}"
    if [[ $VERBOSE -eq 0 ]]; then
      sed 's/^/    /' "$OUT" | head -20
      sed 's/^/    ERR /' "$ERR" | head -10
    fi
  fi
  return 0
}

assert_exit() {
  local expected="$1" name="$2"
  if [[ "$RC" -eq "$expected" ]]; then
    report PASS "$name"
  else
    report FAIL "$name" "expected exit $expected, got $RC"
  fi
}

assert_exit_nonzero() {
  local name="$1"
  if [[ "$RC" -ne 0 ]]; then
    report PASS "$name"
  else
    report FAIL "$name" "expected non-zero exit, got 0"
  fi
}

# assert_lint_finding <name> <req-id> [severity] [grandfathered:true|false]
# Checks the lint --json report captured in $OUT.
assert_lint_finding() {
  local name="$1" req="$2" severity="${3:-}" grand="${4:-}"
  if python3 - "$OUT" "$req" "$severity" "$grand" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
req, severity, grand = sys.argv[2], sys.argv[3], sys.argv[4]
for f in report.get("findings", []):
    if f["id"] != req:
        continue
    if severity and f["severity"] != severity:
        continue
    if grand == "true" and not f.get("grandfathered"):
        continue
    if grand == "false" and f.get("grandfathered"):
        continue
    sys.exit(0)
sys.exit(1)
PY
  then
    report PASS "$name"
  else
    report FAIL "$name" "no finding id=$req${severity:+ severity=$severity}${grand:+ grandfathered=$grand} in JSON report"
  fi
}

# assert_scan_pattern <name> <pattern-name>: checks secret_scan --json output.
assert_scan_pattern() {
  local name="$1" pattern="$2"
  if python3 - "$OUT" "$pattern" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
sys.exit(0 if any(f["pattern"] == sys.argv[2]
                  for f in report.get("findings", [])) else 1)
PY
  then
    report PASS "$name"
  else
    report FAIL "$name" "pattern '$pattern' not in scan findings"
  fi
}

py() { python3 "$SCRIPT_DIR/$1" "${@:2}"; }

# make_wiki <dir> <tool>: scaffold a clean wiki at runtime.
make_wiki() {
  python3 "$SCRIPT_DIR/init_wiki.py" \
    --wiki-path "$1" --tool "$2" --date 2026-07-01 >/dev/null
}

echo "test_pipeline: repo $REPO_ROOT"
echo "test_pipeline: work dir $WORK"
echo

# ---------------------------------------------------------------------------
# find_config
# ---------------------------------------------------------------------------
make_wiki "$WORK/fc-wiki" logseq

run env LLM_WIKI_CONFIG="$WORK/fc-wiki/llm-wiki.yml" \
  python3 "$SCRIPT_DIR/find_config.py" --json
assert_exit 0 "find_config: green via LLM_WIKI_CONFIG"

run env LLM_WIKI_CONFIG="$WORK/does-not-exist.yml" \
  python3 "$SCRIPT_DIR/find_config.py"
assert_exit 2 "find_config: red on invalid LLM_WIKI_CONFIG"

mkdir -p "$WORK/nohome"
run env -u LLM_WIKI_CONFIG HOME="$WORK/nohome" \
  bash -c "cd '$WORK/nohome' && python3 '$SCRIPT_DIR/find_config.py'"
assert_exit 2 "find_config: red when discovery finds nothing"

# ---------------------------------------------------------------------------
# check_config
# ---------------------------------------------------------------------------
run py check_config.py "$WORK/fc-wiki/llm-wiki.yml"
assert_exit 0 "check_config: green on generated config"

run py check_config.py --skip-path-checks "$FIXTURES/configs/invalid-tool.yml"
assert_exit 2 "check_config: red (critical) on invalid tool"

run py check_config.py --skip-path-checks "$FIXTURES/configs/no-pipeline.yml"
assert_exit 1 "check_config: red (warning) on missing pipeline keys"

# ---------------------------------------------------------------------------
# init_wiki
# ---------------------------------------------------------------------------
run python3 "$SCRIPT_DIR/init_wiki.py" \
  --wiki-path "$WORK/fc-wiki" --tool logseq --date 2026-07-01
assert_exit 1 "init_wiki: warns (exit 1) instead of overwriting existing pages"

# ---------------------------------------------------------------------------
# lint: clean fixtures green, planted defects red, in BOTH tool modes
# ---------------------------------------------------------------------------
# defect-name:expected-REQ-id (asserted in the --json findings)
LINT_DEFECTS=(
  "orphan-page:REQ-110"
  "broken-ref:REQ-141"
  "missing-property:REQ-132"
  "bad-date:REQ-560"
  "archived-in-live-index:REQ-197"
  "empty-page:REQ-171"
  "credential-leak:REQ-163"
)

for tool in logseq obsidian; do
  clean="$WORK/clean-$tool"
  make_wiki "$clean" "$tool"

  run py lint.py --config "$clean/llm-wiki.yml" --json
  assert_exit 0 "lint($tool): green on clean fixture"

  # A fresh scaffold must also be strict-clean: every scaffolded page carries
  # schema-spec-version:: (no grandfather floor to hide behind), and the Hub
  # templates keep their [[...]] placeholder examples backticked.
  run py lint.py --config "$clean/llm-wiki.yml" --json --strict
  assert_exit 0 "lint($tool): green on clean fixture with --strict"

  for entry in "${LINT_DEFECTS[@]}"; do
    defect="${entry%%:*}"
    req="${entry##*:}"
    wiki="$WORK/$tool-$defect"
    make_wiki "$wiki" "$tool"
    cp -R "$FIXTURES/defects/$tool/$defect/." "$wiki/"

    run py lint.py --config "$wiki/llm-wiki.yml" --json
    assert_exit_nonzero "lint($tool): red on $defect"
    if [[ "$req" == "REQ-163" ]]; then
      assert_exit 2 "lint($tool): $defect is critical (exit 2)"
      assert_lint_finding "lint($tool): $defect reports $req" "$req" critical
    else
      assert_lint_finding "lint($tool): $defect reports $req" "$req"
    fi
  done

  # Grandfather floor: same missing-property defect on a page WITHOUT
  # schema-spec-version:: is downgraded to info by default (green exit)
  # and kept a warning by --strict.
  wiki="$WORK/$tool-grandfathered"
  make_wiki "$wiki" "$tool"
  cp -R "$FIXTURES/defects/$tool/grandfathered/." "$wiki/"

  run py lint.py --config "$wiki/llm-wiki.yml" --json
  assert_exit 0 "lint($tool): grandfathered defect stays green by default"
  assert_lint_finding \
    "lint($tool): grandfathered finding is info + flagged" \
    REQ-132 info true

  run py lint.py --config "$wiki/llm-wiki.yml" --json --strict
  assert_exit_nonzero "lint($tool): --strict goes red on grandfathered defect"
  assert_lint_finding \
    "lint($tool): --strict keeps the finding a warning" \
    REQ-132 warning false
done

# ---------------------------------------------------------------------------
# check_canon: green on the repo, red on a mutated copy
# ---------------------------------------------------------------------------
run py check_canon.py
assert_exit 0 "check_canon: green on the repo surfaces"

CANON="$WORK/canon"
mkdir -p "$CANON/openspec/specs" "$CANON/skills/wiki-core/references" \
  "$CANON/skills/wiki-core/scripts" "$CANON/templates/logseq" \
  "$CANON/templates/obsidian"
cp "$REPO_ROOT/openspec/specs/lint.md" "$REPO_ROOT/openspec/specs/schema.md" \
  "$CANON/openspec/specs/"
cp "$REPO_ROOT/skills/wiki-core/references/trust.md" \
  "$CANON/skills/wiki-core/references/"
cp "$REPO_ROOT/templates/logseq/Schema.md" "$CANON/templates/logseq/"
cp "$REPO_ROOT/templates/obsidian/Schema.md" "$CANON/templates/obsidian/"
cp "$SCRIPT_DIR/lint.py" "$SCRIPT_DIR/check_canon.py" \
  "$CANON/skills/wiki-core/scripts/"
python3 - "$CANON/skills/wiki-core/scripts/lint.py" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
mutated = text.replace('SCHEMA_SPEC_VERSION = "', 'SCHEMA_SPEC_VERSION = "9.9.9-', 1)
assert mutated != text
open(path, "w").write(mutated)
PY

run python3 "$CANON/skills/wiki-core/scripts/check_canon.py"
assert_exit 2 "check_canon: red on a mutated schema-spec-version surface"

# ---------------------------------------------------------------------------
# secret_scan: clean green; planted secrets red (blocking and advisory)
# ---------------------------------------------------------------------------
run py secret_scan.py --json "$FIXTURES/sources/clean-note.md"
assert_exit 0 "secret_scan: green on clean source"

run py secret_scan.py --json "$FIXTURES/sources/clipped-page.html"
assert_exit 2 "secret_scan: blocking (exit 2) on fake AWS key in clipped HTML"
assert_scan_pattern "secret_scan: aws-access-key pattern fired" aws-access-key

run py secret_scan.py --json "$FIXTURES/sources/personal-note.md"
assert_exit 1 "secret_scan: advisory (exit 1) on email + national-ID note"
assert_scan_pattern "secret_scan: email-address pattern fired" email-address
assert_scan_pattern "secret_scan: us-ssn pattern fired" us-ssn
assert_scan_pattern "secret_scan: de-steuer-id pattern fired" de-steuer-id

# PDF-shaped binary with an embedded fake token, generated at runtime so no
# binary is committed. Null bytes force the strings-style binary pass.
PDF="$WORK/embedded-token.pdf"
python3 - "$PDF" <<'PY'
import sys
fake = b"ghp_" + b"FAKE" * 8 + b"1234"  # 36 chars after the prefix
data = (b"%PDF-1.4\n%\x00\x00binary-fixture\n"
        b"stream\n\x00\x01\x02\x03" + fake + b"\x00\x04\nendstream\n%%EOF\n")
open(sys.argv[1], "wb").write(data)
PY
run py secret_scan.py --json "$PDF"
assert_exit 2 "secret_scan: blocking (exit 2) on token embedded in PDF-shaped binary"
assert_scan_pattern "secret_scan: github-token pattern fired in binary pass" github-token

# gitignore-check helper (REQ-046): ignored path green, unignored path red.
GITWIKI="$WORK/gitwiki"
make_wiki "$GITWIKI" logseq
git -C "$GITWIKI" -c init.defaultBranch=main init -q
echo "ingested/notes/" >>"$GITWIKI/.gitignore"

run py secret_scan.py --json --gitignore-check "$GITWIKI" \
  "ingested/notes/private.md"
assert_exit 0 "secret_scan: gitignore-check green on ignored path"

run py secret_scan.py --json --gitignore-check "$GITWIKI" \
  "ingested/papers/tracked.md"
assert_exit 2 "secret_scan: gitignore-check red on path that would enter history"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo
echo "==================== test_pipeline summary ===================="
echo "assertions: $((PASS + FAIL))  passed: $PASS  failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
  for name in "${FAILED_NAMES[@]}"; do
    echo "  FAILED: $name"
  done
  echo "result: RED"
  echo "==============================================================="
  exit 1
fi
echo "result: GREEN"
echo "==============================================================="
