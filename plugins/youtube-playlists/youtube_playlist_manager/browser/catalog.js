  const agePattern = /^([1-9][0-9]{0,3}) (minute|hour|day|week|month|year)s? ago$/;
  const compactAgePattern = /^([1-9][0-9]{0,3})(mo|m|h|d|w|y) ago$/;
  const publicationAgeVersion = 2;
  // RegExp's $ also matches before a trailing newline. Require the entire
  // label so unknown decorations never become exclusion evidence.
  const fullMatch = (pattern, label) => {
    if (typeof label !== 'string') return null;
    const match = label.match(pattern);
    return match && match[0] === label ? match : null;
  };
  const publicationAge = label => fullMatch(agePattern, label) ? {
    source: 'youtube_videos_tab', label, observed_at: new Date().toISOString()
  } : null;
  q.outsideLookback = (evidence, lookback, now = Date.now()) => {
    if (evidence?.source !== 'youtube_videos_tab' || typeof evidence.label !== 'string' ||
        typeof lookback !== 'string' || !/^[1-9][0-9]*[smhd]$/.test(lookback)) return false;
    const match = fullMatch(agePattern, evidence.label), observed = Date.parse(evidence.observed_at);
    if (!match || !Number.isFinite(observed) || observed > now) return false;
    // Mirror publication_age.py: a full unit of rounding uncertainty, plus a
    // day of boundary margin. These labels can exclude, never admit, a video.
    const units = {minute: 60, hour: 3600, day: 86400, week: 604800, month: 2419200, year: 31536000};
    const lower = Math.max(0, (Number(match[1]) - 1) * units[match[2]] - 86400) * 1000;
    const window = Number(lookback.slice(0, -1)) * {s: 1000, m: 60000, h: 3600000, d: 86400000}[lookback.slice(-1)];
    return lower > 0 && observed - lower < now - window;
  };
  const lockupAge = r => {
    const rows = r.metadata?.lockupMetadataViewModel?.metadata?.contentMetadataViewModel?.metadataRows || [];
    const labels = rows.filter(row => !row.lockupContentMetadataRowExtension).flatMap(row =>
      (row.metadataParts || []).filter(part =>
        fullMatch(agePattern, text(part.text)) || fullMatch(compactAgePattern, text(part.text)) ||
        fullMatch(agePattern, part.accessibilityLabel)).map(part => {
        const label = fullMatch(agePattern, part.accessibilityLabel);
        const display = fullMatch(agePattern, text(part.text)) || fullMatch(compactAgePattern, text(part.text));
        const unit = display && ({m: 'minute', h: 'hour', d: 'day', w: 'week', mo: 'month', y: 'year'}[display[2]] || display[2]);
        if (part.text?.commandRuns || !label || !display || label[1] !== display[1] || label[2] !== unit)
          return null;
        return `${label[1]} ${label[2]}${label[1] === '1' ? '' : 's'} ago`;
      }));
    return labels.length === 1 ? publicationAge(labels[0]) : null;
  };
  // Persist normalized pagination commands, never request headers or bodies.
  const pageCommand = cmd => cmd.continuationCommand
    ? {continuationCommand: {token: cmd.continuationCommand.token, request: cmd.continuationCommand.request}}
    : command('browse', 'browseEndpoint', {browseId: cmd.browseEndpoint.browseId,
        ...(cmd.browseEndpoint.params ? {params: cmd.browseEndpoint.params} : {})});
  const catalogFailure = (channel, reason, extra = {}) => attention('Uncertain channel catalog: ' + channel.name + ' (' + reason + ')',
    {code: 'catalog_inconsistent', channel_id: channel.id, reason, ...extra});
  const catalogRows = (data, channel) => {
    const owner = data.metadata?.channelMetadataRenderer?.externalId;
    if (owner && owner !== channel.id) throw catalogFailure(channel, 'response_owner_mismatch');
    const tabs = data.contents?.twoColumnBrowseResultsRenderer?.tabs;
    if (tabs) {
      const selected = tabs.map(t => t.tabRenderer).filter(t => t?.selected);
      if (selected.length !== 1 || selected[0].title !== 'Videos')
        throw catalogFailure(channel, 'response_is_not_videos_tab', {selected_tab: selected[0]?.title || null});
    }
    const rows = new Map();
    roots(data).forEach(root => walk(root, x => {
      if (x.continuationItemRenderer && !nextCommands([x]).length)
        throw catalogFailure(channel, 'unrecognized_continuation');
      if (x.richSectionRenderer || x.shortsLockupViewModel) return false;
      let v;
      if (x.videoRenderer) {
        const r = x.videoRenderer;
        v = {id: r.videoId, title: text(r.title), percent: progress(r),
          publication_age: publicationAge(text(r.publishedTimeText))};
      } else if (x.lockupViewModel) {
        const r = x.lockupViewModel;
        if (r.contentType !== 'LOCKUP_CONTENT_TYPE_VIDEO') throw catalogFailure(channel, 'unexpected_video_renderer');
        v = {id: r.contentId, title: text(r.metadata?.lockupMetadataViewModel?.title), percent: progress(r, true),
          publication_age: lockupAge(r)};
      }
      if (v) {
        if (!v.id || !v.title) throw catalogFailure(channel, 'incomplete_video_renderer');
        rows.set(v.id, {...v, channel_id: channel.id, kind: 'normal', publication: null,
          duration: null, playable: true, listing_fresh: true});
        return false;
      }
    }));
    return [...rows.values()];
  };
  const scanChannel = async (channel, needed = null, previous = null, maxAgeMs = 0) => {
    if (needed && !needed.size) return {id: channel.id, complete: true, pages: 0, videos: [], scope: 'manual_entries_only'};
    const d = await request(browse(channel.id));
    if (d.metadata?.channelMetadataRenderer?.externalId !== channel.id) throw Error('Channel identity mismatch');
    const tabs = d.contents?.twoColumnBrowseResultsRenderer?.tabs?.map(t => t.tabRenderer).filter(Boolean);
    if (!tabs?.length) throw catalogFailure(channel, 'unknown_channel_tabs');
    const tab = tabs.find(t => t.title === 'Videos');
    if (!tab) return {id: channel.id, complete: true, pages: 0, videos: [], page_index: [], scan: 'full',
      publication_age_version: publicationAgeVersion,
      scanned_at: new Date().toISOString(), full_scanned_at: new Date().toISOString(), available_tabs: tabs.map(t => t.title)};
    if (tab.endpoint?.browseEndpoint?.browseId !== channel.id)
      throw catalogFailure(channel, 'videos_endpoint_owner_mismatch');
    const age = Date.now() - Date.parse(previous?.full_scanned_at);
    // Old catalogs contain ages rejected by the earlier parser. Refresh all
    // listing pages once after an evidence-version change; player metadata,
    // known IDs and playlist history remain reusable and untouched.
    const incremental = !needed && previous?.complete && !previous.scope && previous.id === channel.id &&
      previous.publication_age_version === publicationAgeVersion &&
      previous.page_index?.length && age >= 0 && age < maxAgeMs;
    const old = new Map((incremental ? previous.videos : []).map(v => {
      const {listing_unavailable, ...known} = v; // Skips apply to one collection, not future runs.
      return [v.id, {...known, listing_fresh: false}];
    }));
    const rows = new Map(), index = [], seen = new Set();
    let cmd = pageCommand(tab.endpoint), count = 0, recognized = 0, ended = false;
    while (cmd) {
      const key = JSON.stringify(cmd);
      if (seen.has(key) || count >= 300) throw catalogFailure(channel, 'pagination_not_terminated');
      seen.add(key);
      const data = await request(cmd), page = catalogRows(data, channel);
      recognized += page.length; count++;
      index.push({command: cmd, ids: page.map(v => v.id)});
      page.forEach(v => { if (!needed || needed.has(v.id)) rows.set(v.id, v); });
      q.job.progress = {phase: channel.name, pages: count, incremental: !!incremental};
      const next = nextCommands(roots(data));
      if (next.length > 1) throw catalogFailure(channel, 'ambiguous_pagination');
      if (!next.length) { ended = true; break; }
      if (needed && [...needed].every(id => rows.has(id))) break;
      if (incremental && page.length && page.every(v => old.has(v.id))) break;
      cmd = pageCommand(next[0]);
    }
    if (!recognized) throw catalogFailure(channel, 'no_recognized_videos');
    // Reaching the end is a full audit. Otherwise retain the earlier complete
    // inventory, explicitly marking untouched listing/progress evidence stale.
    const merged = incremental && !ended ? old : new Map();
    rows.forEach((v, id) => merged.set(id, v));
    const commands = new Set(index.map(p => JSON.stringify(p.command)));
    return {id: channel.id, complete: true, pages: count, videos: [...merged.values()],
      publication_age_version: publicationAgeVersion,
      page_index: [...index, ...(incremental && !ended ? previous.page_index.filter(p => !commands.has(JSON.stringify(p.command))) : [])],
      full_scanned_at: incremental && !ended ? previous.full_scanned_at : new Date().toISOString(),
      scanned_at: new Date().toISOString(),
      scan: incremental && !ended ? 'incremental' : 'full',
      ...(needed ? {scope: 'manual_entries_only'} : {})};
  };
  q.channel = async (channel, needed = null, previous = null, maxAgeMs = 0) => {
    const first = await scanChannel(channel, needed, previous, maxAgeMs);
    if (needed || !previous?.complete || previous.scope || previous.id !== channel.id) return first;
    const rows = new Map(first.videos.map(v => [v.id, v]));
    const missing = previous.videos.filter(v => !rows.has(v.id));
    // Even matching full browse scans are not evidence of deletion. Keep known
    // IDs, but never admit an absent video using its old watch progress.
    for (const v of missing) rows.set(v.id, {...v, listing_fresh: false, listing_unavailable: true});
    return {...first, videos: [...rows.values()], discovery_complete: !missing.length,
      ...(missing.length ? {warnings: [{code: 'catalog_omissions', channel_id: channel.id,
        retained_count: missing.length, message: 'Known videos omitted by YouTube were retained; unverified candidates are skipped this run.'}]} : {})};
  };
  q.refreshCatalog = async (channel, catalog, ids) => {
    if (catalog.id !== channel.id || !catalog.complete || !Array.isArray(ids) || !ids.length)
      throw Error('Invalid catalog refresh');
    // Stored continuation commands are discovery history, not reusable cursors.
    // One full fresh-root chain refreshes all candidate progress for this channel
    // so successive vacancies cannot trigger repeated scans of the same backlog.
    const full = await q.channel(channel, null, catalog);
    const old = new Map(catalog.videos.map(v => [v.id, v]));
    full.videos = full.videos.map(v => {
      const saved = old.get(v.id);
      return saved ? {...saved, ...v, publication: saved.publication, duration: saved.duration,
        playable: saved.playable, listing_unavailable: v.listing_unavailable === true} : v;
    });
    return full;
  };
  q.metadata = async (id, contentWarnings = 'stop') => {
    const d = await request(command('player', 'watchEndpoint', {videoId: id}));
    const v = d.videoDetails, m = d.microformat?.playerMicroformatRenderer;
    if (v?.videoId && v.videoId !== id) throw Error('Player identity mismatch');
    const status = d.playabilityStatus?.status;
    const screen = d.playabilityStatus?.errorScreen?.playerErrorMessageRenderer;
    const availability = {status: status || null, reason: d.playabilityStatus?.reason || '',
      error_reason: text(screen?.reason), subreason: text(screen?.subreason)};
    const explanation = [availability.reason, availability.error_reason, availability.subreason].filter(Boolean).join(' — ');
    const contentWarning = status === 'CONTENT_CHECK_REQUIRED';
    const membersOnly = status === 'UNPLAYABLE' && (availability.reason ===
      'Join this channel to get access to members-only content like this video, and other exclusive perks.' ||
      /^This video is available to this channel's members on level: [^\r\n]{1,200} \(or any higher level\)\. Join this channel to get access to members-only content and other exclusive perks\.$/.test(availability.reason));
    if (membersOnly) availability.restriction = 'members_only';
    // UNPLAYABLE also carries temporary session failures. It cannot establish
    // unavailable inventory, even if publication/duration are returned with it.
    if (status !== 'OK' && !membersOnly && !(contentWarning && contentWarnings === 'include')) {
      const limited = /try again later|too many requests|rate.?limit/i.test(explanation);
      throw attention('Playback needs attention for ' + id + ': availability check incomplete (' +
        (status || 'missing status') + ')' + (explanation ? ': ' + explanation : ''), {
        code: limited ? 'rate_limited' : 'availability_incomplete', video_id: id, ...availability});
    }
    const raw = m?.publishDate;
    if (!v?.channelId || !raw || !Number(v.lengthSeconds))
      throw Error('Publication, duration or owner unavailable: ' + id);
    // Eligibility never accepts the warning: the only request is player metadata.
    // Login challenges and unfamiliar statuses still require attention.
    return {id, channel_id: v.channelId, publication: raw,
      duration: Number(v.lengthSeconds), playable: !membersOnly, availability,
      metadata_checked_at: new Date().toISOString(),
      content_warning: contentWarning,
      unlisted_normal: v.videoId === id && m.isUnlisted === true &&
        m.isShortsEligible === false && v.isLiveContent === false && !v.isLive && !v.isUpcoming,
      is_live: v.isLiveContent === true || v.isLive === true || v.isUpcoming === true};
  };
  q.exclusions = async (channel, needed) => {
    const root = await request(browse(channel.id));
    if (root.metadata?.channelMetadataRenderer?.externalId !== channel.id) throw Error('Exclusion channel identity mismatch');
    const tabs = root.contents?.twoColumnBrowseResultsRenderer?.tabs?.map(t => t.tabRenderer).filter(Boolean);
    if (!tabs) throw Error('Unknown exclusion tabs');
    const found = {};
    for (const tab of tabs.filter(t => ['Shorts', 'Live'].includes(t.title))) {
      await pages(await request(tab.endpoint), rs => rs.forEach(r => walk(r, x => {
        let id;
        if (tab.title === 'Shorts' && x.shortsLockupViewModel) {
          const e = x.shortsLockupViewModel.onTap?.innertubeCommand;
          if (e?.commandMetadata?.webCommandMetadata?.webPageType !== 'WEB_PAGE_TYPE_SHORTS' || !e.reelWatchEndpoint?.videoId)
            throw Error('Unknown Shorts renderer');
          id = e.reelWatchEndpoint.videoId;
        }
        if (tab.title === 'Live') id = x.videoRenderer?.videoId ||
          (x.lockupViewModel?.contentType === 'LOCKUP_CONTENT_TYPE_VIDEO' ? x.lockupViewModel.contentId : null);
        if (id && needed.has(id)) found[id] = tab.title === 'Shorts' ? 'short' : 'live';
        if (id) return false;
      })), channel.name + ' ' + tab.title);
    }
    return found;
  };
