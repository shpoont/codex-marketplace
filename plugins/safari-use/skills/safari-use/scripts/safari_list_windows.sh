#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: safari_list_windows.sh [--current-only]

List Safari windows/tabs as JSON.

Options:
  --current-only   Only include the current tab per window
  -h, --help       Show this help
USAGE
}

current_only="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --current-only)
      current_only="true"
      shift
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

CURRENT_ONLY="$current_only" osascript <<'APPLESCRIPT'
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

on joinList(theList, separator)
  if (count of theList) = 0 then return ""
  set AppleScript's text item delimiters to separator
  set joinedText to theList as text
  set AppleScript's text item delimiters to ""
  return joinedText
end joinList

set currentOnly to (system attribute "CURRENT_ONLY")

tell application "Safari"
  if not running then return "{\"running\":false,\"window_count\":0,\"windows\":[]}"

  set windowList to every window
  set windowsOut to {}

  repeat with w in windowList
    set wid to id of w
    set widx to index of w
    set tabCount to count of tabs of w
    set currentTabIndex to -1
    if tabCount > 0 then
      try
        set currentTabIndex to index of current tab of w
      end try
    end if

    set tabsOut to {}
    if tabCount is 0 then
      set tabsToInspect to {}
    else if currentOnly is "true" then
      set tabsToInspect to {current tab of w}
    else
      set tabsToInspect to tabs of w
    end if

    repeat with t in tabsToInspect
      set tidx to -1
      set turl to ""
      set ttitle to ""
      set isCurrentText to "false"

      try
        set tidx to index of t
      end try
      try
        set turl to URL of t
      end try
      try
        set ttitle to name of t
      end try
      if tidx is currentTabIndex then set isCurrentText to "true"

      set tabJSON to "{\"index\":" & tidx & ",\"current\":" & isCurrentText & ",\"url\":\"" & my jsonEscape(turl) & "\",\"title\":\"" & my jsonEscape(ttitle) & "\"}"
      set end of tabsOut to tabJSON
    end repeat

    set windowJSON to "{\"index\":" & widx & ",\"id\":" & wid & ",\"tab_count\":" & tabCount & ",\"current_tab_index\":" & currentTabIndex & ",\"tabs\":[" & my joinList(tabsOut, ",") & "]}"
    set end of windowsOut to windowJSON
  end repeat

  return "{\"running\":true,\"window_count\":" & (count of windowList) & ",\"windows\":[" & my joinList(windowsOut, ",") & "]}"
end tell
APPLESCRIPT
