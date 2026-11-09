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
            '],claimed:Object.prototype.hasOwnProperty.call(window,' + JSON.stringify(MARKER) +
            '),url:location.href,ready:document.readyState});})()';
    }
    function stampCode(state) {
        var startup = state.binding_kind !== 'reuse' && state.binding_pending &&
            state.created_windows.indexOf(state.window_id) !== -1;
        return '(function(){if(location.href!==' + JSON.stringify(state.expected_url) +
            '){if(' + JSON.stringify(startup) + '&&location.href==="about:blank")' +
            'return JSON.stringify({status:"loading",dispatched:false,reason:"initial-navigation"});' +
            'return JSON.stringify({status:"context-mismatch",dispatched:false,reason:"unexpected-page"});}' +
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
    function observe(browser, address, state) {
        var result = parsed(browser, address, probeCode(state));
        if (typeof result.url !== 'string' || typeof result.claimed !== 'boolean' ||
            ['loading', 'interactive', 'complete'].indexOf(result.ready) === -1 ||
            (result.marker !== undefined && typeof result.marker !== 'string')) {
            throw new Error('Malformed probe observation');
        }
        return result;
    }
    function bind(browser, state, address, save) {
        state.window_id = address.window_id;
        state.binding_pending = true;
        state.binding_kind = 'initial';
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
        if (state.creation_pending) return creationUnknown(state);
        var addresses;
        try { addresses = browser.tabs(state.window_id); }
        catch (_) { return reply('unreadable'); }
        if (addresses === null || addresses.length === 0) return reply('missing');
        var matches = [], unreadable = 0, observations = [];
        addresses.forEach(function (address) {
            try {
                var observation = observe(browser, address, state);
                observations.push({tab_index: address.tab_index,
                    page: observation.url === state.expected_url ? 'expected' :
                        observation.url === 'about:blank' ? 'blank' : 'other',
                    ready: observation.ready, marker: observation.marker === state.marker ?
                        'matching' : observation.claimed ? 'other' : 'absent'});
                if (observation.marker === state.marker) matches.push({address: address, observation: observation});
            } catch (_) { unreadable += 1; }
        });
        var details = {window_id: state.window_id, tab_count: addresses.length, observations: observations};
        if (matches.length > 1) return reply('ambiguous', Object.assign(details, {match_count: matches.length}));
        // An unreadable tab could be a second copy. Do not pick a visible winner.
        if (unreadable) return reply('unreadable', Object.assign(details, {unreadable_count: unreadable}));
        if (matches.length === 0) {
            if (state.binding_pending) {
                // Finish initial installation only in the sole tab of the new
                // dedicated window. This is not repair of a lost established marker.
                if (state.binding_kind !== 'reuse' &&
                    state.created_windows.indexOf(state.window_id) !== -1 && addresses.length === 1) {
                    return bind(browser, state, addresses[0], save);
                }
                return reply('unbound', Object.assign(details, {reason: state.binding_kind === 'reuse' ?
                    'explicit-reuse-verification-required' : 'multiple-tabs-before-binding'}));
            }
            return reply('missing', details);
        }
        var match = matches[0];
        if (match.observation.url !== (expectedUrl === undefined ? state.expected_url : expectedUrl)) return reply('context-mismatch', details);
        if (match.observation.ready === 'loading') return reply('loading', details);
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
            operation = {id: nonce(), state: 'dispatch-unknown', context: {
                window_id: state.window_id, generation: state.generation, expected_url: state.expected_url}};
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
    function creationUnknown(state) {
        return reply('creation-outcome-unknown', {reason: state.creation_pending.reason ||
            'creation-not-reconciled', stage: state.creation_pending.stage || 'unknown',
            candidate_window_ids: state.creation_pending.candidate_window_ids || []});
    }
    function creationReason(error) {
        var allowed = ['multiple-new-windows', 'no-new-window', 'window-inspection-failed'];
        if (error && allowed.indexOf(error.creationReason) !== -1) return error.creationReason;
        return error && error.number === -1743 ? 'automation-denied' : 'creation-event-failed';
    }
    function open(browser, state, save) {
        if (state.pending) return reply('pending-outcome');
        if (state.creation_pending) return creationUnknown(state);
        // Persist intent before creation. A lost creation reply is never replayed.
        state.creation_pending = {generation: state.generation, stage: 'intent-recorded'};
        save(state);
        var address;
        try {
            address = browser.createWindow(state.expected_url, function (progress) {
                Object.assign(state.creation_pending, progress);
                save(state);
            });
        } catch (error) {
            state.creation_pending.reason = creationReason(error);
            save(state);
            if (!Number.isInteger(state.creation_pending.window_id)) return creationUnknown(state);
            // The window is identified even if its tab inspection failed.
            state.window_id = state.creation_pending.window_id;
            if (state.created_windows.indexOf(state.window_id) === -1) state.created_windows.push(state.window_id);
            state.last_creation = state.creation_pending;
            state.creation_pending = null;
            state.binding_pending = true;
            state.binding_kind = 'initial';
            save(state);
            return reply('unreadable', {window_id: state.window_id, reason: 'window-inspection-failed'});
        }
        state.window_id = address.window_id;
        if (state.created_windows.indexOf(address.window_id) === -1) state.created_windows.push(address.window_id);
        state.last_creation = state.creation_pending;
        state.creation_pending = null;
        state.binding_pending = true;
        state.binding_kind = 'initial';
        save(state);
        var addresses;
        try { addresses = browser.tabs(state.window_id); }
        catch (_) {
            state.last_creation.reason = 'window-inspection-failed';
            save(state);
            return reply('unreadable', {window_id: state.window_id, reason: 'window-inspection-failed'});
        }
        if (!addresses || addresses.length !== 1) return reply('unbound', {window_id: state.window_id,
            tab_count: addresses ? addresses.length : 0, reason: addresses && addresses.length ?
                'multiple-tabs-before-binding' : 'empty-created-window'});
        return bind(browser, state, address, save);
    }
    function reuse(browser, state, address, expectedUrl, guard, save) {
        validate(state);
        if (state.creation_pending) return creationUnknown(state);
        if (address.window_id !== state.window_id) return reply('outside-task-window');
        var addresses, matching = [], unreadable = false, candidate = null, sameUrl = 0;
        try { addresses = browser.tabs(state.window_id); }
        catch (_) { return reply('unreadable'); }
        if (!addresses || !addresses.length) return reply('missing');
        addresses.forEach(function (a) {
            try {
                var p = observe(browser, a, state);
                if (p.marker === state.marker) matching.push(a);
                if (p.url === expectedUrl) sameUrl += 1;
                if (a.tab_index === address.tab_index) candidate = p;
            } catch (_) { unreadable = true; }
        });
        if (matching.length > 1) return reply('ambiguous', {match_count: matching.length});
        if (unreadable) return reply('unreadable');
        if (!candidate) return reply('missing');
        if (matching.length && matching[0].tab_index !== address.tab_index)
            return reply('target-still-present', {address: matching[0]});
        if (candidate.url !== expectedUrl) return reply('context-mismatch');
        if (candidate.ready === 'loading') return reply('loading');
        if (candidate.claimed && candidate.marker !== state.marker) return reply('already-bound');
        if (!matching.length && sameUrl > 1) return reply('ambiguous', {match_count: sameUrl});
        if (matching.length) {
            var checked = Object.assign({}, state, {expected_url: expectedUrl}), retained;
            try { retained = parsed(browser, address, guardedCode(checked, 'return true;', guard)); }
            catch (_) { return reply('unreadable'); }
            if (retained.status !== 'ok') return retained;
            state.expected_url = expectedUrl;
            state.binding = {tab_index: address.tab_index};
            state.binding_pending = false;
            save(state);
            return reply('reused', {window_id: state.window_id, generation: state.generation});
        }
        var previous = JSON.parse(JSON.stringify(state));
        var continuing = state.binding_pending && state.binding_kind === 'reuse' &&
            state.binding && state.binding.tab_index === address.tab_index && state.expected_url === expectedUrl;
        if (!continuing) state.generation += 1;
        state.marker = state.id + ':' + state.generation;
        state.expected_url = expectedUrl;
        state.binding = {tab_index: address.tab_index};
        state.binding_pending = true;
        state.binding_kind = 'reuse';
        save(state); // Record the new binding token BEFORE its possibly lost reply.
        var code = '(function(){"use strict";const reject=(status)=>JSON.stringify({status,dispatched:false});' +
            'if(location.href!==' + JSON.stringify(expectedUrl) + ')return reject("context-mismatch");' +
            'if(document.readyState==="loading")return reject("loading");' +
            'if(Object.prototype.hasOwnProperty.call(window,' + JSON.stringify(MARKER) + '))return reject("already-bound");' +
            'try{if((function(){\n' + guard + '\n})()!==true)return reject("guard-failed");}' +
            'catch(e){return reject("guard-error");}' +
            'Object.defineProperty(window,' + JSON.stringify(MARKER) + ',{value:' + JSON.stringify(state.marker) +
            ',writable:false,configurable:false});return JSON.stringify({status:"reused",dispatched:false});})()';
        var result;
        try { result = parsed(browser, address, code); }
        catch (_) { return reply('binding-outcome-unknown', {window_id: state.window_id, generation: state.generation}); }
        if (result.status !== 'reused') {
            Object.keys(state).forEach(function (key) { delete state[key]; });
            Object.assign(state, previous);
            save(state);
            return result;
        }
        state.binding_pending = false;
        save(state);
        return reply('reused', {window_id: state.window_id, generation: state.generation});
    }
    function recover(browser, state, save, options) {
        options = options || {};
        validate(state);
        if (state.pending) return reply('pending-outcome');
        if (state.creation_pending) return creationUnknown(state);
        var target = inspect(browser, state, save);
        if (target.status !== 'missing') return target;
        if (options.guard) {
            var addresses, candidates = [], unreadable = false;
            try { addresses = browser.tabs(state.window_id) || []; }
            catch (_) { return reply('unreadable'); }
            addresses.forEach(function (address) {
                try {
                    var p = observe(browser, address, state);
                    if (p.url === state.expected_url) candidates.push(address);
                } catch (_) { unreadable = true; }
            });
            if (unreadable) return reply('unreadable');
            if (candidates.length > 1) return reply('ambiguous', {match_count: candidates.length});
            if (candidates.length === 1) return reuse(browser, state, candidates[0], state.expected_url, options.guard, save);
        }
        if (!options.allowNewWindow) return reply(state.recovery.enabled ? 'reuse-required' : 'recovery-not-authorized',
            {window_id: state.window_id, reason: 'inspect-existing-task-contexts-first'});
        if (!state.recovery.enabled) return reply('recovery-not-authorized');
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
        evaluate: evaluate, transition: transition, open: open, reuse: reuse, recover: recover, resolve: resolve,
        guardedCode: guardedCode, stampCode: stampCode, markerKey: MARKER};
}());

function safariBrowser(app) {
    return {
        tabs: function (windowId) {
            var found = app.windows().filter(function (w) { return w.id() === windowId; });
            if (found.length !== 1) return null;
            var count = found[0].tabs.length, addresses = [];
            for (var index = 0; index < count; index += 1) addresses.push({window_id: windowId, tab_index: index + 1});
            return addresses;
        },
        execute: function (target, code) {
            return app.doJavaScript(code, {in: app.windows.byId(target.window_id).tabs[target.tab_index - 1]});
        },
        createWindow: function (url, progress) {
            var before = app.windows().map(function (w) { return w.id(); });
            progress({stage: 'before-event', before_window_ids: before});
            app.Document({url: url}).make();
            var added = app.windows().filter(function (w) { return before.indexOf(w.id()) === -1; });
            var ids = added.map(function (w) { return w.id(); });
            progress({stage: 'after-event', candidate_window_ids: ids});
            if (added.length !== 1) {
                var error = new Error('Creation identification requires reconciliation');
                error.creationReason = added.length ? 'multiple-new-windows' : 'no-new-window';
                throw error;
            }
            var id = added[0].id();
            progress({stage: 'window-identified', window_id: id});
            // Extra tabs affect binding, not whether this window was identified.
            return {window_id: id, tab_index: 1};
        }
    };
}

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
        if (key === '--recover-readonly' || key === '--allow-new-window') { options[key] = true; continue; }
        if (key.slice(0, 2) !== '--' || i + 1 >= argv.length || options[key] !== undefined) {
            throw new Error('Invalid or duplicate option');
        }
        options[key] = argv[++i];
    }
    var accepted = ['--target-file', '--url', '--recover-readonly', '--recovery-limit',
        '--window-id', '--tab-index', '--expect-url', '--js-file', '--guard-file',
        '--effect', '--operation-id', '--evidence', '--allow-new-window'];
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
    if (command === 'reuse') {
        if (!options['--expect-url'] || !options['--guard-file']) throw new Error('reuse requires exact URL and a context/work-state guard');
        guard = read(options['--guard-file']);
    }
    if (command === 'recover' && options['--guard-file']) guard = read(options['--guard-file']);
    if (command === 'bind' || command === 'reuse') {
        address = {window_id: options['--window-id'] === undefined && state ? state.window_id : Number(options['--window-id']),
            tab_index: Number(options['--tab-index'])};
        if (!Number.isInteger(address.window_id) || address.window_id <= 0 ||
            !Number.isInteger(address.tab_index) || address.tab_index <= 0) throw new Error('Positive window ID and initial tab index required');
    }
    if (['open', 'bind', 'inspect', 'eval', 'transition', 'reuse', 'recover', 'resolve'].indexOf(command) === -1) throw new Error('Unknown command');
    if (options['--allow-new-window'] && command !== 'recover') throw new Error('--allow-new-window applies only to recover');
    if (command === 'resolve') return JSON.stringify(SafariTarget.resolve(state,
        options['--operation-id'] || '', options['--evidence'] || '', save));
    var app = Application('com.apple.Safari');
    if (!app.running()) throw new Error('Safari is not running');
    var browser = safariBrowser(app);
    var result;
    if (command === 'open') result = SafariTarget.open(browser, state, save);
    else if (command === 'bind') result = SafariTarget.bind(browser, state, address, save);
    else if (command === 'inspect') result = SafariTarget.inspect(browser, state, save);
    else if (command === 'eval') result = SafariTarget.evaluate(browser, state, body, guard, options['--effect'], save, nonce);
    else if (command === 'transition') result = SafariTarget.transition(browser, state, options['--expect-url'], guard, save);
    else if (command === 'reuse') result = SafariTarget.reuse(browser, state, address, options['--expect-url'], guard, save);
    else result = SafariTarget.recover(browser, state, save, {guard: guard, allowNewWindow: !!options['--allow-new-window']});
    return JSON.stringify(result);
}

if (typeof module !== 'undefined') { module.exports = SafariTarget; module.exports.safariBrowser = safariBrowser; }
