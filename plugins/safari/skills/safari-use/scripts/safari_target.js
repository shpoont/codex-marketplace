/* Native JXA entrypoint; the same controller is exported for offline tests.
 * The marker is page-local evidence, NOT a native tab ID or security boundary.
 */
var SafariTarget = (function () {
    'use strict';
    var MARKER = '__codexSafariTaskBinding';
    function reply(status, extra) {
        return Object.assign({status: status, dispatched: false}, extra || {});
    }
    function validate(state) {
        if (!state || state.schema !== 1 || typeof state.id !== 'string' ||
            typeof state.marker !== 'string' || typeof state.expected_url !== 'string' ||
            !Number.isInteger(state.generation) || !Array.isArray(state.created_windows)) {
            throw new Error('Invalid target handle');
        }
        if (!state.recovery || !Number.isInteger(state.recovery.attempts) ||
            !Number.isInteger(state.recovery.limit) || state.recovery.limit < 0 ||
            state.recovery.limit > 3 || state.recovery.attempts < 0) {
            throw new Error('Invalid recovery budget');
        }
        return state;
    }
    function newState(id, url, recovery, limit) {
        return {schema: 1, id: id, window_id: null, generation: 0, marker: id + ':0',
            expected_url: url, binding: null, binding_pending: false, created_windows: [], pending: null,
            creation_pending: null,
            recovery: {enabled: !!recovery, url: url, limit: limit, attempts: 0}};
    }
    function probeCode(state) {
        return '(function(){return JSON.stringify({marker:window[' + JSON.stringify(MARKER) +
            '],url:location.href,ready:document.readyState});})()';
    }
    function stampCode(state) {
        return '(function(){if(location.href!==' + JSON.stringify(state.expected_url) +
            ')return JSON.stringify({status:"context-mismatch",dispatched:false});' +
            'if(document.readyState==="loading")return JSON.stringify({status:"loading",dispatched:false});' +
            'if(Object.prototype.hasOwnProperty.call(window,' + JSON.stringify(MARKER) +
            '))return JSON.stringify({status:"already-bound",dispatched:false});' +
            'Object.defineProperty(window,' + JSON.stringify(MARKER) + ',{value:' +
            JSON.stringify(state.marker) + ',writable:false,configurable:false});' +
            'return JSON.stringify({status:"bound",dispatched:false});})()';
    }
    function guardedCode(state, body, guard) {
        return '(function(){"use strict";' +
            'const reject=(status)=>JSON.stringify({status,dispatched:false});' +
            'if(window[' + JSON.stringify(MARKER) + ']!==' + JSON.stringify(state.marker) +
            ')return reject("binding-mismatch");' +
            'if(location.href!==' + JSON.stringify(state.expected_url) +
            ')return reject("context-mismatch");' +
            'try{if((function(){\n' + guard + '\n})()!==true)return reject("guard-failed");}' +
            'catch(e){return reject("guard-error");}' +
            'try{const value=(function(){\n' + body + '\n})();' +
            'if(value&&typeof value.then==="function")return JSON.stringify({status:"async-result-unsupported",dispatched:true});' +
            'return JSON.stringify({status:"ok",dispatched:true,value:value===undefined?null:value});}' +
            'catch(e){return JSON.stringify({status:"operation-error",dispatched:true});}})()';
    }
    function parsed(browser, address, code) {
        var result = JSON.parse(browser.execute(address, code));
        if (!result || typeof result !== 'object' || Array.isArray(result)) {
            throw new Error('Unreadable page response');
        }
        return result;
    }
    function bind(browser, state, address, save) {
        state.window_id = address.window_id;
        state.binding_pending = true;
        save(state); // Keep the marker token even if its installation reply is lost.
        var result;
        try { result = parsed(browser, address, stampCode(state)); }
        catch (_) { return reply('unreadable'); }
        if (result.status !== 'bound') return result;
        state.binding_pending = false;
        state.binding = {tab_index: address.tab_index};
        save(state);
        return reply('bound', {window_id: state.window_id, generation: state.generation});
    }
    function inspect(browser, state, save, expectedUrl) {
        validate(state);
        if (state.creation_pending) return reply('creation-outcome-unknown');
        var addresses;
        try { addresses = browser.tabs(state.window_id); }
        catch (_) { return reply('unreadable'); }
        if (addresses === null || addresses.length === 0) return reply('missing');
        var matches = [], unreadable = 0;
        addresses.forEach(function (address) {
            try {
                var observation = parsed(browser, address, probeCode(state));
                if (typeof observation.url !== 'string' ||
                    ['loading', 'interactive', 'complete'].indexOf(observation.ready) === -1 ||
                    (observation.marker !== undefined && typeof observation.marker !== 'string')) {
                    throw new Error('Malformed probe observation');
                }
                if (observation.marker === state.marker) matches.push({address: address, observation: observation});
            } catch (_) { unreadable += 1; }
        });
        if (matches.length > 1) return reply('ambiguous', {match_count: matches.length});
        // An unreadable tab could be a second copy. Do not pick a visible winner.
        if (unreadable) return reply('unreadable');
        if (matches.length === 0) {
            if (state.binding_pending) {
                // Finish initial installation only in the sole tab of the new
                // dedicated window. This is not repair of a lost established marker.
                if (state.created_windows.indexOf(state.window_id) !== -1 && addresses.length === 1) {
                    return bind(browser, state, addresses[0], save);
                }
                return reply('unbound');
            }
            return reply('missing');
        }
        var match = matches[0];
        if (match.observation.url !== (expectedUrl === undefined ? state.expected_url : expectedUrl)) return reply('context-mismatch');
        if (match.observation.ready === 'loading') return reply('loading');
        state.binding = {tab_index: match.address.tab_index};
        state.binding_pending = false;
        save(state);
        return reply('ready', {address: match.address, generation: state.generation});
    }
    function evaluate(browser, state, body, guard, effect, save, nonce) {
        if (effect !== 'read' && effect !== 'write') throw new Error('Explicit read/write effect required');
        if (effect === 'write' && state.pending) return reply('pending-outcome');
        var target = inspect(browser, state, save);
        if (target.status !== 'ready') return target;
        var operation = null;
        if (effect === 'write') {
            operation = {id: nonce(), state: 'dispatch-unknown'};
            state.pending = operation;
            save(state); // Before any possibly mutating AppleEvent.
        }
        var result;
        try { result = parsed(browser, target.address, guardedCode(state, body, guard)); }
        catch (_) {
            return reply(effect === 'write' ? 'outcome-unknown' : 'unreadable',
                {operation_id: operation ? operation.id : null});
        }
        if (effect === 'write') {
            if (result.dispatched === false) state.pending = null;
            else state.pending.state = 'needs-effect-verification';
            save(state);
            result.operation_id = operation.id;
        }
        return result;
    }
    function transition(browser, state, expectedUrl, guard, save) {
        // An explicit, independently verified expected navigation, not a retry
        // that silently relaxes a failed operation guard or changes ownership.
        if (typeof expectedUrl !== 'string' || !expectedUrl || state.binding_pending) return reply('unbound');
        var located = inspect(browser, state, function () {}, expectedUrl);
        if (located.status !== 'ready') return located;
        var checkState = Object.assign({}, state, {expected_url: expectedUrl}), result;
        try { result = parsed(browser, located.address, guardedCode(checkState, 'return true;', guard)); }
        catch (_) { return reply('unreadable'); }
        if (result.status !== 'ok') return result;
        state.expected_url = expectedUrl;
        save(state); // Retain pending effects, recovery budget and original recipe.
        return reply('transitioned', {generation: state.generation});
    }
    function open(browser, state, save) {
        // Persist intent before creation. A lost creation reply is never replayed.
        state.creation_pending = {generation: state.generation};
        save(state);
        var address;
        try { address = browser.createWindow(state.expected_url); }
        catch (_) { return reply('creation-outcome-unknown'); }
        state.window_id = address.window_id;
        state.created_windows.push(address.window_id);
        state.creation_pending = null;
        save(state);
        return bind(browser, state, address, save);
    }
    function recover(browser, state, save) {
        validate(state);
        if (state.pending) return reply('pending-outcome');
        if (state.creation_pending) return reply('creation-outcome-unknown');
        if (!state.recovery.enabled) return reply('recovery-not-authorized');
        var target = inspect(browser, state, save);
        if (target.status !== 'missing') return target;
        if (state.recovery.attempts >= state.recovery.limit) return reply('recovery-exhausted');
        state.recovery.attempts += 1;
        state.generation += 1;
        state.marker = state.id + ':' + state.generation;
        state.expected_url = state.recovery.url;
        state.binding = null;
        var result = open(browser, state, save);
        if (result.status === 'bound') result.status = 'replaced';
        return result;
    }
    function resolve(state, operationId, evidence, save) {
        validate(state);
        if (!state.pending || state.pending.id !== operationId || !evidence.trim()) {
            return reply('resolution-mismatch');
        }
        state.last_resolution = {operation_id: operationId, evidence: evidence};
        state.pending = null;
        save(state);
        return reply('resolved');
    }
    return {newState: newState, validate: validate, bind: bind, inspect: inspect,
        evaluate: evaluate, transition: transition, open: open, recover: recover, resolve: resolve,
        guardedCode: guardedCode, stampCode: stampCode, markerKey: MARKER};
}());

function run(argv) {
    'use strict';
    ObjC.import('Foundation');
    function read(path) {
        var data = $.NSString.stringWithContentsOfFileEncodingError(path, $.NSUTF8StringEncoding, null);
        if (data.isNil()) throw new Error('Cannot read input file');
        return ObjC.unwrap(data);
    }
    function nonce() { return ObjC.unwrap($.NSUUID.UUID.UUIDString); }
    var options = {}, command = argv[0];
    for (var i = 1; i < argv.length; i += 1) {
        var key = argv[i];
        if (key === '--recover-readonly') { options[key] = true; continue; }
        if (key.slice(0, 2) !== '--' || i + 1 >= argv.length || options[key] !== undefined) {
            throw new Error('Invalid or duplicate option');
        }
        options[key] = argv[++i];
    }
    var accepted = ['--target-file', '--url', '--recover-readonly', '--recovery-limit',
        '--window-id', '--tab-index', '--expect-url', '--js-file', '--guard-file',
        '--effect', '--operation-id', '--evidence'];
    Object.keys(options).forEach(function (key) {
        if (accepted.indexOf(key) === -1) throw new Error('Unknown option');
    });
    var path = options['--target-file'];
    if (!path) throw new Error('Missing target file');
    function save(state) {
        var success = $(JSON.stringify(state, null, 2) + '\n')
            .writeToFileAtomicallyEncodingError(path, true, $.NSUTF8StringEncoding, null);
        if (!success) throw new Error('Cannot persist target handle');
    }
    var exists = $.NSFileManager.defaultManager.fileExistsAtPath(path);
    var initializing = command === 'open' || command === 'bind';
    if (initializing === !!exists) throw new Error(initializing ? 'Target file already exists' : 'Target file missing');
    var state, limit;
    if (initializing) {
        var url = options[command === 'open' ? '--url' : '--expect-url'];
        if (!url || !/^(https?:\/\/|file:\/\/|about:blank$)/.test(url)) throw new Error('Explicit page URL required');
        limit = options['--recovery-limit'] === undefined ? 1 : Number(options['--recovery-limit']);
        if (!Number.isInteger(limit) || limit < 0 || limit > 3) throw new Error('Recovery limit must be 0..3');
        if (command === 'bind' && options['--recover-readonly']) throw new Error('Recovery requires a dedicated reader opened by this helper');
        state = SafariTarget.newState(nonce(), url, options['--recover-readonly'], limit);
    } else state = SafariTarget.validate(JSON.parse(read(path)));
    // Read payloads and validate arguments BEFORE touching Safari.
    var body, guard, address;
    if (command === 'eval') {
        if (!options['--js-file'] || !options['--guard-file'] || ['read', 'write'].indexOf(options['--effect']) === -1) {
            throw new Error('eval requires payload, guard and explicit effect');
        }
        body = read(options['--js-file']); guard = read(options['--guard-file']);
    }
    if (command === 'transition') {
        if (!options['--expect-url'] || !options['--guard-file']) throw new Error('transition requires expected URL and guard');
        guard = read(options['--guard-file']);
    }
    if (command === 'bind') {
        address = {window_id: Number(options['--window-id']), tab_index: Number(options['--tab-index'])};
        if (!Number.isInteger(address.window_id) || address.window_id <= 0 ||
            !Number.isInteger(address.tab_index) || address.tab_index <= 0) throw new Error('Positive window ID and initial tab index required');
    }
    if (['open', 'bind', 'inspect', 'eval', 'transition', 'recover', 'resolve'].indexOf(command) === -1) throw new Error('Unknown command');
    if (command === 'resolve') return JSON.stringify(SafariTarget.resolve(state,
        options['--operation-id'] || '', options['--evidence'] || '', save));
    var app = Application('com.apple.Safari');
    if (!app.running()) throw new Error('Safari is not running');
    var browser = {
        tabs: function (windowId) {
            var windows = app.windows();
            var found = windows.filter(function (w) { return w.id() === windowId; });
            if (found.length !== 1) return null;
            var count = found[0].tabs.length, addresses = [];
            // Safari can retain a zero-tab object after close. Its element-list
            // get may fail although the count is zero; normalize without probing.
            for (var index = 0; index < count; index += 1) {
                addresses.push({window_id: windowId, tab_index: index + 1});
            }
            return addresses;
        },
        execute: function (target, code) {
            return app.doJavaScript(code, {in: app.windows.byId(target.window_id).tabs[target.tab_index - 1]});
        },
        createWindow: function (url) {
            var before = app.windows().map(function (w) { return w.id(); });
            app.Document({url: url}).make();
            var added = app.windows().filter(function (w) { return before.indexOf(w.id()) === -1; });
            if (added.length !== 1 || added[0].tabs.length !== 1) throw new Error('Ambiguous new window');
            return {window_id: added[0].id(), tab_index: 1};
        }
    };
    var result;
    if (command === 'open') result = SafariTarget.open(browser, state, save);
    else if (command === 'bind') result = SafariTarget.bind(browser, state, address, save);
    else if (command === 'inspect') result = SafariTarget.inspect(browser, state, save);
    else if (command === 'eval') result = SafariTarget.evaluate(browser, state, body, guard, options['--effect'], save, nonce);
    else if (command === 'transition') result = SafariTarget.transition(browser, state, options['--expect-url'], guard, save);
    else result = SafariTarget.recover(browser, state, save);
    return JSON.stringify(result);
}

if (typeof module !== 'undefined') module.exports = SafariTarget;
