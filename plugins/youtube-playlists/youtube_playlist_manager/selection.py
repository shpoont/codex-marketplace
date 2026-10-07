"""Rank eligible channel inventory and request only metadata that can affect selection."""
from datetime import datetime, timezone

from .config import timestamp
from .publication_age import earliest_possible_publication, latest_possible_publication


def select_candidates(candidates, incomplete, p, current_ids, now):
    """Apply count/selection rules, returning chosen rows and unresolved metadata IDs."""
    required, deferred = [], []
    oldest = p['retention']['selection'] == 'oldest_eligible_unwatched'
    candidates.sort(key=lambda v: (timestamp(v['publication']), v['id']), reverse=not oldest)
    # An ignored channel can retain current inventory but cannot select absent items.
    if p['additions'] == 'ignored':
        candidates = [v for v in candidates if v['id'] in current_ids]
    before_count = candidates
    count = p['retention']['maximum_count']
    if isinstance(count, int):
        if p['retention']['selection'] == 'keep_current_and_refill':
            held = [v for v in candidates if v['id'] in current_ids]
            fresh = [v for v in candidates if v['id'] not in current_ids]
            candidates = (held + fresh)[:count]
        else:
            candidates = candidates[:count]
    # A count limit is resolved only by verified eligible candidates. An
    # absent unresolved video needs no player check if it cannot displace
    # those candidates. Unknown dates/ties and queued stays remain required.
    # This uses every catalog row; listing position is never exclusion proof.
    publication_bound = earliest_possible_publication if oldest else latest_possible_publication
    unknown_bound = datetime.min.replace(tzinfo=timezone.utc) if oldest else timestamp(now)
    def possible_publication(video):
        return (timestamp(video['publication']) if video.get('publication') else
                publication_bound(video.get('publication_age'), now))
    incomplete.sort(key=lambda item: possible_publication(item[0]) or unknown_bound, reverse=not oldest)
    for v, queued in incomplete:
        full = isinstance(count, int) and len(candidates) >= count
        held_full = full and p['retention']['selection'] == 'keep_current_and_refill' and all(
            chosen['id'] in current_ids for chosen in candidates)
        bound = possible_publication(v)
        outside_selection = full and bound is not None and (
            bound > timestamp(candidates[-1]['publication']) if oldest else
            bound < timestamp(candidates[-1]['publication']))
        if not queued and (held_full or outside_selection):
            deferred.append(v['id'])
        else:
            required.append(v['id'])
    return candidates, before_count, required, deferred
