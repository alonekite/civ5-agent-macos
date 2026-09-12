#!/usr/bin/env bash

# Installs the minimal read probe into the Mac App Store edition's sandbox.
# Existing installations are never overwritten.

set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
source_dir="${script_dir}/../mods/read_probe"
mods_dir="${HOME}/Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/Civilization V Campaign Edition/MODS"
target_dir="${mods_dir}/Civ5 Agent Read Probe (v 1)"

if [ ! -d "$mods_dir" ]; then
  printf 'ERROR: Civ V MODS directory not found: %s\n' "$mods_dir" >&2
  exit 1
fi

if [ -e "$target_dir" ]; then
  printf 'ERROR: refusing to overwrite existing path: %s\n' "$target_dir" >&2
  exit 1
fi

mkdir "$target_dir"
cp "${source_dir}/ReadProbe.lua" "$target_dir/"
cp "${source_dir}/ReadProbe.xml" "$target_dir/"
cp "${source_dir}/Civ5 Agent Read Probe (v 1).modinfo" "$target_dir/"

printf 'Installed: %s\n' "$target_dir"
