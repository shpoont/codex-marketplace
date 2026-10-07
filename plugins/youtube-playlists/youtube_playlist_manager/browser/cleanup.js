// Owned-resource cleanup only. No browser-specific APIs or page/playlist writes.
'use strict';
const {performance} = require('node:perf_hooks');

class CleanupError extends Error {
  constructor(details) {
    super('Browser page cleanup could not be verified');
    this.code = 'browser_cleanup_failed';
    this.details = details;
  }
}

function createCleanup({timeoutMs = 5000, pollMs = 100, now = () => performance.now(),
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms))} = {}) {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 30000 ||
      !Number.isFinite(pollMs) || pollMs <= 0) throw Error('Invalid cleanup bounds');
  return async function cleanup(owned, {verifyOnly, matches, ensureActive, save}) {
    const started = now(), end = started + timeoutMs;
    let checks = 0, reason = 'verification_error', lastPresent;
    const details = classification => ({classification, page_id: owned.page.id,
      close_ack: owned.closeAck || 'not_sent', presence_checks: checks,
      elapsed_ms: Math.max(0, Math.round(now() - started))});
    // Bound every browser call, including an unresponsive presence/close callback.
    async function bounded(call) {
      await ensureActive().catch(() => {reason = 'request_inactive'; throw Error(reason);});
      const left = end - now();
      if (left <= 0) {reason = 'deadline_exceeded'; throw Error(reason);}
      let timer;
      try {
        const value = await Promise.race([Promise.resolve().then(call),
          new Promise((_, reject) => {timer = setTimeout(() => {
            reason = 'deadline_exceeded'; reject(Error(reason));
          }, left);})]);
        await ensureActive().catch(() => {reason = 'request_inactive'; throw Error(reason);});
        return value;
      } finally {clearTimeout(timer);}
    }
    async function present() {
      reason = 'presence_error';
      const value = await bounded(() => owned.page.isPresent());
      checks++;
      if (value !== true && value !== false) {reason = 'presence_unknown'; throw Error(reason);}
      lastPresent = value;
      return value;
    }
    async function finish(classification) {
      const result = details(classification);
      owned.state = classification === 'preserved_changed_page' ? 'preserved' : 'released';
      owned.cleanupResult = result;
      reason = 'receipt_error';
      await save();
      return result;
    }
    try {
      if (!await present()) return await finish(owned.closeStarted ? 'closed' : 'already_absent');
      reason = 'inspection_error';
      const observed = await bounded(() => owned.page.inspect());
      if (!observed || typeof observed.url !== 'string' ||
          (observed.token !== null && typeof observed.token !== 'string')) {
        throw Error('Invalid page inspection');
      }
      const atInitialPage = !owned.bound && !owned.page.navigationCompleted &&
        typeof owned.page.initialURL === 'string' && observed.url === owned.page.initialURL;
      if ((!atInitialPage && !matches(observed.url, owned.url)) ||
          (observed.token !== null && observed.token !== owned.token)) {
        return await finish('preserved_changed_page');
      }
      if (observed.token === null && owned.bound) {reason = 'identity_lost'; throw Error(reason);}
      if (!verifyOnly && !owned.closeStarted) {
        owned.closeStarted = true; // Record once, even if close/acknowledgement is lost.
        owned.state = 'closing';
        owned.closeAck = 'uncertain';
        reason = 'receipt_error';
        await save();
        try {
          reason = 'close_error';
          await bounded(() => owned.page.close());
          owned.closeAck = 'received';
        } catch {
          // Only observation can resolve an uncertain close; never resubmit it.
          if (reason === 'request_inactive') throw Error(reason);
        }
      }
      // Repeated close requests and verifyOnly perform reads only.
      while (await present()) {
        reason = 'page_present';
        const left = end - now();
        if (left <= 0) throw Error(reason);
        await bounded(() => sleep(Math.min(pollMs, left)));
      }
      return await finish(owned.closeStarted ? 'closed' : 'already_absent');
    } catch {
      const failure = {...details(lastPresent === true && (reason === 'page_present' || reason === 'deadline_exceeded')
        ? 'page_still_present' : 'verification_error'), reason};
      owned.state = 'unverified';
      owned.lastFailure = failure;
      // Receipt errors must not turn uncertainty into successful cleanup.
      try {await save();} catch {failure.reason = 'receipt_error';}
      throw new CleanupError(failure);
    }
  };
}

module.exports = {createCleanup, CleanupError};
