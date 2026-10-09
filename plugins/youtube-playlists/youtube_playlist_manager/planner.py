"""Pure policy evaluation. Explicit input time and stable tie-breaks."""
from __future__ import annotations

from datetime import timedelta
from collections import Counter

from .config import channel_policy, digest, seconds, timestamp, unresolved
from . import lifecycle
from .timing import manual_policy
from .publication_age import outside_lookback
from .selection import select_candidates
from .ordering import manual_entry, normal_active, viewing_key, viewing_order


PLAN_SCHEMA = 17

# Approval covers lifecycle history, not just the IDs sent to YouTube.
APPROVAL_FIELDS = ('status', 'blockers', 'identity', 'before', 'remove', 'add', 'desired', 'expire',
                  'movable', 'policies', 'added_duration_seconds', 'decisions', 'adopt', 'paused_channels',
                  'valid_until', 'valid_until_inclusive', 'development_trial')


def membership(playlist):
    return [[e['entry_id'], e['id']] for e in playlist['entries']]


def observation_digest(observation):
    # Collection receipts describe work performed, not a change in YouTube state.
    def semantic(value, parent=None):
        if isinstance(value, dict):
            return {k: semantic(v, k) for k, v in value.items()
                    if k not in ['collected_at', 'collection', 'metadata_checked_at'] and
                    not (parent == 'publication_age' and k == 'observed_at')}
        if isinstance(value, list):
            return [semantic(v) for v in value]
        return value
    return digest(semantic(observation))


def policy_config(config):
    return {**{k: v for k, v in config.items() if k not in ['playlist_name', 'storage', 'channels', 'channel_defaults']},
            'channels': sorted((channel_policy(c, config['channel_defaults']) for c in config['channels']), key=lambda c: c['id'])}


def plan(config, observation, state, now, metadata_only=False):
    now_dt = timestamp(now)
    policies = {c['id']: channel_policy(c, config['channel_defaults']) for c in config['channels']}
    output = {'schema': PLAN_SCHEMA, 'status': 'ready', 'created_at': now,
              'config_hash': digest(policy_config(config)), 'state_version': state['version'],
              'observation_hash': None if metadata_only else observation_digest(observation),
              'identity': {k: config[k] for k in ['account_channel_id', 'playlist_id']},
              'before': membership(observation['playlist']), 'blockers': [], 'channels': [],
              'remove': [], 'add': [], 'desired': [], 'pending': [], 'policies': policies,
              'metadata_requests': [], 'metadata_deferred': [], 'listing_requests': [],
              'decisions': [], 'adopt': [],
              'warnings': [w for c in observation['channels'] for w in c.get('warnings', [])]}
    blockers = output['blockers']
    if observation.get('schema') != 2:
        blockers.append('Collect again with the updated availability checks; older observations are not usable')
    if not observation.get('complete') or not observation['playlist'].get('complete') or not observation['subscriptions'].get('complete'):
        blockers.append('Incomplete live observation')
    if any(observation['playlist'].get(k) != v for k, v in output['identity'].items()):
        blockers.append('Target identity mismatch')
    if observation.get('account_channel_id') != config['account_channel_id']:
        blockers.append('Account identity mismatch')
    if state.get('in_flight'):
        blockers.append('An earlier write requires recovery')
    if (state.get('development_trial') or {}).get('state') == 'running':
        blockers.append('Finish the development sample before normal reconciliation')
    blockers.extend('Deferred policy: ' + x for x in unresolved(config))
    catalogs = {c['id']: c for c in observation['channels']}
    subs = {c['id'] for c in observation['subscriptions']['channels'] if c['subscribed']}
    unavailable_channels = {cid for cid, c in catalogs.items()
                            if c.get('catalog_unavailable') and cid in policies and cid in subs}
    entries = observation['playlist']['entries']
    current_ids = {e['id'] for e in entries}
    dismissed = set(state['dismissed'])
    old = state['policies']
    managed = set(policies) | set(old)
    manual_ids = {e['id'] for e in entries if lifecycle.manual_protected(state, e)}
    released_ids = {e['id'] for e in entries if lifecycle.member(state, e).get('status') == 'released'}
    returned = {e['id'] for e in entries if e['id'] in dismissed and
                e['channel_id'] in managed and normal_active(e) and e['id'] not in manual_ids}
    reappearance = manual_policy(config)['dismissed_reappearance']
    if returned and reappearance == 'deferred':
        blockers.append('Previously dismissed video reappeared; reappearance policy is deferred')
    elif reappearance == 'readmit':
        dismissed -= returned
    if len(current_ids) != len(entries):
        blockers.append('Duplicate playlist videos require an explicit resolution')
    for e in entries:
        if (e['channel_id'] in managed and e['id'] not in manual_ids and e.get('percent') is not None
                and e['percent'] < 100 and e['kind'] == 'unknown'
                and e['channel_id'] not in unavailable_channels):
            blockers.append('Unclassified managed playlist entry: ' + e['id'])
    # Legacy maintenance absence is a departure, never permission to restore.
    dismissed |= set(state.get('restorations', {})) - current_ids
    selections, removals = {}, {}
    exception_ids, approved_removals = set(), {}
    count_pending, deadlines = [], []
    clocks, expired = state.get('entry_times', {}), state.get('expired', {})
    expiry_details = {}
    for channel_id in list(policies) + sorted(set(old) - set(policies)):
        p = policies.get(channel_id)
        channel_entries = [e for e in entries if e['channel_id'] == channel_id
                           and lifecycle.member(state, e).get('status') != 'released'
                           and e['id'] not in manual_ids]
        existing = [e for e in channel_entries if normal_active(e)]
        if p is None or channel_id not in subs:
            output['channels'].append({'id': channel_id, 'evaluation_status': 'removed_or_unsubscribed'})
            for e in channel_entries:
                if e['kind'] != 'normal' and not lifecycle.member(state, e):
                    continue
                m = lifecycle.member(state, e)
                d = lifecycle.decision(config, e, p, 'channel_unmanaged', channel_id in subs, m.get('stay_id'))
                if m.get('status') == 'remove_requested' and m.get('decision_id') == d['id']:
                    removals[e['id']] = 'user_decision'
                    approved_removals[e['id']] = d
                else:
                    output['decisions'].append(d)
            continue
        catalog = catalogs.get(channel_id)
        if channel_id in unavailable_channels:
            output['channels'].append({'id': channel_id, 'evaluation_status': 'catalog_unavailable',
                                       'eligible_inventory_complete': False})
            continue
        if catalog is None or not catalog.get('complete'):
            output['channels'].append({'id': channel_id, 'evaluation_status': 'incomplete_catalog'})
            blockers.append('Incomplete channel catalog: ' + channel_id)
            continue
        if p['additions'] == 'ignored' and not existing:
            output['channels'].append({'id': channel_id, 'evaluation_status': 'ignored_empty',
                                       'candidates_after_resolved_rules': 0})
            continue
        exceptions = [e for e in existing if lifecycle.member(state, e).get('status') == 'exception']
        exception_ids.update(e['id'] for e in exceptions)
        bound, inclusive = None, True
        start = p['catch_up']['start']
        if start == 'new_only':
            bound = timestamp(state['enabled_at'].get(channel_id, now))
        elif isinstance(start, dict):
            inclusive = start['inclusive']
            if 'video_id' in start:
                anchor = next((v for v in catalog['videos'] if v['id'] == start['video_id']), None)
                if not anchor or not anchor.get('publication'):
                    blockers.append('Cutoff publication unavailable: ' + start['video_id'])
                else:
                    bound = timestamp(anchor['publication'])
            else:
                bound = timestamp(start['published_after'])
        merged = {v['id']: v for v in catalog['videos']}
        # Playlist progress is authoritative, including completed entries that
        # no longer occupy a slot but may lag in the channel catalog.
        for e in channel_entries:
            merged[e['id']] = e
        candidates, incomplete, future_publications = [], [], []
        filtered = Counter()
        known_filtered = 0
        for v in merged.values():
            queued = v['id'] in current_ids
            if v['id'] in exception_ids or v['id'] in released_ids or v['id'] in manual_ids:
                continue  # Durable keep decisions do not occupy channel slots.
            # Ignored channels retain current entries only. Missing catalog
            # entries need no metadata and cannot block other channels' plans.
            if p['additions'] == 'ignored' and v['id'] not in current_ids:
                filtered['additions_ignored'] += 1
                continue
            if not normal_active(v):
                filtered['not_normal' if v.get('kind') != 'normal' else
                         'unknown_progress' if v.get('percent') is None else 'fully_watched'] += 1
                continue
            if v['id'] in dismissed:
                filtered['dismissed'] += 1
                continue
            if not queued and v.get('listing_unavailable'):
                filtered['watch_status_unavailable'] += 1
                continue  # Retry from fresh listing evidence on the next collection.
            if not v.get('playable'):
                filtered['unavailable_or_unknown'] += 1
                continue
            if v['id'] in expired and not queued:
                filtered['previously_expired'] += 1
                continue
            if not queued and not v.get('publication') and outside_lookback(
                    v.get('publication_age'), p['lookback'], now):
                filtered['outside_lookback'] += 1
                continue
            if not v.get('publication') or not v.get('duration'):
                incomplete.append((v, queued))
                continue
            pub = timestamp(v['publication'])
            if pub > now_dt:
                filtered['future_publication'] += 1
                if bound is None or pub > bound or (inclusive and pub == bound):
                    future_publications.append(v)
                continue
            if bound is not None and (pub < bound or (not inclusive and pub == bound)):
                filtered['before_catch_up_start'] += 1
                continue
            lookback = p['lookback']
            if not queued and lookback not in [None, 'deferred']:
                if pub < now_dt - timedelta(seconds=seconds(lookback)):
                    filtered['outside_lookback'] += 1
                    continue
            age = p['retention']['maximum_age']
            if queued and age not in [None, 'deferred']:
                added_at = clocks.get(v['id'], {}).get('added_at')
                if not added_at:
                    filtered['unknown_addition_time'] += 1
                    blockers.append('Playlist addition time unavailable; choose a manual timestamp convention and collect: ' + v['id'])
                    continue
                expiry = timestamp(added_at) + timedelta(seconds=seconds(age))
                if now_dt >= expiry:
                    filtered['time_expired'] += 1
                    expiry_details[v['id']] = {'expired_at': expiry.isoformat(), 'channel_id': channel_id,
                                               'added_at': added_at}
                    if v['id'] in current_ids:
                        removals[v['id']] = 'time_expired'
                    continue
                # Overflow entries still have an approved removal and history
                # effect. Their expiry can change both without changing IDs.
                deadlines.append((expiry, False, channel_id, v['id'], 'time_expired'))
            known_filtered += 1
            candidates.append(v)
        candidates, before_count, required, deferred = select_candidates(
            candidates, incomplete, p, current_ids, now)
        count = p['retention']['maximum_count']
        full = isinstance(count, int) and len(candidates) >= count
        held_full = full and p['retention']['selection'] == 'keep_current_and_refill' and all(
            v['id'] in current_ids for v in candidates)
        # A later publication cannot displace a full oldest window or full
        # held-refill window. Preserve selective metadata collection: knowing
        # an irrelevant future date must not shorten an otherwise identical plan.
        future_can_enter = not full or (p['retention']['selection'] != 'oldest_eligible_unwatched'
                                       and not held_full)
        for v in future_publications:
            if future_can_enter or v['id'] in current_ids:
                deadlines.append((timestamp(v['publication']), False, channel_id, v['id'], 'publication_reached'))
        if deferred:
            filtered['metadata_not_needed_for_count'] += len(deferred)
        if required:
            filtered['missing_metadata'] += len(required)
        output['metadata_deferred'].extend(deferred)
        output['metadata_requests'].extend(required)
        blockers.extend('Missing publication or duration: ' + vid for vid in required)
        filtered['count_limit'] = len(before_count) - len(candidates)
        count_pending.extend(v['id'] for v in before_count if v['id'] not in {c['id'] for c in candidates}
                             and v['id'] not in current_ids)
        chosen = {v['id'] for v in candidates}
        count_overflow = {v['id'] for v in before_count} - chosen
        unresolved_ids = {v['id'] for v, _ in incomplete}
        for e in existing:
            if e['id'] in exception_ids or e['id'] in unresolved_ids:
                continue
            if e['id'] not in chosen:
                m = lifecycle.member(state, e)
                if m.get('status') != 'managed':
                    d = lifecycle.decision(config, e, p, 'outside_channel_rules', True, m.get('stay_id'))
                    if m.get('status') == 'remove_requested' and m.get('decision_id') == d['id']:
                        removals[e['id']] = 'user_decision'
                        approved_removals[e['id']] = d
                    else:
                        removals.pop(e['id'], None)
                        expiry_details.pop(e['id'], None)
                        output['decisions'].append(d)
                else:
                    removals.setdefault(e['id'], 'dismissed' if e['id'] in dismissed else
                                        'count_window_overflow' if e['id'] in count_overflow else
                                        'retention_or_eligibility')
            elif lifecycle.member(state, e).get('status') != 'managed':
                output['adopt'].append(e['id'])
        for v in candidates:
            if v['id'] not in current_ids and p['lookback'] not in [None, 'deferred']:
                deadlines.append((timestamp(v['publication']) + timedelta(seconds=seconds(p['lookback'])),
                                  True, channel_id, v['id'], 'outside_lookback'))
        # Channel exceptions still participate in ordinary placement; missing
        # publication evidence must not be guessed for their ordering.
        for e in exceptions:
            if not e.get('publication'):
                output['metadata_requests'].append(e['id'])
                blockers.append('Missing publication for kept exception: ' + e['id'])
        selections[channel_id] = candidates + [e for e in exceptions if e.get('publication')]
        if filtered['watch_status_unavailable']:
            output['warnings'].append({'code': 'watch_status_unavailable', 'channel_id': channel_id,
                                       'skipped_count': filtered['watch_status_unavailable'],
                                       'message': 'Candidates with unverified watch status were skipped until a later refresh.'})
        output['channels'].append({'id': channel_id, 'catalog': len(catalog['videos']),
                                    'normal_unwatched_after_start': known_filtered,
                                    'eligible_inventory_complete': not incomplete and
                                        not filtered['watch_status_unavailable'] and catalog.get('discovery_complete', True),
                                    'candidates_after_resolved_rules': len(candidates), 'subscribed': True,
                                    'evaluation_status': 'evaluated',
                                    'evaluated_videos': len(merged), 'filter_counts': dict(filtered)})
    # Explain eligible inventory separately from the exact membership changes.
    decision_paused = {d['channel_id'] for d in output['decisions']}
    paused = decision_paused | unavailable_channels
    paused_ids = {e['id'] for e in entries if e['channel_id'] in paused and e['id'] not in manual_ids}
    for e in entries:
        if (e['id'] in paused_ids or e.get('percent') == 100 or e.get('playable') is False
                or not (e['id'] in manual_ids or manual_entry(e, managed, state))):
            continue
        if e['kind'] == 'unknown':
            blockers.append('Unclassified manual playlist entry; collect again: ' + e['id'])
        elif normal_active(e) and not e.get('publication'):
            blockers.append('Missing publication for manual playlist entry; collect again: ' + e['id'])
    for cid in paused:
        selections.pop(cid, None)
    removals = {vid: reason for vid, reason in removals.items() if vid not in paused_ids}
    for e in entries:
        if (e['percent'] == 100 and e.get('playable') is True
                and (e['channel_id'] not in decision_paused or e['id'] in manual_ids)
                and e['id'] not in approved_removals):
            removals[e['id']] = 'fully_watched'
    expiry_details = {vid: details for vid, details in expiry_details.items() if vid not in paused_ids}
    output['adopt'] = [vid for vid in output['adopt'] if vid not in paused_ids]
    output['paused_channels'] = sorted(paused)
    for channel in output['channels']:
        if channel['id'] in decision_paused:
            channel['evaluation_status'] = 'awaiting_decision'
    # Retain ownership of removed-config channels until their questions resolve.
    output['policies'].update({cid: old[cid] for cid in paused if cid in old and cid not in policies})
    candidates = [v for videos in selections.values() for v in videos]
    # Cached inventory can nominate candidates, but stale progress cannot admit
    # a missing video. Collection follows fresh pagination, then plans again.
    competing = {v['id'] for v in candidates} | set(output['metadata_requests'])
    output['listing_requests'] = sorted(v['id'] for c in catalogs.values() for v in c['videos']
                                        if v['id'] in competing and v['id'] not in current_ids
                                        and v.get('listing_fresh') is False)
    blockers.extend('Stale candidate listing: ' + vid for vid in output['listing_requests'])
    output['decisions_complete'] = not blockers
    def display_key(video):
        return viewing_key(video, policies)
    output['candidate_preview'] = {
        'scope': 'eligible_managed_videos',
        'complete': not blockers,
        'discovery_complete': not unavailable_channels and
            all(c.get('eligible_inventory_complete', True) for c in output['channels']),
        'blockers': sorted(set(blockers)),
        'videos': [{**{k: v[k] for k in ['id', 'channel_id', 'title', 'publication', 'duration', 'percent']},
                    'content_warning': v.get('content_warning', False)}
                   for v in sorted(candidates, key=display_key)],
    }
    if blockers:
        output['status'] = 'needs_attention'
        output['blockers'] = sorted(set(blockers))
        output['decisions'] = []  # Do not ask questions based on incomplete evidence.
        # Partial calculations explain candidates, but never expose an executable partial plan.
        return output
    output['pending'] = count_pending
    output['expire'] = [{'video_id': vid, **details} for vid, details in sorted(expiry_details.items())]
    pool = [v for vs in selections.values() for v in vs]
    additions = sorted((v for v in pool if v['id'] not in current_ids),
                       key=display_key)
    selected_ids = {v['id'] for v in additions}
    output['add'] = [{'video_id': v['id'], 'channel_id': v['channel_id'],
                      'reason': 'eligible_missing'}
                     for v in additions]
    output['remove'] = [{'video_id': e['id'], 'entry_id': e['entry_id'], 'reason': removals[e['id']],
                         **expiry_details.get(e['id'], {}),
                         **({'purpose': 'watched_cleanup', 'expected_percent': 100}
                            if removals[e['id']] == 'fully_watched' else {}),
                         **({'purpose': 'user_decision', 'expected_percent': e['percent'],
                             'decision_id': approved_removals[e['id']]['id']}
                            if e['id'] in approved_removals else {})}
                        for e in entries if e['id'] in removals]
    output['desired'], output['movable'] = viewing_order(
        pool, selected_ids, entries, removals, policies, managed, state, paused_ids)
    output['added_duration_seconds'] = sum(v['duration'] for v in additions)
    # A paused channel cannot change this plan's actions or lifecycle effects.
    deadlines = [d for d in deadlines if d[2] not in paused]
    earliest = min(deadlines)[:2] if deadlines else None
    output['valid_until'] = earliest[0].isoformat() if earliest else None
    output['valid_until_inclusive'] = earliest[1] if earliest else True
    output['valid_until_causes'] = [{'channel_id': cid, 'video_id': vid, 'reason': reason}
                                  for at, _, cid, vid, reason in sorted(deadlines)
                                  if at == earliest[0]] if earliest else []
    return output
