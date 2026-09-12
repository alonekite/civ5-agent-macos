#!/usr/bin/env bash

# Read-only reconnaissance for Civilization V on macOS. Permission failures are
# reported as "unverified" rather than being mistaken for a negative result.

set -u

section() {
  printf '\n=== %s ===\n' "$1"
}

found_or_missing() {
  if [ -e "$1" ]; then
    printf 'FOUND: %s\n' "$1"
  else
    printf 'MISS : %s\n' "$1"
  fi
}

read_plist_value() {
  /usr/libexec/PlistBuddy -c "Print :$2" "$1" 2>/dev/null || printf 'unknown'
}

section "Run metadata"
date '+timestamp=%Y-%m-%dT%H:%M:%S%z'
printf 'script=%s\n' "$0"

section "macOS host"
sw_vers 2>&1 || true
printf 'MachineArchitecture: '
uname -m 2>&1 || true

section "Civilization V application candidates"
app_path=""
for candidate in \
  "/Applications/Civilization V Campaign Edition.app" \
  "/Applications/Sid Meier's Civilization V.app" \
  "${HOME}/Applications/Civilization V Campaign Edition.app" \
  "${HOME}/Applications/Sid Meier's Civilization V.app" \
  "${HOME}/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization V/Civilization V.app"
do
  found_or_missing "$candidate"
  if [ -z "$app_path" ] && [ -d "$candidate" ]; then
    app_path="$candidate"
  fi
done

if [ -n "$app_path" ]; then
  info_plist="${app_path}/Contents/Info.plist"
  executable_name="$(read_plist_value "$info_plist" CFBundleExecutable)"
  printf 'SelectedApplication: %s\n' "$app_path"
  printf 'BundleIdentifier: %s\n' "$(read_plist_value "$info_plist" CFBundleIdentifier)"
  printf 'BundleShortVersion: %s\n' "$(read_plist_value "$info_plist" CFBundleShortVersionString)"
  printf 'BundleBuildVersion: %s\n' "$(read_plist_value "$info_plist" CFBundleVersion)"
  printf 'FiraxisBuildString: %s\n' "$(read_plist_value "$info_plist" FiraxisBuildString)"
  if [ -d "${app_path}/Contents/_MASReceipt" ]; then
    printf 'DistributionEvidence: Mac App Store receipt present\n'
  elif [ -f "${app_path}/Contents/MacOS/steam_appid.txt" ]; then
    printf 'DistributionEvidence: Steam app id file present\n'
  else
    printf 'DistributionEvidence: unverified\n'
  fi
  executable_path="${app_path}/Contents/MacOS/${executable_name}"
  if [ -f "$executable_path" ]; then
    printf 'ExecutableArchitecture: '
    file -b "$executable_path" 2>&1 || true
  else
    printf 'ExecutableArchitecture: unverified (executable not found)\n'
  fi
else
  printf 'SelectedApplication: none\n'
fi

section "Rosetta"
if pkgutil --pkg-info com.apple.pkg.RosettaUpdateAuto >/dev/null 2>&1; then
  printf 'RosettaInstalled: yes\n'
  pkgutil --pkg-info com.apple.pkg.RosettaUpdateAuto 2>/dev/null | sed -n '1,3p'
else
  printf 'RosettaInstalled: no-or-unverified\n'
fi

section "Civilization V user-data candidates"
user_data_path=""
for candidate in \
  "${HOME}/Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/Civilization V Campaign Edition" \
  "${HOME}/Library/Application Support/Sid Meier's Civilization 5" \
  "${HOME}/Library/Application Support/Civilization V Campaign Edition" \
  "${HOME}/Documents/Aspyr/Sid Meier's Civilization 5"
do
  found_or_missing "$candidate"
  if [ -z "$user_data_path" ] && [ -d "$candidate" ]; then
    user_data_path="$candidate"
  fi
done

if [ -n "$user_data_path" ]; then
  printf 'SelectedUserData: %s\n' "$user_data_path"
  for relative_path in MODS ModUserData Logs Saves ModdedSaves cache config.ini UserSettings.ini; do
    found_or_missing "${user_data_path}/${relative_path}"
  done
else
  printf 'SelectedUserData: none\n'
fi

section "Bundled DLC content (presence does not prove activation)"
if [ -n "$app_path" ] && [ -d "${app_path}/Contents/Assets/Assets/DLC" ]; then
  find "${app_path}/Contents/Assets/Assets/DLC" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort
else
  printf 'UNVERIFIED: DLC content directory not found\n'
fi

section "Mod inventory and activation evidence"
if [ -n "$user_data_path" ]; then
  mods_path="${user_data_path}/MODS"
  mods_db="${user_data_path}/cache/Civ5ModsDatabase.db"
  if [ -d "$mods_path" ]; then
    custom_mod_count="$(find "$mods_path" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
    printf 'CustomModDirectories: %s\n' "$custom_mod_count"
    find "$mods_path" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort
  else
    printf 'CustomModDirectories: unverified (MODS directory missing)\n'
  fi
  if command -v sqlite3 >/dev/null 2>&1 && [ -f "$mods_db" ]; then
    printf 'ModsDatabase: %s\n' "$mods_db"
    sqlite3 -header -column "$mods_db" \
      'SELECT COUNT(*) AS installed, SUM(CASE WHEN Enabled != 0 THEN 1 ELSE 0 END) AS enabled, SUM(CASE WHEN Activated != 0 THEN 1 ELSE 0 END) AS activated FROM Mods WHERE Installed != 0;' 2>&1 || true
  else
    printf 'ModsDatabase: unverified (database or sqlite3 missing)\n'
  fi
  modding_log="${user_data_path}/Logs/modding.log"
  lua_log="${user_data_path}/Logs/Lua.log"
  if [ -f "$modding_log" ]; then
    stat -f 'ModdingLog: %N; modified=%Sm' -t '%Y-%m-%dT%H:%M:%S%z' "$modding_log"
    tail -n 20 "$modding_log" 2>/dev/null || true
  else
    printf 'ModdingLog: missing\n'
  fi
  if [ -f "$lua_log" ]; then
    stat -f 'LuaLog: %N; modified=%Sm' -t '%Y-%m-%dT%H:%M:%S%z' "$lua_log"
    tail -n 20 "$lua_log" 2>/dev/null || true
  else
    printf 'LuaLog: missing\n'
  fi
fi

section "macOS mod-browser gate"
if [ -n "$app_path" ]; then
  main_menu_lua="${app_path}/Contents/Assets/Assets/UI/FrontEnd/MainMenu.lua"
  if [ -f "$main_menu_lua" ]; then
    hide_line="$(grep -n 'Controls\.ModsButton:SetHide[[:space:]]*([[:space:]]*true[[:space:]]*)' "$main_menu_lua" 2>/dev/null || true)"
    if [ -n "$hide_line" ]; then
      printf 'MOD BROWSER DISABLED BY INSTALLED GAME ASSET:\n%s\n' "$hide_line"
    else
      printf 'No forced ModsButton hide statement detected\n'
    fi
  else
    printf 'UNVERIFIED: MainMenu.lua not found\n'
  fi
fi

section "ModUserData / OpenUserData persistence candidates"
if [ -n "$user_data_path" ] && [ -d "${user_data_path}/ModUserData" ]; then
  db_count="$(find "${user_data_path}/ModUserData" -maxdepth 1 -type f -name '*.db' 2>/dev/null | wc -l | tr -d ' ')"
  printf 'DatabaseCount: %s\n' "$db_count"
  find "${user_data_path}/ModUserData" -maxdepth 1 -type f -name '*.db' -print 2>/dev/null | sort
else
  printf 'UNVERIFIED: ModUserData directory not found\n'
fi

section "FireTuner configuration"
if [ -n "$user_data_path" ] && [ -f "${user_data_path}/config.ini" ]; then
  config_path="${user_data_path}/config.ini"
  printf 'Config: %s\n' "$config_path"
  grep -E '^(EnableTuner|SendRemarksToTuner|LoggingEnabled)[[:space:]]*=' "$config_path" 2>/dev/null || true
else
  printf 'UNVERIFIED: config.ini not found\n'
fi

section "Civilization V process"
process_output="$(pgrep -afil 'Civilization|AppBundleExe' 2>&1)"
process_status=$?
if [ "$process_status" -eq 0 ]; then
  printf '%s\n' "$process_output"
elif printf '%s' "$process_output" | grep -qiE 'not permitted|cannot get process|failed'; then
  printf 'UNVERIFIED: process inspection denied: %s\n' "$process_output"
else
  printf 'NOT DETECTED\n'
fi

section "TCP 4318 listener"
port_output="$(lsof -nP -iTCP:4318 -sTCP:LISTEN 2>&1)"
port_status=$?
if [ "$port_status" -eq 0 ] && [ -n "$port_output" ]; then
  printf '%s\n' "$port_output"
elif printf '%s' "$port_output" | grep -qiE 'not permitted|denied|failed'; then
  printf 'UNVERIFIED: listener inspection denied: %s\n' "$port_output"
else
  printf 'NOT DETECTED\n'
fi
