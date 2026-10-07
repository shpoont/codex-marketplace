  q.collect = async (config, previous = null, persistent = null, requiredMetadataIds = [], deferMissing = false) => {
    stopCollection = false;
    collectionLease = Date.now() + 60000;
    const settings = {metadata_max_age: '30d', recent_metadata_max_age: '1d',
      restricted_metadata_max_age: '1d', recent_video_age: '7d', player_request_interval: '5s', catalog_max_age: '7d', ...config.collection};
    const millis = value => Number(value.slice(0, -1)) * {s: 1000, m: 60000, h: 3600000, d: 86400000}[value.slice(-1)];
    playerInterval = millis(settings.player_request_interval);
    if (persistent && persistent.account_channel_id !== config.account_channel_id)
      throw Error('Metadata cache account differs from the configured owner');
    lastPlayerRequest = Math.max(lastPlayerRequest, Date.parse(persistent?.last_player_request_at) || 0);
    if (previous && (!previous.complete || !previous.playlist?.complete ||
        previous.account_channel_id !== config.account_channel_id ||
        previous.playlist.account_channel_id !== config.account_channel_id ||
        previous.playlist.playlist_id !== config.playlist_id))
      throw Error('Previous collection does not belong to this complete account/playlist baseline');
    const cached = new Map((previous?.channels || []).flatMap(c => c.videos).map(v => [v.id, v]));
    // Persistent records contain metadata only. Current listings always supply
    // title, channel classification and progress, even when metadata is reused.
    const metadataCache = new Map((persistent?.videos || []).map(v => [v.id, v]));
    const catalogCache = new Map((persistent?.catalogs || []).map(c => [c.id, c]));
    const knownIds = new Set([...(persistent?.known_video_ids || []), ...cached.keys(),
      ...metadataCache.keys(), ...(persistent?.catalogs || []).flatMap(c => c.videos.map(v => v.id))]);
    const metadataOnly = v => Object.fromEntries(Object.entries(v).filter(([key]) => [
      'id', 'channel_id', 'publication', 'duration', 'playable', 'availability',
      'metadata_checked_at', 'playlist_duration', 'content_warning', 'unlisted_normal', 'is_live'].includes(key)));
    const cacheFresh = (old, v, entry) => {
      const restricted = old?.playable === false && old.availability?.status === 'UNPLAYABLE' &&
        old.availability.restriction === 'members_only';
      if (!old || old.channel_id !== v.channel_id || !old.publication || !old.duration ||
          (!restricted && (!old.playable || !['OK', 'CONTENT_CHECK_REQUIRED'].includes(old.availability?.status))) ||
          !old.metadata_checked_at ||
          (old.content_warning && config.content_warnings !== 'include') ||
          (entry?.duration && entry.duration !== old.playlist_duration)) return false;
      const age = Date.now() - Date.parse(old.metadata_checked_at);
      const recent = Date.now() - Date.parse(old.publication) < millis(settings.recent_video_age);
      return age >= 0 && age < millis(restricted ? settings.restricted_metadata_max_age :
        recent ? settings.recent_metadata_max_age : settings.metadata_max_age);
    };
    const fetchMetadata = async (id, entry) => {
      const m = await q.metadata(id, config.content_warnings);
      // Playlist and player durations can differ. Track the playlist's own
      // value at the check, so a stable difference never forces repeated reads.
      if (entry?.duration) m.playlist_duration = entry.duration;
      checkpoints.push({type: 'metadata', video: m});
      return m;
    };
    const changes = {since: previous?.collected_at || null, new_videos: 0,
      metadata_fetched: 0, metadata_reused: 0, metadata_skipped: 0, metadata_outside_lookback: 0,
      metadata_deferred: 0};
    const anchors = new Set(config.channels.map(c => c.catch_up?.start?.video_id).filter(Boolean));
    const protectedIds = new Set([...anchors, ...requiredMetadataIds]);
    const lookbacks = new Map(config.channels.map(c => [c.id,
      Object.hasOwn(c, 'lookback') ? c.lookback : config.channel_defaults?.lookback]));
    const ignoredIds = new Set(config.channels.filter(c => c.additions === 'ignored').map(c => c.id));
    const identity = await q.identity(config);
    const subscriptions = await q.subscriptions();
    const before = await q.playlist(config);
    // Some playable playlist rows omit the owner. Resolve it before requesting
    // channel classifications; this does not configure or adopt that channel.
    // Reuse this read below so one entry never pays for two player requests.
    const ownerMetadata = new Map();
    for (const entry of before.entries) {
      if (entry.channel_id || entry.percent >= 100 || !entry.playable) continue;
      const saved = metadataCache.get(entry.id) || cached.get(entry.id);
      const reuse = cacheFresh(saved, {...entry, channel_id: saved?.channel_id}, entry);
      const metadata = reuse ? metadataOnly(saved) : await fetchMetadata(entry.id, entry);
      if (!metadata.channel_id) throw Error('Queued video owner unavailable: ' + entry.id);
      changes[reuse ? 'metadata_reused' : 'metadata_fetched']++;
      ownerMetadata.set(entry.id, metadata);
      entry.channel_id = metadata.channel_id;
    }
    const channels = [];
    const readChannels = [...config.channels];
    const configuredIds = new Set(readChannels.map(c => c.id));
    const needsListing = e => e.percent < 100 && e.playable !== false &&
      !ownerMetadata.get(e.id)?.unlisted_normal && !ownerMetadata.get(e.id)?.is_live;
    const manualIds = new Set(before.entries.filter(needsListing).map(e => e.id));
    // Classify current manual entries so excluded formats stay outside management.
    for (const entry of before.entries) {
      if (needsListing(entry) && entry.channel_id && !readChannels.some(c => c.id === entry.channel_id))
        readChannels.push({id: entry.channel_id, name: entry.channel_id});
    }
    // Managed catalogs remain exhaustive. For unmanaged channels, collection only
    // needs the queued entries and can finish once every requested ID is found.
    for (const channel of readChannels) {
      const needed = configuredIds.has(channel.id) && !ignoredIds.has(channel.id) ? null :
        new Set(before.entries.filter(e => e.channel_id === channel.id && manualIds.has(e.id)).map(e => e.id));
      if (needed?.size && channel.catch_up?.start?.video_id) needed.add(channel.catch_up.start.video_id);
      let prior = previous?.channels?.find(c => c.id === channel.id);
      const checkpoint = catalogCache.get(channel.id);
      if (checkpoint && (!prior?.complete || !prior.scanned_at || checkpoint.scanned_at > prior.scanned_at)) prior = checkpoint;
      let catalog;
      try {
        catalog = await q.channel(channel, needed, prior, millis(settings.catalog_max_age));
      } catch (error) {
        // Only a scoped catalog contract failure is recoverable here. Account,
        // session, rate-limit and request-contract failures still stop the run.
        if (error.details?.code !== 'catalog_inconsistent' || error.details.channel_id !== channel.id) throw error;
        catalog = {id: channel.id, complete: false, catalog_unavailable: true, pages: 0,
          videos: (prior?.videos || []).map(v => ({...v, listing_fresh: false, listing_unavailable: true})),
          warnings: [{code: 'catalog_unavailable', channel_id: channel.id, reason: error.details.reason,
            message: 'Channel discovery failed; its additions and retention changes are paused for this run.'}]};
      }
      if (catalog.complete && !catalog.scope && Array.isArray(catalog.page_index))
        checkpoints.push({type: 'catalog', catalog: JSON.parse(JSON.stringify(catalog))});
      if (!configuredIds.has(channel.id)) {
        catalog.videos = catalog.videos.filter(v => manualIds.has(v.id));
        catalog.scope = 'manual_entries_only';
      }
      channels.push(catalog);
    }
    changes.catalog_pages_read = channels.reduce((n, c) => n + c.pages, 0);
    changes.catalogs_full = channels.filter(c => c.scan === 'full').length;
    changes.catalogs_incremental = channels.filter(c => c.scan === 'incremental').length;
    changes.catalogs_skipped = channels.filter(c => c.pages === 0).length;
    const unavailableChannels = new Set(channels.filter(c => c.catalog_unavailable).map(c => c.id));
    const videos = channels.flatMap(c => c.videos);
    const normalIds = new Set(videos.map(v => v.id)), exclusions = {};
    for (const channel of readChannels) {
      if (unavailableChannels.has(channel.id)) continue;
      const needed = new Set(before.entries.filter(e => e.channel_id === channel.id && needsListing(e) && !normalIds.has(e.id)).map(e => e.id));
      if (needed.size) Object.assign(exclusions, await q.exclusions(channel, needed));
    }
    const current = new Map(before.entries.map(e => [e.id, e]));
    const deferredIds = [], ageSkippedIds = [];
    let index = 0, completed = 0;
    async function worker() {
      while (index < videos.length) {
        const v = videos[index++];
        const old = cached.get(v.id), entry = current.get(v.id);
        const ageEvidence = v.publication_age;
        delete v.publication_age;
        v.percent = entry && v.listing_fresh === false ? entry.percent : Math.max(v.percent, entry?.percent || 0);
        if (!knownIds.has(v.id)) changes.new_videos++;
        if (unavailableChannels.has(v.channel_id)) {
          // The planner preserves queued entries without guessing classification
          // or eligibility. Do not make more channel-dependent reads this run.
          changes.metadata_skipped++;
          completed++;
          continue;
        }
        // Missing ignored-channel videos cannot enter selection. Keep complete
        // listing coverage, but only fetch their metadata when queued or needed
        // as a cutoff anchor. Enabling additions later requires fresh metadata.
        if (ignoredIds.has(v.channel_id) && !entry && !anchors.has(v.id)) {
          changes.metadata_skipped++;
          completed++; q.job.progress = {phase: 'publication metadata', completed, total: videos.length};
          continue;
        }
        // Watched entries are outside management. Their playback warnings cannot
        // block unrelated work; only a configured cutoff still needs publication.
        if (v.percent >= 100 && !anchors.has(v.id)) {
          if (old?.publication && old.duration) {
            Object.assign(v, {publication: old.publication, duration: old.duration,
              playable: entry ? entry.playable : old.playable, kind: old.kind,
              ...('unlisted_normal' in old ? {unlisted_normal: old.unlisted_normal} : {}),
              content_warning: old.content_warning === true});
            changes.metadata_reused++;
          } else {
            changes.metadata_skipped++;
          }
          completed++; q.job.progress = {phase: 'publication metadata', completed, total: videos.length};
          continue;
        }
        // Reuse verified metadata for queued and missing candidates. Listings
        // supply progress/title; restrictions from either source still apply.
        // Cache expiry never changes playlist addition clocks.
        const saved = ownerMetadata.get(v.id) || metadataCache.get(v.id) || old;
        const reuse = ownerMetadata.has(v.id) || cacheFresh(saved, v, entry);
        if (!reuse && !entry && !protectedIds.has(v.id) &&
            q.outsideLookback(ageEvidence, lookbacks.get(v.channel_id))) {
          // No player availability/publication is claimed or cached here. The
          // planner must independently validate this evidence for absent items.
          v.publication_age = ageEvidence;
          changes.metadata_skipped++;
          changes.metadata_outside_lookback++;
          ageSkippedIds.push(v.id);
          completed++; q.job.progress = {phase: 'publication metadata', completed, total: videos.length, ...changes};
          continue;
        }
        if (deferMissing && !reuse && !entry && !protectedIds.has(v.id)) {
          // Python's planner decides which absent candidates need a check.
          // No count, retention or dismissal policy is duplicated here.
          if (ageEvidence) v.publication_age = ageEvidence;
          changes.metadata_skipped++;
          changes.metadata_deferred++;
          deferredIds.push(v.id);
          completed++; q.job.progress = {phase: 'publication metadata', completed, total: videos.length, ...changes};
          continue;
        }
        const m = reuse ? {...metadataOnly(saved), playable: entry ? entry.playable && saved.playable : saved.playable} : await fetchMetadata(v.id, entry);
        if (!ownerMetadata.has(v.id)) changes[reuse ? 'metadata_reused' : 'metadata_fetched']++;
        if (m.channel_id && m.channel_id !== v.channel_id)
          throw Error(`Video owner differs from channel for ${v.id}: listed under ${v.channel_id}, player owner ${m.channel_id}`);
        Object.assign(v, m);
        if (m.is_live) v.kind = 'live';
        completed++; q.job.progress = {phase: 'publication metadata', completed, total: videos.length, ...changes};
      }
    }
    // One worker bounds request volume and stops immediately on an ambiguous
    // response; successful checkpoints survive without advancing membership.
    await worker();
    // Unlisted entries can remain queued after disappearing from channel tabs.
    // Classify only from explicit YouTube flags, never from title or duration.
    const queuedUnlisted = new Map();
    for (const entry of before.entries) {
      if (!entry.channel_id || entry.percent >= 100 || !entry.playable ||
          normalIds.has(entry.id) || exclusions[entry.id] ||
          unavailableChannels.has(entry.channel_id)) continue;
      const saved = ownerMetadata.get(entry.id) || metadataCache.get(entry.id);
      const reuse = ownerMetadata.has(entry.id) || cacheFresh(saved, entry, entry);
      const metadata = reuse ? saved : await fetchMetadata(entry.id, entry);
      if (!ownerMetadata.has(entry.id)) changes[reuse ? 'metadata_reused' : 'metadata_fetched']++;
      if (metadata.channel_id !== entry.channel_id) throw Error('Queued unlisted video owner differs from channel');
      if (metadata.unlisted_normal === true)
        queuedUnlisted.set(entry.id, {...metadata, kind: 'normal', classification: 'player_unlisted_normal'});
      else if (metadata.is_live === true)
        queuedUnlisted.set(entry.id, {...metadata, kind: 'live'});
    }
    const after = await q.playlist(config);
    const membership = p => JSON.stringify(p.entries.map(e => [e.entry_id, e.id, e.percent]));
    if (membership(before) !== membership(after)) throw Error('Playlist changed during collection; collect again');
    const baseline = before.entries.map(e => [e.entry_id, e.id, e.percent]);
    await q.identity(config);
    const byId = new Map(videos.map(v => [v.id, v]));
    for (const entry of after.entries) {
      if (ownerMetadata.has(entry.id)) entry.channel_id = ownerMetadata.get(entry.id).channel_id;
      if (unavailableChannels.has(entry.channel_id)) continue; // Preserve the actual playlist row.
      const v = byId.get(entry.id);
      if (v) Object.assign(entry, v, {percent: Math.max(entry.percent, v.percent),
        playable: entry.playable && v.playable});
      else if (exclusions[entry.id]) entry.kind = exclusions[entry.id];
      else if (queuedUnlisted.has(entry.id)) Object.assign(entry, queuedUnlisted.get(entry.id), {
        playable: entry.playable && queuedUnlisted.get(entry.id).playable});
    }
    collectionLease = 0;
    return {schema: 2, ...identity, playlist: after, subscriptions, channels, collection: changes,
      ...(deferMissing ? {metadata_stage: {baseline, deferred_ids: deferredIds, age_skipped_ids: ageSkippedIds}} : {}),
      collected_at: new Date().toISOString(), complete: true};
  };
