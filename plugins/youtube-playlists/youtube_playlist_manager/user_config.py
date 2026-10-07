"""Initialize or import external settings without changing a YouTube playlist."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile

import yaml

from .config import ConfigurationError, SCHEMA_PATH, _read_yaml, digest, load
from .planner import policy_config


def config_directory():
    return Path.home() / 'Library/Application Support/info.komarovsky.codex-plugin-youtube-playlist-management/config'


def initialize_config(account_channel_id, playlist_id, playlist_name, channels, *,
                      destination=None, profile='development.yaml', lookback='30d',
                      maximum_count=3, selection='latest_eligible_unwatched'):
    """Create a decided starter profile; identities come from the user's choices.

    Local initialization neither verifies browser bindings nor authorizes apply.
    The ordinary collection checks the actual account, ownership and membership.
    """
    if playlist_id == 'WL':
        raise ConfigurationError('First-time setup uses a separate playlist; Watch Later needs an explicit separate production profile')
    if not channels:
        raise ConfigurationError('Choose at least one source channel before initializing settings')
    destination = Path(destination).expanduser() if destination is not None else config_directory()
    root = destination.resolve().parent
    # Identity syntax is validated before any user file or directory is written.
    settings = {
        'version': 3, 'environment': 'development',
        'account_channel_id': account_channel_id, 'playlist_id': playlist_id,
        'playlist_name': playlist_name, 'execution': {'trigger': 'manual'},
        'transport': {'access': 'in_page_internal_api'},
        'content_warnings': 'stop',
        'storage': {
            'metadata_cache_directory': str(root / 'accounts' / account_channel_id),
            'data_directory': str(root / 'playlists' / account_channel_id / playlist_id),
        },
        'manual_actions': {'unknown_addition_time': 'first_observed', 'dismissed_reappearance': 'readmit'},
        'channel_defaults': {
            'unconfigured_additions': 'disabled', 'lookback': lookback,
            'retention': {'maximum_age': None, 'maximum_count': maximum_count, 'selection': selection},
        },
        'channels': [
            {'id': channel['id'], 'name': channel['name'], 'additions': 'enabled',
             'catch_up': {'start': 'all_history'},
             'placement': {'pinned_rank': None, 'order': 'oldest_first'}}
            for channel in channels
        ],
    }
    if lookback in (None, 'deferred') or maximum_count in (None, 'deferred'):
        raise ConfigurationError('Starter lookback and count must be decided and bounded; edit validated settings later for an unlimited backlog')
    # Reuse import validation, permissions, locked no-overwrite publication and
    # identical-repeat behavior. Temporary inputs never live in the package.
    with tempfile.TemporaryDirectory(prefix='youtube-playlist-settings-') as tmp:
        source = Path(tmp) / profile
        if source.parent != Path(tmp):
            raise ConfigurationError('Profile must be a filename, not a path')
        source.write_text(yaml.safe_dump(settings, allow_unicode=True, sort_keys=False))
        result = import_config(source, destination)
    return {**result, 'status': 'initialized', 'browser_session_checked': False,
            'playlist_changed': False, 'next_action': 'validate, then preview; review before an authorized apply'}


def import_config(source, destination=None):
    source = Path(source).expanduser().resolve()
    destination = Path(destination) if destination is not None else config_directory()
    if not re.fullmatch(r'[a-z][a-z0-9-]*\.yaml', source.name):
        raise ConfigurationError('Target filename must be lower-case letters, digits and hyphens ending in .yaml')
    if source.name == 'channels.yaml':
        raise ConfigurationError('channels.yaml is reserved for shared channel rules')
    package = Path(__file__).resolve().parent.parent
    if destination.is_symlink() or destination.resolve().is_relative_to(package):
        raise ConfigurationError('Personal configuration must be outside the installed package')
    resolved = load(source)
    target = _read_yaml(source)
    files = {}
    if 'channel_rules_file' in target:
        rules_source = source.parent / target['channel_rules_file']
        rules = _read_yaml(rules_source)
        target['channel_rules_file'] = 'channels.yaml'
        files['channels.yaml'] = '# yaml-language-server: $schema=./schemas/channels.schema.json\n' + yaml.safe_dump(rules, allow_unicode=True, sort_keys=False)
    files[source.name] = '# yaml-language-server: $schema=./schemas/settings.schema.json\n' + yaml.safe_dump(target, allow_unicode=True, sort_keys=False)
    for name in ['settings.schema.json', 'channels.schema.json']:
        files['schemas/' + name] = (SCHEMA_PATH.parent / name).read_text()
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = destination / '.import.lock'
    if lock_path.is_symlink():
        raise ConfigurationError('Configuration import refuses a symlink lock')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Validate all existing files before writing anything; never replace a user's edits.
        for name, text in files.items():
            path = destination / name
            if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(destination.resolve()):
                raise ConfigurationError('Configuration import refuses symlinks or paths escaping the destination')
            if path.exists() and path.read_text() != text:
                raise ConfigurationError('Existing configuration differs; review instead of overwriting: ' + str(path))
        # Write shared resources first, target last. An interrupted import can resume.
        ordered = sorted(files, key=lambda name: name == source.name)
        for name in ordered:
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not path.exists():
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
                        temporary = Path(handle.name)
                        handle.write(files[name])
                        handle.flush()
                        os.fsync(handle.fileno())
                    # Publish a complete file without replacing an existing edit.
                    os.link(temporary, path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        imported = load(destination / source.name)
        if imported != resolved:
            raise ConfigurationError('Imported configuration does not match the source; no playlist operation was performed')
    return {'status': 'imported', 'configuration': str(destination / source.name),
            'policy_hash': digest(policy_config(imported)), 'storage': imported['storage'],
            'state_moved': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(import_config(args.source), indent=2))
        return 0
    except (ConfigurationError, OSError) as error:
        print(json.dumps({'status': 'needs_attention', 'error': str(error)}))
        return 2


def initialize_main(argv=None):
    parser = argparse.ArgumentParser(description='Initialize a separate-playlist profile locally; no YouTube writes')
    parser.add_argument('--account-channel-id', required=True)
    parser.add_argument('--playlist-id', required=True)
    parser.add_argument('--playlist-name', required=True)
    parser.add_argument('--channel', action='append', required=True, help='Chosen source channel as UC-channel-ID=Name')
    parser.add_argument('--directory', type=Path, help='External config directory; defaults to the user configuration namespace')
    parser.add_argument('--profile', default='development.yaml')
    parser.add_argument('--lookback', default='30d')
    parser.add_argument('--maximum-count', type=int, default=3)
    parser.add_argument('--selection', choices=['latest_eligible_unwatched', 'oldest_eligible_unwatched', 'keep_current_and_refill'], default='latest_eligible_unwatched')
    args = parser.parse_args(argv)
    try:
        channels = []
        for value in args.channel:
            channel_id, separator, name = value.partition('=')
            if not separator or not name.strip():
                raise ConfigurationError('Each --channel needs an observed channel ID and a non-empty name: UC-channel-ID=Name')
            channels.append({'id': channel_id, 'name': name})
        result = initialize_config(args.account_channel_id, args.playlist_id, args.playlist_name,
                                   channels, destination=args.directory, profile=args.profile,
                                   lookback=args.lookback, maximum_count=args.maximum_count, selection=args.selection)
        print(json.dumps(result, indent=2))
        return 0
    except (ConfigurationError, OSError, ValueError) as error:
        print(json.dumps({'status': 'needs_attention', 'error': str(error)}))
        return 2
