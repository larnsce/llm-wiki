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

# Logseq :hidden scaffold (issue #69, REQ-787): a fresh scaffold writes
# logseq/config.edn hiding the source dirs; an app-initialized graph gets
# the entries MERGED into its existing :hidden vector (commented vectors
# are not touched).
HIDDEN_WIKI="$WORK/hidden-fresh"
run python3 "$SCRIPT_DIR/init_wiki.py" \
  --wiki-path "$HIDDEN_WIKI" --tool logseq --date 2026-07-01
assert_exit 0 "init_wiki: clean scaffold including logseq/config.edn"
if grep -q ':hidden \["raw" "ingested"\]' "$HIDDEN_WIKI/logseq/config.edn"; then
  report PASS "init_wiki: fresh config.edn hides raw/ and ingested/"
else
  report FAIL "init_wiki: fresh config.edn hides raw/ and ingested/"
fi

HIDDEN_WIKI="$WORK/hidden-merge"
mkdir -p "$HIDDEN_WIKI/logseq"
printf '{:meta/version 1\n ;; :hidden ["commented"]\n :hidden ["existing"]}\n' \
  >"$HIDDEN_WIKI/logseq/config.edn"
run python3 "$SCRIPT_DIR/init_wiki.py" \
  --wiki-path "$HIDDEN_WIKI" --tool logseq --date 2026-07-01
assert_exit 0 "init_wiki: clean scaffold over an app-initialized graph"
if grep -q ':hidden \["existing" "raw" "ingested"\]' "$HIDDEN_WIKI/logseq/config.edn" \
  && grep -q ';; :hidden \["commented"\]' "$HIDDEN_WIKI/logseq/config.edn"; then
  report PASS "init_wiki: merges :hidden entries, leaves commented vector alone"
else
  report FAIL "init_wiki: merges :hidden entries, leaves commented vector alone"
fi

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
  "credential-base64:REQ-163"
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
# lint rule 6 regression (#104, REQ-160): a 40+ char lowercase namespace path
# is link syntax, not a credential candidate, both inside [[...]] and as
# plain routing-line text. lint REQ-241a (#105): the Logseq built-in contents
# page is a system page and draws no findings.
# ---------------------------------------------------------------------------
for tool in logseq obsidian; do
  wiki="$WORK/$tool-linkpath"
  make_wiki "$wiki" "$tool"
  if [[ "$tool" == logseq ]]; then
    cat >"$wiki/pages/wiki___tech___washopenresearch___uncnewsletter.md" <<'EOF'
- type:: knowledge
- domain:: tech
- created:: 2026-07-01
- updated:: 2026-07-01
- confidence:: medium
- schema-spec-version:: 2.0.0
- ## Notes
	- plain-text path mention: wiki/tech/washopenresearch/uncnewsletter
	- [[wiki/tech]]
EOF
    python3 - "$wiki/pages/wiki___tech.md" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
line = ("\t\t- [[wiki/tech/washopenresearch/uncnewsletter]] -- "
        "UNC newsletter dataset notes #data\n")
text = text.replace("\t- ### Index\n", "\t- ### Index\n" + line, 1)
open(path, "w").write(text)
PY
  else
    mkdir -p "$wiki/wiki/tech/washopenresearch"
    cat >"$wiki/wiki/tech/washopenresearch/uncnewsletter.md" <<'EOF'
---
type: knowledge
domain: tech
created: 2026-07-01
updated: 2026-07-01
confidence: medium
schema-spec-version: 2.0.0
---

## Notes

plain-text path mention: wiki/tech/washopenresearch/uncnewsletter

[[wiki/tech]]
EOF
    python3 - "$wiki/wiki/tech/_index.md" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
line = ("- [[wiki/tech/washopenresearch/uncnewsletter]] -- "
        "UNC newsletter dataset notes #data\n")
text = text.replace("### Index\n", "### Index\n\n" + line, 1)
open(path, "w").write(text)
PY
  fi
  run py lint.py --config "$wiki/llm-wiki.yml" --json
  assert_exit 0 "lint($tool): green with 40-char namespace path in link and plain text (#104)"
  assert_report "lint($tool): no REQ-163 finding on the namespace path (#104)" \
    'not any(f["id"] == "REQ-163" for f in r["findings"])'
done

wiki="$WORK/logseq-contents"
make_wiki "$wiki" logseq
printf -- '- [[wiki/tech]]\n- [[wiki/projects]]\n' >"$wiki/pages/contents.md"
run py lint.py --config "$wiki/llm-wiki.yml" --json
assert_exit 0 "lint(logseq): green with built-in contents page (#105)"
assert_report "lint(logseq): contents page draws no findings (REQ-241a)" \
  'all(f["page"] != "contents" for f in r["findings"])'
run py lint.py --config "$wiki/llm-wiki.yml" --json --strict
assert_exit 0 "lint(logseq): contents page green under --strict (#105)"

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

  # Capture refs (ingest REQ-086): archive.db:voice_notes/<id> is a valid
  # cite target and joins the source-file union like an ingested/ path.
  wiki="$WORK/$tool-capture-cited"
  make_wiki "$wiki" "$tool"
  cp -R "$FIXTURES/citations/$tool/capture-cited/." "$wiki/"
  run py check_citations.py --config "$wiki/llm-wiki.yml" --json
  assert_exit 0 "check_citations($tool): green on capture-ref cited page (REQ-086)"
done

# A ref whose path contains whitespace (un-slugged web-clipping filename,
# issue #67): the union invariant fires critical AND the REQ-901 warning
# points at the actual cause (slugify at intake) instead of the generic
# malformed-ref message.
wiki="$WORK/logseq-spacey-ref"
make_wiki "$wiki" "logseq"
mkdir -p "$wiki/ingested/clippings"
cat > "$wiki/pages/wiki___tech___spacey-ref.md" <<'EOF'
- type:: knowledge
- domain:: tech
- created:: 2026-07-01
- updated:: 2026-07-01
- confidence:: medium
- source:: ingest
- source-file:: ingested/clippings/Before the Guardrails.md
- reliability:: medium
- schema-spec-version:: 2.0.0
- ## Body
	- A claim citing an un-slugged clipping filename.
	  cite:: ingested/clippings/Before the Guardrails.md
- ## Cross-References
	- [[wiki/tech]]
EOF
run py check_citations.py --config "$wiki/llm-wiki.yml" --json
assert_exit 2 "check_citations: critical (exit 2) on whitespace ref (union unresolvable)"
assert_report "check_citations: whitespace ref gets the slugify hint" \
  "any(f['id'] == 'REQ-901' and 'slugify' in f['message'] for f in r['findings'])"

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
  "$REPO_ROOT/openspec/specs/citations.md" \
  "$REPO_ROOT/openspec/specs/namespaces.md" "$CANON/openspec/specs/"
cp "$REPO_ROOT/skills/wiki-core/references/trust.md" \
  "$CANON/skills/wiki-core/references/"
cp "$REPO_ROOT/templates/logseq/Schema.md" "$CANON/templates/logseq/"
cp "$REPO_ROOT/templates/obsidian/Schema.md" "$CANON/templates/obsidian/"
cp "$SCRIPT_DIR/lint.py" "$SCRIPT_DIR/check_canon.py" "$SCRIPT_DIR/wikilib.py" \
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

# Installed-copy conditions (#106): the skill bundle ships no openspec/ or
# templates/, so the script must fail fast with exit 3 (not phantom drift),
# and --repo must point it back at a real checkout from anywhere.
INSTALLED="$WORK/installed/skills/wiki-core/scripts"
mkdir -p "$INSTALLED" "$WORK/somewhere-else"
cp "$SCRIPT_DIR/check_canon.py" "$INSTALLED/"
run bash -c "cd '$WORK/somewhere-else' && python3 '$INSTALLED/check_canon.py'"
assert_exit 3 "check_canon: exit 3 outside a checkout (not phantom drift, #106)"
if grep -q "not in an llm-wiki checkout" "$OUT"; then
  report PASS "check_canon: fail-fast names the fix (#106)"
else
  report FAIL "check_canon: fail-fast names the fix (#106)"
fi
run bash -c "cd '$WORK/somewhere-else' && python3 '$INSTALLED/check_canon.py' --repo '$REPO_ROOT'"
assert_exit 0 "check_canon: --repo <checkout> works from anywhere (#106)"
run bash -c "cd '$REPO_ROOT' && python3 '$INSTALLED/check_canon.py'"
assert_exit 0 "check_canon: installed copy green when cwd is the checkout (#106)"

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

# Transcript route (ingest REQ-1300/1301, issue #107): transcripts is a
# configured source type AND sensitive by default in config.example.yml,
# and the gitignore-check accepts the ingested/transcripts/ destination.
run bash -c "awk '/^source_types:/,/^default_source_type:/' \
  '$REPO_ROOT/config.example.yml' | grep -q -- '- transcripts'"
assert_exit 0 "config.example: transcripts is a source type (REQ-623)"
run bash -c "awk '/^sensitive_source_types:/,/^\$/' \
  '$REPO_ROOT/config.example.yml' | grep -q -- '^  - transcripts'"
assert_exit 0 "config.example: transcripts is sensitive by default (REQ-624, ingest REQ-1301)"
echo "ingested/transcripts/" >>"$GITWIKI/.gitignore"
run py secret_scan.py --json --gitignore-check "$GITWIKI" \
  "ingested/transcripts/chat-2026-06-25-vault-design.md"
assert_exit 0 "secret_scan: gitignore-check green on sensitive transcript path (REQ-1301)"
run test -f "$REPO_ROOT/tests/golden/source/chat-2026-06-25-vault-design.md"
assert_exit 0 "golden: frozen transcript fixture present (REQ-1300, issue #107)"

# ---------------------------------------------------------------------------
# author:: provenance (schema REQ-585a, ingest REQ-011a/033c, #73) and the
# born-cited person page (ingest REQ-024a, #74): both shapes lint clean and
# pass the citation gate.
# ---------------------------------------------------------------------------
AUTHWIKI="$WORK/author-wiki"
make_wiki "$AUTHWIKI" logseq
mkdir -p "$AUTHWIKI/ingested/clippings"
echo "clipped text" >"$AUTHWIKI/ingested/clippings/insanely-human-kieffer.md"
cat >"$AUTHWIKI/pages/wiki___tech___insanely-human.md" <<'EOF'
schema-spec-version:: 2.0.0
type:: knowledge
domain:: tech
created:: 2026-07-01
updated:: 2026-07-01
confidence:: medium
source:: ingest
source-file:: ingested/clippings/insanely-human-kieffer.md
author:: Sam Kieffer
reliability:: medium

- ## Body
	- Being insanely human is the differentiator.
	  cite:: ingested/clippings/insanely-human-kieffer.md
- ## Pending Review
	- Single medium source.
- ## Cross-References
	- [[wiki/tech]]
EOF
cat >"$AUTHWIKI/pages/wiki___people___Sam Kieffer.md" <<'EOF'
schema-spec-version:: 2.0.0
type:: entity
entity-type:: person
created:: 2026-07-01
updated:: 2026-07-01
confidence:: medium
status:: active
source:: ingest
source-file:: ingested/clippings/insanely-human-kieffer.md
author:: Sam Kieffer
reliability:: medium

- ## Sam Kieffer
	- Author of the clipped essays behind [[wiki/tech/insanely-human]].
	  cite:: ingested/clippings/insanely-human-kieffer.md
- ## Pending Review
	- Synthesis from provenance metadata; single source.
- ## Cross-References
	- [[wiki/tech/insanely-human]]
EOF
python3 - "$AUTHWIKI/pages" <<'PY'
import sys, pathlib
pages = pathlib.Path(sys.argv[1])
lines = {
    "wiki___tech.md": "\t\t- [[wiki/tech/insanely-human]] -- what makes work insanely human #essay\n",
    "wiki___people.md": "\t\t- [[wiki/people/Sam Kieffer]] -- essayist behind the insanely-human clippings #author\n",
}
for name, line in lines.items():
    hub = pages / name
    hub.write_text(hub.read_text().replace("\t- ### Index\n",
                                           "\t- ### Index\n" + line, 1))
PY
run py lint.py --config "$AUTHWIKI/llm-wiki.yml" --strict --json
assert_exit 0 "lint(logseq): author:: page + born-cited person page lint clean under --strict (REQ-585a/024a)"
run py check_citations.py --config "$AUTHWIKI/llm-wiki.yml" --json
assert_exit 0 "check_citations(logseq): person page cites the works' ingested files (union holds, REQ-024a)"

# ---------------------------------------------------------------------------
# Glossary layer (specs/glossary.md): --with-glossary scaffold, config
# REQ-628, lint rule 15 (REQ-250..253).
# ---------------------------------------------------------------------------
for tool in logseq obsidian; do
  GLWIKI="$WORK/glossary-$tool"
  run python3 "$SCRIPT_DIR/init_wiki.py" --wiki-path "$GLWIKI" \
    --tool "$tool" --date 2026-07-01 --with-glossary
  assert_exit 0 "init_wiki($tool): --with-glossary scaffolds clean"
  run py check_config.py "$GLWIKI/llm-wiki.yml"
  assert_exit 0 "check_config($tool): glossary_dir is a known key (REQ-628)"
  run py lint.py --config "$GLWIKI/llm-wiki.yml" --strict --json
  assert_exit 0 "lint($tool): --with-glossary scaffold lints clean under --strict"
done

GLDEFECT="$WORK/glossary-defects"
make_wiki "$GLDEFECT" logseq
cat >"$GLDEFECT/pages/glossary___tech.md" <<'EOF'
schema-spec-version:: 2.0.0
type:: glossary-domain

- ## Terms
	- | EN | DE | Rule | Note |
	  | --- | --- | --- | --- |
	  | prompt | der Prompt | keep-english | invalid enum value |
	  | workflow | der Arbeitsablauf | | undecided row on a domain page |
EOF
cat >"$GLDEFECT/pages/glossary___teaching.md" <<'EOF'
schema-spec-version:: 2.0.0
type:: glossary-domain

- ## Terms
	- | EN | German | Rule | Note |
	  | --- | --- | --- | --- |
	  | homework | die Hausaufgabe | translate | header is off-canon |
EOF
cat >"$GLDEFECT/pages/glossary___imported___glosario.md" <<'EOF'
schema-spec-version:: 2.0.0
type:: glossary-staging
source:: Glosario (The Carpentries), CC-BY

- ## Terms
	- | EN | DE | Rule | Note |
	  | --- | --- | --- | --- |
	  | repository | das Repositorium | | staging row, empty Rule is fine |
EOF
cat >"$GLDEFECT/pages/glossary___tech___repository.md" <<'EOF'
schema-spec-version:: 2.0.0
type:: glossary-term
alias:: Repository, Repositorium
domain:: tech

- Term page without rule::
EOF
run py lint.py --config "$GLDEFECT/llm-wiki.yml" --json
assert_exit_nonzero "lint(logseq): red on glossary defect vault"
assert_lint_finding "lint(logseq): invalid Rule enum reports REQ-251" REQ-251
assert_lint_finding "lint(logseq): off-canon header reports REQ-250" REQ-250
assert_lint_finding "lint(logseq): staging without status reports REQ-252" REQ-252
assert_lint_finding "lint(logseq): term page without rule:: reports REQ-253" REQ-253
assert_report "lint(logseq): undecided domain row flagged, staging row accepted (REQ-251)" \
  "len([f for f in r['findings'] if f['id'] == 'REQ-251' and 'undecided' in f['message']]) == 1"
assert_report "lint(logseq): no wiki-only findings on glossary pages (REQ-1002)" \
  "not [f for f in r['findings'] if f['page'].startswith('glossary') and f['id'] not in ('REQ-250', 'REQ-251', 'REQ-252', 'REQ-253')]"

# ---------------------------------------------------------------------------
# setup.sh personal tier (setup REQ-803) + archive_db config key (config
# REQ-626). setup.sh runs non-interactively here: no init, no pointer.
# ---------------------------------------------------------------------------
run bash "$REPO_ROOT/setup.sh" --project "$WORK/tier-default"
assert_exit 0 "setup: default install runs clean"
run test -d "$WORK/tier-default/.claude/skills/wiki-ingest"
assert_exit 0 "setup: default install includes wiki-ingest"
run test -d "$WORK/tier-default/.claude/skills/wiki-ingest-voice"
assert_exit 1 "setup: default install SKIPS wiki-ingest-voice (REQ-803)"
run test -d "$WORK/tier-default/.claude/skills/wiki-chat-voice"
assert_exit 1 "setup: default install SKIPS wiki-chat-voice (REQ-803)"

# Agent definitions (REQ-807): installed by default, all four, with model
# frontmatter intact; --symlink links instead of copying.
for agent in wiki-triage wiki-audit-verify wiki-audit-judge wiki-synthesize; do
  run test -f "$WORK/tier-default/.claude/agents/$agent.md"
  assert_exit 0 "setup: default install includes agents/$agent (REQ-807)"
done
run grep -q "^model: haiku" "$WORK/tier-default/.claude/agents/wiki-triage.md"
assert_exit 0 "setup: installed wiki-triage keeps its model: frontmatter (REQ-807)"
run bash "$REPO_ROOT/setup.sh" --project "$WORK/tier-symlink" --symlink
assert_exit 0 "setup: --symlink install runs clean"
run test -L "$WORK/tier-symlink/.claude/agents/wiki-triage.md"
assert_exit 0 "setup: --symlink links agent definitions (REQ-807)"

run bash "$REPO_ROOT/setup.sh" --project "$WORK/tier-personal" --with-personal
assert_exit 0 "setup: --with-personal install runs clean"
run test -d "$WORK/tier-personal/.claude/skills/wiki-ingest-voice"
assert_exit 0 "setup: --with-personal installs wiki-ingest-voice (REQ-803)"
run test -d "$WORK/tier-personal/.claude/skills/wiki-chat-voice"
assert_exit 0 "setup: --with-personal installs wiki-chat-voice (REQ-803)"

# ---------------------------------------------------------------------------
# chat-voice browse (ingest REQ-1200): the picker read lists processed and
# unprocessed rows newest first and is mechanically read-only against
# archive.db (mode=ro URI; the db bytes are unchanged by browsing).
# ---------------------------------------------------------------------------
CHATDB="$WORK/chat-archive.db"
python3 - "$CHATDB" <<'PY'
import sys, sqlite3
db = sqlite3.connect(sys.argv[1])
db.execute("""CREATE TABLE voice_notes (
    id INTEGER PRIMARY KEY, recorded_at TEXT, duration REAL,
    transcript TEXT, audio_path TEXT, processed INTEGER DEFAULT 0)""")
db.execute("INSERT INTO voice_notes VALUES (1, '2026-07-05T18:40:00+02:00', "
           "62.0, 'older memo already drained by the queue ingest', "
           "'/tmp/a.m4a', 1)")
db.execute("INSERT INTO voice_notes VALUES (2, '2026-07-06T17:05:00+02:00', "
           "88.0, 'newer memo still waiting in the queue', "
           "'/tmp/b.m4a', 0)")
db.commit()
PY
hash_db() {
  python3 -c 'import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}
CHATDB_BEFORE="$(hash_db "$CHATDB")"

# The browse snippet from skills/wiki-chat-voice/SKILL.md Phase 0, verbatim.
run python3 - "$CHATDB" <<'PY'
import sys, sqlite3, pathlib
db = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
rows = db.execute(
    "SELECT id, recorded_at, duration, processed, audio_path, transcript "
    "FROM voice_notes ORDER BY id DESC LIMIT 20").fetchall()
for id_, rec, dur, proc, audio, t in rows:
    words = t.split()
    print("%s | %s | %.0fs | %s | %s | %d words | %s..." % (
        id_, rec[:16], dur,
        "processed" if proc else "UNPROCESSED",
        pathlib.PurePath(audio).name if audio else "-",
        len(words), " ".join(words[:12])))
PY
assert_exit 0 "chat-voice: browse query runs clean (REQ-1200)"
if head -1 "$OUT" | grep -q '^2 | 2026-07-06' \
  && head -1 "$OUT" | grep -q 'UNPROCESSED' \
  && sed -n 2p "$OUT" | grep -q '^1 | 2026-07-05' \
  && sed -n 2p "$OUT" | grep -q '| processed |'; then
  report PASS "chat-voice: picker lists newest first with processed marks (REQ-1200)"
else
  report FAIL "chat-voice: picker lists newest first with processed marks (REQ-1200)"
fi
# Original filename in the picker (issue #121): basename of audio_path only,
# never the full cold-storage path.
if head -1 "$OUT" | grep -q '| b\.m4a |' \
  && sed -n 2p "$OUT" | grep -q '| a\.m4a |' \
  && ! grep -q '/tmp/a\.m4a' "$OUT"; then
  report PASS "chat-voice: picker shows the original filename (REQ-1200, issue #121)"
else
  report FAIL "chat-voice: picker shows the original filename (REQ-1200, issue #121)"
fi
if [[ "$(hash_db "$CHATDB")" == "$CHATDB_BEFORE" ]]; then
  report PASS "chat-voice: browse left archive.db bytes unchanged (REQ-1200)"
else
  report FAIL "chat-voice: browse left archive.db bytes unchanged (REQ-1200)"
fi

# A write through the read-only connection must fail: the mode=ro URI is
# the mechanical guarantee behind REQ-1200/1202.
run python3 - "$CHATDB" <<'PY'
import sys, sqlite3
db = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
try:
    db.execute("UPDATE voice_notes SET processed = 1 WHERE id = 2")
    db.commit()
except sqlite3.OperationalError:
    sys.exit(1)
sys.exit(0)
PY
assert_exit 1 "chat-voice: read-only connection refuses a write (REQ-1200)"

ARCHWIKI="$WORK/arch-wiki"
make_wiki "$ARCHWIKI" logseq
echo "archive_db: ~/archive/archive.db" >>"$ARCHWIKI/llm-wiki.yml"
echo "index_db: ~/archive/index.db" >>"$ARCHWIKI/llm-wiki.yml"
run py check_config.py "$ARCHWIKI/llm-wiki.yml"
assert_exit 0 "check_config: archive_db and index_db are known optional keys (REQ-626/627)"

# ---------------------------------------------------------------------------
# rebuild_index.py (storage REQ-1130..1133, config REQ-627)
# ---------------------------------------------------------------------------
IDXWIKI="$WORK/idx-wiki"
make_wiki "$IDXWIKI" logseq
echo "index_db: $WORK/idx-db/index.db" >>"$IDXWIKI/llm-wiki.yml"
cat >"$IDXWIKI/pages/wiki___people___Ada Example.md" <<'EOF'
schema-spec-version:: 2.0.0
type:: person
alias:: Ada, A. Example
created:: 2026-07-01
updated:: 2026-07-01

- ## Ada Example
	- Fixture person page for the index harness.
- ## Cross-References
	- [[wiki/people]]
EOF
mkdir -p "$IDXWIKI/journals"
cat >"$IDXWIKI/journals/2026_07_01.md" <<'EOF'
- #meeting sync with [[wiki/people/Ada Example]] about the index layer
- an ordinary journal line without a tag
EOF

run py rebuild_index.py --config "$IDXWIKI/llm-wiki.yml" --json
assert_exit 0 "rebuild_index: clean rebuild on scaffolded vault"
assert_report "rebuild_index: one people row indexed (REQ-1130)" \
  "r['people'] == 1"
assert_report "rebuild_index: one #meeting block indexed with the journal date" \
  "r['meetings'] == 1"

# Reproducibility (REQ-1131): two rebuilds from the same vault state
# produce identical dumps.
run python3 - "$SCRIPT_DIR/rebuild_index.py" "$IDXWIKI/llm-wiki.yml" \
  "$WORK/idx-db/index.db" <<'PY'
import hashlib, sqlite3, subprocess, sys
script, config, db_path = sys.argv[1:4]
def dump_hash():
    db = sqlite3.connect(db_path)
    digest = hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()
    db.close()
    return digest
first = dump_hash()
subprocess.run([sys.executable, script, "--config", config],
               check=True, capture_output=True)
sys.exit(0 if dump_hash() == first else 1)
PY
assert_exit 0 "rebuild_index: two rebuilds produce identical dumps (REQ-1131)"

# The three P-5 SQL template shapes (query.md REQ-462) run against the
# frozen schema and find the fixture rows.
run python3 - "$WORK/idx-db/index.db" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
people = db.execute(
    "SELECT page, name, aliases FROM people WHERE name LIKE ? OR "
    "aliases LIKE ?", ("%Ada%", "%Ada%")).fetchall()
meetings = db.execute(
    "SELECT page, date, text FROM meetings WHERE date BETWEEN ? AND ? "
    "ORDER BY date, page", ("2026-07-01", "2026-07-31")).fetchall()
fts = db.execute(
    "SELECT page FROM page_text WHERE page_text MATCH ? ORDER BY rank",
    ("index",)).fetchall()
ok = (len(people) == 1 and len(meetings) == 1
      and meetings[0][1] == "2026-07-01"
      and any("journals/2026_07_01" in row for row, in [(r[0],) for r in fts]))
sys.exit(0 if ok else 1)
PY
assert_exit 0 "rebuild_index: P-5 SQL templates (people, meetings, fts) hit the fixtures (REQ-462)"

run py rebuild_index.py --config "$IDXWIKI/llm-wiki.yml" --stale-check
assert_exit 0 "rebuild_index: stale-check fresh after rebuild (REQ-1133)"
echo "- new content" >"$IDXWIKI/pages/wiki___tech___fresh-page.md"
run py rebuild_index.py --config "$IDXWIKI/llm-wiki.yml" --stale-check
assert_exit 1 "rebuild_index: stale-check detects a vault change (REQ-1133)"
run py rebuild_index.py --config "$IDXWIKI/llm-wiki.yml"
assert_exit 0 "rebuild_index: rebuild clears staleness"

# Placement guard (REQ-1103): a target inside the vault's git tree that is
# not gitignored is refused; gitignoring it makes the same path legal.
git -C "$IDXWIKI" -c init.defaultBranch=main init -q
cp "$IDXWIKI/llm-wiki.yml" "$IDXWIKI/llm-wiki-inside.yml"
sed -i.bak "s|^index_db:.*|index_db: $IDXWIKI/index.db|" \
  "$IDXWIKI/llm-wiki-inside.yml" && rm "$IDXWIKI/llm-wiki-inside.yml.bak"
run py rebuild_index.py --config "$IDXWIKI/llm-wiki-inside.yml"
assert_exit 2 "rebuild_index: refuses an unignored in-vault target (REQ-1103)"
echo "index.db" >>"$IDXWIKI/.gitignore"
run py rebuild_index.py --config "$IDXWIKI/llm-wiki-inside.yml"
assert_exit 0 "rebuild_index: gitignored in-vault target is accepted (REQ-1103)"

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
