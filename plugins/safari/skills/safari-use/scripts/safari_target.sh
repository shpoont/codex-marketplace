#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '%s\n' 'Usage: safari_target.sh <open|bind|inspect|eval|transition|recover|resolve> --target-file <path> [options]' \
    '  open     --url <url> [--recover-readonly] [--recovery-limit <0..3>]' \
    '  bind     --window-id <id> --tab-index <index> --expect-url <url>' \
    '  inspect  Reconcile the marked tab inside the tracked window.' \
    '  eval     --js-file <body.js> --guard-file <predicate.js> --effect <read|write>' \
    '  transition --expect-url <observed-authorized-url> --guard-file <predicate.js>' \
    '  recover  Create a replacement reader only if explicitly enabled at open.' \
    '  resolve  --operation-id <id> --evidence <sanitized outcome evidence>' \
    'JS files contain synchronous function bodies with explicit return statements.' \
    'A tab index is used only for initial binding or fresh dispatch, never as identity.'
}

if [[ $# == 0 || "$1" == --help || "$1" == -h ]]; then usage; exit 0; fi
target_file=""
previous=""
for argument in "$@"; do
  if [[ "$previous" == --target-file ]]; then target_file="$argument"; fi
  previous="$argument"
done
if [[ -z "$target_file" || "$target_file" == -* ]]; then
  printf '%s\n' 'Missing --target-file' >&2; exit 2
fi
if [[ ! -d "$(dirname "$target_file")" || -L "$target_file" ]]; then
  printf '%s\n' 'Target file needs an existing parent and must not be a symlink' >&2; exit 2
fi
# This lock coordinates users of this handle only, not the person or other tools.
lock_dir="${target_file}.lock"
if ! mkdir -m 700 "$lock_dir" 2>/dev/null; then
  printf '%s\n' '{"status":"busy","dispatched":false}'; exit 1
fi
cleanup() { rmdir "$lock_dir"; }
trap cleanup EXIT
umask 077
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
/usr/bin/osascript -l JavaScript "$script_dir/safari_target.js" "$@"
