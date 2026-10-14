"""Bounded observation recovery; this module never dispatches a playlist write."""
from __future__ import annotations

from contextlib import contextmanager
import time


RECOVERY_LIMIT = 2
RECOVERY_SECONDS = 60
READ_METHODS = {'identity', 'playlist', 'metadata', 'refreshCatalog', 'channel', 'subscriptionSnapshot'}
TERMINAL_CODES = {'auth_required', 'session_changed', 'target_mismatch', 'playlist_unavailable',
                  'api_incompatible', 'rate_limited', 'browser_capability_missing', 'ytpm_page_ambiguous'}


def transient_read(error):
    details = getattr(error, 'details', {}) or {}
    return (details.get('code') == 'read_failed' or
            (details.get('code') == 'http_error' and details.get('http_status') in {500, 502, 503, 504}))


def terminal_recovery_error(error):
    return (getattr(error, 'details', {}) or {}).get('code') in TERMINAL_CODES


def playlist_delta(before, after, *, stage):
    """Compare raw entry stays, order and progress without logging full snapshots."""
    if isinstance(before, list):
        before = {'complete': True, 'entries': [dict(entry_id=eid, id=vid, percent=p)
                                               for eid, vid, p in before]}
    old = {(e['entry_id'], e['id']): (i, e.get('percent')) for i, e in enumerate(before['entries'])}
    new = {(e['entry_id'], e['id']): (i, e.get('percent')) for i, e in enumerate(after['entries'])}
    added, removed = new.keys() - old.keys(), old.keys() - new.keys()
    shared = old.keys() & new.keys()
    order = [k for k in old if k in shared] != [k for k in new if k in shared]
    progress = [k for k in old if k in shared and old[k][1] != new[k][1]]
    classes = (['incomplete_read'] if after.get('complete') is not True else [])
    classes += ['membership'] if added or removed else []
    classes += ['order'] if order else []
    classes += ['progress'] if progress else []
    changes = []
    for key in dict.fromkeys([*old, *new]):
        a, b = old.get(key), new.get(key)
        if a == b:
            continue
        changes.append({'entry_id': key[0], 'video_id': key[1],
                        'before_position': a[0] + 1 if a else None,
                        'after_position': b[0] + 1 if b else None,
                        'before_percent': a[1] if a else None, 'after_percent': b[1] if b else None})
    return {'code': 'playlist_changed', 'stage': stage, 'classifications': classes,
            'before_count': len(old), 'after_count': len(new),
            'added_count': len(added), 'removed_count': len(removed), 'progress_count': len(progress),
            'changes': changes[:10], 'changes_omitted': max(0, len(changes) - 10)}


class RecoveryBudget:
    """A single invocation shares its restart/read budget across all stages.

    Collection can legitimately take minutes. The recovery deadline therefore
    starts at the first failure, not at the start of healthy metadata work.
    """
    def __init__(self, record=None):
        self.attempts = 0
        self.started = None
        self.record = record or (lambda kind, details: None)

    def take(self, error, stage):
        # Preserve the stage that actually exhausted the shared budget; outer
        # collection/refresh layers must not relabel or retry that failure.
        if (getattr(error, 'details', {}) or {}).get('recovery', {}).get('exhausted') is True:
            return False
        current = time.monotonic()
        if self.started is None:
            self.started = current
        exhausted = self.attempts >= RECOVERY_LIMIT or current - self.started >= RECOVERY_SECONDS
        if not exhausted:
            self.attempts += 1
        details = {'stage': stage, 'attempts': self.attempts, 'limit': RECOVERY_LIMIT,
                   'elapsed_seconds': round(current - self.started, 3), 'deadline_seconds': RECOVERY_SECONDS,
                   'exhausted': exhausted, 'outcome': 'exhausted' if exhausted else 'retrying'}
        error.details = {**(getattr(error, 'details', {}) or {}), 'recovery': details}
        self.record('refresh_recovery', error.details)
        return not exhausted

    def complete(self):
        if self.attempts:
            self.record('refresh_recovery', {'recovery': {
                'stage': 'completion', 'attempts': self.attempts, 'limit': RECOVERY_LIMIT,
                'elapsed_seconds': round(time.monotonic() - self.started, 3),
                'deadline_seconds': RECOVERY_SECONDS, 'exhausted': False, 'outcome': 'recovered'}})


@contextmanager
def recovery_scope(transport, record=None):
    existing = getattr(transport, 'recovery_budget', None)
    budget = existing or RecoveryBudget(record)
    transport.recovery_budget = budget
    try:
        yield budget
    finally:
        if existing is None:
            transport.recovery_budget = None
