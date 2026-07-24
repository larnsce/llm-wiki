#!/bin/bash
# wiki-sweep.sh - move captured clips into the vault's raw/ folder.
#
# Sweeps one or more capture folders (the iPhone shortcut's iCloud container,
# the desktop browser clipper's ~/Downloads/wiki-raw) into the vault's raw/
# queue, where /wiki-ingest picks them up. Filenames are slugified to
# kebab-case on the way in (llm-wiki #67), and an article's companion asset
# folder (name.md plus a same-named name/ folder of images) moves with it.
#
# Install:
#   1. Copy this file somewhere stable (e.g. into your vault) and edit the
#      two EDIT THIS blocks below.
#   2. Install the launchd job: see scripts/com.wiki.sweep.plist.
#   3. Logs: /tmp/wiki-sweep.log (sweeps), /tmp/wiki-sweep.err (failures).

# >>> EDIT THIS: absolute path to your vault's raw folder <<<
VAULT_RAW="$HOME/path/to/your-vault/raw"

# >>> EDIT THIS: capture folders to sweep into raw/ (one per line) <<<
#   - the iPhone shortcut's iCloud container (Shortcuts)
#   - the desktop browser clipper's output folder
SOURCES=(
  "$HOME/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/wiki-raw-phone"
  "$HOME/Downloads/wiki-raw"
)

mkdir -p "$VAULT_RAW"

# Kebab-case a filename stem so downstream cite:: refs and archive paths
# never contain spaces (llm-wiki #67).
slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

# Move one item (file or companion asset folder) into the vault by
# copy-verify-delete. A plain mv across the iCloud boundary fails with
# "Resource deadlock avoided" (iCloud treats its container as a special
# volume and refuses the atomic rename), so copy first and remove the source
# only after the copy verifies against it. A failed copy is deleted before
# logging, because cp can leave a zero-byte target behind; keeping it would
# make the next retry mint a fresh collision-suffixed name every run
# (llm-wiki #154). cp errors are not suppressed so /tmp/wiki-sweep.err
# shows why a clip is stuck.
move_item() {
  local src="$1" base slug target
  base="$(basename "$src")"

  if [ -d "$src" ]; then
    # Companion asset folder (article + its images), mirrors ingested/ layout.
    slug="$(slugify "$base")"
    [ -z "$slug" ] && slug="clip-$(date +%s)"
    target="$VAULT_RAW/$slug"
    [ -e "$target" ] && target="$VAULT_RAW/$slug-$(date +%s)"
    if cp -R "$src" "$target" && diff -rq "$src" "$target" >/dev/null; then
      rm -rf "$src"
      echo "$(date '+%Y-%m-%d %H:%M:%S') swept dir: $base -> $(basename "$target")"
    else
      rm -rf "$target"
      echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED, will retry next run: $base" >&2
    fi
  else
    local ext="${base##*.}"
    slug="$(slugify "${base%.*}")"
    [ -z "$slug" ] && slug="clip-$(date +%s)"
    target="$VAULT_RAW/$slug.$ext"
    # Name collision: keep both files, suffix the newcomer.
    [ -e "$target" ] && target="$VAULT_RAW/$slug-$(date +%s).$ext"
    if cp "$src" "$target" && cmp -s "$src" "$target"; then
      rm -f "$src"
      echo "$(date '+%Y-%m-%d %H:%M:%S') swept: $base -> $(basename "$target")"
    else
      rm -f "$target"
      echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED, will retry next run: $base" >&2
    fi
  fi
}

# Sweep one source folder: force-download iCloud content, then move the
# fully-downloaded .md/.txt files and any companion asset folders.
sweep_dir() {
  local dir="$1" tries
  [ -d "$dir" ] || return 0

  # Force-download iCloud content. Eviction takes two shapes: *.icloud
  # placeholder names, and dataless files kept under their normal names.
  # cp cannot materialize a dataless file itself (it fails persistently
  # with "Resource deadlock avoided"), so download both kinds first
  # (llm-wiki #154).
  while IFS= read -r -d '' f; do
    brctl download "$f" >/dev/null 2>&1
  done < <(find "$dir" -maxdepth 1 \( -name "*.icloud" -o -name "*.md" -o -name "*.txt" \) -print0 2>/dev/null)

  # Wait (bounded) for the downloads to land: poll until no candidate file
  # is still flagged dataless. A file that never materializes fails the
  # copy cleanly below and is retried next run.
  tries=0
  while [ "$tries" -lt 10 ]; do
    find "$dir" -maxdepth 1 \( -name "*.md" -o -name "*.txt" \) ! -name ".*" -exec stat -f %Sf {} + 2>/dev/null | grep -q dataless || break
    sleep 2
    tries=$((tries + 1))
  done

  # Files. Skip hidden files: iCloud sync artifacts and empty-title clips
  # start with a dot.
  while IFS= read -r -d '' f; do
    move_item "$f"
  done < <(find "$dir" -maxdepth 1 \( -name "*.md" -o -name "*.txt" \) ! -name ".*" -print0 2>/dev/null)

  # Companion asset folders (top level, non-hidden).
  while IFS= read -r -d '' d; do
    move_item "$d"
  done < <(find "$dir" -maxdepth 1 -mindepth 1 -type d ! -name ".*" -print0 2>/dev/null)
}

for src in "${SOURCES[@]}"; do
  sweep_dir "$src"
done
