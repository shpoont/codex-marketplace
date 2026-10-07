  // Own request construction and signing; never run YouTube's UI processors.
  const q = window.__playlistManager = {job: {state: 'idle'}, requestMetrics: {},
    adapter: {mode: 'in_page_contract', build: nativeBuild}};
  let checkpoints = [], lastPlayerRequest = 0, playerInterval = 5000, stopCollection = false, collectionLease = 0;
  q.cancelCollection = () => { stopCollection = true; };
  q.drainCheckpoints = () => {
    if (collectionLease) collectionLease = Date.now() + 60000;
    const result = checkpoints; checkpoints = []; return result;
  };
  const attention = (message, details) => Object.assign(new Error(message), {details});
  const text = x => x?.simpleText || x?.runs?.map(r => r.text).join('') || x?.content || '';
  const walk = (x, fn) => {
    if (!x || typeof x !== 'object') return;
    if (fn(x) === false) return;
    Object.values(x).forEach(v => walk(v, fn));
  };
  const command = (path, endpoint, body) => ({
    commandMetadata: {webCommandMetadata: {sendPost: true, apiUrl: '/youtubei/v1/' + path}},
    [endpoint]: body
  });
  const browse = id => command('browse', 'browseEndpoint', {browseId: id});
  const requestPayload = cmd => {
    const names = ['browseEndpoint', 'watchEndpoint', 'continuationCommand',
      'signalServiceEndpoint', 'playlistEditEndpoint', 'createPlaylistServiceEndpoint'];
    const present = names.filter(name => cmd?.[name]);
    if (present.length !== 1) throw adapterFailure('request_contract');
    const name = present[0], value = cmd[name];
    const id = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,256}$/.test(value);
    const token = value => typeof value === 'string' && value.length > 0 && value.length <= 32768;
    let path, body;
    if (name === 'browseEndpoint' && id(value.browseId) &&
        (value.params == null || token(value.params))) {
      path = 'browse'; body = {browseId: value.browseId, ...(value.params ? {params: value.params} : {})};
    } else if (name === 'continuationCommand' &&
        value.request === 'CONTINUATION_REQUEST_TYPE_BROWSE' && token(value.token)) {
      path = 'browse'; body = {continuation: value.token};
    } else if (name === 'watchEndpoint' && id(value.videoId)) {
      path = 'player'; body = {videoId: value.videoId};
    } else if (name === 'signalServiceEndpoint' && value.signal === 'GET_ACCOUNT_MENU') {
      path = 'account/account_menu'; body = {};
    } else if (name === 'playlistEditEndpoint' && id(value.playlistId) &&
        Array.isArray(value.actions) && value.actions.length > 0 && value.actions.length <= 50) {
      const actions = value.actions.map(action => {
        if (action.action === 'ACTION_ADD_VIDEO' && id(action.addedVideoId))
          return {action: action.action, addedVideoId: action.addedVideoId};
        if (action.action === 'ACTION_REMOVE_VIDEO' && token(action.setVideoId))
          return {action: action.action, setVideoId: action.setVideoId};
        if (action.action === 'ACTION_MOVE_VIDEO_AFTER' && token(action.setVideoId) &&
            (action.movedSetVideoIdPredecessor == null || token(action.movedSetVideoIdPredecessor)))
          return {action: action.action, setVideoId: action.setVideoId,
            movedSetVideoIdPredecessor: action.movedSetVideoIdPredecessor};
        throw adapterFailure('request_contract');
      });
      path = 'browse/edit_playlist'; body = {playlistId: value.playlistId, actions};
    } else if (name === 'createPlaylistServiceEndpoint' && typeof value.title === 'string' &&
        value.title.trim() && value.title.length <= 150 && value.privacyStatus === 'PRIVATE' &&
        Array.isArray(value.videoIds) && value.videoIds.length <= 5000 &&
        value.videoIds.every(videoId => typeof videoId === 'string' && /^[\w-]{11}$/.test(videoId))) {
      path = 'playlist/create'; body = {title: value.title, privacyStatus: 'PRIVATE', videoIds: [...value.videoIds]};
    } else { throw adapterFailure('request_contract'); }
    const expectedPath = '/youtubei/v1/' + path;
    const metadata = cmd.commandMetadata?.webCommandMetadata;
    // Navigation metadata can omit sendPost. The owned API client always uses
    // POST; only the declared destination must agree with the supported route.
    if (metadata?.apiUrl && metadata.apiUrl !== expectedPath)
      throw adapterFailure('request_contract');
    return {path: expectedPath, body, readOnly: ['browse', 'player', 'account/account_menu'].includes(path)};
  };
  const request = async (cmd, allowWrite = false) => {
    if (stopCollection || (collectionLease && Date.now() > collectionLease))
      throw Error('Collection cancelled or host disconnected; no further requests');
    const payload = requestPayload(cmd), url = new URL(payload.path, window.location.origin);
    if (!payload.readOnly && !allowWrite) throw adapterFailure('request_contract');
    url.searchParams.set('prettyPrint', 'false');
    const readOnly = payload.readOnly;
    let data;
    for (let attempt = 0; attempt < 2; attempt++) {
      if (cmd.watchEndpoint && url.pathname === '/youtubei/v1/player') {
        const delay = Math.max(0, lastPlayerRequest + playerInterval - Date.now());
        if (delay) {
          q.job.progress = {phase: 'pacing player requests', next_request_at: new Date(Date.now() + delay).toISOString()};
          await new Promise(resolve => setTimeout(resolve, delay));
        }
        if (stopCollection || (collectionLease && Date.now() > collectionLease))
          throw Error('Collection cancelled or host disconnected; no further requests');
        lastPlayerRequest = Date.now();
        checkpoints.push({type: 'player_request', at: new Date(lastPlayerRequest).toISOString()});
      }
      const active = clientContext();
      const headers = {'Content-Type': 'application/json', Authorization: await authorization(active.session),
        'X-Goog-AuthUser': active.session.index, 'X-Origin': window.location.origin,
        'X-Youtube-Client-Name': active.name, 'X-Youtube-Client-Version': active.version};
      if (active.session.delegated) headers['X-Goog-PageId'] = active.session.delegated;
      const visitor = active.context.client.visitorData;
      if (visitor) headers['X-Goog-Visitor-Id'] = visitor;
      clientContext(); // Signing is async; reject an account switch before dispatch.
      if (stopCollection || (collectionLease && Date.now() > collectionLease))
        throw Error('Collection cancelled or host disconnected; no further requests');
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 45000);
      const metrics = q.requestMetrics[url.pathname] ||= {attempts: 0, retries: 0,
        http_errors: 0, network_errors: 0, rate_limited: 0, duration_ms: 0};
      metrics.attempts++; metrics.retries += attempt > 0 ? 1 : 0;
      const requestStarted = Date.now();
      let receivedResponse = false;
      try {
        const response = await fetch(url.href, {method: 'POST', headers,
          body: JSON.stringify({context: active.context, ...payload.body}), credentials: 'same-origin',
          mode: 'same-origin', redirect: 'error', cache: 'no-store', signal: controller.signal});
        receivedResponse = true;
        if (!response.ok) metrics.http_errors++;
        if (response.status === 429) {
          metrics.rate_limited++;
          const raw = response.headers?.get('Retry-After');
          const retry = raw && (/^\d+$/.test(raw) ? Number(raw) : (Date.parse(raw) - Date.now()) / 1000);
          throw attention('YouTube rate limited this session; collection is incomplete', {
            code: 'rate_limited', http_status: 429, endpoint: url.pathname,
            retry_after_seconds: Number.isFinite(retry) ? Math.max(0, Math.ceil(retry)) : null});
        }
        if (response.status === 401) throw adapterFailure('session_authorization', 'auth_required');
        if (response.status === 404) throw adapterFailure('endpoint_contract');
        if (!response.ok) throw attention('YouTube request failed: HTTP ' + response.status,
          {code: 'http_error', http_status: response.status, endpoint: url.pathname});
        try { data = await response.json(); }
        catch (_) { throw adapterFailure('response_contract'); }
        break;
      } catch (error) {
        if (!receivedResponse) metrics.network_errors++;
        // Retry the same read once after a transport failure. Writes, HTTP
        // rejections and unknown response formats always stop for inspection.
        if (!readOnly || attempt || !['AbortError', 'TypeError'].includes(error?.name)) throw error;
        q.job.progress = {phase: 'retrying interrupted read', endpoint: url.pathname};
      } finally { clearTimeout(timer); metrics.duration_ms += Math.max(0, Date.now() - requestStarted); }
    }
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw adapterFailure('response_contract');
    // HTTP 200 can still be a guest response while bootstrap says logged in.
    // Do not mistake its missing account header or private playlist for an
    // incompatible API or a deleted target.
    if (data.responseContext?.mainAppWebResponseContext?.loggedOut === true)
      throw adapterFailure('session_authorization', 'auth_required');
    if (data.error) throw attention('YouTube rejected the request; this update cannot finish',
      {code: 'request_rejected', endpoint: url.pathname});
    return data;
  };
  const roots = d => {
    const tabs = d.contents?.twoColumnBrowseResultsRenderer?.tabs;
    if (tabs) {
      const content = tabs.map(t => t.tabRenderer).find(t => t?.selected)?.content;
      if (!content) throw adapterFailure('browse_response');
      return [content];
    }
    const r = [...(d.onResponseReceivedActions || []), ...(d.onResponseReceivedEndpoints || [])]
      .map(a => a.appendContinuationItemsAction?.continuationItems || a.reloadContinuationItemsCommand?.continuationItems)
      .filter(Boolean);
    if (!r.length) throw adapterFailure('browse_response');
    return r;
  };
  const nextCommands = rs => {
    const result = [];
    rs.forEach(r => walk(r, x => {
      if (!x.continuationItemRenderer) return;
      walk(x.continuationItemRenderer, y => {
        if (y.continuationCommand?.token) { result.push(y); return false; }
      });
      return false;
    }));
    return result;
  };
  async function pages(first, consume, label, selectRoots = roots, finished = null) {
    let d = first, count = 0;
    const seen = new Set();
    while (d) {
      const rs = selectRoots(d);
      consume(rs); count++;
      q.job.progress = {phase: label, pages: count};
      if (finished?.()) return count;
      const next = nextCommands(rs);
      if (next.length > 1 || count > 300) throw Error('Unexpected pagination: ' + label);
      if (!next.length) return count;
      const token = next[0].continuationCommand.token;
      if (seen.has(token)) throw Error('Repeated continuation: ' + label);
      seen.add(token);
      d = await request(next[0]);
    }
  }
  function progress(renderer, lockup = false) {
    // Absence of the supported progress overlay is YouTube's zero-progress signal.
    const values = [];
    walk(lockup ? renderer.contentImage : renderer.thumbnailOverlays, x => {
      if (x.thumbnailOverlayResumePlaybackRenderer) values.push(x.thumbnailOverlayResumePlaybackRenderer.percentDurationWatched);
      if (x.thumbnailOverlayProgressBarViewModel) values.push(x.thumbnailOverlayProgressBarViewModel.startPercent);
    });
    if (values.some(v => !Number.isFinite(v) || v < 0 || v > 100)) throw Error('Unknown watch-progress value');
    return values.length ? Math.max(...values) : 0;
  }
