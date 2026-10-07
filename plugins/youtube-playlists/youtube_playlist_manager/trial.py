"""Explicit development samples with a requested number per channel."""
from collections import Counter
from .planner import plan


def plan_trial(config, observation, state, now, per_channel):
    output = plan(config, observation, state, now)
    output.update(remove=[], add=[], desired=[], pending=[], movable=[])
    output.pop('added_duration_seconds', None)
    blockers = [b for b in output['blockers'] if b != 'Finish the development sample before normal reconciliation']
    if config['environment'] != 'development' or config['playlist_id'] == 'WL' \
            or observation['playlist'].get('privacy') != 'Private':
        blockers.append('A sample requires the private development playlist')
    if type(per_channel) is not int or per_channel < 1:
        blockers.append('Sample size must be a positive number of videos per channel')
    trial = state.get('development_trial')
    entries = observation['playlist']['entries']
    candidates = output['candidate_preview']['videos']
    current_ids = {e['id'] for e in entries}
    if trial:
        if trial['state'] != 'running':
            blockers.append('The development sample is already populated')
        if trial['per_channel'] != per_channel or trial['config_hash'] != output['config_hash']:
            blockers.append('Resume with the original sample size and configuration')
        if current_ids != set(trial['confirmed_ids']):
            blockers.append('Sample membership differs from confirmed manager additions')
        by_id = {v['id']: v for v in candidates}
        if any(vid not in by_id for vid in trial['video_ids']):
            blockers.append('Sample eligibility changed; review the original sample before resuming')
        selected = [by_id[vid] for vid in trial['video_ids'] if vid in by_id]
    else:
        if entries:
            blockers.append('Start the development sample in an empty playlist')
        selected, counts = [], Counter()
        if type(per_channel) is int and per_channel > 0:
            for video in candidates:
                if counts[video['channel_id']] < per_channel:
                    selected.append(video)
                    counts[video['channel_id']] += 1
    if not selected:
        blockers.append('No eligible sample videos')
    additions = [v for v in selected if v['id'] not in current_ids]
    output['development_trial'] = {'per_channel': per_channel}
    output['blockers'] = sorted(set(blockers))
    if blockers:
        output['status'] = 'needs_attention'
        return output
    output.update(status='ready', added_duration_seconds=sum(v['duration'] for v in additions),
                  add=[{'video_id': v['id'], 'channel_id': v['channel_id'],
                        'reason': 'development_sample', 'purpose': 'development_trial'}
                       for v in additions],
                  desired=[v['id'] for v in selected], movable=[v['id'] for v in selected],
                  pending=[v['id'] for v in candidates if v['id'] not in {s['id'] for s in selected}])
    return output
