// Deterministic local bridge for any tool that controls a browser page.
// openPage must return the created handle before connecting or binding it.
// Each page supplies id, bind(url, token), evaluate(source, seconds), inspect(),
// close(), and isPresent(). No credentials, policies or YouTube endpoints here.
'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const {gzipSync} = require('node:zlib');
const makeBoundedSender = require('./cdp.js');
const {createCleanup, CleanupError} = require('./cleanup.js');
const sha256 = text => crypto.createHash('sha256').update(text, 'utf8').digest('hex');

class OpenError extends Error {
  constructor(stage) {
    super('Browser page setup failed');
    this.code = 'browser_open_failed';
    this.stage = stage;
  }
}

async function atomic(file, value) {
  const temporary = file + '.tmp';
  await fs.writeFile(temporary, JSON.stringify(value), {flag: 'wx', mode: 0o600});
  await fs.rename(temporary, file);
}

function matches(url, expected) {
  const actual = new URL(url), target = new URL(expected);
  return actual.origin === target.origin && actual.pathname === target.pathname &&
    [...new Set(target.searchParams.keys())].every(key =>
      JSON.stringify(actual.searchParams.getAll(key)) === JSON.stringify(target.searchParams.getAll(key)));
}

function createCDPPage({id, send, close, isPresent, event = async () => {}}) {
  let binding = null;
  const rawSend = async (expression, seconds = 60) => {
    if (Buffer.byteLength(expression, 'utf8') > 262144) throw Error('CDP expression exceeds transfer bound');
    const response = await send('Runtime.evaluate', {expression, returnByValue: true,
      awaitPromise: true, allowUnsafeEvalBlockedByCSP: true}, {timeoutMs: Math.max(1, Math.floor(seconds * 1000))});
    if (response.exceptionDetails || !response.result || !Object.hasOwn(response.result, 'value')) {
      // Keep arbitrary page exceptions, messages and stacks inside the browser.
      throw Error('CDP JavaScript evaluation did not return a value');
    }
    return response.result.value;
  };
  const evaluate = makeBoundedSender({rawSend, owned: () => binding,
    gzip: gzipSync, sha256, randomId: crypto.randomUUID, event});
  return {id, close, isPresent, evaluate,
    async inspect() {
      return rawSend('({url:location.href, token:window.__ytpmPageIdentity || null})');
    },
    async bind(url, token) {
      const state = await rawSend('({url:location.href})');
      if (!matches(state.url, url)) throw Error('Created page is not the requested target');
      const bound = await rawSend(`(()=>{if(Object.hasOwn(window,'__ytpmPageIdentity'))throw Error('Page already owned');
        Object.defineProperty(window,'__ytpmPageIdentity',{value:${JSON.stringify(token)}});return {bound:true};})()`);
      if (bound.bound !== true) throw Error('Page binding failed');
      binding = {url, token};
    }
  };
}

async function createController({directory, openPage, cleanupOptions}) {
  const root = path.resolve(directory), controllerId = crypto.randomUUID();
  await fs.mkdir(root, {mode: 0o700}); // Fresh directory only: never steal another controller.
  for (const name of ['requests', 'responses', 'started', 'abandoned', 'owned']) {
    await fs.mkdir(path.join(root, name), {mode: 0o700});
  }
  const sessions = new Map();
  const released = new Map();
  const cleanup = createCleanup(cleanupOptions);
  let busy = false;
  await atomic(path.join(root, 'ready.json'), {schema: 1, controller_id: controllerId});

  async function save(key, owned) {
    await atomic(path.join(root, 'owned', key + '.json'), {
      page_id: owned.page?.id ?? null, url: owned.url, page_token: owned.token, controller_id: controllerId,
      state: owned.state, bound: owned.bound === true, close_started: owned.closeStarted === true,
      close_ack: owned.closeAck || 'not_sent', cleanup: owned.cleanupResult,
      initial_url: owned.page?.initialURL,
      navigation_started: owned.page?.navigationStarted === true,
      navigation_completed: owned.page?.navigationCompleted === true,
      last_failure: owned.lastFailure, open_failure: owned.openFailure});
  }
  async function release(key, verifyOnly, ensureActive) {
    const owned = sessions.get(key);
    if (!owned) return released.get(key) || {classification: 'already_absent'};
    if (verifyOnly && !owned.cleanupStarted) throw Error('Cleanup has not been requested');
    verifyOnly = verifyOnly || owned.cleanupStarted === true;
    owned.cleanupStarted = true;
    if (!owned.page) {
      const details = {classification: 'verification_error', reason: 'creation_unverified', close_ack: 'not_sent'};
      owned.state = 'unverified';
      owned.lastFailure = details;
      await save(key, owned);
      throw new CleanupError(details);
    }
    const result = await cleanup(owned, {verifyOnly, matches, ensureActive, save: () => save(key, owned)});
    sessions.delete(key); // Changed pages are relinquished too, never still counted as owned.
    released.set(key, result);
    return result;
  }

  async function dispatch(request) {
    const ensureActive = async () => {
      if (request.deadline * 1000 <= Date.now() ||
          await fs.stat(path.join(root, 'abandoned', request.id + '.json')).then(() => true, () => false)) {
        throw Error('Browser request expired or abandoned');
      }
    };
    await ensureActive();
    const key = request.session_id;
    if (request.operation === 'open') {
      if (sessions.has(key) || released.has(key)) throw Error('Repeated open is forbidden');
      const target = new URL(request.url);
      if (target.protocol !== 'https:' || target.username || target.password ||
          typeof request.page_token !== 'string' || !request.page_token) throw Error('Invalid page target');
      const owned = {page: null, url: request.url, token: request.page_token, state: 'creating'};
      sessions.set(key, owned); // An uncertain creation must never look already absent.
      let stage = 'create_page';
      try {
        const page = await openPage(request.url);
        stage = 'register_page';
        if (!page || !['string', 'number'].includes(typeof page.id) ||
            !['bind', 'evaluate', 'inspect', 'close', 'isPresent'].every(k => typeof page[k] === 'function')) {
          throw Error('Invalid created page contract');
        }
        owned.page = page;
        owned.state = 'created';
        await save(key, owned);
        await ensureActive();
        stage = 'bind_page';
        await page.bind(owned.url, owned.token, {ensureActive, checkpoint: () => save(key, owned)});
        owned.bound = true;
        await ensureActive();
        owned.state = 'bound';
        stage = 'register_page';
        await save(key, owned);
        return {page_id: page.id};
      } catch (error) {
        owned.openFailure = {stage: error instanceof OpenError ? error.stage : stage,
          ownership: owned.page ? 'registered' : 'unknown'};
        owned.state = 'open_failed';
        try {await save(key, owned);} catch {} // Retain the first failure, not a receipt failure.
        const failure = new OpenError(owned.openFailure.stage);
        failure.details = owned.openFailure;
        throw failure;
      }
    }
    const owned = sessions.get(key);
    if (request.operation === 'evaluate') {
      if (!owned?.bound || owned.cleanupStarted || sha256(request.source) !== request.source_sha256) {
        throw Error('Unbound, closing page or source mismatch');
      }
      return owned.page.evaluate(request.source, request.script_timeout, ensureActive);
    }
    if (request.operation === 'close' || request.operation === 'verify_close') {
      return release(key, request.operation === 'verify_close', ensureActive);
    }
    throw Error('Unsupported browser operation');
  }

  return {directory: root, controllerId,
    async serveFor(milliseconds = 1000) {
      if (!Number.isInteger(milliseconds) || milliseconds < 1 || milliseconds > 60000) {
        throw Error('Invalid service interval');
      }
      const end = Date.now() + milliseconds;
      let processed = 0, snapshot;
      do {
        snapshot = await this.serveOnce();
        processed += snapshot.processed;
        if (!snapshot.processed && Date.now() < end) {
          await new Promise(resolve => setTimeout(resolve, Math.min(100, end - Date.now())));
        }
      } while (Date.now() < end);
      return {...snapshot, processed};
    },
    async verifyCleanup() {
      if (busy) throw Error('Concurrent dispatch is forbidden');
      busy = true;
      const results = [];
      try {
        for (const [key, owned] of sessions) {
          if (!owned.cleanupStarted) continue;
          try {results.push({session_id: key, ok: true, value: await release(key, true, async () => {})});}
          catch (error) {
            if (!(error instanceof CleanupError)) throw error;
            results.push({session_id: key, ok: false, code: error.code, details: error.details});
          }
        }
        return {results, owned_pages: sessions.size};
      } finally {busy = false;}
    },
    async serveOnce() {
      if (busy) throw Error('Concurrent dispatch is forbidden');
      busy = true;
      let processed = 0;
      try {
        for (const name of (await fs.readdir(path.join(root, 'requests'))).sort()) {
          if (!/^[a-f0-9-]{36}-[0-9]{6}\.json$/.test(name)) continue;
          const resultFile = path.join(root, 'responses', name);
          if (await fs.stat(resultFile).then(() => true, () => false)) continue;
          const request = JSON.parse(await fs.readFile(path.join(root, 'requests', name), 'utf8'));
          if (request.id + '.json' !== name || request.session_id !== name.slice(0, 36) ||
              request.controller_id !== controllerId || request.schema !== 1) throw Error('Request identity mismatch');
          const response = {schema: 1, controller_id: controllerId, id: request.id, session_id: request.session_id};
          const startedFile = path.join(root, 'started', name);
          if (await fs.stat(startedFile).then(() => true, () => false)) {
            Object.assign(response, {ok: false, code: 'browser_execution_uncertain'});
          } else if (!Number.isFinite(request.deadline) || request.deadline * 1000 < Date.now() ||
                     await fs.stat(path.join(root, 'abandoned', name)).then(() => true, () => false)) {
            Object.assign(response, {ok: false, code: 'browser_request_expired'});
          } else {
            await atomic(startedFile, {id: request.id, operation: request.operation});
            try {
              const value = await dispatch(request);
              Object.assign(response, {ok: true, value});
            } catch (error) {
              Object.assign(response, error instanceof CleanupError || error instanceof OpenError
                ? {ok: false, code: error.code, details: error.details}
                : {ok: false, code: request.operation === 'evaluate'
                  ? 'browser_execution_uncertain' : 'browser_controller_error'});
            }
          }
          await atomic(resultFile, response);
          processed++;
        }
        return {processed, owned_pages: sessions.size};
      } finally { busy = false; }
    }
  };
}

module.exports = {createController, createCDPPage, OpenError};
