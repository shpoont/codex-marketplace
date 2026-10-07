"""Durable playlist stays and review decisions, independent of viewing slots."""
from .config import digest


def member(state, entry):
    record = state.get('managed_entries', {}).get(entry['id'], {})
    return record if record.get('entry_id') == entry['entry_id'] else {}


def new_member(data, entry, status):
    stay = member(data, entry).get('stay_id')
    if stay is None:
        data['stay_sequence'] = data.get('stay_sequence', 0) + 1
        stay = data['stay_sequence']
    return {'entry_id': entry['entry_id'], 'channel_id': entry['channel_id'],
            'status': status, 'stay_id': stay}


def observe_members(data, observation, configured, enabled_channels=()):
    entries = observation['playlist']['entries']
    present = {e['id'] for e in entries}
    members = data.setdefault('managed_entries', {})
    dismissed = set(data['dismissed'])
    dismissed.update(vid for vid, m in members.items()
                     if vid not in present and m['status'] != 'released')
    members = {vid: m for vid, m in members.items() if vid in present}
    for e in entries:
        vid = e['id']
        prior = members.get(vid, {})
        if prior.get('status') == 'released' and e['channel_id'] in enabled_channels:
            prior = {}
        if prior.get('entry_id') == e['entry_id']:
            continue
        # Entry identity guards decisions/exception ownership. The timestamp
        # convention deliberately cannot infer every action between observations.
        if e['channel_id'] in configured and (e['kind'] == 'normal' or prior):
            receipt = data.get('entry_policies', {}).get(vid, {})
            known = receipt.get('entry_id') == e['entry_id']
            members[vid] = new_member(data, e, 'managed' if known else 'candidate')
        else:
            members.pop(vid, None)
    data['managed_entries'] = members
    data['dismissed'] = sorted(dismissed)


def decision(config, entry, policy, reason, subscribed, stay_id=None):
    binding = {k: config[k] for k in ('account_channel_id', 'playlist_id')}
    binding.update(video_id=entry['id'], entry_id=entry['entry_id'],
                   channel_id=entry['channel_id'], policy=policy, subscribed=subscribed,
                   reason=reason, percent=entry['percent'], stay_id=stay_id)
    return {'id': digest(binding), **binding, 'title': entry.get('title', entry['id']),
            'choices': ['keep', 'remove']}


def applied_members(data, plan, playlist):
    """Only a verified applied plan adopts eligible manual arrivals."""
    adopted = set(plan.get('adopt', []))
    for e in playlist['entries']:
        if e['id'] in adopted:
            data.setdefault('managed_entries', {})[e['id']] = new_member(data, e, 'managed')
