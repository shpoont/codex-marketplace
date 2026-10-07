"""Explicit collect, preview and apply commands; no implicit playlist mutation."""
from __future__ import annotations

import argparse
import contextlib
import sqlite3
import json
import sys
import time
from zoneinfo import ZoneInfoNotFoundError
from datetime import datetime, timezone
from pathlib import Path

from . import executor, reporting, telemetry
from .config import ConfigurationError, load, unresolved
from .planner import plan
from .trial import plan_trial
from .browser_control import TransportError, browser_session
from .javascript import JavaScriptPage
from .safari import SafariPage
from .transport import YouTubeTransport
from .state import State, StateError


def now():
    return datetime.now(timezone.utc).isoformat()


def progress_reporter(store=None, *, visible=False):
    last = [0.0]
    def report(value):
        if time.monotonic() - last[0] > 10:
            if store is not None:
                safe = {k: v for k, v in value.items() if k in {
                    'phase', 'pages', 'completed', 'total', 'removed', 'remaining_entries', 'next_request_at',
                    'channel_id', 'remaining_possible_checks', 'metadata_fetched', 'metadata_reused',
                    'metadata_skipped', 'metadata_outside_lookback', 'metadata_deferred'}}
                telemetry.record(store, 'progress', safe)
            if visible:
                print(json.dumps({'run_id': getattr(store, 'run_id', None), 'progress': value}), file=sys.stderr, flush=True)
            last[0] = time.monotonic()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(Path.home() / 'Library/Application Support/info.komarovsky.codex-plugin-youtube-playlist-management/config/development.yaml'))
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument('--window-id', type=int, help='Explicitly reuse a dedicated Safari window')
    browser.add_argument('--javascript-bridge', help='Use a running main-page JavaScript controller directory')
    output_options = argparse.ArgumentParser(add_help=False)
    output_options.add_argument('--details', action='store_true', help='Print complete plans and failure details')
    output_options.add_argument('--progress', action='store_true', help='Also print progress to stderr; always recorded locally')
    sub = parser.add_subparsers(dest='command', required=True)
    def add_command(name, **kwargs):
        return sub.add_parser(name, parents=[output_options], **kwargs)
    for name in ['validate', 'collect', 'preview', 'status', 'recover', 'subscriptions', 'decisions']:
        add_command(name)
    add_command('apply').add_argument('--plan', required=True)
    decision = add_command('resolve-decision', help='Recheck a saved keep/remove question and record your answer')
    decision.add_argument('--decision', required=True)
    decision.add_argument('--choice', required=True, choices=['keep', 'remove'])
    add_command('revoke-exception', help='Restore ordinary channel rules for a kept exception').add_argument('--video', required=True)
    add_command('show-plan', help='Read a saved plan locally without collecting or replanning').add_argument('--plan', required=True)
    repair = add_command('repair-legacy-ownership', help='Repair local ownership from a trusted pre-migration KV snapshot; no YouTube writes')
    repair.add_argument('--snapshot', required=True, help='Target-bound before-state.json exported before lifecycle migration')
    repair.add_argument('--apply', dest='apply_repair', action='store_true', help='Back up SQLite and persist the reviewed local repair')
    add_command('refresh', help='Collect and plan once; optionally apply configured rules').add_argument(
        '--apply', dest='apply_changes', action='store_true', help='Apply the configured policies within this refresh')
    add_command('trial-preview', help='Preview an explicitly requested one-time development sample').add_argument(
        '--per-channel', required=True, type=int, help='First N eligible videos per configured channel')
    test = add_command('transport-test')
    test.add_argument('--video', action='append', required=True, help='Supply twice; temporary add/move/remove in empty development target')
    report = add_command('analytics', help='Local daily run, queue and channel metrics; no browser access')
    report.add_argument('--days', type=int, default=30)
    report.add_argument('--timezone', default='Europe/Lisbon')
    log = add_command('logs', help='Latest durable events, optionally restricted to one run')
    log.add_argument('--run', dest='run_id')
    log.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    command_prefix = reporting.COMMAND_PREFIX
    if args.javascript_bridge:
        reporting.COMMAND_PREFIX = (*command_prefix, '--javascript-bridge', args.javascript_bridge)
    run_id = None
    report_root = None
    try:
        config = load(args.config)
        if args.command == 'validate':
            print(json.dumps({'valid': True, 'unresolved': unresolved(config)}, indent=2)); return 0
        with State(config) as store:
            report_root = store.root
            migration_before = store.get('state').get('count_window_migration')
            context = (contextlib.nullcontext() if args.command in {'status', 'analytics', 'logs', 'show-plan', 'decisions'} else
                       telemetry.Run(store, args.command, config, getattr(args, 'plan', None)))
            with context as run, contextlib.ExitStack() as browsers:
                run_id = run.id if run else None
                progress = progress_reporter(store, visible=args.progress)
                # Read former managed channels until their rule-change cleanup is verified.
                # This changes observation coverage, never the user's desired YAML policies.
                configured_ids = {c['id'] for c in config['channels']}
                former = set(store.snapshot()['policies']) - configured_ids
                transport_config = {**config, 'channels': config['channels'] +
                                    [{'id': cid, 'name': cid} for cid in sorted(former)]}

                def create_transport():
                    runner = (JavaScriptPage(args.javascript_bridge) if args.javascript_bridge
                              else SafariPage(args.window_id))
                    transport = YouTubeTransport(transport_config, runner)
                    transport.telemetry = lambda value: telemetry.record(store, 'transport_sample', value)
                    return browsers.enter_context(browser_session(
                        transport, lambda value: telemetry.record(store, 'browser_cleanup', value)))

                if args.command == 'repair-legacy-ownership':
                    result = store.repair_legacy_ownership(json.loads(Path(args.snapshot).read_text()), apply=args.apply_repair)
                    if not args.details:
                        result = {k: v for k, v in result.items() if k not in {'repaired', 'superseded_decisions'}}
                elif args.command == 'show-plan':
                    result = {**store.read_plan(args.plan), 'plan_id': args.plan}
                elif args.command == 'decisions':
                    result = {'decisions': [d for d in (store.get('decisions') or {}).values()
                                             if d['status'] == 'pending'],
                              'exceptions': [{'video_id': vid, **m} for vid, m in
                                  store.snapshot().get('managed_entries', {}).items() if m['status'] == 'exception']}
                elif args.command == 'analytics':
                    result = telemetry.analytics(store, args.days, args.timezone, now())
                elif args.command == 'logs':
                    result = telemetry.logs(store, args.run_id, args.limit)
                elif args.command == 'refresh':
                    if (store.get('transport_test') or {}).get('state') == 'running':
                        raise StateError('Finish the interrupted transport test before refreshing')
                    transport = create_transport()
                    result = executor.refresh(store, transport, config, now, progress,
                                              apply_changes=args.apply_changes)
                elif args.command == 'collect':
                    if store.pending_operations():
                        raise StateError('Recover the pending operation before collecting again')
                    if (store.get('transport_test') or {}).get('state') == 'running':
                        raise StateError('Finish the interrupted transport test before collecting again')
                    transport = create_transport()
                    observation = executor.collect_observation(store, transport, progress, open_browser=True)
                    store.observe(observation, config)
                    result = {'status': 'collected', 'window_id': transport.window_id,
                              'playlist_entries': len(observation['playlist']['entries']),
                              'collection': observation.get('collection'),
                              'channels': [{'id': c['id'], 'videos': len(c['videos']), 'pages': c['pages']} for c in observation['channels']]}
                elif args.command in ['preview', 'trial-preview']:
                    attempt = store.get('collection_attempt')
                    if attempt and attempt['status'] != 'complete':
                        raise StateError('The latest collection is incomplete; finish collection before previewing')
                    observation = store.get('observation')
                    if observation is None:
                        raise StateError('Collect a complete observation before previewing')
                    state = store.snapshot()
                    if state.get('observation_version') != state['version']:
                        raise StateError('Operations changed state since collection; collect again before previewing')
                    result = (plan_trial(config, observation, state, now(), args.per_channel)
                              if args.command == 'trial-preview' else plan(config, observation, state, now()))
                    result = {**result, 'plan_id': store.save_plan(result)}
                elif args.command == 'status':
                    data = store.snapshot()
                    result = {'identity': store.identity, 'state_version': data['version'],
                              'dismissed': len(data['dismissed']), 'pending': len(data['pending']),
                              'expired': len(data.get('expired', {})),
                              'decisions': sum(d['status'] == 'pending' for d in (store.get('decisions') or {}).values()),
                              'exceptions': sum(m['status'] == 'exception' for m in data.get('managed_entries', {}).values()),
                              'last_reappearance': store.get('last_reappearance'),
                              'unresolved_operations': len(data['in_flight']),
                              'last_collection': (store.get('observation') or {}).get('collected_at'),
                              'collection_attempt': store.get('collection_attempt'),
                              'development_trial': data['development_trial'],
                              'transport_test': store.get('transport_test'),
                              'telemetry_started_at': store.get('telemetry_started_at')}
                elif args.command == 'recover' and not store.pending_operations():
                    result = {'status': 'nothing_to_recover'}
                else:
                    if args.command == 'apply' and store.read_plan(args.plan)['status'] != 'ready':
                        raise executor.ExecutionError('Preview is blocked; no browser writes attempted')
                    transport = create_transport()
                    if args.command not in {'resolve-decision', 'revoke-exception'}:
                        transport.open()
                    if args.command == 'subscriptions':
                        result = {'status': 'subscriptions_checked', 'window_id': transport.window_id,
                                  **transport.call('subscriptionSnapshot', config, progress=progress)}
                    elif args.command == 'apply':
                        result = executor.apply(store, transport, config, args.plan, now, progress)
                    elif args.command == 'recover':
                        result = executor.recover(store, transport)
                    elif args.command == 'resolve-decision':
                        result = executor.resolve_decision(store, transport, config, args.decision,
                                                           args.choice, now, progress)
                    elif args.command == 'revoke-exception':
                        result = executor.revoke_exception(store, transport, config, args.video, progress)
                    else:
                        result = executor.transport_test(store, transport, config, args.video)
                try:
                    browsers.close()
                except TransportError as error:
                    error.details = {**error.details, 'operation_result': {
                        k: result[k] for k in ('status', 'plan_id', 'added', 'removed', 'moves') if k in result}}
                    raise
                migration = store.get('state').get('count_window_migration')
                if migration_before is None and migration and migration['repaired_count']:
                    result = {**result, 'count_overflow_history_repair': {
                        k: migration[k] for k in ('repaired_count', 'backup_path')}}
                if run is not None:
                    result = {**result, 'run_id': run.id}
                    run.finish(result)
                if 'desired' in result and 'plan_id' in result and not args.details:
                    result = reporting.plan_summary(result, args.config)
                elif 'decisions' in result and isinstance(result['decisions'], list) and not args.details:
                    result = reporting.decision_summary(result, args.config)
            print(json.dumps(result, indent=2))
            return 2 if result.get('status') == 'needs_attention' or result.get('decisions') else 0
    except (ConfigurationError, StateError, TransportError, executor.ExecutionError, OSError, ValueError,
            sqlite3.Error, ZoneInfoNotFoundError) as error:
        print(json.dumps(reporting.error_report(error, run_id, args.config, report_root,
                                               details=args.details)), file=sys.stderr)
        return 2
    finally:
        reporting.COMMAND_PREFIX = command_prefix


if __name__ == '__main__':
    raise SystemExit(main())
