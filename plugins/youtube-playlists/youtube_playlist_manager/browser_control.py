"""Contract for JavaScript execution in a bound browser page, independent of YouTube."""
from __future__ import annotations

import json
import math
import re
from contextlib import contextmanager
from typing import Any, Protocol
from urllib.parse import urlparse

SCRIPT_TIMEOUT_SECONDS = 60
JOB_STATUS_SCRIPT_TIMEOUT_SECONDS = 300
READ_ONLY_PAGE_RECOVERIES = 2


def open_diagnostics(value):
    """Preserve the first setup stage without arbitrary browser error text."""
    if not isinstance(value, dict) or value.get('stage') not in {
            'create_page', 'register_page', 'inspect_page', 'navigate_page', 'connect_page', 'bind_page'}:
        return {}
    safe = {'stage': value['stage']}
    if value.get('ownership') in {'registered', 'unknown'}:
        safe['ownership'] = value['ownership']
    return safe


class TransportError(RuntimeError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


def cleanup_diagnostics(value, *, include_history=True):
    """Keep neutral cleanup receipts useful without arbitrary controller errors."""
    if not isinstance(value, dict) or value.get('classification') not in {
            'empty_window_persisted', 'window_still_open', 'verification_error', 'close_error',
            'page_still_present', 'closed', 'already_absent', 'preserved_changed_page',
            'closed_owned_tab', 'released_hidden_empty_window', 'preserved_existing_window',
            'preserved_changed_window'}:
        return {}
    safe = {'classification': value['classification']}
    for key in ('page_id', 'window_id'):
        item = value.get(key)
        if type(item) is int or (key == 'page_id' and isinstance(item, str) and
                                re.fullmatch(r'[A-Za-z0-9_-]{1,128}', item)):
            safe[key] = item
    if value.get('reason') in {'verification_error', 'request_inactive', 'deadline_exceeded',
            'presence_error', 'presence_unknown', 'inspection_error', 'identity_lost',
            'receipt_error', 'close_error', 'page_present', 'creation_unverified'}:
        safe['reason'] = value['reason']
    if value.get('close_ack') in {'received', 'uncertain', 'not_sent'}:
        safe['close_ack'] = value['close_ack']
    if type(value.get('presence_checks')) is int and 0 <= value['presence_checks'] <= 1000000:
        safe['presence_checks'] = value['presence_checks']
    elapsed = value.get('elapsed_ms')
    if type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= 60000:
        safe['elapsed_ms'] = elapsed
    if include_history:
        restarts = value.get('read_only_restarts')
        if type(restarts) is int and 0 <= restarts <= READ_ONLY_PAGE_RECOVERIES:
            safe['read_only_restarts'] = restarts
        if isinstance(value.get('previous_cleanups'), list):
            safe['previous_cleanups'] = [receipt for previous in value['previous_cleanups'][:READ_ONLY_PAGE_RECOVERIES]
                                        if (receipt := cleanup_diagnostics(previous, include_history=False))]
    return safe


class JavaScriptRunner(Protocol):
    """Execute once in the authenticated main page; never replay uncertain commands.

    open binds the requested URL, evaluate returns decoded JSON from the source,
    and close verifies release of owned resources while preserving borrowed ones.
    Recovery is optional and applies only to owned read-only collection pages.
    """
    page_id: str | int | None
    can_recover: bool

    def open(self, url: str) -> Any: ...
    def evaluate(self, source: str, script_timeout: int = SCRIPT_TIMEOUT_SECONDS) -> Any: ...
    def close(self) -> dict: ...
    def recover_read_only(self) -> None: ...


def page_match_source(url):
    """Exact origin/path and requested query values; permit unrelated UI parameters."""
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise TransportError('A page runner requires an HTTPS URL without embedded credentials')
    return ('(()=>{const expected=new URL(' + json.dumps(url) + ');'
            'const actual=new URL(location.href);return actual.origin===expected.origin && '
            'actual.pathname===expected.pathname && [...new Set(expected.searchParams.keys())].every('
            'key=>JSON.stringify(actual.searchParams.getAll(key))===JSON.stringify(expected.searchParams.getAll(key)));})()')


def guarded_source(source, url, token):
    guard = page_match_source(url) + ' && window.__ytpmPageIdentity === ' + json.dumps(token)
    return ('(()=>{if(!(' + guard + '))return JSON.stringify({bound:false});'
            'return JSON.stringify({bound:true,value:(' + source + ')});})()')


@contextmanager
def browser_session(transport, report_cleanup=None):
    """Release owned browser resources on success, failure and handled interruption."""
    def cleanup():
        try:
            result = transport.close()
        except TransportError as error:
            if report_cleanup:
                report_cleanup(error.details)
            raise
        if report_cleanup:
            report_cleanup(result)
    try:
        yield transport
    except BaseException as error:
        try:
            cleanup()
        except Exception as cleanup_error:
            error.add_note('Browser cleanup also failed: ' + str(cleanup_error))
            if hasattr(error, 'details'):
                error.details = {**error.details, 'browser_cleanup': getattr(cleanup_error, 'details',
                                                                          {'error': str(cleanup_error)})}
        raise
    else:
        cleanup()
