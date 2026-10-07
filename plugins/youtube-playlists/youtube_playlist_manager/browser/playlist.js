  q.identity = async config => {
    // Verify fresh API account data, independently of account-button/UI bootstrap.
    const headers = [];
    walk(await request(command('account/account_menu', 'signalServiceEndpoint', {signal: 'GET_ACCOUNT_MENU'})),
      x => { if (x.activeAccountHeaderRenderer) headers.push(x.activeAccountHeaderRenderer); });
    if (headers.length !== 1) throw adapterFailure('account_response');
    const header = headers[0];
    const handle = text(header?.channelHandle);
    if (!handle.startsWith('@')) throw adapterFailure('account_response');
    const d = await request(browse(config.account_channel_id));
    const m = d.metadata?.channelMetadataRenderer;
    const resolved = m?.vanityChannelUrl ? decodeURIComponent(new URL(m.vanityChannelUrl).pathname).replace(/^\//, '') : '';
    if (m?.externalId !== config.account_channel_id || resolved.toLowerCase() !== handle.toLowerCase())
      throw Error('Active YouTube account does not match configured owner');
    return {account_channel_id: m.externalId, handle, name: text(header.accountName)};
  };
  q.playlist = async config => {
    let first = await request(browse('VL' + config.playlist_id));
    if (first.alerts?.some(a => text(a.alertRenderer?.text) === 'The playlist does not exist.'))
      throw attention('YouTube reports that the configured playlist does not exist; check the playlist setting',
        {code: 'playlist_unavailable'});
    let showUnavailable;
    walk(first.header, x => {
      const r = x.menuNavigationItemRenderer;
      if (text(r?.text) === 'Show unavailable videos') showUnavailable = r.navigationEndpoint;
    });
    if (showUnavailable) first = await request(showUnavailable);
    const owners = new Set(), targets = new Set(), selectedPrivacy = [];
    walk(first.sidebar, x => {
      if (x.videoOwnerRenderer) {
        const r = x.videoOwnerRenderer;
        const id = r.navigationEndpoint?.browseEndpoint?.browseId || r.title?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.browseId;
        if (id) owners.add(id);
      }
      if (x.playlistEditEndpoint?.playlistId) targets.add(x.playlistEditEndpoint.playlistId);
      if (x.privacyDropdownItemRenderer?.isSelected) selectedPrivacy.push(text(x.privacyDropdownItemRenderer.label));
    });
    if (!owners.has(config.account_channel_id) || !targets.has(config.playlist_id))
      throw Error('Playlist owner or editable target identity is unverified');
    if (config.environment === 'development' && !selectedPrivacy.includes('Private'))
      throw Error('Development playlist is not verified private');
    const playlistRoots = d => {
      // Watch Later continuations can also contain an unrelated page shell.
      // Use the update explicitly addressed to this playlist before page contents.
      const updates = [...(d.onResponseReceivedActions || []), ...(d.onResponseReceivedEndpoints || [])]
        .map(a => a.appendContinuationItemsAction || a.reloadContinuationItemsCommand).filter(Boolean);
      const addressed = updates.filter(a => a.targetId === config.playlist_id);
      if (addressed.length > 1) throw Error('Multiple playlist continuation updates');
      if (addressed.length === 1) {
        if (!Array.isArray(addressed[0].continuationItems)) throw Error('Missing playlist continuation items');
        return [addressed[0].continuationItems];
      }
      if (!d.contents) {
        if (updates.some(a => a.targetId)) throw Error('Unexpected playlist continuation target');
        return roots(d);
      }
      const lists = [], messages = [];
      walk(d.contents, x => {
        if (x.playlistVideoListRenderer) lists.push(x.playlistVideoListRenderer);
        if (text(x.messageRenderer?.text) === 'No videos in this playlist yet') messages.push(x);
      });
      if (lists.length === 1 && lists[0].playlistId === config.playlist_id)
        return [lists[0].contents];
      if (!lists.length && messages.length === 1) return messages;
      throw adapterFailure('playlist_response');
    };
    const rows = [], seen = new Set();
    const count = await pages(first, rs => rs.forEach(root => walk(root, x => {
      if (!x.playlistVideoRenderer) return;
      const r = x.playlistVideoRenderer;
      if (!r.setVideoId || !r.videoId || seen.has(r.setVideoId)) throw Error('Invalid or repeated playlist item');
      seen.add(r.setVideoId);
      rows.push({id: r.videoId, entry_id: r.setVideoId, title: text(r.title),
        channel_id: r.shortBylineText?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.browseId || null,
        playable: r.isPlayable === true, percent: progress(r),
        kind: 'unknown', publication: null, duration: Number(r.lengthSeconds) || null});
      return false;
    })), 'playlist', playlistRoots);
    if (!rows.length) {
      let empty = false;
      walk(first.contents, x => { if (text(x.messageRenderer?.text) === 'No videos in this playlist yet') empty = true; });
      if (!empty) throw Error('Empty playlist has no verified empty-state marker');
    }
    return {playlist_id: config.playlist_id, account_channel_id: config.account_channel_id,
      complete: true, pages: count, title: first.metadata?.playlistMetadataRenderer?.title,
      privacy: selectedPrivacy[0], entries: rows};
  };
  q.subscriptions = async () => {
    const rows = new Map();
    const count = await pages(await request(browse('FEchannels')), rs => rs.forEach(root => walk(root, x => {
      if (!x.channelRenderer) return;
      const r = x.channelRenderer;
      if (!r.channelId || typeof r.subscriptionButton?.subscribed !== 'boolean') throw Error('Unknown subscription state');
      rows.set(r.channelId, {id: r.channelId, name: text(r.title), subscribed: r.subscriptionButton.subscribed});
      return false;
    })), 'subscriptions');
    if (!rows.size) throw Error('Subscription list contained no recognized channels; cannot infer unsubscriptions');
    return {complete: true, pages: count, channels: [...rows.values()]};
  };
  q.subscriptionSnapshot = async config => {
    const identity = await q.identity(config);
    const subscriptions = await q.subscriptions();
    await q.identity(config);
    return {identity, subscriptions, checked_at: new Date().toISOString()};
  };
