#!/bin/bash
# Wrapper script for prettier in pre-commit
# Strips 'frontend/' prefix from file paths before running prettier

cd frontend
files=()
for file in "$@"; do
  files+=("${file#frontend/}")
done

node_modules/.bin/prettier --write "${files[@]}"
