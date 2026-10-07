"""Small terminal reports; complete plans and diagnostics remain inspectable locally."""
from collections import Counter
import json
import os
from pathlib import Path
import shlex

from . import telemetry

COMMAND_PREFIX = ('youtube-playlists',)


def command(config_path, *args):
    return shlex.join([*COMMAND_PREFIX, '--config', str(Path(config_path).resolve()), *args])


def decision_summary(result, config_path, limit=5):
    result = dict(result)
    result.update(warning_summary(result, limit))
    decisions = result.get('decisions', [])
    result.update(decision_count=len(decisions),
                  decisions=[{k: d[k] for k in ('id', 'video_id', 'channel_id', 'title', 'reason', 'choices', 'status')
                              if k in d} for d in decisions[:limit]],
                  decisions_omitted=max(0, len(decisions) - limit),
                  decisions_command=command(config_path, 'decisions', '--details'))
    if 'exceptions' in result:
        exceptions = result['exceptions']
        result.update(exception_count=len(exceptions), exceptions=[
            {k: e[k] for k in ('video_id', 'channel_id', 'entry_id', 'status')} for e in exceptions[:limit]],
            exceptions_omitted=max(0, len(exceptions) - limit))
    return result


def plan_summary(plan, config_path):
    ready = plan['status'] == 'ready'
    blockers = plan.get('blockers', [])
    result = {k: plan[k] for k in ('status', 'plan_id', 'run_id', 'window_id', 'identity', 'created_at',
                                  'valid_until', 'valid_until_inclusive', 'count_overflow_history_repair') if k in plan}
    result.update({
        'executable': ready,
        'playlist_entries': {'before': len(plan['before']), 'after': len(plan['desired']) if ready else None},
        'changes': ({'add': len(plan['add']), 'remove': len(plan['remove']),
                     'playlist_changed': [row[1] for row in plan['before']] != plan['desired'],
                     'addition_reasons': dict(Counter(v['reason'] for v in plan['add'])),
                     'removal_reasons': dict(Counter(v['reason'] for v in plan['remove'])),
                     'added_duration_seconds': plan.get('added_duration_seconds', 0)} if ready else None),
        'inventory': {key: len(plan.get(key, [])) for key in
                      ('pending', 'metadata_requests', 'metadata_deferred', 'listing_requests')},
        'candidate_evidence_complete': plan.get('candidate_preview', {}).get('complete', False),
        'discovery_complete': plan.get('candidate_preview', {}).get('discovery_complete', False),
        **warning_summary(plan),
        'decision_count': len(plan.get('decisions', [])),
        'paused_channels': plan.get('paused_channels', []),
        'decisions': [{k: d[k] for k in ('id', 'video_id', 'channel_id', 'title', 'reason', 'choices')}
                      for d in plan.get('decisions', [])[:5]],
        'decisions_omitted': max(0, len(plan.get('decisions', [])) - 5),
        'decisions_command': command(config_path, 'decisions', '--details'),
        'blocker_count': len(blockers),
        'blockers': [text[:500] for text in blockers[:5]],
        'blockers_omitted': max(0, len(blockers) - 5),
        'blocker_text_truncated': any(len(text) > 500 for text in blockers[:5]),
        'details_command': command(config_path, 'show-plan', '--plan', plan['plan_id'], '--details'),
    })
    causes = plan.get('valid_until_causes', [])
    result.update(valid_until_causes=causes[:5], valid_until_causes_omitted=max(0, len(causes) - 5))
    return result


def warning_summary(result, limit=5):
    warnings = result.get('warnings', [])
    return {'warning_count': len(warnings), 'warnings': warnings[:limit],
            'warnings_omitted': max(0, len(warnings) - limit)}


def error_report(error, run_id, config_path, root=None, *, details=False):
    full = {'status': 'needs_attention', 'run_id': run_id, 'error': str(error),
            'details': getattr(error, 'details', {})}
    result = (dict(full) if details else {
        'status': full['status'], 'run_id': run_id, 'error': str(error)[:500],
        'error_truncated': len(str(error)) > 500, 'details': telemetry.failure(error),
    })
    if run_id:
        result['logs_command'] = command(config_path, 'logs', '--run', run_id, '--limit', '10')
        # Only started runs have an established target directory. Do not create
        # operational state for a configuration or lock failure.
        path = root / 'runs' / run_id / 'error.json'
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
                json.dump(full, handle, indent=2)
            result['error_report'] = str(path)
        except OSError as save_error:
            result['error_report_failure'] = str(save_error)[:500]
            # No retry of the failed operation is needed to recover diagnostics
            # if storage failed: return the original details explicitly.
            result['unsaved_error'] = full
    return result
