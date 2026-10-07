#!/usr/bin/env python3
"""Explicit setup and isolated launch; all mutable files stay outside the plugin."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'requirements.txt'
APP_NAME = 'info.komarovsky.codex-plugin-youtube-playlist-management'


def data_root():
    path = Path.home() / 'Library/Application Support' / APP_NAME
    if path.resolve().is_relative_to(ROOT):
        raise RuntimeError('Local storage resolves inside the installed plugin; correct the path before setup')
    return path


def runtime_key():
    base = str(Path(getattr(sys, '_base_executable', sys.executable)).resolve())
    identity = REQUIREMENTS.read_bytes() + (base + sys.implementation.cache_tag).encode()
    return hashlib.sha256(identity).hexdigest()[:20]


def runtime_path():
    directory = data_root() / 'runtimes'
    path = directory / runtime_key()
    if directory.is_symlink() or path.is_symlink():
        raise RuntimeError('Runtime directories must not be symlinks')
    return path


def ready(path):
    try:
        return (path / 'ready.json').read_text() == json.dumps({'schema': 1, 'key': runtime_key()}) + '\n' and (path / 'bin/python').is_file()
    except OSError:
        return False


@contextlib.contextmanager
def setup_lock():
    runtime_path()  # Validate before creating or opening anything.
    directory = data_root() / 'runtimes'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = directory / '.setup.lock'
    if lock.is_symlink():
        raise RuntimeError('Runtime lock must not be a symlink')
    with lock.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another runtime setup is running; let it finish before retrying') from None
        yield


def setup(repair=False):
    path = runtime_path()
    with setup_lock():
        if ready(path):
            return {'status': 'ready', 'runtime': str(path), 'changed': False}
        if path.exists():
            if not repair:
                raise RuntimeError('Incomplete runtime exists. Run setup --repair to rebuild only that incomplete environment')
            if path.is_symlink() or path.resolve().parent != (data_root() / 'runtimes').resolve():
                raise RuntimeError('Refusing to repair a runtime with an unexpected path')
            shutil.rmtree(path)
        try:
            venv.EnvBuilder(with_pip=True).create(path)
            python = str(path / 'bin/python')
            subprocess.run([python, '-I', '-m', 'pip', 'install', '--disable-pip-version-check',
                            '--only-binary=:all:', '-r', str(REQUIREMENTS)], check=True, stdout=sys.stderr)
            subprocess.run([python, '-I', '-m', 'pip', 'check'], check=True, stdout=sys.stderr)
            (path / 'ready.json').write_text(json.dumps({'schema': 1, 'key': runtime_key()}) + '\n')
        except BaseException:
            # Only the new environment owned by this setup attempt is removed.
            if path.exists():
                shutil.rmtree(path)
            raise
    return {'status': 'ready', 'runtime': str(path), 'changed': True}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if sys.version_info < (3, 11):
        raise RuntimeError('Python 3.11 or newer is required. Invoke this script with an existing supported Python interpreter')
    if argv[:1] == ['--runtime']:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT))
        if argv[1:2] == ['import-config']:
            from youtube_playlist_manager.user_config import main as import_main
            return import_main(argv[2:])
        if argv[1:2] == ['init-config']:
            from youtube_playlist_manager.user_config import initialize_main
            return initialize_main(argv[2:])
        from youtube_playlist_manager.cli import main as cli_main
        from youtube_playlist_manager import reporting
        reporting.COMMAND_PREFIX = (sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--runtime')
        sys.argv = [str(Path(__file__)), *argv[1:]]
        return cli_main()
    if argv[:1] == ['setup']:
        if argv not in (['setup'], ['setup', '--repair']):
            raise RuntimeError('Use setup or setup --repair')
        print(json.dumps(setup('--repair' in argv), indent=2))
        return 0
    if argv[:1] == ['doctor']:
        if len(argv) != 1:
            raise RuntimeError('doctor takes no arguments; use --config PATH validate to validate a target')
        path = runtime_path()
        configs = sorted(str(p) for p in (data_root() / 'config').glob('*.yaml') if p.name != 'channels.yaml')
        ok = ready(path)
        if ok:
            subprocess.run([str(path / 'bin/python'), '-I', '-m', 'pip', 'check'], check=True, stdout=sys.stderr)
        status = 'setup_needed' if not ok else 'configuration_needed' if not configs else 'local_setup_ready'
        print(json.dumps({'status': status, 'python': platform.python_version(), 'runtime': str(path),
                          'configurations': configs, 'safari_available': Path('/Applications/Safari.app').exists(),
                          'javascript_bridge_supported': True,
                          'browser_session_checked': False}, indent=2))
        return 0 if status == 'local_setup_ready' else 2
    path = runtime_path()
    if not ready(path):
        raise RuntimeError('Runtime is not ready. Run this launcher with setup first; normal commands never install dependencies')
    if not argv:
        argv = ['--help']
    return subprocess.run([str(path / 'bin/python'), '-I', '-B', str(Path(__file__).resolve()), '--runtime', *argv]).returncode


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({'status': 'needs_attention', 'error': str(error)}), file=sys.stderr)
        raise SystemExit(2)
