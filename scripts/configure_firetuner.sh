#!/usr/bin/env bash

# Reversible FireTuner configuration for the Mac App Store edition.

set -eu

action="${1:-status}"
user_data_dir="${HOME}/Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/Civilization V Campaign Edition"
config_path="${user_data_dir}/config.ini"
backup_path="${user_data_dir}/config.ini.civ5-agent-backup"

show_status() {
  grep -E '^(EnableTuner|SendRemarksToTuner|LoggingEnabled)[[:space:]]*=' "$config_path"
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
