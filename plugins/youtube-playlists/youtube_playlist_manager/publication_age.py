"""Conservative exclusion evidence, never an estimated publication date."""
from datetime import timedelta
import re

from .config import seconds, timestamp


def _age_evidence(evidence, now):
    if not isinstance(evidence, dict) or evidence.get('source') != 'youtube_videos_tab':
        return None
    label = evidence.get('label')
    if not isinstance(label, str):
        return None
    match = re.fullmatch(r'([1-9][0-9]{0,3}) (minute|hour|day|week|month|year)s? ago', label)
    if not match:
        return None
    try:
        observed = timestamp(evidence.get('observed_at'))
        current = timestamp(now)
    except (TypeError, ValueError):
        return None
    if observed > current:
        return None
    return observed, int(match[1]), match[2]


def latest_possible_publication(evidence, now):
    """Upper date bound, allowing a whole unit and day for rounding.

    Months use 28 days and years 365. This is exclusion evidence, never an
    estimated publication date; boundary cases still require exact metadata.
    """
    parsed = _age_evidence(evidence, now)
    if parsed is None:
        return None
    observed, amount, unit = parsed
    units = {'minute': 60, 'hour': 3600, 'day': 86400, 'week': 7 * 86400,
             'month': 28 * 86400, 'year': 365 * 86400}
    lower = max(0, (amount - 1) * units[unit] - 86400)
    # Do not age an uncertain zero lower bound into a proof of publication.
    return observed - timedelta(seconds=lower) if lower > 0 else None


def earliest_possible_publication(evidence, now):
    """Lower date bound for oldest-first selection, never a guessed date.

    Use the longest month/year and an extra displayed unit plus a day. Unknown
    or overlapping bounds cannot eliminate a candidate from metadata checks.
    """
    parsed = _age_evidence(evidence, now)
    if parsed is None:
        return None
    observed, amount, unit = parsed
    units = {'minute': 60, 'hour': 3600, 'day': 86400, 'week': 7 * 86400,
             'month': 31 * 86400, 'year': 366 * 86400}
    try:
        return observed - timedelta(seconds=(amount + 1) * units[unit] + 86400)
    except OverflowError:
        return None


def outside_lookback(evidence, lookback, now):
    if lookback in (None, 'deferred'):
        return False
    bound = latest_possible_publication(evidence, now)
    try:
        return bound is not None and bound < timestamp(now) - timedelta(seconds=seconds(lookback))
    except (TypeError, ValueError):
        return False
