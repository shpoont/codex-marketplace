#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  safari_eval_js_window.sh --window-id <id> --js-file <path>
  safari_eval_js_window.sh --window-id <id> --js '<javascript>'

Run JavaScript in the current tab of a specific Safari window id.

Notes:
  - Prefer --js-file for robust quoting.
  - If the JS returns an object/array, use JSON.stringify(...) in JS.
USAGE
}

window_id=""
js_file=""
inline_js=""
tmp_js=""

cleanup() {
  if [[ -n "$tmp_js" && -f "$tmp_js" ]]; then
    rm -f "$tmp_js"
  fi
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --window-id)
      window_id="${2:-}"
      shift 2
      ;;
    --js-file)
      js_file="${2:-}"
      shift 2
      ;;
    --js)
      inline_js="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$window_id" ]]; then
  echo "Missing required --window-id" >&2
  usage >&2
  exit 2
fi

if [[ -z "$js_file" && -z "$inline_js" ]]; then
  echo "Provide one of --js-file or --js" >&2
  usage >&2
  exit 2
fi

if [[ -n "$js_file" && -n "$inline_js" ]]; then
  echo "Use either --js-file or --js, not both" >&2
  usage >&2
  exit 2
fi

if [[ -n "$inline_js" ]]; then
  tmp_js="$(mktemp /tmp/safari_eval_js.XXXXXX.js)"
  printf '%s' "$inline_js" >"$tmp_js"
  js_file="$tmp_js"
fi

if [[ ! -f "$js_file" ]]; then
  echo "JS file not found: $js_file" >&2
  exit 2
fi

WINDOW_ID="$window_id" JS_FILE="$js_file" osascript <<'APPLESCRIPT'
on fail(msg)
  error msg number 1
end fail

set windowIdText to (system attribute "WINDOW_ID")
set jsPath to (system attribute "JS_FILE")

if windowIdText is "" then my fail("WINDOW_ID is empty")
if jsPath is "" then my fail("JS_FILE is empty")

try
  set windowIdNum to windowIdText as integer
on error
  my fail("Invalid --window-id: " & windowIdText)
end try

tell application "Safari"
  if not running then my fail("Safari is not running")

  set targetWindow to missing value
  repeat with w in every window
    if (id of w as integer) is windowIdNum then
      set targetWindow to w
      exit repeat
    end if
  end repeat

  if targetWindow is missing value then
    my fail("No Safari window with id " & windowIdText)
  end if

  set tabCount to count of tabs of targetWindow
  if tabCount is 0 then
    my fail("Safari window id " & windowIdText & " has no tabs")
  end if

  set jsCode to read (POSIX file jsPath) as «class utf8»
  try
    set resultValue to do JavaScript jsCode in current tab of targetWindow
  on error errMsg number errNum
    my fail("JavaScript execution failed: " & errMsg & " (code " & errNum & ")")
  end try

  if resultValue is missing value then return ""
  return resultValue as text
end tell
APPLESCRIPT
