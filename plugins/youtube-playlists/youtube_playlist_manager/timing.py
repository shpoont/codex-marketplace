"""Playlist-entry clocks and observed returns, independent of upload dates."""
from .config import channel_policy, timestamp


def manual_policy(config):
    return {'unknown_addition_time': 'deferred', 'dismissed_reappearance': 'deferred',
            **config.get('manual_actions', {})}


def observe_entries(data, observation, config):
    moment = observation['collected_at']
    present = {e['id'] for e in observation['playlist']['entries']}
    previous = {vid for _, vid in data.get('membership', [])}
    clocks = data.setdefault('entry_times', {})
    expired = data.setdefault('expired', {})
    actions = manual_policy(config)
    returned = present & set(data['dismissed'])
    if returned and actions['dismissed_reappearance'] == 'readmit':
        data['dismissed'] = sorted(set(data['dismissed']) - returned)
    policies = {c['id']: channel_policy(c, config['channel_defaults']) for c in config['channels']}
    enabled = data.setdefault('retention_enabled_at', {})
    for cid, policy in policies.items():
        if policy['retention']['maximum_age'] not in [None, 'deferred']:
            enabled.setdefault(cid, moment)
        else:
            enabled.pop(cid, None)
    for cid in set(enabled) - set(policies):
        enabled.pop(cid)
    for entry in observation['playlist']['entries']:
        vid = entry['id']
        # Manager maintenance owns the original clock across an observed absence.
        restoration = vid in data.get('restorations', {})
        new_stay = vid not in previous and not restoration
        if vid not in clocks or new_stay:
            clocks[vid] = {'first_seen_at': moment, 'source': 'observation'}
            expired.pop(vid, None)
        clock = clocks[vid]
        clock['entry_id'] = entry['entry_id']
        if clock.get('added_at'):
            continue
        convention = actions['unknown_addition_time']
        if convention == 'first_observed':
            clock.update(added_at=clock['first_seen_at'], source='first_observed')
        elif convention == 'retention_enabled' and entry['channel_id'] in enabled:
            start = max([clock['first_seen_at'], enabled[entry['channel_id']]], key=timestamp)
            clock.update(added_at=start, source='retention_enabled')
    return {'returned': sorted(returned), 'action': actions['dismissed_reappearance']}


def initialize_clocks(data, observations):
    """Recover observed membership episodes from old snapshots without inventing dates."""
    if 'entry_times' in data:
        return
    clocks, previous = {}, set()
    restorations = set(data.get('restorations', {}))
    for observation in observations:
        present = {e['id'] for e in observation['playlist']['entries']}
        for entry in observation['playlist']['entries']:
            vid = entry['id']
            if vid not in clocks or (vid not in previous and vid not in restorations):
                clocks[vid] = {'first_seen_at': observation['collected_at'], 'source': 'observation',
                               'entry_id': entry['entry_id']}
        previous = present
    data['entry_times'] = clocks
