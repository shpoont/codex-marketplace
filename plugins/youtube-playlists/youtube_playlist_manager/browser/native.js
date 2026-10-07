  // Script builds are diagnostics. Never invoke minified exports or UI handlers.
  const builds = [...new Set([...document.scripts].flatMap(script => {
    const url = new URL(script.src || '', window.location.origin);
    if (url.origin !== 'https://www.youtube.com') return [];
    const match = url.pathname.match(/\.kevlar_base\.([A-Za-z]{2,3}_[A-Za-z]{2}\.([A-Za-z0-9_-]{1,80}))\.es5\./);
    return match ? [match[1]] : [];
  }))];
  const nativeBuild = builds.length === 1 ? builds[0] : null;
  const adapterFailure = (stage, code = 'api_incompatible') => Object.assign(
    new Error(code === 'auth_required'
      ? 'YouTube sign-in is unavailable; sign in to the intended account in the selected browser and try again'
      : code === 'session_changed'
        ? 'The active YouTube session changed; collect again before updating the playlist'
        : 'YouTube API compatibility check failed; this update cannot finish and the plugin may need an update'),
    {details: {code, adapter: {stage, build: nativeBuild, error_type: 'Error'}}});
  if (window.location.origin !== 'https://www.youtube.com' ||
      typeof window.ytcfg?.get !== 'function') throw adapterFailure('page_context');
  const get = key => {
    try { return window.ytcfg.get(key); }
    catch (_) { throw adapterFailure('page_context'); }
  };
  const sessionIdentity = () => {
    if (get('LOGGED_IN') !== true) throw adapterFailure('session_context', 'auth_required');
    const index = get('SESSION_INDEX'), user = get('USER_SESSION_ID'), delegated = get('DELEGATED_SESSION_ID');
    const validSessionId = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,256}$/.test(value);
    if (!/^\d{1,6}$/.test(String(index)) || !validSessionId(user) ||
        (delegated != null && !validSessionId(delegated)))
      throw adapterFailure('session_context');
    return {index: String(index), user, delegated: delegated || null};
  };
  const boundSession = sessionIdentity();
  const clientContext = () => {
    const session = sessionIdentity();
    if (JSON.stringify(session) !== JSON.stringify(boundSession))
      throw adapterFailure('session_context', 'session_changed');
    const context = get('INNERTUBE_CONTEXT'), client = context?.client;
    const version = get('INNERTUBE_CONTEXT_CLIENT_VERSION'), name = get('INNERTUBE_CONTEXT_CLIENT_NAME');
    if (client?.clientName !== 'WEB' || String(name) !== '1' ||
        typeof version !== 'string' || !/^[A-Za-z0-9_.-]{1,100}$/.test(version) ||
        client.clientVersion !== version || (context.user?.onBehalfOfUser &&
          context.user.onBehalfOfUser !== session.delegated)) throw adapterFailure('client_context');
    if (client.visitorData != null && (typeof client.visitorData !== 'string' ||
        client.visitorData.length > 32768 || /[\r\n]/.test(client.visitorData)))
      throw adapterFailure('client_context');
    let copy;
    try { copy = JSON.parse(JSON.stringify(context)); }
    catch (_) { throw adapterFailure('client_context'); }
    if (session.delegated) copy.user = {...copy.user, onBehalfOfUser: session.delegated};
    return {context: copy, session, name: String(name), version};
  };
  clientContext();
  if (typeof window.crypto?.subtle?.digest !== 'function') throw adapterFailure('session_signing');
  const authorization = async session => {
    // Consume only this page's signing cookies. Values and hashes remain in this
    // closure for immediate use, without credential files or exported secrets.
    const cookies = new Map();
    for (const part of document.cookie.split(';')) {
      const index = part.indexOf('=');
      if (index < 0) continue;
      const name = part.slice(0, index).trim();
      // YouTube's cookie reader returns the first matching cookie. A Map
      // constructed from all pairs would silently select the last instead.
      if (!cookies.has(name)) cookies.set(name, part.slice(index + 1));
    }
    const timestamp = Math.floor(Date.now() / 1000), signatures = [];
    // Third-party-only sessions still require the main signature, using the
    // same cookie as the third-party signature, just as YouTube's client does.
    for (const [scheme, sid] of [
        ['SAPISIDHASH', cookies.get('SAPISID') || cookies.get('__Secure-3PAPISID')],
        ['SAPISID1PHASH', cookies.get('__Secure-1PAPISID')],
        ['SAPISID3PHASH', cookies.get('__Secure-3PAPISID')]]) {
      if (!sid) continue;
      try {
        const input = [session.user, timestamp, sid, window.location.origin].join(' ');
        const digest = await window.crypto.subtle.digest('SHA-1', new TextEncoder().encode(input));
        const hash = [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
        signatures.push(scheme + ' ' + timestamp + '_' + hash + '_u');
      } catch (_) { throw adapterFailure('session_signing'); }
    }
    if (!signatures.length) throw adapterFailure('session_signing', 'auth_required');
    return signatures.join(' ');
  };
