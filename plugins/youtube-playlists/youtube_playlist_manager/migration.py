"""Evidence-preserving conversion and explicit repair of legacy membership."""
import json
import os
import sqlite3
import tempfile
from contextlib import closing

from .config import digest, timestamp
from . import telemetry
from .state import StateError


def backup_before_repair(store, prefix):
    backups = store.root / 'backups'
    backups.mkdir(mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix=prefix, suffix='.sqlite3', dir=backups)
    os.close(fd)
    with closing(sqlite3.connect(path)) as backup:
        store.db.backup(backup)
    return path


def _legacy_count_overflow(plan, observation, operation):
    """Prove count-only exclusion under the recorded schema 11–13 contract.

    The old generic reason is insufficient. Recheck the queued entry, cutoff,
    selected full window and ranking against the immutable observation/policy.
    These planners separately labeled time expiry and explicit decisions.
    """
    from .ordering import normal_active
    from .planner import membership, observation_digest
    if (plan.get('schema') not in {11, 12, 13} or plan.get('status') != 'ready'
            or operation.get('reason') != 'retention_or_eligibility'
            or observation_digest(observation) != plan.get('observation_hash')
            or membership(observation['playlist']) != plan.get('before')):
        return False
    vid, eid = operation['video_id'], operation.get('entry_id')
    removal = next((r for r in plan.get('remove', [])
                    if (r['video_id'], r['entry_id']) == (vid, eid)), {})
    if removal.get('reason') != 'retention_or_eligibility' or removal.get('purpose'):
        return False
    e = next((e for e in observation['playlist']['entries']
              if (e['id'], e['entry_id']) == (vid, eid)), None)
    if not e or not normal_active(e) or not e.get('playable') or not e.get('publication') or not e.get('duration'):
        return False
    cid = e['channel_id']
    policy = plan.get('policies', {}).get(cid)
    channel = next((c for c in plan.get('channels', []) if c['id'] == cid), {})
    if (not policy or not channel.get('subscribed') or cid in plan.get('paused_channels', [])
            or channel.get('filter_counts', {}).get('count_limit', 0) < 1
            or any(r['video_id'] == vid for r in plan.get('expire', []))):
        return False
    count = policy['retention']['maximum_count']
    selected = [v for v in plan.get('candidate_preview', {}).get('videos', []) if v['channel_id'] == cid]
    if not isinstance(count, int) or isinstance(count, bool) or count < 1 or len(selected) != count:
        return False
    pub, moment = timestamp(e['publication']), timestamp(plan['created_at'])
    if pub > moment or vid in {v['id'] for v in selected}:
        return False
    start = policy['catch_up']['start']
    if start == 'from_enablement' or start == 'deferred':
        return False  # No historical enablement clock is part of a saved plan.
    if isinstance(start, dict):
        boundary = start.get('published_after')
        if 'video_id' in start:
            boundary = next((v.get('publication') for c in observation['channels'] if c['id'] == cid
                             for v in c['videos'] if v['id'] == start['video_id']), None)
        if not boundary or pub < timestamp(boundary) or (not start['inclusive'] and pub == timestamp(boundary)):
            return False
    key = lambda v: (timestamp(v['publication']), v['id'])
    mode = policy['retention']['selection']
    if mode == 'oldest_eligible_unwatched':
        return key(e) > max(map(key, selected))
    if mode == 'keep_current_and_refill':
        queued = {e['id'] for e in observation['playlist']['entries']}
        if any(v['id'] not in queued for v in selected):
            return False
    elif mode != 'latest_eligible_unwatched':
        return False
    return key(e) < min(map(key, selected))


def count_overflow_repair_candidates(store):
    """Return proven old count dismissals, preserving any later stay/removal.

    Pure read-only analysis; complete observation preparation applies the result.
    Read only playlist slices when checking later presence, not full catalogs.
    """
    last = {}
    for oid, payload in store.db.execute("SELECT id,payload FROM operations WHERE state='confirmed' ORDER BY rowid"):
        parent = json.loads(payload)
        for child in parent.get('operations', [parent]):
            op = {**parent, **child, 'operation_id': oid}
            if op['kind'] in {'add', 'remove'}:
                last[op['video_id']] = op
    candidates, plans, baselines = [], {}, {}
    for vid, op in last.items():
        if (op['kind'] != 'remove' or op.get('purpose') or not op.get('started_at')
                or op.get('reason') not in {'retention_or_eligibility', 'count_window_overflow'}
                or not op.get('plan_id')):
            continue
        pid = op['plan_id']
        if pid not in plans:
            row = store.db.execute('SELECT payload FROM plans WHERE id=?', (pid,)).fetchone()
            plans[pid] = json.loads(row[0]) if row else None
        plan = plans[pid]
        if not plan or plan.get('identity') != store.identity or plan.get('status') != 'ready':
            continue
        if pid not in baselines:
            from .planner import membership, observation_digest
            baselines[pid] = None
            for rowid, payload in store.db.execute(
                    "SELECT id,payload FROM observations WHERE julianday(json_extract(payload,'$.collected_at')) "
                    "<= julianday(?) ORDER BY id DESC", (plan['created_at'],)):
                o = json.loads(payload)
                if (o.get('complete') and o['playlist'].get('complete')
                        and all(o['playlist'].get(k) == v for k, v in store.identity.items())
                        and membership(o['playlist']) == plan.get('before')
                        and observation_digest(o) == plan.get('observation_hash')):
                    baselines[pid] = (rowid, o)
                    break
        baseline = baselines[pid]
        if not baseline:
            continue
        if op.get('reason') == 'count_window_overflow':
            proven = any(r.get('reason') == 'count_window_overflow'
                         and (r['video_id'], r['entry_id']) == (vid, op.get('entry_id'))
                         for r in plan.get('remove', []))
        else:
            proven = _legacy_count_overflow(plan, baseline[1], op)
        if proven:
            candidates.append({'video_id': vid, 'operation_id': op['operation_id'], 'plan_id': pid,
                               'started_at': op['started_at'], 'observation_id': baseline[0]})
    if not candidates:
        return []
    latest_presence = {}
    for rowid, moment, entries in store.db.execute(
            "SELECT id,json_extract(payload,'$.collected_at'),json_extract(payload,'$.playlist.entries') "
            "FROM observations WHERE id>?", (min(r['observation_id'] for r in candidates),)):
        for e in json.loads(entries):
            latest_presence.setdefault(e['id'], []).append((rowid, timestamp(moment)))
    return [r for r in candidates if not any(rowid > r['observation_id'] and moment >= timestamp(r['started_at'])
                                            for rowid, moment in latest_presence.get(r['video_id'], []))]


def legacy_entries(data, playlists, identity):
    """Only the legacy tracked map establishes ownership, not current settings."""
    membership = dict(data.get('membership', []))
    known = {}
    for playlist in playlists:
        if not playlist:
            continue
        if not playlist.get('complete') or any(playlist.get(k) != v for k, v in identity.items()):
            raise StateError('Legacy ownership evidence has incomplete or mismatched playlist identity')
        for e in playlist['entries']:
            key = e['entry_id'], e['id']
            if e.get('channel_id'):
                if key in known and known[key]['channel_id'] != e['channel_id']:
                    raise StateError('Conflicting channel evidence for a legacy managed entry')
                known[key] = e
    entries = []
    for eid, vid in data.get('tracked', {}).items():
        if membership.get(eid) != vid:
            continue
        e = known.get((eid, vid))
        if not e or not e.get('channel_id'):
            raise StateError('Missing channel evidence for a legacy managed entry; restore its saved readback')
        entries.append(e)
    return entries


def repair_legacy_ownership(store, snapshot, *, apply=False):
    """Restore candidate ownership from a trusted pre-migration KV export.

    This repairs local classification only. It does not renew observations or
    plans, decide manual conflicts, restore the entire backup, or contact YouTube.
    """
    if store.pending_operations() or (store.get('transport_test') or {}).get('state') == 'running':
        raise StateError('Recover pending operations and finish the transport test before ownership repair')
    source = snapshot.get('state', {})
    data = store.get('state')
    if (snapshot.get('identity') != store.identity or snapshot.get('schema_version') != 1
            or 'managed_entries' in source or 'managed_entries' not in data
            or not isinstance(source.get('version'), int) or source['version'] >= data['version']):
        raise StateError('Ownership repair requires an older pre-migration snapshot of this target')
    baseline = snapshot.get('observation')
    if not baseline or not baseline.get('complete'):
        raise StateError('Ownership repair requires a complete saved baseline observation')
    history = [(i, json.loads(payload)) for i, payload in store.db.execute(
        'SELECT id,payload FROM observations ORDER BY id')]
    anchors = [i for i, o in history if o == baseline]
    if len(anchors) != 1:
        raise StateError('Baseline observation is not uniquely anchored in this target database')
    baseline_at = timestamp(baseline['collected_at'])
    source_playlist = snapshot.get('last_readback') or baseline['playlist']
    if source.get('membership') != [[e['entry_id'], e['id']] for e in source_playlist['entries']]:
        raise StateError('Legacy membership differs from the saved complete readback')
    entries = legacy_entries(source, [baseline['playlist'], source_playlist], store.identity)
    # A repeated entry ID does not prove the same stay after an observed absence.
    continuous = {(e['entry_id'], e['id'], e['channel_id']) for e in entries}
    for i, o in history:
        if i <= anchors[0]:
            continue
        p = o['playlist']
        if (not o.get('complete') or not p.get('complete')
                or any(p.get(k) != v for k, v in store.identity.items())):
            raise StateError('Ownership repair requires complete target-bound observation history')
        continuous.intersection_update((e['entry_id'], e['id'], e['channel_id']) for e in p['entries'])
    removed = set()
    for (payload,) in store.db.execute("SELECT payload FROM operations WHERE state='confirmed'"):
        parent = json.loads(payload)
        for child in parent.get('operations', [parent]):
            op = {**parent, **child}
            if op['kind'] == 'remove' and (not op.get('started_at') or timestamp(op['started_at']) >= baseline_at):
                # Include transport-test removals: their observed absence also
                # breaks continuity. Missing times cannot prove an older removal.
                removed.add(op['video_id'])
    current_pairs = dict(data.get('membership', []))
    inbox = store.get('decisions') or {}
    repaired = []
    for e in entries:
        vid, eid = e['id'], e['entry_id']
        m = data['managed_entries'].get(vid, {})
        if (m.get('status') != 'candidate' or m.get('entry_id') != eid
                or m.get('channel_id') != e['channel_id'] or m.get('stay_id') is None
                or current_pairs.get(eid) != vid or (eid, vid, e['channel_id']) not in continuous
                or vid in removed or vid in data['dismissed'] or m.get('decision_id')):
            continue
        if any(d.get('status') == 'resolved' and d.get('video_id') == vid
               and d.get('stay_id') == m['stay_id'] for d in inbox.values()):
            continue
        repaired.append({'video_id': vid, 'entry_id': eid, 'channel_id': e['channel_id'], 'stay_id': m['stay_id']})
    bindings = {(e['video_id'], e['entry_id'], e['stay_id']) for e in repaired}
    superseded = [did for did, d in inbox.items() if d.get('status') == 'pending'
                  and (d.get('video_id'), d.get('entry_id'), d.get('stay_id')) in bindings]
    result = {'status': 'ownership_repaired' if apply else 'ownership_repair_preview',
              'identity': store.identity, 'source_sha256': digest(snapshot),
              'source_version': source['version'], 'state_version_before': data['version'],
              'repaired_count': len(repaired), 'superseded_decision_count': len(superseded),
              'repaired': repaired, 'superseded_decisions': superseded,
              'next': 'Collect a fresh observation before applying the configured playlist rules'}
    if not apply or not repaired:
        return result
    backups = store.root / 'backups'
    backups.mkdir(mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix='before-ownership-repair-', suffix='.sqlite3', dir=backups)
    os.close(fd)
    with closing(sqlite3.connect(path)) as backup:
        store.db.backup(backup)
    result['backup_path'] = path
    for e in repaired:
        data['managed_entries'][e['video_id']]['status'] = 'managed'
    for did in superseded:
        inbox[did].update(status='superseded', superseded_reason='legacy_ownership_repaired')
    data['version'] += 1
    # Leave observation_version unchanged: this maintenance must not make a
    # stale collected playlist or old execution plan look current.
    result['state_version_after'] = data['version']
    with store.db:
        store.put('state', data)
        store.put('decisions', inbox)
        store.put('last_ownership_repair', result)
        telemetry.event(store, 'legacy_ownership_repaired', result)
    return result
