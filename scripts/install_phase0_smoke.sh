#!/usr/bin/env bash

# Installs the Phase 0 smoke mod into the Mac App Store edition's sandbox.
# Existing installations are never overwritten.

set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
source_dir="${script_dir}/../mods/phase0_smoke"
mods_dir="${HOME}/Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/Civilization V Campaign Edition/MODS"
target_dir="${mods_dir}/Civ5 Agent Phase 0 Smoke (v 1)"

if [ ! -d "$mods_dir" ]; then
  printf 'ERROR: Civ V MODS directory not found: %s\n' "$mods_dir" >&2
  exit 1
fi

if [ -e "$target_dir" ]; then
  printf 'ERROR: refusing to overwrite existing path: %s\n' "$target_dir" >&2
  exit 1
fi

mkdir "$target_dir"
cp "${source_dir}/Phase0Smoke.lua" "$target_dir/"
cp "${source_dir}/Phase0Smoke.xml" "$target_dir/"
cp "${source_dir}/Civ5 Agent Phase 0 Smoke (v 1).modinfo" "$target_dir/"

printf 'Installed: %s\n' "$target_dir"
printf 'Next: open Civ V > MODS, enable "Civ5 Agent Phase 0 Smoke", and start a game.\n'
