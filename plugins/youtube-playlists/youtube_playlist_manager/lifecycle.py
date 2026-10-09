"""Durable playlist stays and review decisions, independent of viewing slots."""
from .config import digest


def member(state, entry):
    record = state.get('managed_entries', {}).get(entry['id'], {})
    return record if record.get('entry_id') == entry['entry_id'] else {}


def manual_protected(state, entry):
    record = member(state, entry)
    return record.get('status') == 'manual' or (
        record.get('origin') == 'manual' and
        record.get('status') in {'candidate', 'exception', 'released'})


def new_member(data, entry, status, *, origin=None):
    previous = member(data, entry)
    stay = previous.get('stay_id')
    if stay is None:
        data['stay_sequence'] = data.get('stay_sequence', 0) + 1
        stay = data['stay_sequence']
    return {'entry_id': entry['entry_id'], 'channel_id': entry['channel_id'],
            'status': status, 'stay_id': stay,
            'origin': origin or previous.get('origin') or
                      ('manual' if status in {'manual', 'candidate'} else 'manager')}


def initialize_origins(data, last_operations):
    """Use saved evidence, never current selection, to classify older stays."""
    if 'arrival_origin_migration' in data:
        return
    counts = {'manual': 0, 'manager': 0, 'unknown': 0}
    for vid, record in data.get('managed_entries', {}).items():
        if 'origin' in record:
            continue
        receipt = data.get('entry_policies', {}).get(vid, {})
        clock = data.get('entry_times', {}).get(vid, {})
        manager = (receipt.get('entry_id') == record['entry_id'] or
                   clock.get('entry_id') == record['entry_id'] and
                   clock.get('source') == 'manager_write')
        observed = (clock.get('entry_id') == record['entry_id'] and
                    clock.get('source') in {'observation', 'first_observed', 'retention_enabled'})
        if manager:
            origin = 'manager'
        elif record['status'] in {'candidate', 'exception', 'released'} or (
                observed and last_operations.get(vid, {}).get('kind') != 'add'):
            origin = 'manual'
        else:
            origin = 'unknown'
        record['origin'] = origin
        if origin == 'manual' and record['status'] in {'managed', 'candidate'}:
            record['status'] = 'manual'
        counts[origin] += 1
    data['arrival_origin_migration'] = {'version': 1, 'classified': counts,
                                       'source_state_version': data['version']}


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
        if (prior.get('status') == 'released' and prior.get('origin') != 'manual'
                and e['channel_id'] in enabled_channels):
            prior = {}
        if prior.get('entry_id') == e['entry_id']:
            continue
        # Entry identity guards decisions/exception ownership. The timestamp
        # convention deliberately cannot infer every action between observations.
        if e['channel_id'] in configured and (e['kind'] == 'normal' or prior):
            receipt = data.get('entry_policies', {}).get(vid, {})
            # A receipt cannot reclaim an externally re-added stay after an
            # observed absence, even if YouTube reuses the entry ID.
            known = (receipt.get('entry_id') == e['entry_id'] and
                     [e['entry_id'], vid] in data.get('membership', []))
            members[vid] = new_member(data, e, 'managed' if known else 'manual',
                                      origin='manager' if known else 'manual')
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
    """Adoption can resolve older unknown ownership, never manual intent."""
    adopted = set(plan.get('adopt', []))
    for e in playlist['entries']:
        if e['id'] in adopted and not manual_protected(data, e):
            data.setdefault('managed_entries', {})[e['id']] = new_member(data, e, 'managed')
