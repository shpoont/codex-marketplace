"""One YouTube client using an injected authenticated main-page JavaScript runner."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

from .browser import initialization_source
from .browser_control import (JavaScriptRunner, TransportError, browser_session,
                              SCRIPT_TIMEOUT_SECONDS, JOB_STATUS_SCRIPT_TIMEOUT_SECONDS,
                              READ_ONLY_PAGE_RECOVERIES)


class YouTubeTransport:
    def __init__(self, config: dict, runner: JavaScriptRunner):
        self.config = config
        self.runner = runner
        self.telemetry = None
        self.adapter = None

    @property
    def page_id(self):
        return self.runner.page_id

    @property
    def window_id(self):
        # Legacy command-output field; the neutral identity is page_id.
        return self.page_id

    def evaluate(self, source: str, script_timeout=SCRIPT_TIMEOUT_SECONDS):
        return self.runner.evaluate(source, script_timeout=script_timeout)

    def open(self):
        self.runner.open('https://www.youtube.com/playlist?list=' + self.config['playlist_id'])
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            ready = self.evaluate('''JSON.stringify({
                capable: typeof window.fetch === 'function',
                ready: typeof window.ytcfg?.get === 'function' &&
                    !!window.ytcfg.get('INNERTUBE_CONTEXT'),
                accountReady: window.ytcfg?.get?.('LOGGED_IN') === true,
                signedOut: window.ytcfg?.get?.('LOGGED_IN') === false,
                url: location.href
            })''')
            if ready.get('capable') is False:
                raise TransportError('The JavaScript runner cannot access the actual YouTube page APIs; enable its advanced page execution permission',
                                     {'code': 'browser_capability_missing'})
            if ready['ready'] and ready.get('signedOut'):
                raise TransportError('YouTube sign-in is unavailable; sign in to the intended account in the selected browser and try again',
                                     {'code': 'auth_required'})
            if ready['ready'] and ready['accountReady']:
                url = urlparse(ready['url'])
                if url.hostname != 'www.youtube.com' or parse_qs(url.query).get('list') != [self.config['playlist_id']]:
                    raise TransportError('Dedicated tab is not the configured YouTube playlist')
                initialized = self.evaluate(initialization_source())
                if not initialized.get('ready'):
                    adapter = initialized.get('adapter', {})
                    code = initialized.get('code', 'api_incompatible')
                    message = {
                        'auth_required': 'YouTube sign-in is unavailable; sign in to the intended account in the selected browser and try again',
                        'session_changed': 'The active YouTube session changed; collect again before updating the playlist',
                    }.get(code, 'YouTube API compatibility check failed; this update cannot finish and the plugin may need an update')
                    raise TransportError(message, {'code': code, 'adapter': adapter})
                self.adapter = initialized.get('adapter')
                return self
            time.sleep(0.5)
        raise TransportError('YouTube page or signed-in account menu data did not become ready')

    def close(self):
        return self.runner.close()

    def call(self, method: str, *args, progress=None, timeout=2400, checkpoint=None):
        self.evaluate('JSON.stringify(window.__playlistManager.start(' +
                      json.dumps(method) + ',' + json.dumps(args) + '))')
        deadline, last = time.monotonic() + timeout, None
        call_id, last_sample = str(uuid.uuid4()), 0
        while time.monotonic() < deadline:
            if checkpoint:
                envelope = self.evaluate('''(()=>{const q=window.__playlistManager; return JSON.stringify({
                    job:q?.job || {state:"error",error:"Browser job lost"}, events:q?.drainCheckpoints() || []});})()''',
                                         script_timeout=JOB_STATUS_SCRIPT_TIMEOUT_SECONDS)
                checkpoint(envelope['events'])
                result = envelope['job']
            else:
                result = self.evaluate(
                    'JSON.stringify(window.__playlistManager?.job || {state:"error",error:"Browser job lost"})',
                    script_timeout=JOB_STATUS_SCRIPT_TIMEOUT_SECONDS,
                )
            if self.telemetry and (result['state'] != 'running' or time.monotonic() - last_sample >= 10):
                self.telemetry({'call_id': call_id, 'method': method, 'status': result['state'],
                                'requests': result.get('requests', {}), 'adapter': self.adapter})
                last_sample = time.monotonic()
            if result['state'] == 'complete':
                return result['result']
            if result['state'] == 'error':
                raise TransportError(result['error'], result.get('details'))
            update = result.get('progress')
            if update and update != last and progress:
                progress(update)
                last = update
            # Short commands otherwise pay a full second for each local status
            # poll. Polling reads browser job state; it sends no YouTube request.
            time.sleep(1 if method == 'collect' else 0.1)
        raise TransportError('Browser job deadline exceeded; writes require readback before retry')

    def collect(self, progress=None, previous=None, required_metadata_ids=None, metadata_selector=None):
        from .metadata_cache import MetadataCache, CacheError
        try:
            with MetadataCache(self.config) as cache:
                recoveries = 0
                while True:
                    payload = cache.payload()
                    try:
                        args = [self.config, previous, payload, required_metadata_ids or []]
                        if metadata_selector is not None:
                            args.append(True)
                        observation = self.call('collect', *args, progress=progress,
                                                checkpoint=cache.checkpoint, timeout=86400)
                        if metadata_selector is None:
                            return observation
                        return self._resolve_metadata(observation, metadata_selector, cache, progress)
                    except BaseException as error:
                        if (isinstance(error, TransportError) and
                                error.details.get('code') == 'ytpm_page_missing' and
                                self.runner.can_recover and
                                recoveries < READ_ONLY_PAGE_RECOVERIES):
                            try:
                                self.runner.recover_read_only()
                                self.open()
                            except BaseException as recovery_error:
                                cache.failure(getattr(recovery_error, 'details', {}))
                                raise
                            recoveries += 1
                            if progress:
                                progress({'phase': 'recovering read-only browser page',
                                          'completed_restarts': recoveries})
                            continue
                        try:
                            self.evaluate('''(()=>{const q=window.__playlistManager;
                                if(q?.job?.state === 'running' && q.job.method === 'collect') q.cancelCollection();
                                return JSON.stringify({cancelRequested:true});})()''')
                        except TransportError:
                            pass  # A closed/navigated page has already lost this collection.
                        cache.failure(getattr(error, 'details', {}))
                        raise
        except CacheError as error:
            raise TransportError(str(error), error.details) from error

    def _resolve_metadata(self, observation, select_metadata, cache, progress):
        stage = observation.get('metadata_stage')
        if not isinstance(stage, dict) or not isinstance(stage.get('baseline'), list):
            raise TransportError('Missing staged collection baseline; update the browser adapter')
        videos = {v['id']: v for channel in observation['channels'] for v in channel['videos']}
        known_ids = {r[0] for r in cache.db.execute('SELECT id FROM known_videos')} | videos.keys()
        queued = {v['id'] for v in observation['playlist']['entries']}
        fetched = set()
        metrics = observation['collection']
        deferred = set(stage.get('deferred_ids', []))
        age_skipped = set(stage.get('age_skipped_ids', []))
        while True:
            observation['collected_at'] = datetime.now(timezone.utc).isoformat()
            needed = select_metadata(observation)
            if not needed:
                # Metadata may take time; membership/progress and account must
                # still match the original raw playlist before state can advance.
                fresh = self.playlist()
                self.call('identity', self.config)
                if (not fresh.get('complete') or
                        [[e['entry_id'], e['id'], e['percent']] for e in fresh['entries']] != stage['baseline']):
                    raise TransportError('Playlist changed during metadata checks; collect again')
                observation['collected_at'] = datetime.now(timezone.utc).isoformat()
                if select_metadata(observation):
                    continue  # A time boundary created a vacancy during readback.
                metrics['catalogs_degraded'] = sum(bool(c.get('catalog_unavailable') or c.get('warnings'))
                                                   for c in observation['channels'])
                metrics['catalog_videos_retained'] = sum(v.get('listing_unavailable') is True
                    for c in observation['channels'] for v in c['videos'])
                metrics['watch_status_skipped'] = sum(v.get('listing_unavailable') is True and v['id'] not in queued
                    for c in observation['channels'] for v in c['videos'])
                del observation['metadata_stage']
                return observation
            vid = needed[0]
            stale = [v for v in needed if videos.get(v, {}).get('listing_fresh') is False]
            if stale:
                cid = videos[stale[0]]['channel_id']
                channel = next(c for c in observation['channels'] if c['id'] == cid)
                try:
                    refreshed = self.call('refreshCatalog', {'id': cid, 'name': cid}, channel,
                                          [v for v in stale if videos[v]['channel_id'] == cid])
                except TransportError as error:
                    if error.details.get('code') != 'catalog_inconsistent' or error.details.get('channel_id') != cid:
                        raise
                    channel.update(complete=False, catalog_unavailable=True, warnings=[{
                        'code': 'catalog_unavailable', 'channel_id': cid, 'reason': error.details.get('reason'),
                        'message': 'Channel discovery failed; its additions and retention changes are paused for this run.'}])
                    continue
                if refreshed.get('page_index') and refreshed.get('scanned_at'):
                    cache.checkpoint([{'type': 'catalog', 'catalog': refreshed}])
                channel.clear()
                channel.update(refreshed)
                new_ids = {v['id'] for v in channel['videos']} - videos.keys()
                metrics['new_videos'] += len(new_ids - known_ids)
                known_ids.update(new_ids)
                metrics['metadata_skipped'] += len(new_ids)
                metrics['metadata_deferred'] += len(new_ids)
                videos = {v['id']: v for c in observation['channels'] for v in c['videos']}
                # A full reconciliation can reveal previously unknown candidates.
                uncategorized = {v['id'] for v in channel['videos'] if v['id'] not in queued
                                 and (not v.get('publication') or not v.get('duration'))} - deferred - age_skipped
                deferred.update(uncategorized)
                metrics['metadata_deferred'] += len(uncategorized - new_ids)
                metrics['listing_pages_refreshed'] = metrics.get('listing_pages_refreshed', 0) + refreshed.get('refreshed_pages', refreshed.get('pages', 0))
                continue
            if vid not in videos or vid in queued or vid in fetched or vid not in deferred | age_skipped:
                raise TransportError('Planner requested unresolved queued, missing or repeated metadata: ' + vid)
            if progress:
                progress({'phase': 'checking candidates selected by rules',
                          'channel_id': videos[vid]['channel_id'],
                          'completed': len(fetched), 'remaining_possible_checks': len(needed), **metrics})
            metadata = self.call('metadata', vid, self.config.get('content_warnings', 'stop'),
                                 checkpoint=cache.checkpoint)
            if metadata.get('id') != vid or metadata.get('channel_id') != videos[vid]['channel_id']:
                raise TransportError('Video owner differs from its channel listing: ' + vid)
            cache.checkpoint([{'type': 'metadata', 'video': metadata}])
            videos[vid].update(metadata)
            videos[vid].pop('publication_age', None)
            if metadata.get('is_live'):
                videos[vid]['kind'] = 'live'
            fetched.add(vid)
            metrics['metadata_fetched'] += 1
            metrics['metadata_skipped'] -= 1
            metrics['metadata_deferred' if vid in deferred else 'metadata_outside_lookback'] -= 1

    def playlist(self):
        self.call('identity', self.config)
        return self.call('playlist', self.config)

    def edit(self, action, expected_before):
        return self.call('edit', self.config, action, expected_before)
