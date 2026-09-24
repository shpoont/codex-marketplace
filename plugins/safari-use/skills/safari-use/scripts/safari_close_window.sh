#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  safari_close_window.sh --window-id <id>

Attempt to close a specific Safari window id and report the resulting state as JSON.

Classifications:
  - already_absent
  - closed
  - empty_window_persisted
  - window_still_open
  - close_error

Notes:
  - This helper does not front Safari.
  - Safari may keep a real 0-tab window object alive after close.
  - Treat `empty_window_persisted` as a Safari cleanup blocker, not a success.
USAGE
}

window_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --window-id)
      window_id="${2:-}"
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

WINDOW_ID="$window_id" osascript <<'APPLESCRIPT'
on replaceText(findText, replaceWith, subjectText)
  set AppleScript's text item delimiters to findText
  set textItems to text items of subjectText
  set AppleScript's text item delimiters to replaceWith
  set newText to textItems as text
  set AppleScript's text item delimiters to ""
  return newText
end replaceText

on jsonEscape(v)
  if v is missing value then set v to ""
  set v to v as text
  set v to my replaceText("\\", "\\\\", v)
  set v to my replaceText("\"", "\\\"", v)
  set v to my replaceText(return, "\\n", v)
  set v to my replaceText(linefeed, "\\n", v)
  set v to my replaceText(tab, "\\t", v)
  return v
end jsonEscape

on findWindowById(windowIdNum)
  tell application "Safari"
    repeat with w in every window
      if (id of w as integer) is windowIdNum then
        return w
      end if
    end repeat
  end tell
  return missing value
end findWindowById

using terms from application "Safari"
  on windowStateJSONForId(windowIdNum)
    tell application "Safari"
      set targetWindow to my findWindowById(windowIdNum)
      if targetWindow is missing value then return "null"

      set wid to id of targetWindow
      set widx to index of targetWindow
      set tabCount to count of tabs of targetWindow
      set currentTabIndex to -1
      if tabCount > 0 then
        try
          set currentTabIndex to index of current tab of targetWindow
        end try
      end if

      return "{\"id\":" & wid & ",\"index\":" & widx & ",\"tab_count\":" & tabCount & ",\"current_tab_index\":" & currentTabIndex & "}"
    end tell
  end windowStateJSONForId
end using terms from

set windowIdText to (system attribute "WINDOW_ID")
if windowIdText is "" then error "WINDOW_ID is empty" number 1

try
  set windowIdNum to windowIdText as integer
on error
  error "Invalid --window-id: " & windowIdText number 1
end try

tell application "Safari"
  if not running then return "{\"closed\":true,\"window_id\":" & windowIdNum & ",\"classification\":\"already_absent\",\"before\":null,\"after\":null}"
end tell

set targetWindow to my findWindowById(windowIdNum)
if targetWindow is missing value then
  return "{\"closed\":true,\"window_id\":" & windowIdNum & ",\"classification\":\"already_absent\",\"before\":null,\"after\":null}"
end if

set beforeStateJSON to my windowStateJSONForId(windowIdNum)

try
  tell application "Safari"
    close (first window whose id is windowIdNum)
  end tell
on error errMsg number errNum
  set afterStateJSON to my windowStateJSONForId(windowIdNum)
  return "{\"closed\":false,\"window_id\":" & windowIdNum & ",\"classification\":\"close_error\",\"before\":" & beforeStateJSON & ",\"after\":" & afterStateJSON & ",\"error\":\"" & my jsonEscape(errMsg & " (code " & errNum & ")") & "\"}"
end try

set remainingWindow to my findWindowById(windowIdNum)
if remainingWindow is missing value then
  return "{\"closed\":true,\"window_id\":" & windowIdNum & ",\"classification\":\"closed\",\"before\":" & beforeStateJSON & ",\"after\":null}"
end if

set afterStateJSON to my windowStateJSONForId(windowIdNum)

tell application "Safari"
  set remainingTabCount to count of tabs of (first window whose id is windowIdNum)
end tell

if remainingTabCount is 0 then
  return "{\"closed\":false,\"window_id\":" & windowIdNum & ",\"classification\":\"empty_window_persisted\",\"before\":" & beforeStateJSON & ",\"after\":" & afterStateJSON & "}"
end if

return "{\"closed\":false,\"window_id\":" & windowIdNum & ",\"classification\":\"window_still_open\",\"before\":" & beforeStateJSON & ",\"after\":" & afterStateJSON & "}"
APPLESCRIPT
