"""Durable, local observability. These records never drive playlist decisions."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
import hashlib
import math
import re
from pathlib import Path
import time
import uuid
from zoneinfo import ZoneInfo

from .config import digest, timestamp
from .browser_control import cleanup_diagnostics, open_diagnostics
from .planner import APPROVAL_FIELDS, policy_config


SCHEMA = 1
ENDPOINTS = {'/youtubei/v1/account/account_menu', '/youtubei/v1/browse',
             '/youtubei/v1/player', '/youtubei/v1/browse/edit_playlist', '/youtubei/v1/playlist/create'}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def initialize(store):
    store.db.executescript('''
        CREATE TABLE IF NOT EXISTS telemetry_runs (
            id TEXT PRIMARY KEY, command TEXT NOT NULL, started_at TEXT NOT NULL,
            finished_at TEXT, status TEXT NOT NULL, duration_seconds REAL,
            config_hash TEXT NOT NULL, plan_id TEXT, summary TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS telemetry_events (
            id INTEGER PRIMARY KEY, run_id TEXT, at TEXT NOT NULL,
            kind TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS telemetry_configurations (
            hash TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS telemetry_events_time ON telemetry_events(at);
        CREATE INDEX IF NOT EXISTS telemetry_events_run ON telemetry_events(run_id, kind);
        CREATE INDEX IF NOT EXISTS telemetry_events_kind ON telemetry_events(kind, id);
        CREATE INDEX IF NOT EXISTS telemetry_runs_time ON telemetry_runs(started_at);
    ''')
    with store.db:
        if store.get('telemetry_started_at') is None:
            store.put('telemetry_started_at', utc_now())
        # The target lock proves that an older recorded owner is no longer running.
        # Its end time/duration are unknown, not the time we noticed the interruption.
        for (run_id,) in store.db.execute("SELECT id FROM telemetry_runs WHERE status='running'").fetchall():
            store.db.execute("UPDATE telemetry_runs SET status='interrupted' WHERE id=?", (run_id,))
            event(store, 'run_interruption_detected', {'reason': 'previous_owner_exited'}, run_id=run_id)
        baseline = store.get('telemetry_membership')
        if baseline and any(e.get('kind') == 'unknown' for e in baseline):
            # Repair the retained comparison baseline where evidence exists,
            # before a new observation replaces that evidence. Keep old progress.
            restored = classified_readback(store, {'entries': baseline})
            restored = [{k: e.get(k) for k in ('id', 'entry_id', 'channel_id', 'kind', 'percent')}
                        for e in restored['entries']]
            if restored != baseline:
                store.put('telemetry_membership', restored)


def event(store, kind, payload, *, run_id=None, at=None):
    """Join the caller's transaction; journal acknowledgments and events commit together."""
    store.db.execute('INSERT INTO telemetry_events(run_id,at,kind,payload) VALUES (?,?,?,?)',
                     (run_id or getattr(store, 'run_id', None), at or utc_now(), kind,
                      json.dumps({'schema': SCHEMA, **payload})))


def record(store, kind, payload):
    if kind == 'browser_cleanup':
        payload = cleanup_diagnostics(payload) or {'classification': 'verification_error'}
    with store.db:
        event(store, kind, payload)


def plan_failure(details):
    """Allowlist and bound diagnostics shared by terminal reports and run logs."""
    if details.get('code') != 'plan_changed' or details.get('stage') not in ('revalidation', 'execution'):
        return {}
    safe = {'stage': details['stage']}
    fields = details.get('changed_fields')
    if isinstance(fields, list):
        safe['changed_fields'] = [k for k in APPROVAL_FIELDS if k in fields]
    def time_fields(value, keys):
        result = {}
        if isinstance(value, dict):
            for key in keys:
                if value.get(key) is None:
                    if key in value:
                        result[key] = None
                elif isinstance(value[key], str):
                    try:
                        result[key] = timestamp(value[key]).isoformat()
                    except (ValueError, TypeError):
                        pass
        return result
    def omitted(value, discarded):
        return discarded + (value if type(value) is int and 0 <= value <= 2**63 - 1 else 0)
    def video_id(value):
        return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', value)
    reasons = {'time_expired', 'count_window_overflow', 'retention_or_eligibility', 'dismissed',
               'fully_watched', 'user_decision', 'eligible_missing', 'outside_lookback', 'publication_reached'}
    deadline = details.get('deadline')
    if isinstance(deadline, dict):
        parsed = time_fields(deadline, ('valid_until', 'checked_at'))
        for key in ('inclusive', 'expired'):
            if type(deadline.get(key)) is bool:
                parsed[key] = deadline[key]
        causes = deadline.get('causes')
        if isinstance(causes, list):
            kept = []
            for cause in causes[:10]:
                if (isinstance(cause, dict) and video_id(cause.get('video_id'))
                        and isinstance(cause.get('reason'), str) and cause['reason'] in reasons):
                    item = {k: cause[k] for k in ('video_id', 'reason')}
                    cid = cause.get('channel_id')
                    if isinstance(cid, str) and re.fullmatch(r'UC[A-Za-z0-9_-]{22}', cid):
                        item['channel_id'] = cid
                    kept.append(item)
            parsed.update(causes=kept, causes_omitted=omitted(deadline.get('causes_omitted'), len(causes)-len(kept)))
        safe['deadline'] = parsed
    changes = details.get('action_changes')
    if isinstance(changes, list):
        kept = []
        for change in changes[:10]:
            if (not isinstance(change, dict) or not video_id(change.get('video_id'))
                    or change.get('action') not in ('remove', 'add', 'expire')):
                continue
            item = {k: change[k] for k in ('video_id', 'action')}
            for key in ('approved', 'current'):
                value = change.get(key)
                if value is None:
                    item[key] = None
                elif isinstance(value, dict):
                    item[key] = time_fields(value, ('expired_at', 'added_at'))
                    if isinstance(value.get('reason'), str) and value['reason'] in reasons:
                        item[key]['reason'] = value['reason']
            kept.append(item)
        safe.update(action_changes=kept,
                    action_changes_omitted=omitted(details.get('action_changes_omitted'), len(changes)-len(kept)))
    return safe


def failure(error):
    """Allowlisted diagnostics only: never store arbitrary exception/response text."""
    details = getattr(error, 'details', {}) or {}
    safe = plan_failure(details)
    for key in ('http_status', 'retry_after_seconds'):
        value = details.get(key)
        if isinstance(value, (int, float)) and math.isfinite(value):
            safe[key] = value
    if details.get('endpoint') in ENDPOINTS:
        safe['endpoint'] = details['endpoint']
    adapter = details.get('adapter')
    if isinstance(adapter, dict) and adapter.get('stage') in {
            'build_detection', 'native_exports', 'transport_resolution',
            'request_builders', 'request_builder', 'bridge_initialization',
            'page_context', 'session_context', 'client_context', 'session_signing',
            'session_authorization', 'request_contract', 'endpoint_contract',
            'response_contract', 'browse_response', 'account_response', 'playlist_response'}:
        safe['adapter'] = {'stage': adapter['stage']}
        build = adapter.get('build')
        if isinstance(build, str) and re.fullmatch(r'[A-Za-z]{2,3}_[A-Za-z]{2}\.[A-Za-z0-9_-]{1,80}', build):
            safe['adapter']['build'] = build
        if adapter.get('error_type') in {'Error', 'TypeError', 'ReferenceError', 'SyntaxError', 'RangeError'}:
            safe['adapter']['error_type'] = adapter['error_type']
    cleanup = details.get('browser_cleanup', details)
    if receipt := cleanup_diagnostics(cleanup):
        safe['browser_cleanup'] = receipt
    if opening := open_diagnostics(details.get('browser_open')):
        safe['browser_open'] = opening
    operation = details.get('operation_result')
    if (isinstance(operation, dict) and isinstance(operation.get('status'), str) and
            operation['status'] in {'applied', 'ready', 'needs_attention', 'collected', 'recovered',
                                    'subscriptions_checked', 'decision_recorded', 'exception_revoked'}):
        safe['operation_result'] = {'status': operation['status']}
    if details.get('retry_at'):
        try:
            safe['retry_at'] = timestamp(details['retry_at']).isoformat()
        except (ValueError, TypeError):
            pass
    message = str(error).lower()
    category = 'unexpected_error'
    for term, label in [('rate limit', 'rate_limited'), ('cooldown', 'rate_limited'),
                        ('readback', 'readback_required'), ('recover', 'recovery_required'),
                        ('changed', 'stale_or_changed_evidence'), ('incomplete', 'incomplete_evidence'),
                        ('collect', 'collection_required'), ('deferred', 'unresolved_policy'),
                        ('account', 'identity_or_authentication'), ('safari', 'browser_unavailable'),
                        ('browser', 'browser_unavailable'), ('controller', 'browser_unavailable'),
                        ('deadline', 'timeout'), ('http', 'http_error')]:
        if term in message:
            category = label
            break
    if details.get('code') == 'rate_limited' or safe.get('http_status') == 429:
        category = 'rate_limited'
    elif details.get('code') == 'catalog_inconsistent':
        category = 'catalog_inconsistent'
    elif details.get('code') in ('ytpm_page_missing', 'ytpm_page_ambiguous'):
        category = 'browser_page_binding'
    elif details.get('code') == 'browser_capability_missing':
        category = 'browser_capability_missing'
    elif details.get('code') == 'browser_dispatch_timeout':
        category = 'timeout'
    elif details.get('code') == 'browser_cleanup_failed':
        category = 'browser_cleanup'
    elif details.get('code') in ('browser_execution_uncertain', 'browser_response_invalid'):
        category = 'readback_required'
    elif details.get('code') in ('auth_required', 'session_changed'):
        category = 'identity_or_authentication'
    elif details.get('code') == 'api_incompatible':
        category = 'adapter_incompatible'
    elif 'browser_cleanup' in safe and 'browser_cleanup' not in details:
        category = 'browser_cleanup'
    elif 'adapter' in safe:
        category = 'adapter_incompatible'
    elif details.get('code') == 'playlist_unavailable':
        category = 'playlist_unavailable'
    elif details.get('code') == 'plan_changed' and 'stage' in safe:
        category = 'stale_or_changed_evidence'
    return {'category': category, 'error_type': type(error).__name__, **safe}


def runtime_fingerprint():
    root = Path(__file__).parent
    digest = hashlib.sha256()
    browser_sources = [p for p in root.glob('browser/*')
                       if p.suffix in {'.py', '.js', '.json', '.applescript'}]
    for path in sorted([*root.glob('*.py'), *browser_sources]):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class Run:
    def __init__(self, store, command, config, plan_id=None):
        self.store, self.command = store, command
        self.id, self.plan_id = str(uuid.uuid4()), plan_id
        self.config_hash = digest(policy_config(config))
        self.policies = policy_config(config)
        self.result = None

    def __enter__(self):
        self.started = time.monotonic()
        self.store.run_id = self.id
        self.store.plan_id = self.plan_id
        with self.store.db:
            self.store.db.execute('INSERT OR IGNORE INTO telemetry_configurations VALUES (?,?)',
                                  (self.config_hash, json.dumps(self.policies)))
            self.store.db.execute('INSERT INTO telemetry_runs VALUES (?,?,?,?,?,?,?,?,?)',
                (self.id, self.command, utc_now(), None, 'running', None, self.config_hash, self.plan_id, '{}'))
            event(self.store, 'run_started', {'command': self.command, 'config_hash': self.config_hash,
                  'environment': self.store.config['environment'], 'runtime_fingerprint': runtime_fingerprint()})
        return self

    def finish(self, result):
        self.result = result

    def __exit__(self, exc_type, error, tb):
        status = ('interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else
                  'needs_attention' if error or (self.result or {}).get('status') == 'needs_attention'
                  or (self.result or {}).get('decisions') else 'success')
        summary = {'result_status': (self.result or {}).get('status'),
                   'unresolved_operations': len(self.store.pending_operations())}
        if error:
            summary['error'] = failure(error)
        rows = self.store.db.execute("SELECT payload FROM telemetry_events WHERE run_id=? AND kind='operation_confirmed'",
                                     (self.id,)).fetchall()
        summary['confirmed_operations'] = dict(Counter(json.loads(r[0])['kind'] for r in rows))
        summary['no_changes'] = (self.command in {'apply', 'refresh'} and status == 'success'
                                 and (self.result or {}).get('status') == 'applied' and not rows)
        with self.store.db:
            self.store.db.execute('UPDATE telemetry_runs SET finished_at=?,status=?,duration_seconds=?,plan_id=?,summary=? WHERE id=?',
                (utc_now(), status, round(time.monotonic() - self.started, 3),
                 (self.result or {}).get('plan_id', self.plan_id), json.dumps(summary), self.id))
            event(self.store, 'run_finished', {'status': status, **summary})
        self.store.run_id = None
        self.store.plan_id = None


def operation_event(store, kind, oid, operation, playlist=None):
    if operation['kind'] == 'batch':
        for index, child in enumerate(operation['operations']):
            operation_event(store, kind, f'{oid}:{index}', {**operation, **child}, playlist)
        return
    videos = operation.get('video_ids') or [operation.get('video_id')]
    known = {e['id']: e for e in (playlist or {}).get('entries', [])}
    payload = {key: operation[key] for key in ('kind', 'reason', 'purpose', 'started_at', 'plan_id', 'run_id') if key in operation}
    payload.update(operation_id=oid, videos=[{'id': vid, 'channel_id': known.get(vid, {}).get('channel_id')
                                            or operation.get('video_channels', {}).get(vid) or operation.get('channel_id')}
                                            for vid in videos if vid])
    event(store, kind, payload)


def observe_changes(store, observation, previous_state):
    """Sampled transitions, not proof of a human action or of minutes watched."""
    prior = store.get('telemetry_membership')
    entries = observation['playlist']['entries']
    current = {e['id']: e for e in entries}
    if prior is not None:
        before = {e['id']: e for e in prior}
        changes = defaultdict(Counter)
        for vid in before.keys() | current.keys():
            old, new = before.get(vid), current.get(vid)
            cid = (new or old).get('channel_id') or 'unknown'
            if old is None:
                changes[cid]['external_additions_observed'] += 1
                if vid in previous_state.get('dismissed', []):
                    changes[cid]['dismissed_returns_observed'] += 1
            elif new is None:
                changes[cid]['external_removals_observed'] += 1
            elif old.get('entry_id') == new.get('entry_id') and old.get('kind') == new.get('kind') == 'normal':
                a, b = old.get('percent'), new.get('percent')
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    if a < 100 <= b:
                        changes[cid]['completions_observed'] += 1
                    elif a < b < 100:
                        changes[cid]['progress_increases_observed'] += 1
        event(store, 'membership_changes', {'observed_at': observation['collected_at'], 'channels': dict(changes)})
    save_membership(store, observation['playlist'])


def classified_readback(store, playlist):
    """Join stable video facts without changing raw receipts or fresh watch state."""
    observation = store.get('observation') or {}
    known = {v['id']: v for channel in observation.get('channels', []) for v in channel['videos']}
    known.update({e['id']: e for e in observation.get('playlist', {}).get('entries', [])})
    entries = []
    for raw in playlist['entries']:
        item = dict(raw)
        evidence = known.get(raw['id'], {})
        # An observed conflicting owner must remain unresolved.
        if evidence and (not raw.get('channel_id') or raw['channel_id'] == evidence.get('channel_id')):
            if raw.get('kind') in (None, 'unknown'):
                item['kind'] = evidence.get('kind', 'unknown')
            if not raw.get('channel_id'):
                item['channel_id'] = evidence.get('channel_id')
            if raw.get('duration') is None:
                item['duration'] = evidence.get('duration')
        entries.append(item)
    return {**playlist, 'entries': entries}


def save_membership(store, playlist, *, raw_readback=False):
    if raw_readback:
        playlist = classified_readback(store, playlist)
    store.put('telemetry_membership', [{k: e.get(k) for k in ('id', 'entry_id', 'channel_id', 'kind', 'percent')}
                                     for e in playlist['entries']])


def queue_snapshot(store, playlist, at, source):
    if source != 'collection':
        playlist = classified_readback(store, playlist)
    clocks = store.get('state').get('entry_times', {})
    channels = {c['id']: {'name': c['name'], 'additions': c['additions']} for c in store.config['channels']}
    fields = ('entries', 'active_videos', 'active_duration_seconds', 'partially_watched',
              'fully_watched', 'excluded_or_unclassified', 'unknown_progress',
              'unavailable_or_unknown', 'unknown_duration_videos', 'unknown_addition_time_videos',
              'oldest_active_age_seconds')
    def empty():
        return Counter(dict.fromkeys(fields, 0))
    totals, groups = empty(), {cid: empty() for cid in channels}
    for entry in playlist['entries']:
        cid = entry.get('channel_id') or 'unknown'
        group = groups.setdefault(cid, empty())
        values = {'entries': 1}
        percent = entry.get('percent')
        if entry.get('kind') != 'normal':
            values['excluded_or_unclassified'] = 1
        elif percent is None:
            values['unknown_progress'] = 1
        elif percent >= 100:
            values['fully_watched'] = 1
        elif entry.get('playable') is not True:
            values['unavailable_or_unknown'] = 1
        else:
            values['active_videos'] = 1
            values['partially_watched'] = int(percent > 0)
            if entry.get('duration') is not None:
                values['active_duration_seconds'] = entry['duration']
            else:
                values['unknown_duration_videos'] = 1
            added = clocks.get(entry['id'], {}).get('added_at')
            if added:
                age = max(0, (timestamp(at) - timestamp(added)).total_seconds())
                group['oldest_active_age_seconds'] = max(age, group['oldest_active_age_seconds'])
                totals['oldest_active_age_seconds'] = max(age, totals['oldest_active_age_seconds'])
            else:
                values['unknown_addition_time_videos'] = 1
        group.update(values); totals.update(values)
    event(store, 'queue_snapshot', {'observed_at': at, 'source': source, 'classification_version': 1, 'totals': dict(totals),
          'channels': {cid: {**channels.get(cid, {'name': cid, 'additions': 'unconfigured'}), **v}
                       for cid, v in groups.items()}})


def plan_event(store, plan_id, plan):
    event(store, 'plan_saved', {'plan_id': plan_id, 'status': plan['status'], 'config_hash': plan['config_hash'],
          'blocker_count': len(plan['blockers']), 'channels': plan.get('channels', []),
          'decision_count': len(plan.get('decisions', [])),
          'warning_count': len(plan.get('warnings', [])),
          'warnings_by_code': dict(Counter(w['code'] for w in plan.get('warnings', []))),
          'planned_additions': len(plan['add']), 'planned_removals': len(plan['remove']),
          'removal_reasons': dict(Counter(v['reason'] for v in plan['remove'])),
          'pending_candidates': len(plan['pending']), 'desired_entries': len(plan['desired']),
          'added_duration_seconds': plan.get('added_duration_seconds', 0)})


def analytics(store, days=30, timezone_name='Europe/Lisbon', now=None):
    """Daily counters and latest sampled gauges; absence of evidence stays explicit."""
    if not 1 <= days <= 3660:
        raise ValueError('Analytics days must be between 1 and 3660')
    zone = ZoneInfo(timezone_name)
    end = timestamp(now or utc_now())
    start_day = end.astimezone(zone).date() - timedelta(days=days - 1)
    start = datetime.combine(start_day, datetime.min.time(), zone).astimezone(timezone.utc).isoformat()
    daily = {str(start_day + timedelta(days=n)): {'date': str(start_day + timedelta(days=n)),
              'runs': {}, 'operations': {}, 'membership_changes': {}, 'channel_changes': {},
              'collection': {}, 'requests': {}, 'transport_calls_by_last_status': {}}
             for n in range(days)}
    durations, outcomes, commands, errors = [], Counter(), defaultdict(Counter), Counter()
    command_durations = defaultdict(list)
    def day(at):
        return daily[str(timestamp(at).astimezone(zone).date())]
    def queue_quality(value):
        if value.get('source') in ('verified_apply', 'verified_recovery') and not value.get('classification_version'):
            # Historical aggregates do not retain enough membership evidence to
            # reconstruct every old snapshot. Do not show bogus zeros as facts.
            value['classification_valid'] = False
            value['limitation'] = 'Legacy raw-readback snapshot: classified counts unavailable'
            for group in [value.get('totals', {}), *value.get('channels', {}).values()]:
                for key in list(group):
                    if key not in ('entries', 'name', 'additions'):
                        group[key] = None
        else:
            value['classification_valid'] = True
        return value
    runs = store.db.execute('SELECT id,command,started_at,finished_at,status,duration_seconds,summary FROM telemetry_runs WHERE started_at>=? AND started_at<=? ORDER BY started_at',
                            (start, end.isoformat())).fetchall()
    for rid, command, started, finished, status, duration, raw in runs:
        summary = json.loads(raw)
        bucket = day(started)
        bucket['runs'][status] = bucket['runs'].get(status, 0) + 1
        outcomes[status] += 1; commands[command][status] += 1
        if duration is not None:
            durations.append(duration)
            command_durations[command].append(duration)
        if summary.get('error'):
            errors[summary['error']['category']] += 1
    request_samples = {}
    channel_changes = defaultdict(Counter)
    for at, kind, raw in store.db.execute('SELECT at,kind,payload FROM telemetry_events WHERE at>=? AND at<=? ORDER BY at,id', (start, end.isoformat())):
        value, bucket = json.loads(raw), day(at)
        if kind == 'queue_snapshot':
            bucket['queue'] = queue_quality(value)
        elif kind == 'plan_saved':
            bucket['latest_preview'] = value  # Repeated previews are not new inventory.
        elif kind == 'operation_confirmed':
            purpose = value.get('purpose', 'management')
            reason = value.get('reason', 'unspecified')
            key = '/'.join((purpose, value['kind'], reason))
            bucket['operations'][key] = bucket['operations'].get(key, 0) + len(value['videos'])
            for video in value['videos']:
                cid = video['channel_id'] or 'unknown'
                channel_changes[cid][key] += 1
                counts = bucket['channel_changes'].setdefault(cid, {})
                counts[key] = counts.get(key, 0) + 1
        elif kind == 'membership_changes':
            for cid, counts in value['channels'].items():
                channel_changes[cid].update(counts)
                bucket['channel_changes'][cid] = dict(Counter(bucket['channel_changes'].get(cid, {})) + Counter(counts))
                bucket['membership_changes'] = dict(Counter(bucket['membership_changes']) + Counter(counts))
        elif kind == 'collection_finished':
            bucket['collection']['attempts'] = bucket['collection'].get('attempts', 0) + 1
            bucket['collection'][value['status']] = bucket['collection'].get(value['status'], 0) + 1
            for key, count in value.get('metrics', {}).items():
                if key in {'new_videos', 'metadata_fetched', 'metadata_reused', 'metadata_skipped',
                           'metadata_outside_lookback', 'metadata_deferred', 'catalog_pages_read',
                           'catalogs_full', 'catalogs_incremental', 'catalogs_skipped', 'listing_pages_refreshed',
                           'catalogs_degraded', 'catalog_videos_retained', 'watch_status_skipped'}:
                    bucket['collection'][key] = bucket['collection'].get(key, 0) + count
        elif kind == 'transport_sample':
            request_samples[value['call_id']] = (at, value)
    # Cumulative samples: use each call's last durable sample exactly once.
    for at, value in request_samples.values():
        statuses = day(at)['transport_calls_by_last_status']
        status = value['status']
        statuses[status] = statuses.get(status, 0) + 1
        for endpoint, counts in value.get('requests', {}).items():
            target = day(at)['requests'].setdefault(endpoint, {})
            for key, number in counts.items():
                target[key] = target.get(key, 0) + number
    queue = store.db.execute("SELECT at,payload FROM telemetry_events WHERE kind='queue_snapshot' ORDER BY id DESC LIMIT 1").fetchone()
    latest_run = store.db.execute('SELECT id,command,started_at,status,summary FROM telemetry_runs ORDER BY started_at DESC,rowid DESC LIMIT 1').fetchone()
    completed = outcomes['success'] + outcomes['needs_attention'] + outcomes['interrupted']
    collected_at = (store.get('observation') or {}).get('collected_at')
    last_queue = queue_quality(json.loads(queue[1])) if queue else None
    def percentile(values, fraction):
        return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None
    return {'schema': SCHEMA, 'identity': store.identity, 'generated_at': end.isoformat(),
            'coverage_started_at': store.get('telemetry_started_at'), 'timezone': timezone_name, 'days': days,
            'runs': {'total': len(runs), 'outcomes': dict(outcomes),
                     'by_command': {command: {'outcomes': dict(counts),
                         'duration_seconds_p50': percentile(command_durations[command], .5),
                         'duration_seconds_p95': percentile(command_durations[command], .95)}
                         for command, counts in commands.items()},
                     'success_fraction': outcomes['success'] / completed if completed else None,
                     'duration_seconds_p50': percentile(durations, .5), 'duration_seconds_p95': percentile(durations, .95),
                     'errors_by_category': dict(errors)},
            'health': {'pending_operations': len(store.pending_operations()),
                       'state_storage_bytes': sum(p.stat().st_size for p in store.root.glob('manager.sqlite3*')),
                       'latest_run': dict(zip(('id', 'command', 'started_at', 'status', 'summary'),
                                             (*latest_run[:4], json.loads(latest_run[4])))) if latest_run else None,
                       'last_collection': collected_at,
                       'collection_age_seconds': max(0, (end - timestamp(collected_at)).total_seconds()) if collected_at else None,
                       'queue_age_seconds': max(0, (end - timestamp(last_queue['observed_at'])).total_seconds()) if last_queue else None,
                       'collection_attempt': store.get('collection_attempt')},
            'latest_queue': last_queue,
            'channel_changes': dict(channel_changes), 'daily': list(daily.values())}


def logs(store, run_id=None, limit=100):
    if not 1 <= limit <= 10000:
        raise ValueError('Log limit must be between 1 and 10000')
    query = 'SELECT id,run_id,at,kind,payload FROM telemetry_events'
    params = []
    if run_id:
        query += ' WHERE run_id=?'
        params.append(run_id)
    rows = store.db.execute(query + ' ORDER BY id DESC LIMIT ?', (*params, limit)).fetchall()
    return {'schema': SCHEMA, 'identity': store.identity, 'run_id': run_id,
            'events': [dict(id=rid, run_id=run, at=at, kind=kind, payload=json.loads(raw))
                       for rid, run, at, kind, raw in reversed(rows)]}
