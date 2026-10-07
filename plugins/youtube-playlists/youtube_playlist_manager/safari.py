"""Safari page control only. YouTube behavior lives in transport.py."""
from __future__ import annotations

import json
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .browser_control import (TransportError, browser_session, guarded_source, page_match_source,
                              SCRIPT_TIMEOUT_SECONDS, JOB_STATUS_SCRIPT_TIMEOUT_SECONDS)


class SafariPage:
    def __init__(self, window_id: int | None = None):
        self.window_id = window_id
        self.url = None
        self.page_token = None
        self.tab_index = None
        self._owned_window_id = None
        self.cleanup_result = None
        self._read_recovery_cleanups = []

    @property
    def page_id(self):
        return self.window_id

    @property
    def can_recover(self):
        return self._owned_window_id is not None and self.window_id == self._owned_window_id

    @staticmethod
    def _script(source: str, *args: str, timeout=SCRIPT_TIMEOUT_SECONDS) -> str:
        try:
            result = subprocess.run(['osascript', '-', *args], input=source, text=True,
                                    capture_output=True, timeout=timeout, check=True)
        except subprocess.TimeoutExpired as error:
            raise TransportError(
                f'Safari AppleScript timed out after {timeout} seconds',
                {'code': 'ytpm_applescript_timeout', 'timeout_seconds': timeout},
            ) from error
        except subprocess.CalledProcessError as error:
            details = getattr(error, 'stderr', '') or ''
            for marker, message in [('YTPM_PAGE_MISSING', 'Bound Safari page was closed, reloaded or navigated; collect again'),
                                    ('YTPM_PAGE_AMBIGUOUS', 'Multiple matching Safari pages; choose a window with one target playlist tab')]:
                if marker in details:
                    raise TransportError(message, {'code': marker.lower()}) from error
            raise TransportError('Safari AppleScript failed; verify automation permission and the dedicated window') from error
        except OSError as error:
            raise TransportError('Safari AppleScript control is unavailable; it requires macOS automation access',
                                 {'code': 'browser_controller_unavailable'}) from error
        return result.stdout.strip()

    def open(self, url):
        self.url = url
        created = self.window_id is None
        if self.window_id is None:
            self.window_id = int(self._script('''on run argv
tell application "Safari"
    make new document with properties {URL:(item 1 of argv)}
    return id of window 1
end tell
end run''', self.url))
            self._owned_window_id = self.window_id
            self.cleanup_result = None
            # A command-owned page does not need to be visible while its
            # same-page data requests run. Hide it promptly so it does not
            # compete with the user's Safari windows during long collections.
            self._script('''on run argv
tell application "Safari"
    set visible of window id ((item 1 of argv) as integer) to false
end tell
end run''', str(self.window_id))
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.page_token is None:
                try:
                    self._bind_page()
                except TransportError as error:
                    if not created or error.details.get('code') != 'ytpm_page_missing':
                        raise
                    # A newly created document can still be about:blank while
                    # its first navigation starts. No page has been bound yet.
                    time.sleep(0.5)
                    continue
            return self
        raise TransportError('Browser page did not become ready')

    def close(self):
        """Clean up command-owned resources, never an explicitly reused window."""
        if self.cleanup_result is None:
            if self._owned_window_id is None:
                self.cleanup_result = {'classification': 'preserved_existing_window'}
            else:
                guard = ('JSON.stringify({owned:(' + self._page_matches() +
                         ' && window.__ytpmPageIdentity === ' + json.dumps(self.page_token) + ')})')
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', encoding='utf-8') as js:
                        js.write(guard); js.flush()
                        classification = self._script(
                            (Path(__file__).parent / 'browser/window_cleanup.applescript').read_text(),
                            str(self._owned_window_id), js.name,
                            'true' if self.page_token is None else 'false',
                            self.url)
                    self.cleanup_result = {'classification': classification,
                                           'window_id': self._owned_window_id}
                except (TransportError, OSError) as error:
                    self.cleanup_result = {'classification': 'close_error',
                                           'window_id': self._owned_window_id, 'error': str(error)}
        if self.cleanup_result['classification'] not in {
                'closed', 'already_absent', 'closed_owned_tab', 'released_hidden_empty_window',
                'preserved_existing_window', 'preserved_changed_window'}:
            raise TransportError('Safari temporary-window cleanup needs attention: ' +
                                 self.cleanup_result['classification'], self.cleanup_result)
        if self._read_recovery_cleanups:
            return {**self.cleanup_result,
                    'read_only_restarts': len(self._read_recovery_cleanups),
                    'previous_cleanups': list(self._read_recovery_cleanups)}
        return self.cleanup_result

    def _owned_window_present(self):
        state = self._script('''on run argv
tell application "Safari"
    if not running then return "not_running"
    return (exists window id ((item 1 of argv) as integer)) as text
end tell
end run''', str(self._owned_window_id)).lower()
        if state == 'not_running':
            raise TransportError('Safari quit during collection; the read-only page was not reopened',
                                 {'code': 'ytpm_browser_stopped'})
        return state == 'true'

    def recover_read_only(self):
        """Re-establish an owned read page; never use this for an edit."""
        if self._owned_window_id is None or self.window_id != self._owned_window_id:
            raise TransportError('Cannot replace a borrowed or moved Safari page')
        present = self._owned_window_present()
        if present:
            # A reload loses our page-local marker but may leave the exact
            # target in the original window. Rebind only after open checks its
            # URL and initializes the native adapter again.
            self.page_token = None
            self.tab_index = None
            try:
                self.open(self.url)
                return
            except TransportError as error:
                if (error.details.get('code') != 'ytpm_page_missing' and
                        self._owned_window_present()):
                    raise
        self.close()
        self._read_recovery_cleanups.append(dict(self.cleanup_result))
        self.window_id = None
        self._owned_window_id = None
        self.page_token = None
        self.tab_index = None
        self.cleanup_result = None
        self.open(self.url)

    def _bind_page(self):
        """Bind one explicitly matching tab; never infer identity from selection."""
        if self.page_token is not None:
            return
        probe = 'JSON.stringify({matches:(' + self._page_matches() + ')})'
        token = str(uuid.uuid4())
        bind = ('(()=>{if(!(' + self._page_matches() + '))return JSON.stringify({missing:true});'
                'if(!Object.hasOwn(window,"__ytpmPageIdentity"))Object.defineProperty(window,"__ytpmPageIdentity",'
                '{value:' + json.dumps(token) + '});return JSON.stringify({token:window.__ytpmPageIdentity});})()')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js') as a, \
                tempfile.NamedTemporaryFile(mode='w', suffix='.js') as b:
            a.write(probe); a.flush(); b.write(bind); b.flush()
            result = self._script('''on run argv
set windowId to (item 1 of argv) as integer
set probe to read (POSIX file (item 2 of argv)) as «class utf8»
set bindCode to read (POSIX file (item 3 of argv)) as «class utf8»
tell application "Safari"
    set matches to {}
    set targetWindow to window id windowId
    repeat with candidate in tabs of targetWindow
        if URL of candidate starts with "https://" then
            if (do JavaScript probe in candidate) is "{\\"matches\\":true}" then set end of matches to candidate
        end if
    end repeat
    if (count of matches) is 0 then error "YTPM_PAGE_MISSING"
    if (count of matches) is not 1 then error "YTPM_PAGE_AMBIGUOUS"
    set targetTab to item 1 of matches
    return (index of targetTab as text) & linefeed & (do JavaScript bindCode in targetTab)
end tell
end run''', str(self.window_id), a.name, b.name)
        index, raw = result.split('\n', 1)
        value = json.loads(raw)
        if not isinstance(value.get('token'), str):
            raise TransportError('Bound Safari page changed during initialization')
        self.tab_index, self.page_token = int(index), value['token']

    def evaluate(self, source: str, script_timeout=SCRIPT_TIMEOUT_SECONDS):
        if self.page_token is None:
            raise TransportError('Bind the Safari playlist page before executing a command')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', encoding='utf-8') as js:
            js.write(self._guarded_source(source))
            js.flush()
            # Fast path: cached coordinates, with the identity check inside the
            # same JS execution as the payload. A moved tab is located by marker.
            raw = self._script('''on run argv
set windowId to (item 1 of argv) as integer
set jsCode to read (POSIX file (item 2 of argv)) as «class utf8»
set tabIndex to (item 3 of argv) as integer
tell application "Safari"
    try
        set targetTab to get tab tabIndex of window id windowId
    on error
        return "{\\"bound\\":false}"
    end try
    return do JavaScript jsCode in targetTab
end tell
end run''', str(self.window_id), js.name, str(self.tab_index), timeout=script_timeout)
            result = json.loads(raw)
            if not result.get('bound'):
                # Locate only; do not execute a payload on each candidate.
                with tempfile.NamedTemporaryFile(mode='w', suffix='.js') as probe:
                    probe.write(self._guarded_source('null')); probe.flush()
                    located = self._script('''on run argv
set probe to read (POSIX file (item 1 of argv)) as «class utf8»
tell application "Safari"
    set matches to {}
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t starts with "https://" then
                try
                    if (do JavaScript probe in t) is "{\\"bound\\":true,\\"value\\":null}" then set end of matches to {id of w, index of t}
                end try
            end if
        end repeat
    end repeat
    if (count of matches) is 0 then error "YTPM_PAGE_MISSING"
    if (count of matches) is not 1 then error "YTPM_PAGE_AMBIGUOUS"
    set coords to item 1 of matches
    return (item 1 of coords as text) & ":" & (item 2 of coords as text)
end tell
end run''', probe.name, timeout=script_timeout)
                self.window_id, self.tab_index = map(int, located.split(':'))
                # One guarded retry after relocation. Never repeat after an
                # uncertain execution error: that could duplicate a mutation.
                raw = self._script('''on run argv
set jsCode to read (POSIX file (item 1 of argv)) as «class utf8»
tell application "Safari"
    return do JavaScript jsCode in tab ((item 3 of argv) as integer) of window id ((item 2 of argv) as integer)
end tell
end run''', js.name, str(self.window_id), str(self.tab_index), timeout=script_timeout)
                result = json.loads(raw)
                if not result.get('bound'):
                    raise TransportError('Bound Safari page moved again; command was not executed')
        try:
            return json.loads(result['value'])
        except ValueError as error:
            raise TransportError('Browser returned an unknown result format') from error

    def _page_matches(self):
        return page_match_source(self.url)

    def _guarded_source(self, source):
        return guarded_source(source, self.url, self.page_token)


def Safari(config, window_id=None):
    """Compatibility factory for existing diagnostics; no separate YouTube client."""
    from .transport import YouTubeTransport
    return YouTubeTransport(config, SafariPage(window_id))
