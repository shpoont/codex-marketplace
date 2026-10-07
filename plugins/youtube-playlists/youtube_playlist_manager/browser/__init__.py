"""Assemble the ordered browser sources into one in-page lexical scope.

sources.json is shared with the browser tests. No browser module loader, network
imports or build step is required; transport state stays private to the closure.
"""
import json
from pathlib import Path


def bridge_source():
    directory = Path(__file__).parent
    parts = json.loads((directory / 'sources.json').read_text())
    body = ''.join((directory / name).read_text() for name in parts)
    return ('/* Authenticated requests stay in the page. Export normalized data only. */\n'
            '(() => {\n' + body + '})()\n')


def initialization_source():
    """Keep arbitrary page exceptions, stacks and native values inside the browser."""
    return ('(()=>{try{return (' + bridge_source() + ''');}catch(error){
        const stages = ['build_detection', 'native_exports', 'transport_resolution',
                        'request_builders', 'request_builder', 'page_context', 'session_context',
                        'client_context', 'session_signing', 'session_authorization',
                        'request_contract', 'endpoint_contract', 'response_contract', 'browse_response',
                        'account_response', 'playlist_response'];
        const details = error?.details?.adapter;
        return JSON.stringify({ready:false,
          code: ['api_incompatible','auth_required','session_changed'].includes(error?.details?.code)
            ? error.details.code : 'api_incompatible', adapter:{
            stage: stages.includes(details?.stage) ? details.stage : 'bridge_initialization',
            build: typeof details?.build === 'string' &&
                /^[A-Za-z]{2,3}_[A-Za-z]{2}\\.[A-Za-z0-9_-]{1,80}$/.test(details.build)
                ? details.build : null,
            error_type: ['Error','TypeError','ReferenceError','SyntaxError','RangeError'].includes(error?.name)
                ? error.name : 'Error'
        }});
    }})()''')
