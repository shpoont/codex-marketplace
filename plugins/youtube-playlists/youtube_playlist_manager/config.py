"""Strict readable configuration. Deferred values are never defaults."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from functools import cache
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, validators
from jsonschema.exceptions import SchemaError, best_match


SCHEMA_PATH = Path(__file__).resolve().parent / 'schemas/settings.schema.json'
# YAML preserves 1.0 as a float; downstream count limits require actual ints.
ConfigValidator = validators.extend(Draft7Validator, type_checker=Draft7Validator.TYPE_CHECKER.redefine(
    'integer', lambda checker, value: type(value) is int))


class ConfigurationError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ConfigurationError('YAML keys must be unique strings')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def seconds(value):
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]*[smhd]', value):
        raise ConfigurationError('Duration must be a positive integer plus s, m, h or d')
    return int(value[:-1]) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[value[-1]]


def timestamp(value):
    if not isinstance(value, str):
        raise ConfigurationError('Publication bounds must be quoted ISO dates or timestamps')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if len(value) == 10:
        from datetime import timezone
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        raise ConfigurationError('Timestamp requires a timezone')
    return parsed


@cache
def schema_validator(section=None):
    try:
        schema = json.loads(SCHEMA_PATH.read_text())
        ConfigValidator.check_schema(schema)
    except (OSError, ValueError, SchemaError) as error:
        raise ConfigurationError(f'Cannot load configuration schema {SCHEMA_PATH}: {error}') from error
    if section is not None:
        schema = {'$ref': f'#/definitions/{section}',
                  'definitions': schema['definitions'], 'properties': schema['properties']}
    return ConfigValidator(schema)


def _field_path(parts):
    result = ''
    for part in parts:
        result += f'[{part}]' if isinstance(part, int) else ('.' if result else '') + part
    return result or 'configuration'


def channel_policy(channel, defaults):
    return {
        'id': channel['id'], 'additions': channel['additions'],
        'catch_up': copy.deepcopy(channel['catch_up']),
        'placement': copy.deepcopy(channel['placement']),
        'lookback': channel.get('lookback', defaults['lookback']),
        'retention': {**defaults['retention'], **channel.get('retention', {})},
    }


def substantive(policy):
    return {k: v for k, v in policy.items() if k != 'additions'}


def _validate_structure(config, section=None):
    if isinstance(config, dict) and config.get('version') in [1, 2]:
        raise ConfigurationError('Configuration version 3 is required; remove admission_budget and set version: 3. Keep the same target and data directory.')
    error = best_match(schema_validator(section).iter_errors(config))
    if error is not None:
        message = error.message
        if list(error.absolute_path) == ['version'] and error.validator == 'const':
            message = f'Configuration version {error.validator_value} is required'
        raise ConfigurationError(f'{_field_path(error.absolute_path)}: {message}')


def validate(config, root: Path):
    """Validate resolved settings. Use load() for YAML containing a file reference."""
    _validate_structure(config)
    if 'channel_rules_file' in config:
        raise ConfigurationError('channel_rules_file: use load() to resolve the shared rules before validation')
    # Structural rules live in the schema. These checks need filesystem,
    # timezone/calendar knowledge, or comparisons across channel entries.
    try:
        directory = Path(config['storage']['data_directory']).expanduser()
        path = directory.resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise ConfigurationError(f'storage.data_directory: invalid path: {error}') from error
    if not directory.is_absolute():
        raise ConfigurationError('storage.data_directory: must be absolute or start with ~')
    if path.is_relative_to(root.resolve()):
        raise ConfigurationError('storage.data_directory: operational data must be outside the repository')
    if 'metadata_cache_directory' in config['storage']:
        directory = Path(config['storage']['metadata_cache_directory']).expanduser()
        if not directory.is_absolute() or directory.resolve().is_relative_to(root.resolve()):
            raise ConfigurationError('storage.metadata_cache_directory: must be an absolute path outside the repository')
    ids, ranks = set(), set()
    for index, channel in enumerate(config['channels']):
        prefix = f'channels[{index}]'
        if channel['id'] in ids:
            raise ConfigurationError(f'{prefix}.id: duplicate channel ID')
        ids.add(channel['id'])
        rank = channel['placement']['pinned_rank']
        if rank is not None:
            if rank in ranks:
                raise ConfigurationError(f'{prefix}.placement.pinned_rank: duplicate pinned rank')
            ranks.add(rank)
        start = channel['catch_up']['start']
        if isinstance(start, dict) and 'published_after' in start:
            try:
                timestamp(start['published_after'])
            except ValueError as error:
                raise ConfigurationError(f'{prefix}.catch_up.start.published_after: {error}') from error
    return config


def _read_yaml(path):
    try:
        return yaml.load(path.read_text(), Loader=UniqueLoader)
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise ConfigurationError(f'{path}: cannot read valid YAML: {error}') from error


def load(path):
    """Resolve exactly one channel-rule source; file paths never enter runtime policy."""
    path = Path(path).expanduser().resolve()
    config = _read_yaml(path)
    _validate_structure(config)
    if 'channel_rules_file' in config:
        reference = Path(config['channel_rules_file'])
        if reference.is_absolute() or str(reference).startswith('~'):
            raise ConfigurationError('channel_rules_file: must be a local path relative to the target YAML')
        rules_path = path.parent / reference
        rules = _read_yaml(rules_path)
        try:
            _validate_structure(rules, 'channelRules')
        except ConfigurationError as error:
            raise ConfigurationError(f'{rules_path}: {error}') from error
        config = {k: v for k, v in config.items() if k != 'channel_rules_file'}
        config.update(rules)
    root = Path(__file__).resolve().parent.parent
    # Development installs protect the whole source checkout; distributed
    # installs protect the package without depending on that source layout.
    if root.name == 'plugin' and (root.parent / 'plugin-source.json').is_file():
        root = root.parent
    return validate(config, root)


def unresolved(config):
    result = []
    def visit(x, prefix):
        if isinstance(x, dict):
            for k, v in x.items():
                visit(v, prefix + '.' + k if prefix else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                visit(v, f'{prefix}[{i}]')
        elif x == 'deferred':
            result.append(prefix)
    for channel in config['channels']:
        visit(channel_policy(channel, config['channel_defaults']), f'channels.{channel["id"]}')
    return result
