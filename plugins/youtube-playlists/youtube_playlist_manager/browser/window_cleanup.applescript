-- Close only the original command-owned window/tab, without activation.
on run argv
    set windowId to (item 1 of argv) as integer
    set guardCode to read (POSIX file (item 2 of argv)) as «class utf8»
    set allowUnbound to (item 3 of argv) is "true"
    set expectedURL to item 4 of argv
    tell application "Safari"
        if not running then return "already_absent"
        if not (exists window id windowId) then return "already_absent"
        set ownedWindow to window id windowId
        set originalCount to count of tabs of ownedWindow
        set matches to {}
        repeat with candidate in tabs of ownedWindow
            set candidateURL to URL of candidate
            if allowUnbound then
                if originalCount is 1 and (candidateURL is expectedURL or candidateURL is "about:blank" or candidateURL is "") then
                    set end of matches to candidate
                end if
            else if candidateURL starts with "https://www.youtube.com/playlist?" then
                try
                    if (do JavaScript guardCode in candidate) is "{\"owned\":true}" then set end of matches to candidate
                on error
                    return "verification_error"
                end try
            end if
        end repeat
        if originalCount is not 0 and (count of matches) is not 1 then return "preserved_changed_window"
        if originalCount > 1 then
            close (item 1 of matches)
            if not (exists window id windowId) then return "closed"
            set remainingCount to count of tabs of window id windowId
            if remainingCount is 0 then return my observeClosedWindow(windowId)
            repeat with candidate in tabs of window id windowId
                if URL of candidate starts with "https://www.youtube.com/playlist?" then
                    try
                        if (do JavaScript guardCode in candidate) is "{\"owned\":true}" then return "window_still_open"
                    on error
                        return "verification_error"
                    end try
                end if
            end repeat
            return "closed_owned_tab"
        end if
        close ownedWindow
        return my observeClosedWindow(windowId)
    end tell
end run

-- Safari can retain an invisible scripting object after releasing the page.
-- Observe the outcome once; never close again or activate Safari to erase it.
on observeClosedWindow(windowId)
    tell application "Safari"
        try
            if not (exists window id windowId) then return "closed"
            set isVisible to visible of window id windowId
            set remainingCount to count of tabs of window id windowId
            return my retainedWindowOutcome(remainingCount, isVisible)
        on error
            return "verification_error"
        end try
    end tell
end observeClosedWindow

on retainedWindowOutcome(remainingCount, isVisible)
    if remainingCount is not 0 then return "window_still_open"
    if isVisible is false then return "released_hidden_empty_window"
    if isVisible is true then return "empty_window_persisted"
    return "verification_error"
end retainedWindowOutcome
