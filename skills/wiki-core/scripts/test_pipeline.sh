#!/usr/bin/env bash
# test_pipeline.sh - mechanical test harness for the llm-wiki validators.
#
# Builds temporary wikis (clean fixtures are generated at runtime via
# init_wiki.py to avoid fixture rot; only defect deltas are checked in under
# tests/fixtures/), runs every validator (find_config, check_config, lint.py
# including --strict and the grandfather floor, check_citations.py,
# check_canon.py, secret_scan.py, migrate_wiki.py --lowercase), and asserts
# GREEN on clean fixtures and RED on each
# planted defect (exit code AND, for lint, the expected REQ id in the --json
# findings).
#
# Pre-migration fixtures (Title Case Wiki/ corpora: defects/*/grandfathered
# and the migration/ vaults) run in BARE vaults (make_bare_vault), never
# overlaid on a lowercase scaffold: on a case-insensitive filesystem
# (macOS APFS) Wiki___Tech.md and wiki___tech.md are the SAME file and the
# copy would silently merge the two casings.
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

# assert_report <name> <python-expr>: evaluate a python expression against
# the JSON report captured in $OUT (bound to r).
assert_report() {
  local name="$1" expr="$2"
  if python3 - "$OUT" "$expr" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PY
  then
    report PASS "$name"
  else
    report FAIL "$name" "report expression failed: $expr"
  fi
}

py() { python3 "$SCRIPT_DIR/$1" "${@:2}"; }

# make_wiki <dir> <tool>: scaffold a clean wiki at runtime.
make_wiki() {
  python3 "$SCRIPT_DIR/init_wiki.py" \
    --wiki-path "$1" --tool "$2" --date 2026-07-01 >/dev/null
}

# make_bare_vault <dir> <tool>: config only, NO scaffolded pages. For the
# deliberately pre-migration (Title Case) fixtures; see the header note.
make_bare_vault() {
  local dir="$1" tool="$2" pages_dir=""
  [[ "$tool" == logseq ]] && pages_dir="pages"
  mkdir -p "$dir"
  cat > "$dir/llm-wiki.yml" <<EOF
tool: $tool
wiki_path: $dir
pages_dir: $pages_dir

namespaces:
  - Tech

raw_dir: raw
ingested_dir: ingested
source_types:
  - papers
default_source_type: papers
EOF
}

git_commit_all() {
  git -C "$1" add -A
  git -C "$1" -c user.email=test@example.org -c user.name=test \
    commit -qm "$2"
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
  # and kept a warning by --strict. The fixture is a deliberately
  # PRE-migration (Title Case Wiki/) corpus, so it runs in a bare vault.
  wiki="$WORK/$tool-grandfathered"
  make_bare_vault "$wiki" "$tool"
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
# lint rules 13/14: naming hygiene (REQ-230/231) + namespace hygiene
# (REQ-240), specs/lint.md. The vaults are generated at runtime: the
# en-dash page name and the Title Case segments would be Unicode/case
# traps as checked-in fixtures (see the header note on case-insensitive
# filesystems). Obsidian cannot host Wiki/ beside wiki/ on such a
# filesystem, so the uppercase structural segment moves one level down
# there; obsidian also prunes notes/ from enumeration, so its underscore
# leaf lives under wiki/ instead.
# ---------------------------------------------------------------------------
EN_DASH="$(printf '\342\200\223')"
for tool in logseq obsidian; do
  vault="$WORK/$tool-hygiene"
  make_bare_vault "$vault" "$tool"
  if [[ "$tool" == logseq ]]; then
    upper="Wiki/Foo"
    underscore="notes/My_Note"
    underscore_sev="info"
  else
    upper="wiki/Docs/foo"
    underscore="wiki/tech/my_note"
    underscore_sev="warning"
  fi
  endash="wiki/tech/data${EN_DASH}pipeline"

  python3 - "$vault" "$tool" "$upper" "$underscore" "$endash" <<'PY'
import os
import sys

root, tool, upper, underscore, endash = sys.argv[1:6]
pages_root = os.path.join(root, "pages") if tool == "logseq" else root

STAMPED = (
    ("type", "knowledge"), ("domain", "tech"), ("created", "2026-07-01"),
    ("updated", "2026-07-01"), ("confidence", "medium"),
    ("schema-spec-version", "2.0.0"),
)


def write(name, props, body):
    if tool == "logseq":
        path = os.path.join(pages_root, name.replace("/", "___") + ".md")
        lines = ["- %s:: %s" % (k, v) for k, v in props]
        body = ["- %s" % b for b in body]
    else:
        path = os.path.join(pages_root, name + ".md")
        lines = ["---"] + ["%s: %s" % (k, v) for k, v in props] + ["---"] \
            if props else []
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines + body) + "\n")


def links(*targets):
    return [" ".join("[[%s]]" % t for t in targets)]


# clean-page links every stamped page so none of them is an orphan.
write("wiki/tech/clean-page", STAMPED,
      links(upper, endash, "wiki/tools/Claude Code")
      + links(underscore) * (tool == "obsidian"))
write(upper, STAMPED, links("wiki/tech/clean-page"))
write(endash, STAMPED, links("wiki/tech/clean-page"))
write("wiki/tools/Claude Code", STAMPED, links("wiki/tech/clean-page"))
if tool == "logseq":
    write(underscore, (), ["a human Zettelkasten note, no wiki properties"])
else:
    write(underscore, STAMPED, links("wiki/tech/clean-page"))
write("para/projects/secret-plan", (),
      ["human project plan, no wiki properties"])
write("Scratchpad", (("schema-spec-version", "2.0.0"),),
      ["stray root page outside every namespace"])
PY

  run py lint.py --config "$vault/llm-wiki.yml" --json
  assert_exit_nonzero "lint($tool): red on naming/namespace hygiene vault"
  assert_report "lint($tool): uppercase structural segment flagged (REQ-230 warning)" \
    "any(f[\"id\"] == \"REQ-230\" and f[\"page\"] == \"$upper\" and f[\"severity\"] == \"warning\" for f in r[\"findings\"])"
  assert_report "lint($tool): underscore leaf flagged (REQ-231 $underscore_sev)" \
    "any(f[\"id\"] == \"REQ-231\" and f[\"page\"] == \"$underscore\" and f[\"severity\"] == \"$underscore_sev\" for f in r[\"findings\"])"
  assert_report "lint($tool): en-dash leaf flagged (REQ-231 warning)" \
    "any(f[\"id\"] == \"REQ-231\" and f[\"page\"] == \"$endash\" and f[\"severity\"] == \"warning\" for f in r[\"findings\"])"
  assert_report "lint($tool): proper-noun leaf wiki/tools/Claude Code NOT flagged mechanically" \
    "not any(f[\"rule\"] == \"naming-hygiene\" and f[\"page\"] == \"wiki/tools/Claude Code\" for f in r[\"findings\"])"
  assert_report "lint($tool): clean lowercase-hyphen name passes rule 13" \
    "not any(f[\"rule\"] == \"naming-hygiene\" and f[\"page\"] == \"wiki/tech/clean-page\" for f in r[\"findings\"])"
  assert_report "lint($tool): stray root page flagged (REQ-240 warning)" \
    "any(f[\"id\"] == \"REQ-240\" and f[\"page\"] == \"Scratchpad\" and f[\"severity\"] == \"warning\" for f in r[\"findings\"])"
  assert_report "lint($tool): para/ page exempt from every rule (no findings at all)" \
    "all(f[\"page\"] != \"para/projects/secret-plan\" for f in r[\"findings\"])"
  if [[ "$tool" == logseq ]]; then
    assert_report "lint(logseq): notes/ page exempt from wiki-only rules (naming info only)" \
      "all(f[\"rule\"] == \"naming-hygiene\" for f in r[\"findings\"] if f[\"page\"] == \"notes/My_Note\")"
  fi
done

# ---------------------------------------------------------------------------
# migrate_wiki --lowercase (REQ-580c): dry-run reports every rename plus the
# broken-link count WITHOUT writing; --apply converts (clean git tree
# required) and is idempotent; Roam task markers are converted; the renamed
# corpus lints clean under --strict (all [[wiki/...]] links resolve).
# ---------------------------------------------------------------------------
for tool in logseq obsidian; do
  vault="$WORK/$tool-titlecase"
  make_bare_vault "$vault" "$tool"
  cp -R "$FIXTURES/migration/$tool/." "$vault/"
  git -C "$vault" -c init.defaultBranch=main init -q
  git_commit_all "$vault" "pre-migration baseline"
  if [[ "$tool" == logseq ]]; then
    pagedir="$vault/pages"
    old_entry="Wiki___Tech.md"
    new_entry="wiki___tech.md"
  else
    pagedir="$vault"
    old_entry="Wiki"
    new_entry="wiki"
  fi

  run py migrate_wiki.py --lowercase --config "$vault/llm-wiki.yml" --json
  assert_exit 1 "migrate-lowercase($tool): dry-run reports pending changes"
  assert_report "migrate-lowercase($tool): dry-run lists 3 renames, 2 Roam markers, 0 broken links" \
    'len(r["renames"]) == 3 and r["roam_marker_conversions"] == 2 and r["broken_links_after_rename"] == 0'

  run python3 -c 'import os, sys; sys.exit(0 if sys.argv[2] in os.listdir(sys.argv[1]) else 1)' \
    "$pagedir" "$old_entry"
  assert_exit 0 "migrate-lowercase($tool): dry-run wrote nothing (old casing still on disk)"

  run py migrate_wiki.py --lowercase --apply \
    --config "$vault/llm-wiki.yml" --json
  assert_exit 1 "migrate-lowercase($tool): --apply converts (exit 1: changes applied)"

  run python3 -c 'import os, sys; entries = os.listdir(sys.argv[1]); sys.exit(0 if sys.argv[2] in entries and sys.argv[3] not in entries else 1)' \
    "$pagedir" "$new_entry" "$old_entry"
  assert_exit 0 "migrate-lowercase($tool): files renamed to lowercase on disk"

  run grep -r '{{\[\[' "$pagedir"
  assert_exit 1 "migrate-lowercase($tool): no Roam {{[[...]]}} markers left"

  git_commit_all "$vault" "lowercase migration"
  run py migrate_wiki.py --lowercase --apply \
    --config "$vault/llm-wiki.yml" --json
  assert_report "migrate-lowercase($tool): second --apply is a no-op (0 changes)" \
    'r["changes_total"] == 0 and r["renames"] == [] and r["files_rewritten"] == 0'

  run py lint.py --config "$vault/llm-wiki.yml" --json --strict
  assert_exit 0 "migrate-lowercase($tool): migrated corpus lints clean under --strict (links resolve)"
done

# --apply refuses a dirty working tree.
vault="$WORK/logseq-titlecase"
echo "dirty" >>"$vault/pages/wiki___tech.md"
run py migrate_wiki.py --lowercase --apply --config "$vault/llm-wiki.yml"
assert_exit 2 "migrate-lowercase: --apply refuses a dirty git tree"
git -C "$vault" checkout -q -- .

# ---------------------------------------------------------------------------
# check_citations: clean and cited fixtures green, planted citation defects
# red with the expected REQ id (specs/citations.md), in BOTH tool modes.
# The findings JSON shares the lint report shape, so assert_lint_finding
# works unchanged.
# ---------------------------------------------------------------------------
for tool in logseq obsidian; do
  wiki="$WORK/$tool-cite-scaffold"
  make_wiki "$wiki" "$tool"
  run py check_citations.py --config "$wiki/llm-wiki.yml" --json
  assert_exit 0 "check_citations($tool): green on clean scaffold"

  wiki="$WORK/$tool-cited-clean"
  make_wiki "$wiki" "$tool"
  cp -R "$FIXTURES/citations/$tool/cited-clean/." "$wiki/"
  run py check_citations.py --config "$wiki/llm-wiki.yml" --json
  assert_exit 0 "check_citations($tool): green on fully cited page"

  wiki="$WORK/$tool-uncited-claim"
  make_wiki "$wiki" "$tool"
  cp -R "$FIXTURES/citations/$tool/uncited-claim/." "$wiki/"
  run py check_citations.py --config "$wiki/llm-wiki.yml" --json
  assert_exit 1 "check_citations($tool): warning (exit 1) on uncited claim"
  assert_lint_finding \
    "check_citations($tool): uncited claim reports REQ-902" \
    REQ-902 warning

  wiki="$WORK/$tool-cite-mismatch"
  make_wiki "$wiki" "$tool"
  cp -R "$FIXTURES/citations/$tool/cite-mismatch/." "$wiki/"
  run py check_citations.py --config "$wiki/llm-wiki.yml" --json
  assert_exit 2 "check_citations($tool): critical (exit 2) on source-file/cite mismatch"
  assert_lint_finding \
    "check_citations($tool): union mismatch reports REQ-904" \
    REQ-904 critical
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
  "$REPO_ROOT/openspec/specs/citations.md" "$CANON/openspec/specs/"
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

# The tracking-param carve-out (issue #68) is URL-query-scoped only: the
# same high-entropy value in a bare assignment still blocks. The URL side
# is pinned by the clean fixture above.
ENTROPY_NOTE="$WORK/entropy-note.md"
printf 'config dump\ndeploy_id = AfmBOor7RPqK3x9ZtWc5dd2Xw1QhVbnJ4uE\n' >"$ENTROPY_NOTE"
run py secret_scan.py --json "$ENTROPY_NOTE"
assert_exit 2 "secret_scan: blocking (exit 2) on bare high-entropy assignment"
assert_scan_pattern "secret_scan: high-entropy-token pattern fired" high-entropy-token

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
