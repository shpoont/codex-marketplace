// Generic browser-tool connection. The host supplies documented exact-page APIs.
// No browser names, credentials, YouTube endpoints or channel policy here.
'use strict';
const {createController, createCDPPage, OpenError} = require('./controller.js');

async function createToolController({directory, createPage, connectPage, inspectPage,
  closePage, isPagePresent, navigatePage, initialPageURL = 'about:blank', event, cleanupOptions}) {
  for (const callback of [createPage, connectPage, inspectPage, closePage, isPagePresent]) {
    if (typeof callback !== 'function') throw Error('Missing browser-tool capability');
  }
  if (navigatePage !== undefined && (typeof navigatePage !== 'function' ||
      typeof initialPageURL !== 'string' || !initialPageURL)) {
    throw Error('Invalid browser-tool navigation capability');
  }
  return createController({directory, cleanupOptions, openPage: async url => {
    // Return the exact handle before any navigation or connection can fail.
    const handle = await (navigatePage ? createPage() : createPage(url));
    let connected, bound = false, navigationStarted = false, navigationCompleted = false;
    return {id: handle.id,
      initialURL: navigatePage ? initialPageURL : undefined,
      get navigationStarted() {return navigationStarted;},
      get navigationCompleted() {return navigationCompleted;},
      async bind(target, token, {ensureActive, checkpoint}) {
        if (navigatePage) {
          try {
            await ensureActive();
            const observed = await inspectPage(handle);
            if (observed?.url !== initialPageURL) throw Error('Initial page changed');
            await ensureActive();
          } catch {throw new OpenError('inspect_page');}
          try {
            navigationStarted = true;
            await checkpoint(); // Persist intent before the one native navigation.
            await ensureActive();
            await navigatePage(handle, target);
            navigationCompleted = true;
            await checkpoint();
            await ensureActive();
          } catch {throw new OpenError('navigate_page');}
        }
        let capability;
        try {
          await ensureActive();
          capability = await connectPage(handle);
          if (typeof capability?.send !== 'function') throw Error('Missing CDP send');
          await ensureActive();
        } catch {throw new OpenError('connect_page');}
        connected = createCDPPage({id: handle.id, send: (...args) => capability.send(...args),
          close: () => closePage(handle), isPresent: () => isPagePresent(handle), event});
        try {await connected.bind(target, token);}
        catch {throw new OpenError('bind_page');}
        bound = true;
      },
      evaluate: (...args) => connected.evaluate(...args),
      async inspect() {
        if (bound) return connected.inspect();
        // Setup failure must still be cleanable without the failed CDP capability.
        const observed = await inspectPage(handle);
        return {url: observed?.url, token: null};
      },
      close: () => closePage(handle),
      isPresent: () => isPagePresent(handle)};
  }});
}

module.exports = {createToolController};
