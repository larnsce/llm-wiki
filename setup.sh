#!/usr/bin/env bash
# llm-wiki installer (v2).
#
# Thin by design. It does three things:
#   1. copies or symlinks the skills/wiki-* directories into a Claude Code
#      skills directory (user-level by default, project-level with --project)
#   2. optionally scaffolds a wiki by delegating to
#      skills/wiki-core/scripts/init_wiki.py (no page logic lives here)
#   3. optionally writes the global pointer file
#      ~/.config/llm-wiki/config.yml so config discovery works from anywhere
#
# It patches no files during install: config location is resolved at runtime
# by discovery (openspec/specs/config.md REQ-652). It also detects a legacy
# v1 install (.claude/commands/wiki.md) and offers to remove it.
#
# Spec: openspec/specs/setup.md (REQ-800..806 cover the install steps).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INIT_SCRIPT="$SCRIPT_DIR/skills/wiki-core/scripts/init_wiki.py"
REPO_URL="https://github.com/larnsce/llm-wiki"

usage() {
    cat <<'USAGE'
Usage: setup.sh [options]

Install the llm-wiki skill suite for Claude Code and optionally scaffold a
wiki. Run it from a checkout of the llm-wiki repository.

Options:
  --project <path>     install skills into <path>/.claude/skills/ instead of
                       the default ~/.claude/skills/
  --symlink            symlink the skill directories instead of copying them
                       (updates with the checkout; do not delete the checkout)
  --init               scaffold a wiki via init_wiki.py; in a non-interactive
                       run this requires --tool and --wiki-path
  --tool <name>        note-taking tool: logseq or obsidian
  --wiki-path <path>   wiki/vault root directory (created if missing)
  --namespaces "<A B>" space-separated namespace list (default: Business Tech
                       Content Projects People Learning Reference)
  --memory-path <path> Claude Code memory directory (optional)
  --git-init           run git init plus a best-effort initial commit in the
                       scaffolded wiki (also offered interactively)
  --pointer            write ~/.config/llm-wiki/config.yml (needs a wiki path)
  --no-pointer         never write the pointer file
  --yes                assume "yes" for all offers (legacy removal, pointer
                       file, git init); intended for non-interactive runs
  --help               show this help and exit

Examples:
  ./setup.sh                                 # user-level skill install
  ./setup.sh --project ~/myrepo --symlink    # project-level, symlinked
  ./setup.sh --init --tool logseq --wiki-path ~/notes --yes
USAGE
}

# ----- Flag parsing -----

PROJECT=""
LINK_MODE="copy"
ASSUME_YES=0
DO_INIT=0
TOOL=""
WIKI_PATH=""
NAMESPACES=""
MEMORY_PATH=""
GIT_INIT=0
POINTER_MODE="offer"   # offer | force | never

need_value() {
    if [ "$#" -lt 2 ]; then
        echo "ERROR: $1 requires a value." >&2
        exit 1
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --project)     need_value "$@"; PROJECT="$2"; shift 2 ;;
        --symlink)     LINK_MODE="symlink"; shift ;;
        --init)        DO_INIT=1; shift ;;
        --tool)        need_value "$@"; TOOL="$2"; shift 2 ;;
        --wiki-path)   need_value "$@"; WIKI_PATH="$2"; shift 2 ;;
        --namespaces)  need_value "$@"; NAMESPACES="$2"; shift 2 ;;
        --memory-path) need_value "$@"; MEMORY_PATH="$2"; shift 2 ;;
        --git-init)    GIT_INIT=1; shift ;;
        --pointer)     POINTER_MODE="force"; shift ;;
        --no-pointer)  POINTER_MODE="never"; shift ;;
        --yes|-y)      ASSUME_YES=1; shift ;;
        --help|-h)     usage; exit 0 ;;
        *)             echo "ERROR: unknown option '$1' (see --help)." >&2; exit 1 ;;
    esac
done

# ----- Helpers -----

expand_tilde() {
    case "$1" in
        "~")   printf '%s\n' "$HOME" ;;
        "~/"*) printf '%s/%s\n' "$HOME" "${1#\~/}" ;;
        *)     printf '%s\n' "$1" ;;
    esac
}

is_interactive() {
    [ -t 0 ]
}

# confirm <question>: yes with --yes; otherwise prompt when interactive.
# In a non-interactive run without --yes the answer is "no".
confirm() {
    if [ "$ASSUME_YES" = 1 ]; then
        echo "$1 -> yes (--yes)"
        return 0
    fi
    if ! is_interactive; then
        return 1
    fi
    local answer=""
    read -r -p "$1 [y/N]: " answer
    case "$answer" in
        y|Y|yes|YES) return 0 ;;
        *)           return 1 ;;
    esac
}

# ----- Sanity checks -----

if [ ! -d "$SCRIPT_DIR/skills/wiki-core" ]; then
    echo "ERROR: skills/wiki-core not found next to setup.sh." >&2
    echo "Run setup.sh from a checkout of the llm-wiki repository." >&2
    exit 1
fi

[ -n "$PROJECT" ] && PROJECT="$(expand_tilde "$PROJECT")"
[ -n "$WIKI_PATH" ] && WIKI_PATH="$(expand_tilde "$WIKI_PATH")"
[ -n "$MEMORY_PATH" ] && MEMORY_PATH="$(expand_tilde "$MEMORY_PATH")"

echo ""
echo "llm-wiki setup (v2)"
echo ""

# ----- Step 1: Install the skill suite (REQ-800..802) -----

if [ -n "$PROJECT" ]; then
    SKILLS_DEST="$PROJECT/.claude/skills"
else
    SKILLS_DEST="$HOME/.claude/skills"
fi
mkdir -p "$SKILLS_DEST"

echo "Installing skills into $SKILLS_DEST ($LINK_MODE mode):"
for src in "$SCRIPT_DIR"/skills/wiki-*; do
    [ -d "$src" ] || continue
    name="$(basename "$src")"
    dest="$SKILLS_DEST/$name"
    replaced=""
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        rm -rf "$dest"
        replaced=" (replaced existing)"
    fi
    if [ "$LINK_MODE" = "symlink" ]; then
        ln -s "$src" "$dest"
    else
        cp -R "$src" "$dest"
    fi
    echo "  $name -> $dest$replaced"
done
echo ""

# ----- Step 2: Legacy v1 detection (REQ-806) -----

check_legacy() {
    local legacy="$1"
    if [ -f "$legacy" ]; then
        echo "Legacy v1 install detected: $legacy"
        echo "The old single-command /wiki file keeps working but is unsupported;"
        echo "the skill suite installed above replaces it."
        if confirm "Remove $legacy?"; then
            rm "$legacy"
            echo "  Removed: $legacy"
        else
            echo "  Kept: $legacy"
        fi
        echo ""
    fi
}

check_legacy "$HOME/.claude/commands/wiki.md"
if [ -n "$PROJECT" ]; then
    check_legacy "$PROJECT/.claude/commands/wiki.md"
fi

# ----- Step 3: Optional wiki scaffolding (delegated to init_wiki.py) -----

if [ "$DO_INIT" = 0 ] && is_interactive; then
    if confirm "Scaffold a wiki now (Schema, Dashboard, hubs, config)?"; then
        DO_INIT=1
    fi
fi

INIT_RAN=0
if [ "$DO_INIT" = 1 ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERROR: python3 is required for wiki scaffolding." >&2
        exit 1
    fi

    if [ -z "$TOOL" ]; then
        if is_interactive; then
            echo "Which note-taking tool do you use?"
            echo "  1) Logseq"
            echo "  2) Obsidian"
            read -r -p "Enter choice [1/2]: " tool_choice
            case "$tool_choice" in
                1) TOOL="logseq" ;;
                2) TOOL="obsidian" ;;
                *) echo "ERROR: invalid choice." >&2; exit 1 ;;
            esac
        else
            echo "ERROR: --init in a non-interactive run requires --tool." >&2
            exit 1
        fi
    fi

    if [ -z "$WIKI_PATH" ]; then
        if is_interactive; then
            if [ "$TOOL" = "logseq" ]; then
                default_path="$HOME/Documents/Logseq"
            else
                default_path="$HOME/Documents/ObsidianVault"
            fi
            read -r -p "Wiki path [$default_path]: " WIKI_PATH
            WIKI_PATH="${WIKI_PATH:-$default_path}"
            WIKI_PATH="$(expand_tilde "$WIKI_PATH")"
        else
            echo "ERROR: --init in a non-interactive run requires --wiki-path." >&2
            exit 1
        fi
    fi

    if [ -z "$NAMESPACES" ] && is_interactive; then
        echo "Namespaces (default: Business Tech Content Projects People Learning Reference)"
        read -r -p "Space-separated list (Enter for default): " NAMESPACES
    fi

    init_args=(--wiki-path "$WIKI_PATH" --tool "$TOOL")
    if [ -n "$NAMESPACES" ]; then
        read -r -a ns_array <<< "$NAMESPACES"
        init_args+=(--namespaces "${ns_array[@]}")
    fi
    if [ -n "$MEMORY_PATH" ]; then
        init_args+=(--memory-path "$MEMORY_PATH")
    fi

    echo ""
    init_status=0
    python3 "$INIT_SCRIPT" "${init_args[@]}" || init_status=$?
    if [ "$init_status" -ge 2 ]; then
        echo "ERROR: init_wiki.py failed (exit $init_status)." >&2
        exit "$init_status"
    fi
    INIT_RAN=1
    echo ""
fi

# ----- Step 4: Optional git init in the wiki (REQ-760..765, 810..812) -----

if [ "$INIT_RAN" = 1 ] && command -v git >/dev/null 2>&1 \
        && [ ! -d "$WIKI_PATH/.git" ]; then
    if [ "$GIT_INIT" = 1 ] || confirm "Initialize git in $WIKI_PATH?"; then
        git init "$WIKI_PATH"
        git -C "$WIKI_PATH" add -A
        ns_count="$(echo "${NAMESPACES:-Business Tech Content Projects People Learning Reference}" | wc -w | tr -d ' ')"
        git -C "$WIKI_PATH" commit -m "wiki: initial setup via llm-wiki

Schema, Dashboard, and hub pages for $ns_count namespaces.
Tool: $TOOL

Generated by $REPO_URL" >/dev/null 2>&1 || true
        echo "Git initialized in $WIKI_PATH (initial commit is best-effort)."
        echo ""
    fi
fi

# ----- Step 5: Global pointer file (REQ-805, config REQ-653) -----

POINTER_FILE="$HOME/.config/llm-wiki/config.yml"
POINTER_WRITTEN=0

write_pointer() {
    local wiki_abs="$1"
    mkdir -p "$(dirname "$POINTER_FILE")"
    printf '# llm-wiki global pointer file (openspec/specs/config.md REQ-653)\n# Written by setup.sh on %s\nwiki_path: %s\n' \
        "$(date +%Y-%m-%d)" "$wiki_abs" > "$POINTER_FILE"
    POINTER_WRITTEN=1
    echo "Pointer file written: $POINTER_FILE -> $wiki_abs"
    echo ""
}

if [ "$POINTER_MODE" != "never" ]; then
    if [ -n "$WIKI_PATH" ]; then
        if [ -d "$WIKI_PATH" ]; then
            WIKI_ABS="$(cd "$WIKI_PATH" && pwd)"
        else
            WIKI_ABS="$WIKI_PATH"
        fi
        if [ -f "$POINTER_FILE" ] && grep -q "^wiki_path: $WIKI_ABS$" "$POINTER_FILE"; then
            echo "Pointer file already points at $WIKI_ABS; leaving it as is."
            echo ""
        elif [ "$POINTER_MODE" = "force" ]; then
            write_pointer "$WIKI_ABS"
        elif confirm "Write pointer file $POINTER_FILE (wiki_path: $WIKI_ABS)?"; then
            write_pointer "$WIKI_ABS"
        fi
    elif [ "$POINTER_MODE" = "force" ]; then
        echo "ERROR: --pointer needs a wiki path (pass --wiki-path or --init)." >&2
        exit 1
    fi
fi

# ----- Summary (REQ-820..821) -----

echo "Setup complete."
echo ""
echo "Skills installed: $SKILLS_DEST"
if [ "$INIT_RAN" = 1 ]; then
    echo "Wiki scaffolded:  $WIKI_PATH"
    echo "Config file:      $WIKI_PATH/llm-wiki.yml"
fi
if [ "$POINTER_WRITTEN" = 1 ]; then
    echo "Pointer file:     $POINTER_FILE"
fi
echo ""
echo "Next steps:"
if [ "$INIT_RAN" = 1 ]; then
    echo "  1. Open your wiki in $TOOL"
else
    echo "  1. Scaffold a wiki: ./setup.sh --init (or run /wiki-setup in Claude Code)"
fi
echo "  2. In Claude Code, try: /wiki-ingest \"your first source\""
echo "  3. Run /wiki-maintain for a status report"
echo ""
echo "Documentation: $REPO_URL"
