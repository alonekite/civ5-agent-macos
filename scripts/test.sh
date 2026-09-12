#!/usr/bin/env bash

set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo_dir"

export PYTHONPATH="${repo_dir}/src"
python3 -Wd -m unittest discover -s tests -v
python3 -m compileall -q src tests

for script in scripts/*.sh; do
  bash -n "$script"
done
