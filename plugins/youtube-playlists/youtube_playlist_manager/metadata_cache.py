"""Account-bound metadata and catalog checkpoints; never a membership baseline."""
from __future__ import annotations

import fcntl
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import seconds, timestamp


def collection_settings(config):
    return {**{'metadata_max_age': '30d', 'recent_metadata_max_age': '1d',
               'restricted_metadata_max_age': '1d',
               'recent_video_age': '7d', 'player_request_interval': '5s',
               'rate_limit_cooldown': '1h'}, **config.get('collection', {})}


class CacheError(RuntimeError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


class MetadataCache:
    def __init__(self, config):
        self.account = config['account_channel_id']
        self.settings = collection_settings(config)
        self.root = Path(config['storage'].get('metadata_cache_directory',
                         str(Path(config['storage']['data_directory']).expanduser() / 'metadata-cache'))).expanduser()
        self.db = self.lock = None

    def __enter__(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = (self.root / 'cache.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.db = sqlite3.connect(self.root / 'metadata.sqlite3')
            (self.root / 'metadata.sqlite3').chmod(0o600)
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''CREATE TABLE IF NOT EXISTS metadata (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS catalogs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS known_videos (id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS control (key TEXT PRIMARY KEY, payload TEXT NOT NULL);''')
            owner = self.get('account')
            if owner is not None and owner != self.account:
                raise CacheError('Metadata cache belongs to another YouTube account')
            self.put('account', self.account)
            # Discovery history survives legitimate catalog deletions and reappearances.
            if not self.get('known_videos_initialized'):
                self.db.executemany('INSERT OR IGNORE INTO known_videos VALUES (?)',
                    ((v['id'],) for (raw,) in self.db.execute('SELECT payload FROM catalogs')
                     for v in json.loads(raw)['videos']))
                self.db.execute('INSERT OR IGNORE INTO known_videos SELECT id FROM metadata')
                self.put('known_videos_initialized', True)
            self.db.commit()
            return self
        except BlockingIOError as error:
            self.__exit__(None, None, None)
            raise CacheError('Another collection owns this account metadata cache') from error
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.db:
            self.db.close()
        if self.lock:
            self.lock.close()

    def get(self, key):
        row = self.db.execute('SELECT payload FROM control WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO control VALUES (?,?)', (key, json.dumps(value)))

    def payload(self, now=None):
        now = now or datetime.now(timezone.utc)
        until = self.get('retry_at')
        if until and timestamp(until) > now:
            raise CacheError('YouTube requests are paused until ' + until + '; cached work is saved',
                             {'code': 'rate_limited', 'retry_at': until})
        return {'account_channel_id': self.account,
                'known_video_ids': [r[0] for r in self.db.execute('SELECT id FROM known_videos ORDER BY id')],
                'videos': [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM metadata')],
                'catalogs': [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM catalogs')],
                'last_player_request_at': self.get('last_player_request_at')}

    def checkpoint(self, events):
        for event in events:
            if event['type'] == 'catalog':
                catalog = event['catalog']
                if (not catalog.get('complete') or not catalog.get('id') or catalog.get('scope')
                        or not isinstance(catalog.get('page_index'), list)):
                    raise CacheError('Refusing incomplete catalog checkpoint')
                timestamp(catalog['scanned_at'])
                timestamp(catalog['full_scanned_at'])
                prior = self.db.execute('SELECT payload FROM catalogs WHERE id=?', (catalog['id'],)).fetchone()
                ids = sorted(v['id'] for v in catalog['videos'])
                if len(ids) != len(set(ids)):
                    raise CacheError('Refusing duplicate catalog IDs')
                if prior:
                    old_ids = sorted(v['id'] for v in json.loads(prior[0])['videos'])
                    if set(old_ids) - set(ids):
                        # Matching browse omissions do not prove deletion.
                        raise CacheError('Refusing unconfirmed catalog loss',
                                         {'code': 'catalog_inconsistent', 'channel_id': catalog['id']})
                self.db.execute('INSERT OR REPLACE INTO catalogs VALUES (?,?)',
                                (catalog['id'], json.dumps(catalog)))
                self.db.executemany('INSERT OR IGNORE INTO known_videos VALUES (?)', ((vid,) for vid in ids))
            elif event['type'] == 'player_request':
                self.put('last_player_request_at', event['at'])
            elif event['type'] == 'metadata':
                v = event['video']
                # Cache verified success or a recognized access restriction only;
                # never ambiguous failures, watch progress or membership.
                availability = v.get('availability', {})
                restricted = (v.get('playable') is False and availability.get('status') == 'UNPLAYABLE'
                              and availability.get('restriction') == 'members_only')
                positive = (v.get('playable') is True and availability.get('status') in ['OK', 'CONTENT_CHECK_REQUIRED'])
                if (not (positive or restricted) or not v.get('channel_id') or
                        not v.get('publication') or not v.get('duration') or
                        not v.get('id')):
                    raise CacheError('Refusing unverified metadata checkpoint')
                timestamp(v['metadata_checked_at'])
                v = {k: value for k, value in v.items() if k in {
                    'id', 'channel_id', 'publication', 'duration', 'playable', 'availability',
                    'metadata_checked_at', 'playlist_duration', 'content_warning', 'unlisted_normal', 'is_live'}}
                self.db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', (v['id'], json.dumps(v)))
                self.db.execute('INSERT OR IGNORE INTO known_videos VALUES (?)', (v['id'],))
            else:
                raise CacheError('Unknown metadata checkpoint')
        self.db.commit()

    def failure(self, details, now=None):
        now = now or datetime.now(timezone.utc)
        safe = {k: details[k] for k in ('code', 'channel_id', 'reason', 'selected_tab', 'previous_count',
                'first_count', 'second_count', 'missing_sample', 'retry_at', 'http_status') if k in details}
        self.put('last_failure', {'at': now.isoformat(), **safe})
        if details.get('code') == 'catalog_inconsistent':
            self.put('last_catalog_failure', {'at': now.isoformat(), **safe})
        if details.get('code') == 'rate_limited':
            delay = max(seconds(self.settings['rate_limit_cooldown']), details.get('retry_after_seconds') or 0)
            until = (now + timedelta(seconds=delay)).isoformat()
            existing = self.get('retry_at')
            self.put('retry_at', max(existing, until) if existing else until)
            details['retry_at'] = self.get('retry_at')
        self.db.commit()
