  q.edit = async (config, action, expectedBefore) => {
    await q.identity(config);
    // Identity and exact playlist guards are repeated immediately before every write.
    const before = await q.playlist(config);
    if (JSON.stringify(before.entries.map(e => [e.entry_id, e.id])) !== JSON.stringify(expectedBefore))
      throw Error('Playlist changed immediately before dispatch; readback required');
    const allowed = ['ACTION_ADD_VIDEO', 'ACTION_REMOVE_VIDEO', 'ACTION_MOVE_VIDEO_AFTER'];
    const actions = Array.isArray(action) ? action : [action];
    if (!actions.length || actions.length > 20 || actions.some(a => !allowed.includes(a.action)))
      throw Error('Unsupported playlist operation');
    const d = await request(command('browse/edit_playlist', 'playlistEditEndpoint', {
      playlistId: config.playlist_id, actions
    }), true);
    if (d.status !== 'STATUS_SUCCEEDED') throw Error('Playlist edit not confirmed; readback required');
    return {status: d.status};
  };
  // Explicit one-time library operations; ordinary refreshes never call these.
  q.createPlaylist = async (config, title, videoIds) => {
    if (typeof title !== 'string' || !title.trim() || !Array.isArray(videoIds) ||
        videoIds.some(id => !/^[\w-]{11}$/.test(id)) ||
        new Set(videoIds).size !== videoIds.length)
      throw Error('Invalid private playlist creation request');
    await q.identity(config);
    const d = await request(command('playlist/create', 'createPlaylistServiceEndpoint', {
      title, privacyStatus: 'PRIVATE', videoIds
    }), true);
    if (typeof d.playlistId !== 'string' || !/^PL[\w-]+$/.test(d.playlistId))
      throw Error('Playlist creation outcome is unknown; inspect before retrying');
    return {playlist_id: d.playlistId};
  };
  q.removeBatch = async (config, entryIds, expectedBefore) => {
    if (!Array.isArray(entryIds) || !entryIds.length || entryIds.length > 50 ||
        entryIds.some(id => typeof id !== 'string' || !id) || new Set(entryIds).size !== entryIds.length)
      throw Error('Invalid explicit removal batch');
    await q.identity(config);
    const before = await q.playlist(config);
    if (JSON.stringify(before.entries.map(e => [e.entry_id, e.id])) !== JSON.stringify(expectedBefore))
      throw Error('Playlist changed immediately before dispatch; readback required');
    if (entryIds.some(id => !before.entries.some(e => e.entry_id === id)))
      throw Error('Removal batch includes a missing entry');
    const d = await request(command('browse/edit_playlist', 'playlistEditEndpoint', {
      playlistId: config.playlist_id,
      actions: entryIds.map(id => ({action: 'ACTION_REMOVE_VIDEO', setVideoId: id}))
    }), true);
    if (d.status !== 'STATUS_SUCCEEDED') throw Error('Playlist edit not confirmed; readback required');
    return {status: d.status};
  };
  q.start = (method, args) => {
    if (q.job.state === 'running') throw Error('A browser job is already running');
    if (!['identity', 'playlist', 'channel', 'metadata', 'collect', 'refreshCatalog', 'edit', 'createPlaylist', 'removeBatch', 'subscriptionSnapshot'].includes(method)) throw Error('Unknown bridge operation');
    q.requestMetrics = {};
    q.job = {state: 'running', method, requests: q.requestMetrics};
    q[method](...args).then(result => { collectionLease = 0; q.job = {state: 'complete', result, requests: q.requestMetrics}; })
      .catch(error => { collectionLease = 0;
        q.job = {state: 'error', error: error.message, details: error.details || null, requests: q.requestMetrics}; });
    return {state: 'running'};
  };
  return JSON.stringify({ready: true, adapter: q.adapter});
