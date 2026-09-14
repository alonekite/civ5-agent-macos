#!/usr/bin/env bash

# Reversible FireTuner configuration for the Mac App Store edition.

set -eu

action="${1:-status}"
user_data_dir="${HOME}/Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/Civilization V Campaign Edition"
config_path="${user_data_dir}/config.ini"
backup_path="${user_data_dir}/config.ini.civ5-agent-backup"
firewall_tool="/usr/libexec/ApplicationFirewall/socketfilterfw"
civ_executable="/Applications/Civilization V Campaign Edition.app/Contents/MacOS/Civilization V Campaign Edition"
civ_app_bundle="/Applications/Civilization V Campaign Edition.app"

show_status() {
  grep -E '^(EnableTuner|SendRemarksToTuner|LoggingEnabled)[[:space:]]*=' "$config_path"
}

require_guarded_firewall() {
  local global_state
  local apps_output
  local found_civ
  global_state="$($firewall_tool --getglobalstate)"
  if [[ "$global_state" != *"State = 1"* ]]; then
    printf 'ERROR: refusing to enable FireTuner while the macOS application firewall is disabled\n' >&2
    exit 1
  fi

  apps_output="$($firewall_tool --listapps)"
  found_civ=0
  while IFS= read -r line; do
    if [[ "$line" == *"$civ_executable"* || "$line" == *"$civ_app_bundle"* ]]; then
      found_civ=1
      continue
    fi
    if [ "$found_civ" -eq 1 ]; then
      if [[ "$line" == *"(Block incoming connections)"* ]]; then
        return
      fi
      break
    fi
  done <<< "$apps_output"

  printf 'ERROR: refusing to enable FireTuner without an explicit Civ V block-incoming firewall rule\n' >&2
  exit 1
}

if [ ! -f "$config_path" ]; then
  printf 'ERROR: config not found: %s\n' "$config_path" >&2
  exit 1
fi

case "$action" in
  status)
    show_status
    ;;
  enable)
    require_guarded_firewall
    if [ ! -f "$backup_path" ]; then
      cp -p "$config_path" "$backup_path"
      printf 'Backup created: %s\n' "$backup_path"
    fi

    match_count="$(grep -c '^EnableTuner[[:space:]]*=[[:space:]]*[01][[:space:]]*$' "$config_path")"
    if [ "$match_count" -ne 1 ]; then
      printf 'ERROR: expected one boolean EnableTuner setting, found %s\n' "$match_count" >&2
      exit 1
    fi

    temporary_file="$(mktemp /private/tmp/civ5-agent-config.XXXXXX)"
    trap 'rm -f "$temporary_file"' EXIT
    sed 's/^EnableTuner[[:space:]]*=[[:space:]]*[01][[:space:]]*$/EnableTuner = 1/' "$config_path" > "$temporary_file"
    cp "$temporary_file" "$config_path"

    if ! grep -q '^EnableTuner = 1$' "$config_path"; then
      printf 'ERROR: EnableTuner write verification failed\n' >&2
      exit 1
    fi
    printf 'FireTuner enabled and re-read successfully\n'
    printf 'WARNING: this build may listen on all IPv4 interfaces (TCP *:4318).\n' >&2
    printf 'Use only for a bounded test session; run "%s restore" afterward.\n' "$0" >&2
    show_status
    ;;
  restore)
    if [ ! -f "$backup_path" ]; then
      printf 'ERROR: backup not found: %s\n' "$backup_path" >&2
      exit 1
    fi
    cp -p "$backup_path" "$config_path"
    printf 'Original config restored and re-read\n'
    show_status
    ;;
  *)
    printf 'Usage: %s [status|enable|restore]\n' "$0" >&2
    exit 2
    ;;
esac
