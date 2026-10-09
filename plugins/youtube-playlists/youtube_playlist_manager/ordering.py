"""Arrange selected inventory while preserving protected entries."""
from .config import timestamp
from . import lifecycle
from datetime import datetime, timezone


def normal_active(video):
    return video.get('kind') == 'normal' and video.get('percent') is not None and video['percent'] < 100


def manual_entry(entry, managed, state):
    return entry['channel_id'] not in managed or lifecycle.member(state, entry).get('status') == 'released'


def viewing_key(video, policies, *, manual=False):
    """One key for previews, additions and placement; manual entries are unpinned."""
    placement = policies[video['channel_id']]['placement'] if not manual else {}
    rank = placement.get('pinned_rank')
    published = timestamp(video['publication']) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    if rank is not None and placement['order'] == 'newest_first':
        published = -published
    return rank is None, rank or 0, published, video['id']


def viewing_order(pool, selected_ids, entries, removals, policies, managed, state, paused_ids):
    """Return desired IDs and the IDs allowed to move after planned removals."""
    current_ids = {e['id'] for e in entries}
    kept = [e for e in entries if e['id'] not in removals]
    future = {v['id']: v for v in pool if v['id'] in selected_ids or (v['id'] in current_ids and v['id'] not in removals)}
    manual = [e for e in kept if e['id'] not in paused_ids
              and (manual_entry(e, managed, state) or lifecycle.manual_protected(state, e))
              and normal_active(e) and e.get('playable') is not False]
    # Protected manual stays follow their configured channel's placement.
    # Once that channel is removed, they share the unpinned chronology.
    manual_ids = {e['id'] for e in manual if manual_entry(e, set(policies), state)}
    future.update({e['id']: e for e in manual})
    active_order = sorted(future, key=lambda vid: viewing_key(
        future[vid], policies, manual=vid in manual_ids))
    # Private/unavailable, excluded-format and paused entries remain protected.
    active_ids = set(active_order)
    desired, iterator = [], iter(active_order)
    for e in kept:
        if e['id'] in active_ids:
            nxt = next(iterator, None)
            if nxt:
                desired.append(nxt)
        else:
            desired.append(e['id'])
    desired.extend(iterator)
    return desired, active_order
