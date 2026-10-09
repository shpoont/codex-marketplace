"""Target-bound SQLite state and a single-writer lock, separate from configuration."""
from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import tempfile
import uuid
from pathlib import Path

from .timing import initialize_clocks, observe_entries
from . import lifecycle, telemetry


class StateError(RuntimeError):
    pass


class State:
    def __init__(self, config, registry_directory=None):
        self.config = config
        self.run_id = None
        self.plan_id = None
        self.identity = {k: config[k] for k in ['account_channel_id', 'playlist_id']}
        self.root = Path(config['storage']['data_directory']).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.lock_file = None
        self.db = None
        self.registry = Path(registry_directory) if registry_directory else (
            Path.home() / 'Library/Application Support/info.komarovsky.codex-plugin-youtube-playlist-management')

    def bind_location(self):
        """Changing or deleting the data path cannot silently reset an existing target."""
        self.registry.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.registry / 'bindings.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            path = self.registry / 'bindings.json'
            bindings = json.loads(path.read_text()) if path.exists() else {}
            key = self.identity['account_channel_id'] + '/' + self.identity['playlist_id']
            if key in bindings:
                if bindings[key] != str(self.root):
                    raise StateError('This target is bound to a different data directory; explicit migration required')
                if not (self.root / 'manager.sqlite3').is_file():
                    raise StateError('Bound target database is missing; restore or explicitly migrate it')
                return True
            bindings[key] = str(self.root)
            with tempfile.NamedTemporaryFile(mode='w', dir=self.registry, delete=False) as temp:
                json.dump(bindings, temp, indent=2)
                temp.flush(); os.fsync(temp.fileno())
                temp_path = Path(temp.name)
            os.replace(temp_path, path)
            return False

    def __enter__(self):
        self.lock_file = (self.root / 'manager.lock').open('a')
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.lock_file.close()
            raise StateError('Another manager run owns this target state') from error
        try:
            previously_bound = self.bind_location()
            self.db = sqlite3.connect(self.root / 'manager.sqlite3')
            os.chmod(self.root / 'manager.sqlite3', 0o600)
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY, state TEXT NOT NULL, payload TEXT NOT NULL);
            ''')
            current = self.get('identity')
            if current is None:
                if previously_bound:
                    raise StateError('Bound target identity is missing; restore the operational database')
                self.put('schema_version', 1)
                self.put('identity', self.identity)
                self.put('state', {'version': 0, 'tracked': {}, 'dismissed': [], 'policies': {},
                                   'enabled_at': {}, 'checkpoints': {}, 'pending': [], 'restorations': {},
                                   'managed_entries': {}})
                self.db.commit()
            elif current != self.identity:
                raise StateError('Stored account/playlist identity differs from configuration; explicit migration required')
            elif self.get('schema_version') != 1:
                raise StateError('Unsupported operational schema; explicit migration required')
            telemetry.initialize(self)
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.db:
            self.db.close()
        if self.lock_file:
            self.lock_file.close()

    def get(self, key):
        row = self.db.execute('SELECT value FROM kv WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO kv VALUES (?,?)', (key, json.dumps(value)))

    def pending_operations(self):
        return [dict(json.loads(payload), operation_id=oid) for oid, payload in self.db.execute(
            "SELECT id,payload FROM operations WHERE state='pending'")]

    def snapshot(self):
        result = self.get('state')
        result['in_flight'] = self.pending_operations()
        result['development_trial'] = self.get('development_trial')
        return result

    def _initialize_lifecycle(self, data, playlist=None):
        if 'managed_entries' in data:
            return
        from .migration import legacy_entries
        entries = legacy_entries(data, [(self.get('observation') or {}).get('playlist'),
                                       self.get('last_readback'), playlist], self.identity)
        data['managed_entries'] = {}
        # Legacy tracking includes both confirmed additions and adopted existing
        # entries. Preserve that ownership before classifying new arrivals.
        for e in entries:
            data['managed_entries'][e['id']] = lifecycle.new_member(data, e, 'managed', origin='unknown')
        data['lifecycle_migration'] = {'version': 2, 'source_state_version': data['version'],
                                     'managed_stays': len(entries)}
        membership = dict(data.get('membership', []))
        last = {}
        for oid, payload in self.db.execute("SELECT id,payload FROM operations WHERE state='confirmed' ORDER BY rowid"):
            parent = {**json.loads(payload), 'operation_id': oid}
            for child in parent.get('operations', [parent]):
                op = {**parent, **child}
                if op.get('purpose') != 'transport_test' and op['kind'] in {'add', 'remove'}:
                    last[op['video_id']] = op
        present = set(membership.values())
        repaired = {r['video_id']: r['operation_id'] for r in
                    data.get('count_window_migration', {}).get('repaired', [])}
        removed = {vid for vid, op in last.items() if op['kind'] == 'remove'
                   and op.get('reason') != 'count_window_overflow'
                   and repaired.get(vid) != op.get('operation_id')} | set(data.get('restorations', {}))
        data['dismissed'] = sorted(set(data['dismissed']) | (removed - present))
        data['restorations'] = {}

    def repair_legacy_ownership(self, snapshot, *, apply=False):
        from .migration import repair_legacy_ownership
        return repair_legacy_ownership(self, snapshot, apply=apply)

    def _prepare_observation(self, observation, config):
        if self.pending_operations():
            raise StateError('Unresolved operation journal; recover before advancing membership')
        if (self.get('transport_test') or {}).get('state') == 'running':
            raise StateError('Finish the interrupted transport test before advancing membership')
        if not observation.get('complete') or not observation['playlist'].get('complete'):
            raise StateError('Incomplete observation cannot advance state or infer removals')
        if observation.get('account_channel_id') != self.identity['account_channel_id'] or any(
            observation['playlist'].get(k) != v for k, v in self.identity.items()
        ):
            raise StateError('Observation account or playlist mismatch')
        if not observation['subscriptions'].get('complete') or any(
                not c.get('complete') and not c.get('catalog_unavailable') for c in observation['channels']):
            raise StateError('Incomplete subscriptions or channel catalog')
        data = self.get('state')
        previous_state = json.loads(json.dumps(data))
        self._initialize_lifecycle(data, observation['playlist'])
        if 'entry_times' not in data:
            initialize_clocks(data, (json.loads(payload) for (payload,) in self.db.execute(
                'SELECT payload FROM observations ORDER BY id')))
        if 'arrival_origin_migration' not in data:
            last_operations = {}
            for (payload,) in self.db.execute(
                    "SELECT payload FROM operations WHERE state='confirmed' ORDER BY rowid"):
                parent = json.loads(payload)
                for child in parent.get('operations', [parent]):
                    op = {**parent, **child}
                    if op.get('purpose') != 'transport_test' and op['kind'] in {'add', 'remove'}:
                        last_operations[op['video_id']] = op
            lifecycle.initialize_origins(data, last_operations)
        entries = observation['playlist']['entries']
        present = {e['id'] for e in entries}
        dismissed = set(data['dismissed'])
        dismissed.update(vid for vid in data['tracked'].values() if vid not in present)
        managed = {c['id'] for c in config['channels']} | set(data['policies'])
        data['dismissed'] = sorted(dismissed)
        subscribed = {c['id'] for c in observation['subscriptions']['channels'] if c['subscribed']}
        lifecycle.observe_members(data, observation, managed,
                                  {c['id'] for c in config['channels']} & subscribed)
        data['tracked'] = {e['entry_id']: e['id'] for e in entries
                           if lifecycle.member(data, e) and lifecycle.member(data, e)['status'] != 'released'}
        changes = observe_entries(data, observation, config)
        if 'count_window_migration' not in data:
            from .migration import count_overflow_repair_candidates
            key = previous_state['version']
            cached = getattr(self, '_count_overflow_repair_cache', None)
            if cached is None or cached[0] != key:
                cached = (key, count_overflow_repair_candidates(self))
                self._count_overflow_repair_cache = cached
            repaired = [r for r in cached[1] if r['video_id'] in data['dismissed']
                        and r['video_id'] not in present and r['video_id'] not in data.get('expired', {})]
            data['dismissed'] = sorted(set(data['dismissed']) - {r['video_id'] for r in repaired})
            data['count_window_migration'] = {
                'version': 1, 'observed_at': observation['collected_at'],
                'repaired_count': len(repaired), 'repaired': repaired}
        for c in config['channels']:
            # First observed enablement remains fixed across later runs.
            if c['additions'] == 'enabled':
                data['enabled_at'].setdefault(c['id'], observation['collected_at'])
        for c in observation['channels']:
            if c.get('complete'):
                data['checkpoints'][c['id']] = observation['collected_at']
        data['membership'] = [[e['entry_id'], e['id']] for e in entries]
        # Complete catalogs are retained; checkpoints never discard pending candidates.
        data['version'] += 1
        data['observation_version'] = data['version']
        return data, changes, previous_state

    def project_observation(self, observation, config):
        """Evaluate the same membership/clock transition without persisting it."""
        data, _, _ = self._prepare_observation(observation, config)
        return {**data, 'in_flight': self.pending_operations(),
                'development_trial': self.get('development_trial')}

    def observe(self, observation, config):
        if 'metadata_stage' in observation:
            raise StateError('Staged metadata collection cannot advance state; finish collection first')
        data, changes, previous_state = self._prepare_observation(observation, config)
        migration = data.get('count_window_migration') if 'count_window_migration' not in previous_state else None
        if migration and migration['repaired_count']:
            from .migration import backup_before_repair
            migration['backup_path'] = backup_before_repair(self, 'before-count-window-repair-')
        origins = data.get('arrival_origin_migration') if 'arrival_origin_migration' not in previous_state else None
        if origins and origins['classified']['manual']:
            from .migration import backup_before_repair
            origins['backup_path'] = backup_before_repair(self, 'before-manual-origin-repair-')
        if any(m['status'] == 'candidate' for m in data['managed_entries'].values()):
            from .planner import plan
            classified = plan(config, observation, data, observation['collected_at'])
            if classified['status'] == 'ready':
                lifecycle.applied_members(data, classified, observation['playlist'])
        with self.db:
            self.db.execute('INSERT INTO observations(payload) VALUES (?)', (json.dumps(observation),))
            self.put('observation', observation)
            if changes['returned']:
                self.put('last_reappearance', {**changes, 'observed_at': observation['collected_at']})
            self.put('state', data)
            if migration:
                telemetry.event(self, 'count_overflow_history_repaired', migration)
            if origins:
                telemetry.event(self, 'arrival_origins_initialized', origins)
            telemetry.observe_changes(self, observation, previous_state)
            telemetry.queue_snapshot(self, observation['playlist'], observation['collected_at'], 'collection')
        return data

    def save_plan(self, plan):
        plan_id = str(uuid.uuid4())
        with self.db:
            inbox = self.get('decisions') or {}
            current = {d['id']: d for d in plan.get('decisions', [])}
            for did, d in inbox.items():
                if plan.get('decisions_complete') and d['status'] == 'pending' and did not in current:
                    d['status'] = 'superseded'
            for did, d in current.items():
                if did not in inbox or inbox[did]['status'] != 'pending':
                    telemetry.event(self, 'decision_requested', d)
                inbox[did] = {**d, 'status': 'pending'}
            self.put('decisions', inbox)
            self.db.execute('INSERT INTO plans VALUES (?,?)', (plan_id, json.dumps(plan)))
            telemetry.plan_event(self, plan_id, plan)
        return plan_id

    def resolve_decision(self, decision_id, choice, current_plan):
        """Record a response against a freshly re-evaluated exact entry/policy."""
        if choice not in {'keep', 'remove'} or self.pending_operations():
            raise StateError('Choose keep/remove and recover any pending operation first')
        from .planner import policy_config, observation_digest
        from .config import digest
        data = self.get('state')
        if (not current_plan.get('decisions_complete') or
                current_plan.get('observation_hash') != observation_digest(self.get('observation')) or
                current_plan['state_version'] != data['version'] or
                current_plan['config_hash'] != digest(policy_config(self.config))):
            raise StateError('Decision state or configuration changed; refresh the decision')
        fresh = next((d for d in current_plan.get('decisions', []) if d['id'] == decision_id), None)
        saved = (self.get('decisions') or {}).get(decision_id)
        if not saved or saved['status'] != 'pending' or fresh is None:
            raise StateError('This decision is no longer current; review the latest decisions')
        m = data.get('managed_entries', {}).get(fresh['video_id'])
        if not m or m['entry_id'] != fresh['entry_id']:
            raise StateError('The playlist entry changed; refresh the decision')
        m.update(status=('released' if fresh['reason'] == 'channel_unmanaged' else 'exception')
                 if choice == 'keep' else 'remove_requested', decision_id=decision_id,
                 decision_binding=fresh)
        if m['status'] == 'released':
            data['tracked'].pop(fresh['entry_id'], None)
        data['version'] += 1
        data['observation_version'] = data['version']
        inbox = self.get('decisions')
        inbox[decision_id] = {**saved, 'status': 'resolved', 'choice': choice}
        with self.db:
            self.put('state', data)
            self.put('decisions', inbox)
            telemetry.event(self, 'decision_resolved', {'decision_id': decision_id, 'choice': choice,
                                                       'video_id': fresh['video_id'], 'channel_id': fresh['channel_id']})
        return {'status': 'decision_recorded', 'decision_id': decision_id, 'choice': choice,
                'next': 'Refresh to apply the reviewed choice and channel rules'}

    def revoke_exception(self, video_id, entry_id):
        data = self.get('state')
        m = data.get('managed_entries', {}).get(video_id, {})
        if self.pending_operations() or m.get('status') != 'exception' or m.get('entry_id') != entry_id:
            raise StateError('This kept exception is no longer current; refresh and review it')
        m.update(status='managed')
        m.pop('decision_id', None)
        m.pop('decision_binding', None)
        data['version'] += 1
        data['observation_version'] = data['version']
        with self.db:
            self.put('state', data)
            telemetry.event(self, 'exception_revoked', {'video_id': video_id, 'entry_id': entry_id})
        return {'status': 'exception_revoked', 'video_id': video_id,
                'next': 'Refresh to apply the channel rules'}

    def read_plan(self, plan_id):
        row = self.db.execute('SELECT payload FROM plans WHERE id=?', (plan_id,)).fetchone()
        if not row:
            raise StateError('Plan not found in this target state')
        return json.loads(row[0])

    def begin_operation(self, operation):
        if self.pending_operations():
            raise StateError('An earlier operation still needs readback')
        oid = str(uuid.uuid4())
        operation = {**operation, 'run_id': self.run_id, 'plan_id': self.plan_id}
        with self.db:
            self.db.execute('INSERT INTO operations VALUES (?,?,?)', (oid, 'pending', json.dumps(operation)))
            telemetry.operation_event(self, 'operation_started', oid, operation)
        return oid

    def start_development_trial(self, plan):
        trial = self.get('development_trial')
        if trial is None:
            with self.db:
                self.put('development_trial', {
                    'state': 'running', 'per_channel': plan['development_trial']['per_channel'],
                    'config_hash': plan['config_hash'], 'video_ids': plan['desired'], 'confirmed_ids': [],
                })
        elif trial['state'] != 'running' or trial['video_ids'] != plan['desired'] \
                or trial['config_hash'] != plan['config_hash']:
            raise StateError('The recorded development sample differs from this plan')

    def confirm_operation(self, oid, playlist):
        row = self.db.execute('SELECT state,payload FROM operations WHERE id=?', (oid,)).fetchone()
        if not row:
            raise StateError('Unknown operation')
        if row[0] == 'confirmed':
            return
        operation = json.loads(row[1])
        with self.db:
            # A confirmed manager removal advances tracking in the same transaction.
            # It creates no permanent exemption for a later restoration and disappearance.
            data = self.get('state')
            self._initialize_lifecycle(data, playlist)
            if 'entry_times' not in data:
                initialize_clocks(data, (json.loads(payload) for (payload,) in self.db.execute(
                    'SELECT payload FROM observations ORDER BY id')))
            clocks = data.setdefault('entry_times', {})
            parent = operation
            for child in parent.get('operations', [parent]):
                operation = {**parent, **child}
                vid = operation.get('video_id')
                if operation['kind'] == 'remove' and operation.get('reason') == 'time_expired':
                    data.setdefault('expired', {})[vid] = {
                        'added_at': clocks.get(vid, {}).get('added_at'),
                        'expired_at': operation['expired_at'], 'channel_id': operation['channel_id']}
                if operation['kind'] == 'remove' and operation.get('purpose') != 'transport_test':
                    # Completion cleanup can remove unowned manual entries;
                    # that global housekeeping does not adopt or dismiss them.
                    owned = lifecycle.member(data, {'id': vid, 'entry_id': operation.get('entry_id')})
                    if operation.get('reason') != 'count_window_overflow' and (
                            operation.get('purpose') != 'watched_cleanup' or
                            owned.get('status') in {'managed', 'manual', 'exception', 'remove_requested'}):
                        data['dismissed'] = sorted(set(data['dismissed']) | {vid})
                    data['managed_entries'].pop(vid, None)
                    data.get('entry_policies', {}).pop(vid, None)
                if operation['kind'] == 'add':
                    data.setdefault('restorations', {}).pop(operation['video_id'], None)
                    if operation.get('purpose') != 'transport_test':
                        clock = operation.get('original_clock') or {
                            'added_at': operation.get('started_at'),
                            'first_seen_at': operation.get('started_at'), 'source': 'manager_write'}
                        # Legacy pending writes may have no timestamp. Leave that unknown
                        # until a complete observation supplies evidence and a chosen rule.
                        if clock.get('first_seen_at'):
                            clocks[vid] = clock
                        data.setdefault('expired', {}).pop(vid, None)
                present = {e['entry_id'] for e in playlist['entries']}
                data['tracked'] = {eid: vid for eid, vid in data['tracked'].items() if eid in present}
                if operation['kind'] == 'add' and operation.get('purpose') != 'transport_test':
                    for e in playlist['entries']:
                        if e['id'] == operation['video_id']:
                            data['tracked'][e['entry_id']] = e['id']
                            data['managed_entries'][e['id']] = lifecycle.new_member(
                                data, e, 'managed', origin='manager')
                            if e['id'] in clocks:
                                clocks[e['id']]['entry_id'] = e['entry_id']
                            if operation.get('plan_id'):
                                applied = self.read_plan(operation['plan_id'])['policies'].get(e['channel_id'])
                                if applied is not None:
                                    data.setdefault('entry_policies', {})[e['id']] = {
                                        'entry_id': e['entry_id'], 'policy': applied}
                data['version'] += 1
                data['membership'] = [[e['entry_id'], e['id']] for e in playlist['entries']]
                if operation.get('purpose') == 'development_trial' and operation['kind'] == 'add':
                    trial = self.get('development_trial')
                    if not trial or operation['video_id'] not in trial['video_ids']:
                        raise StateError('Addition is outside the recorded development sample')
                    if operation['video_id'] not in trial['confirmed_ids']:
                        trial['confirmed_ids'].append(operation['video_id'])
                    self.put('development_trial', trial)
            operation = parent
            self.put('state', data)
            self.put('last_readback', playlist)
            self.db.execute("UPDATE operations SET state='confirmed' WHERE id=?", (oid,))
            telemetry.operation_event(self, 'operation_confirmed', oid, operation, playlist)
            telemetry.save_membership(self, playlist, raw_readback=True)

    def record_membership_applied(self, plan_id, playlist, pending=None):
        """Checkpoint verified membership effects independently of ordering.

        Also repairs an older interrupted run from its immutable plan and
        confirmed journal; matching video IDs alone is insufficient proof.
        """
        from .config import digest
        from .planner import membership, policy_config
        plan = self.read_plan(plan_id)
        data = self.get('state')
        if (plan['status'] != 'ready' or plan['config_hash'] != digest(policy_config(self.config))
                or self.pending_operations()):
            raise StateError('Membership checkpoint requires the current approved rules and a recovered journal')
        ids = [e['id'] for e in playlist.get('entries', [])]
        if (not playlist.get('complete') or any(playlist.get(k) != v for k, v in self.identity.items())
                or len(ids) != len(set(ids)) or set(ids) != set(plan['desired'])
                or membership(playlist) != data['membership']):
            raise StateError('Membership checkpoint differs from the verified playlist')
        confirmed = [json.loads(payload) for (payload,) in self.db.execute(
            "SELECT payload FROM operations WHERE state='confirmed'")]
        confirmed = [{**op, **child} for op in confirmed if op.get('plan_id') == plan_id
                     for child in op.get('operations', [op])]
        removed = {(op.get('video_id'), op.get('entry_id')) for op in confirmed if op['kind'] == 'remove'}
        added = {op.get('video_id') for op in confirmed if op['kind'] == 'add'}
        if (any((r['video_id'], r['entry_id']) not in removed for r in plan['remove'])
                or any(a['video_id'] not in added for a in plan['add'])):
            raise StateError('Membership checkpoint has unconfirmed planned changes')
        previous = self.get('last_membership_plan')
        fresh_pending = (data['pending'] if previous and previous['plan_id'] == plan_id else plan['pending']) \
            if pending is None else pending
        if (previous and previous['plan_id'] == plan_id and data['policies'] == plan['policies']
                and data['pending'] == fresh_pending and not data.get('restorations')):
            return False
        data['policies'] = plan['policies']
        lifecycle.applied_members(data, plan, playlist)
        data['pending'] = fresh_pending
        for expiry in plan.get('expire', []):
            data.setdefault('expired', {})[expiry['video_id']] = {
                key: value for key, value in expiry.items() if key != 'video_id'}
        data['restorations'] = {}
        data['version'] += 1
        with self.db:
            self.put('state', data)
            self.put('last_membership_plan', {'plan_id': plan_id, 'config_hash': plan['config_hash'],
                                            'desired': plan['desired']})
            telemetry.record(self, 'membership_applied', {'plan_id': plan_id, 'entries': len(ids)})
        return True

    def finish_plan(self, plan, playlist):
        data = self.get('state')
        data['policies'] = plan['policies']
        lifecycle.applied_members(data, plan, playlist)
        data['pending'] = plan['pending']
        for expiry in plan.get('expire', []):
            data.setdefault('expired', {})[expiry['video_id']] = {
                key: value for key, value in expiry.items() if key != 'video_id'}
        data['restorations'] = {}
        data['version'] += 1
        with self.db:
            if plan.get('development_trial'):
                trial = self.get('development_trial')
                trial['state'] = 'complete'
                self.put('development_trial', trial)
            self.put('state', data)
            self.put('last_readback', playlist)
            self.put('last_applied_plan', plan)
            telemetry.queue_snapshot(self, playlist, telemetry.utc_now(), 'verified_apply')

    def release_channels(self, config, channel_ids):
        """Explicitly stop ownership after removing channels from configuration.

        Preserve observations, clocks and dismissals. This also supports retiring
        channels from a development target while retaining its existing videos.
        """
        channel_ids = set(channel_ids)
        if not channel_ids or channel_ids & {c['id'] for c in config['channels']}:
            raise StateError('Remove the selected channels from configuration before releasing them')
        if any(config[k] != v for k, v in self.identity.items()) or self.pending_operations():
            raise StateError('Verify the target and recover pending operations before releasing channels')
        data = self.get('state')
        observation = self.get('observation') or {}
        known_ids = {v['id'] for c in observation.get('channels', []) if c['id'] in channel_ids
                     for v in c['videos']}
        known_ids.update(e['id'] for e in observation.get('playlist', {}).get('entries', [])
                         if e['channel_id'] in channel_ids)
        data['policies'] = {cid: p for cid, p in data['policies'].items() if cid not in channel_ids}
        data['tracked'] = {eid: vid for eid, vid in data['tracked'].items() if vid not in known_ids}
        data['managed_entries'] = {vid: m for vid, m in data.get('managed_entries', {}).items()
                                   if m['channel_id'] not in channel_ids}
        data['pending'] = [p for p in data['pending'] if p.get('channel_id') not in channel_ids
                           and p.get('video_id') not in known_ids]
        data['restorations'] = {vid: value for vid, value in data.get('restorations', {}).items()
                                if vid not in known_ids}
        data['version'] += 1
        with self.db:
            self.put('state', data)
            self.put('last_channel_release', {'channel_ids': sorted(channel_ids), 'state_version': data['version']})
