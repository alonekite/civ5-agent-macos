#!/usr/bin/env bash

# Read-only verification of the marker written by Phase0Smoke.lua.

set -u

mod_id="0de02ea8-297d-4d14-9cb5-3151ff03e3bf"
expected_marker="CIV5_AGENT_PHASE0_SMOKE_LOADED"
user_data_dir="${HOME}/Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/Civilization V Campaign Edition"
database_path="${user_data_dir}/ModUserData/${mod_id}-1.db"

if ! command -v sqlite3 >/dev/null 2>&1; then
  printf 'UNVERIFIED: sqlite3 is not available\n'
  exit 2
fi

if [ ! -f "$database_path" ]; then
  printf 'UNVERIFIED: smoke database does not exist: %s\n' "$database_path"
  exit 2
fi

marker="$(sqlite3 -readonly "$database_path" "SELECT Value FROM SimpleValues WHERE Name = 'phase0_marker';" 2>/dev/null)"
status="$(sqlite3 -readonly "$database_path" "SELECT Value FROM SimpleValues WHERE Name = 'phase0_smoke';" 2>/dev/null)"

if [ "$marker" = "$expected_marker" ] && [ "$status" = "loaded" ]; then
  printf 'CONFIRMED: custom Lua mod loaded and wrote the expected marker\n'
  printf 'Database: %s\n' "$database_path"
  exit 0
fi

printf 'REJECTED: database exists but expected marker values do not match\n'
printf 'phase0_smoke=%s\nphase0_marker=%s\n' "$status" "$marker"
exit 1
