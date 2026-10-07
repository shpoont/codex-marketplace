"""Serialized writes with durable intent and complete readback before acknowledgment."""
from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from datetime import datetime, timezone
import json
import os
import time
from pathlib import Path

from .config import digest, timestamp
from .planner import APPROVAL_FIELDS, PLAN_SCHEMA, membership, observation_digest, plan, policy_config
from .trial import plan_trial
from . import telemetry


class ExecutionError(RuntimeError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


def plan_change_details(approved, checked_at, *, rechecked=None, stage='execution'):
    """Explain rejection without returning full catalogs, plans or response text."""
    deadline = approved.get('valid_until')
    inclusive = approved.get('valid_until_inclusive', True)
    expired = bool(deadline and (timestamp(checked_at) > timestamp(deadline) or
                                (timestamp(checked_at) == timestamp(deadline) and not inclusive)))
    causes = approved.get('valid_until_causes', [])
    details = {'code': 'plan_changed', 'stage': stage,
               'deadline': {'valid_until': deadline, 'inclusive': inclusive,
                            'checked_at': checked_at, 'expired': expired,
                            'causes': causes[:10], 'causes_omitted': max(0, len(causes) - 10)}}
    if rechecked is not None:
        details['changed_fields'] = [k for k in APPROVAL_FIELDS if approved.get(k) != rechecked.get(k)]
        changes, total = [], 0
        for action in ('remove', 'add', 'expire'):
            before = {v['video_id']: v for v in approved.get(action, [])}
            after = {v['video_id']: v for v in rechecked.get(action, [])}
            for vid in sorted(before.keys() | after.keys()):
                if before.get(vid) == after.get(vid):
                    continue
                total += 1
                if len(changes) < 10:
                    changes.append({'action': action, 'video_id': vid,
                                    **{key: ({k: v[k] for k in ('reason', 'expired_at', 'added_at') if k in v}
                                              if v is not None else None)
                                       for key, v in [('approved', before.get(vid)), ('current', after.get(vid))]}})
        details.update(action_changes=changes, action_changes_omitted=max(0, total - len(changes)))
    return details


def collect_observation(store, transport, progress=None, open_browser=False):
    # A failed attempt must not make an older successful observation look current.
    started = time.monotonic()
    attempt = {'status': 'running', 'started_at': telemetry.utc_now(), 'run_id': store.run_id}
    store.put('collection_attempt', attempt)
    telemetry.event(store, 'collection_started', attempt)
    store.db.commit()
    try:
        if open_browser:
            transport.open()
        def needed_evidence(observation):
            proposed = plan(store.config, observation, store.project_observation(observation, store.config),
                            telemetry.utc_now(), metadata_only=True)
            return list(dict.fromkeys(proposed['listing_requests'] + proposed['metadata_requests']))
        result = transport.collect(progress=progress, previous=store.get('observation'),
                                   required_metadata_ids=sorted(store.snapshot().get('restorations', {})),
                                   metadata_selector=needed_evidence)
    except BaseException as error:
        status = 'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'needs_attention'
        store.put('collection_attempt', {**attempt, 'status': status, 'error': str(error),
                                         'details': getattr(error, 'details', {})})
        telemetry.event(store, 'collection_finished', {'status': status,
                        'duration_seconds': time.monotonic() - started, 'error': telemetry.failure(error)})
        store.db.commit()
        raise
    # Keep the latest normalized readback for diagnosing a rejected apply. It is
    # evidence only: membership advances exclusively through State.observe.
    store.put('last_collection_evidence', {'run_id': store.run_id, 'observation': result})
    store.put('collection_attempt', {**attempt, 'status': 'complete', 'collected_at': result['collected_at']})
    telemetry.event(store, 'collection_finished', {'status': 'complete',
                    'duration_seconds': time.monotonic() - started, 'metrics': result.get('collection', {})})
    store.db.commit()
    return result


def ids(playlist):
    return [e['id'] for e in playlist['entries']]


def verify_effect(operation, playlist):
    if not playlist.get('complete') or ids(playlist) != operation['expected_ids']:
        raise ExecutionError('Readback differs from the expected result; stop and inspect the operation journal')
    original = dict((vid, eid) for eid, vid in operation['before'])
    for e in playlist['entries']:
        if e['id'] in original and e['entry_id'] != original[e['id']]:
            raise ExecutionError('An existing playlist item changed identity during the operation')


def perform(store, transport, current, operation, now=None, guard=None):
    fresh = transport.playlist()
    if membership(fresh) != membership(current):
        raise ExecutionError('Playlist changed before the next operation; collect a new preview')
    # Completion cleanup requires the entry to remain fully watched. Ordinary
    # moves/removals still stop if a formerly active entry becomes watched.
    for child in operation.get('operations', [operation]):
        if child['kind'] in {'remove', 'move'} and child.get('purpose') != 'transport_test':
            target = next(e for e in fresh['entries'] if e['id'] == child['video_id'])
            if child.get('purpose') == 'user_decision':
                if target['percent'] != child['expected_percent']:
                    raise ExecutionError('Reviewed video progress changed; refresh the decision')
            elif child['kind'] == 'remove' and child.get('purpose') == 'watched_cleanup':
                if target['percent'] != 100 or target.get('playable') is not True:
                    raise ExecutionError('Completed video evidence changed; collect a new preview before removing it')
            elif target['percent'] >= 100:
                raise ExecutionError('Video is now fully watched; collect a new preview before managing it')
    if guard:
        guard()
    operation = {**operation, 'before': membership(current),
                 'started_at': now() if now else datetime.now(timezone.utc).isoformat()}
    if not operation.get('channel_id'):
        operation['channel_id'] = next((e.get('channel_id') for e in fresh['entries']
                                       if e['id'] == operation.get('video_id')), None)
    if operation['kind'] == 'batch':
        operation['operations'] = [{**child, 'channel_id': child.get('channel_id') or next(
            (e.get('channel_id') for e in fresh['entries'] if e['id'] == child.get('video_id')), None)}
            for child in operation['operations']]
    oid = store.begin_operation(operation)
    # No blind retry: even a transport exception can mean a committed YouTube write.
    transport.edit(operation['action'], operation['before'])
    # YouTube can acknowledge an edit before browse exposes it. Re-read only
    # while the complete membership is exactly the pre-edit state. An unrelated
    # difference stops immediately, and the write itself is never repeated.
    for attempt in range(5):
        after = transport.playlist()
        try:
            verify_effect(operation, after)
        except ExecutionError:
            if not after.get('complete') or membership(after) != operation['before'] or attempt == 4:
                raise
            telemetry.record(store, 'operation_readback_pending', {'operation_id': oid, 'attempt': attempt + 1})
            time.sleep(2)
        else:
            store.confirm_operation(oid, after)
            return after


def recover(store, transport):
    pending = store.pending_operations()
    if not pending:
        return {'status': 'nothing_to_recover'}
    current = transport.playlist()
    for operation in pending:
        verify_effect(operation, current)
        store.confirm_operation(operation['operation_id'], current)
    # A final add or an ordering move can fail after membership has converged.
    # Preserve that completed phase so the next preview cannot rebuild it again.
    last = pending[-1]
    if last.get('plan_id') and last['kind'] in {'add', 'move', 'batch'}:
        approved = store.read_plan(last['plan_id'])
        if (approved.get('schema') == PLAN_SCHEMA and set(ids(current)) == set(approved['desired'])
                and approved['config_hash'] == digest(policy_config(store.config))):
            store.record_membership_applied(last['plan_id'], current)
    telemetry.record(store, 'recovery_completed', {'confirmed_operations': len(pending)})
    with store.db:
        telemetry.queue_snapshot(store, current, telemetry.utc_now(), 'verified_recovery')
    return {'status': 'confirmed_by_readback', 'operations': len(pending),
            'next': 'Collect and preview again; the old plan is stale'}


def perform_many(store, transport, current, operations, now=None, guard=None):
    """Bounded ordered batches with one durable intent and readback per batch."""
    for offset in range(0, len(operations), 20):
        children = operations[offset:offset + 20]
        if len(children) == 1:
            operation = children[0]
        else:
            operation = {'kind': 'batch', 'operations': children,
                         'action': [child['action'] for child in children],
                         'expected_ids': children[-1]['expected_ids']}
        current = perform(store, transport, current, operation, now, guard)
    return current


def create_private_snapshot(transport, config, title, video_ids, receipt_path):
    """Explicit one-time copy of reviewed IDs; never called by normal refreshes.

    Creation has no idempotency key. An existing intent, including an uncertain
    response, blocks a second request. Inspect the account before any retry.
    """
    path = Path(receipt_path)
    receipt = {'status': 'creation_pending', 'title': title, 'video_ids': video_ids,
               'account_channel_id': config['account_channel_id']}

    def save(handle):
        json.dump(receipt, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())

    with path.open('x') as handle:
        save(handle)
    result = transport.call('createPlaylist', config, title, video_ids)
    receipt.update(result, status='created_awaiting_readback')
    with path.open('w') as handle:
        save(handle)
    target = {**config, 'playlist_id': result['playlist_id'], 'environment': 'development'}
    current = transport.call('playlist', target)
    if (not current.get('complete') or current.get('title') != title or
            current.get('privacy') != 'Private' or ids(current) != video_ids or
            current.get('account_channel_id') != config['account_channel_id'] or
            current.get('playlist_id') != result['playlist_id']):
        raise ExecutionError('Created playlist failed readback; inspect the creation receipt before continuing')
    receipt.update(status='verified', playlist=current)
    with path.open('w') as handle:
        save(handle)
    return receipt


def remove_channel_entries(store, transport, channel_ids, expected_before, progress=None):
    """Explicit removal of all selected channels' entries, including watched ones.

    This is a user-requested library operation, not the routine policy cleanup.
    Each bounded batch keeps a durable intent and uses ordinary readback recovery.
    """
    if not channel_ids or store.pending_operations():
        raise ExecutionError('Select channels and recover pending operations before removal')
    current = transport.playlist()
    if membership(current) != expected_before:
        raise ExecutionError('Playlist changed since the explicit removal preview')
    removed = 0
    while True:
        selected = [e for e in current['entries'] if e['channel_id'] in channel_ids][:50]
        if not selected:
            return current
        entry_ids = {e['entry_id'] for e in selected}
        operation = {'kind': 'remove_batch', 'purpose': 'explicit_channel_removal',
                     'channel_ids': sorted(channel_ids), 'entry_ids': sorted(entry_ids),
                     'video_ids': [e['id'] for e in selected],
                     'video_channels': {e['id']: e['channel_id'] for e in selected},
                     'before': membership(current),
                     'expected_ids': [e['id'] for e in current['entries'] if e['entry_id'] not in entry_ids],
                     'started_at': datetime.now(timezone.utc).isoformat()}
        oid = store.begin_operation(operation)
        transport.call('removeBatch', transport.config, operation['entry_ids'], operation['before'])
        current = transport.playlist()
        verify_effect(operation, current)
        store.confirm_operation(oid, current)
        removed += len(selected)
        if progress:
            progress({'removed': removed, 'remaining_entries': len(current['entries'])})


def apply(store, transport, config, plan_id, now, progress=None):
    return _apply(store, transport, config, plan_id, now, progress)


def resolve_decision(store, transport, config, decision_id, choice, now, progress=None):
    """Freshly validate an answer; playlist writes remain in normal refresh/apply."""
    transport.open()
    if store.pending_operations():
        recover(store, transport)
    observation = collect_observation(store, transport, progress)
    store.observe(observation, config)
    current = plan(config, observation, store.snapshot(), now())
    store.save_plan(current)
    return store.resolve_decision(decision_id, choice, current)


def revoke_exception(store, transport, config, video_id, progress=None):
    expected = store.snapshot().get('managed_entries', {}).get(video_id, {}).get('entry_id')
    transport.open()
    if store.pending_operations():
        recover(store, transport)
    store.observe(collect_observation(store, transport, progress), config)
    return store.revoke_exception(video_id, expected)


def refresh(store, transport, config, now, progress=None, *, apply_changes=False):
    """Own the complete configured refresh, with one bounded recovery cycle.

    Fresh collection, planning and execution share one observation. Preview-only
    remains the default; the apply flag authorizes the configured policies.
    """
    if (store.get('transport_test') or {}).get('state') == 'running':
        raise ExecutionError('Finish the interrupted transport test first')
    confirmed_before = {row[0] for row in store.db.execute("SELECT id FROM operations WHERE state='confirmed'")}
    transport.open()
    if store.pending_operations():
        recover(store, transport)
    for attempt in range(2):
        observation = collect_observation(store, transport, progress)
        store.observe(observation, config)
        proposed = plan(config, observation, store.snapshot(), now())
        plan_id = store.save_plan(proposed)
        if not apply_changes or proposed['status'] != 'ready':
            return {**proposed, 'plan_id': plan_id, 'window_id': transport.window_id}
        try:
            result = _apply(store, transport, config, plan_id, now, progress, live=observation)
            counts = Counter()
            for oid, payload in store.db.execute("SELECT id,payload FROM operations WHERE state='confirmed'"):
                if oid not in confirmed_before:
                    operation = json.loads(payload)
                    counts.update(child['kind'] for child in operation.get('operations', [operation]))
            return {**result, 'added': counts['add'], 'removed': counts['remove'], 'moves': counts['move'],
                    'plan_id': plan_id, 'window_id': transport.window_id}
        except Exception:
            # Only a recorded uncertain write has a known recovery procedure.
            # Unknown errors, read failures and mismatches remain visible.
            if attempt or not store.pending_operations():
                raise
            recover(store, transport)
    raise ExecutionError('Refresh recovery limit reached')


def _apply(store, transport, config, plan_id, now, progress=None, *, live=None):
    approved = store.read_plan(plan_id)
    state = store.snapshot()
    if (store.get('transport_test') or {}).get('state') == 'running':
        raise ExecutionError('Finish the interrupted transport test first')
    if approved['status'] != 'ready':
        raise ExecutionError('This preview has unresolved settings or evidence and cannot be applied')
    if approved['config_hash'] != digest(policy_config(config)) or approved['state_version'] != state['version']:
        raise ExecutionError('Configuration or operational state changed; preview again')
    if approved.get('schema') != PLAN_SCHEMA:
        raise ExecutionError('Saved plan uses an older rule implementation; collect and preview again')
    if state['in_flight']:
        raise ExecutionError('Recover the pending operation first')
    baseline = store.get('observation')
    if baseline is None or observation_digest(baseline) != approved['observation_hash']:
        raise ExecutionError('Saved observation differs from the preview; collect and preview again')
    if live is None:
        live = collect_observation(store, transport, progress)
    elif observation_digest(live) != approved['observation_hash']:
        raise ExecutionError('Refresh observation differs from its saved plan')
    # A complete fresh scan may contain renamed titles, older display labels or
    # activity on ignored channels. Preserve the reviewed playlist baseline and
    # re-evaluate every resulting action instead of requiring identical catalogs.
    progress_baseline = lambda observation: [
        [e['entry_id'], e['id'], e['percent']] for e in observation['playlist']['entries']]
    if membership(live['playlist']) != approved['before'] or progress_baseline(live) != progress_baseline(baseline):
        raise ExecutionError('YouTube observations changed: playlist membership or watch progress; preview again')
    checked_at = now()
    rechecked = (plan_trial(config, live, state, checked_at, approved['development_trial']['per_channel'])
                 if approved.get('development_trial') else plan(config, live, state, checked_at))
    changes = plan_change_details(approved, checked_at, rechecked=rechecked, stage='revalidation')
    if changes['changed_fields'] or changes['deadline']['expired']:
        message = ('YouTube observations changed: saved preview time window ended at ' + approved['valid_until']
                   if changes['deadline']['expired'] else
                   'YouTube observations changed: ' + ', '.join(changes['changed_fields']))
        raise ExecutionError(message + '; collect and preview again', changes)
    telemetry.record(store, 'preview_revalidated', {
        'observation_changed': observation_digest(live) != approved['observation_hash'],
        'approved_actions_unchanged': True,
        'pending_inventory_refreshed': approved['pending'] != rechecked['pending']})
    store.plan_id = plan_id  # Journal ownership is required outside CLI telemetry too.
    if approved.get('development_trial'):
        store.start_development_trial(approved)
    current = live['playlist']
    def check_time():
        if approved.get('valid_until'):
            details = plan_change_details(approved, now())
            if details['deadline']['expired']:
                raise ExecutionError('A playlist time window changed during execution at ' +
                                     approved['valid_until'] + '; collect and preview again', details)
    operations, expected = [], ids(current)
    for removal in approved['remove']:
        expected = [v for v in expected if v != removal['video_id']]
        operations.append({
            'kind': 'remove', **removal, 'config_hash': approved['config_hash'],
            'action': {'action': 'ACTION_REMOVE_VIDEO', 'setVideoId': removal['entry_id']},
            'expected_ids': expected,
        })
    current = perform_many(store, transport, current, operations, now, check_time)
    operations, expected = [], ids(current)
    for addition in approved['add']:
        expected = expected + [addition['video_id']]
        operations.append({
            'kind': 'add', **addition,
            'action': {'action': 'ACTION_ADD_VIDEO', 'addedVideoId': addition['video_id']},
            'expected_ids': expected,
        })
    current = perform_many(store, transport, current, operations, now, check_time)
    check_time()
    store.record_membership_applied(plan_id, current, pending=rechecked['pending'])
    current = reorder(store, transport, current, approved['desired'], set(approved['movable']),
                      'development_trial' if approved.get('development_trial') else 'management', check_time)
    check_time()
    final = transport.playlist()
    if membership(final) != membership(current) or ids(final) != approved['desired']:
        raise ExecutionError('Final playlist changed before completion')
    current = final
    # Unselected inventory is evidence for later runs, not an approved edit.
    # Its metadata may expire or become known without changing any action above.
    # Persist the fresh inventory while leaving the saved approval immutable.
    store.finish_plan({**approved, 'pending': rechecked['pending']}, current)
    return {'status': 'applied', 'removed': len(approved['remove']), 'added': len(approved['add']),
            'added_duration_seconds': approved['added_duration_seconds'], 'playlist_entries': len(current['entries']),
            'decisions': approved.get('decisions', []), 'paused_channels': approved.get('paused_channels', []),
            'warnings': rechecked.get('warnings', [])}


def _stationary_ids(sequence, desired, movable):
    """Keep a longest common subsequence containing every immovable entry.

    Untouched entries must appear in the same relative order in both lists.
    Fixed anchors divide that choice into independent segments; an increasing
    subsequence of destination positions keeps the most entries in each one.
    Moving the complement therefore requires the fewest legal move requests.
    """
    anchors = [vid for vid in sequence if vid not in movable]
    if anchors != [vid for vid in desired if vid not in movable]:
        raise ExecutionError('Ordering would change the relative order of immovable entries')
    positions = {vid: i for i, vid in enumerate(desired)}
    kept = set(anchors)
    boundaries = [i for i, vid in enumerate(sequence) if vid not in movable] + [len(sequence)]
    start, lower = 0, -1
    for end in boundaries:
        upper = positions[sequence[end]] if end < len(sequence) else len(desired)
        tails, tail_positions, previous = [], [], {}
        for vid in sequence[start:end]:
            destination = positions[vid]
            if not lower < destination < upper:
                continue
            index = bisect_left(tail_positions, destination)
            previous[vid] = tails[index - 1] if index else None
            if index == len(tails):
                tails.append(vid)
                tail_positions.append(destination)
            else:
                tails[index] = vid
                tail_positions[index] = destination
        vid = tails[-1] if tails else None
        while vid is not None:
            kept.add(vid)
            vid = previous[vid]
        start, lower = end + 1, upper
    return kept


def reorder(store, transport, current, desired, movable, purpose='management', guard=None):
    sequence = ids(current)
    if set(sequence) != set(desired) or len(desired) != len(sequence) or len(set(sequence)) != len(sequence):
        raise ExecutionError('Ordering cannot change membership')
    stationary = _stationary_ids(sequence, desired, movable)
    # Compile the minimal move sequence locally; entry IDs survive moves.
    successor, operations = None, []
    entries = {e['id']: e['entry_id'] for e in current['entries']}
    for vid in reversed(desired):
        if vid not in stationary:
            without = [x for x in sequence if x != vid]
            position = without.index(successor) if successor else len(without)
            expected = without[:position] + [vid] + without[position:]
            if sequence != expected:
                action = {'action': 'ACTION_MOVE_VIDEO_AFTER', 'setVideoId': entries[vid]}
                if position:
                    action['movedSetVideoIdPredecessor'] = entries[without[position - 1]]
                operations.append({'kind': 'move', 'video_id': vid,
                                   'purpose': purpose,
                                   'action': action, 'expected_ids': expected})
                sequence = expected
        successor = vid
    current = perform_many(store, transport, current, operations, guard=guard)
    if ids(current) != desired:
        raise ExecutionError('Final order failed verification')
    return current


def transport_test(store, transport, config, video_ids):
    """Explicit bounded integration test in an empty private development playlist."""
    if config['environment'] != 'development' or config['playlist_id'] == 'WL':
        raise ExecutionError('Transport test requires the separate development playlist')
    observation = store.get('observation')
    if observation is None:
        raise ExecutionError('Collect first to choose classified test videos')
    videos = {v['id']: v for c in observation['channels'] for v in c['videos']}
    if len(video_ids) != 2 or len(set(video_ids)) != 2:
        raise ExecutionError('Transport test requires exactly two distinct video IDs')
    for vid in video_ids:
        v = videos.get(vid)
        if not v or v['kind'] != 'normal' or v['percent'] >= 100 or not v['playable']:
            raise ExecutionError('Test video is not a verified available unwatched normal video')
    current = transport.playlist()
    prior = store.get('transport_test') or {}
    if prior.get('state') == 'running':
        readback = store.get('last_readback')
        if prior.get('video_ids') != video_ids or store.pending_operations() or readback is None \
                or membership(readback) != membership(current) or set(ids(current)) - set(video_ids):
            raise ExecutionError('Interrupted transport test needs journal readback before resuming')
    else:
        if current['entries'] or current.get('privacy') != 'Private':
            raise ExecutionError('Transport test requires an empty, verified private playlist')
        with store.db:
            store.put('transport_test', {'state': 'running', 'video_ids': video_ids})
    for vid in video_ids:
        if vid in ids(current):
            continue
        current = perform(store, transport, current, {
            'kind': 'add', 'video_id': vid, 'purpose': 'transport_test',
            'action': {'action': 'ACTION_ADD_VIDEO', 'addedVideoId': vid},
            'expected_ids': ids(current) + [vid],
        })
    current = reorder(store, transport, current, list(reversed(video_ids)), set(video_ids), 'transport_test')
    # Verify a second order transition using the same deterministic reorder path.
    current = reorder(store, transport, current, video_ids, set(video_ids), 'transport_test')
    for entry in list(current['entries']):
        current = perform(store, transport, current, {
            'kind': 'remove', 'video_id': entry['id'], 'purpose': 'transport_test',
            'action': {'action': 'ACTION_REMOVE_VIDEO', 'setVideoId': entry['entry_id']},
            'expected_ids': [v for v in ids(current) if v != entry['id']],
        })
    result = {'status': 'passed', 'added': 2, 'reorders': 2, 'removed': 2,
              'final_entries': len(current['entries']),
              'scope': 'transport_test_only'}
    with store.db:
        store.put('transport_test', result)
    return result
