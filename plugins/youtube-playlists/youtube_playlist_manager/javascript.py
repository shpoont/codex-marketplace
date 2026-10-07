"""Use any browser controller that implements the local JavaScript-page bridge.

The bridge carries normalized results and scripts, never credentials. One request
has one identity and deadline; an uncertain execution is never resubmitted.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

from .browser_control import TransportError, cleanup_diagnostics, open_diagnostics, guarded_source, SCRIPT_TIMEOUT_SECONDS


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('x') as handle:
        json.dump(value, handle)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, path)


class JavaScriptPage:
    """An explicitly selected controller, rather than an implicit browser fallback."""
    can_recover = False  # Controllers do not replace an uncertain or borrowed page.

    def __init__(self, directory):
        self.root = Path(directory).expanduser().resolve()
        try:
            ready = json.loads((self.root / 'ready.json').read_text())
            if (ready.get('schema') != 1 or not isinstance(ready.get('controller_id'), str)
                    or not ready['controller_id']):
                raise ValueError('invalid controller identity')
            for name in ('requests', 'responses', 'started', 'abandoned'):
                if not (self.root / name).is_dir():
                    raise ValueError('incomplete controller directory')
        except (OSError, ValueError, TypeError, AttributeError) as error:
            raise TransportError('JavaScript page controller is not ready; start it before this command',
                                 {'code': 'browser_controller_unavailable'}) from error
        self.controller_id = ready['controller_id']
        self.session_id = str(uuid.uuid4())
        self.sequence = 0
        self.page_id = None
        self.page_token = None
        self.url = None
        self.cleanup_result = None
        self.cleanup_attempted = False
        self.open_requested = False

    def _rpc(self, operation, timeout=SCRIPT_TIMEOUT_SECONDS, **payload):
        self.sequence += 1
        request_id = self.session_id + '-' + str(self.sequence).zfill(6)
        deadline = time.time() + timeout + 30
        request = {'schema': 1, 'controller_id': self.controller_id, 'id': request_id,
                   'session_id': self.session_id, 'operation': operation,
                   'deadline': deadline, **payload}
        atomic_json(self.root / 'requests' / (request_id + '.json'), request)
        response = self.root / 'responses' / (request_id + '.json')
        end = time.monotonic() + timeout + 30
        while not response.exists():
            if time.monotonic() >= end:
                atomic_json(self.root / 'abandoned' / (request_id + '.json'), {'id': request_id})
                raise TransportError('JavaScript controller deadline exceeded; verify any uncertain operation before retry',
                                     {'code': 'browser_dispatch_timeout', 'request_id': request_id})
            time.sleep(0.1)
        try:
            result = json.loads(response.read_text())
            if any(result.get(k) != request[k] for k in ('id', 'session_id', 'controller_id', 'schema')):
                raise ValueError('response identity mismatch')
            if result.get('ok') is not True:
                code = result.get('code')
                if code not in {'browser_page_missing', 'browser_controller_error',
                                'browser_request_expired', 'browser_execution_uncertain',
                                'browser_cleanup_failed', 'browser_open_failed'}:
                    code = 'browser_controller_error'
                details = {'code': code, 'request_id': request_id}
                if code == 'browser_cleanup_failed':
                    details.update(cleanup_diagnostics(result.get('details')))
                if code == 'browser_open_failed':
                    details['browser_open'] = open_diagnostics(result.get('details'))
                raise TransportError('Browser cleanup could not be verified' if code == 'browser_cleanup_failed'
                                     else ('Browser page setup failed at ' + details['browser_open'].get('stage', 'unknown'))
                                     if code == 'browser_open_failed'
                                     else 'JavaScript browser controller could not complete the command', details)
            return result['value']
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            raise TransportError('JavaScript controller returned an invalid response; do not replay the command',
                                 {'code': 'browser_response_invalid', 'request_id': request_id}) from error

    def open(self, url):
        if self.open_requested:
            if url != self.url:
                raise TransportError('Cannot switch the bound browser page within a run')
            return self
        self.url, self.page_token = url, str(uuid.uuid4())
        self.open_requested = True  # An uncertain open still requires scoped cleanup.
        result = self._rpc('open', url=url, page_token=self.page_token)
        if not isinstance(result, dict) or not isinstance(result.get('page_id'), (str, int)):
            raise TransportError('JavaScript controller did not return a page identity')
        self.page_id = result['page_id']
        return self

    def evaluate(self, source, script_timeout=SCRIPT_TIMEOUT_SECONDS):
        if self.page_id is None:
            raise TransportError('Bind a browser page before executing JavaScript')
        wrapped = guarded_source(source, self.url, self.page_token)
        raw = self._rpc('evaluate', timeout=script_timeout, source=wrapped,
                        source_sha256=hashlib.sha256(wrapped.encode()).hexdigest(),
                        script_timeout=script_timeout)
        try:
            envelope = json.loads(raw)
            if envelope.get('bound') is not True:
                raise TransportError('Bound browser page was closed, reloaded or navigated',
                                     {'code': 'ytpm_page_missing'})
            return json.loads(envelope['value'])
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise TransportError('JavaScript page returned an invalid result; do not replay the command',
                                 {'code': 'browser_response_invalid'}) from error

    def close(self):
        if self.cleanup_result is None:
            if self.cleanup_attempted:
                raise TransportError('Previous browser cleanup is uncertain; inspect the owned page receipt instead of retrying',
                                     {'code': 'browser_cleanup_failed', 'page_id': self.page_id})
            self.cleanup_attempted = True
            self.cleanup_result = (self._rpc('close') if self.open_requested else
                                   {'classification': 'already_absent'})
        return self._checked_cleanup()

    def verify_cleanup(self):
        """Explicit read-only reconciliation after uncertain cleanup; never resend close."""
        if not self.cleanup_attempted:
            raise TransportError('Request cleanup before verifying its result')
        if (not isinstance(self.cleanup_result, dict) or self.cleanup_result.get('classification') not in {
                'closed', 'already_absent', 'preserved_changed_page'}):
            self.cleanup_result = self._rpc('verify_close')
        return self._checked_cleanup()

    def _checked_cleanup(self):
        if not isinstance(self.cleanup_result, dict) or self.cleanup_result.get('classification') not in {
                'closed', 'already_absent', 'preserved_changed_page'}:
            raise TransportError('Browser resource cleanup needs attention',
                                 {'code': 'browser_cleanup_failed', 'page_id': self.page_id})
        return self.cleanup_result

    def recover_read_only(self):
        raise TransportError('This controller does not support owned-page recovery')
