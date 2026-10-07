# Changelog

User-visible changes to YouTube Playlists and any action required when installing or updating it.

## 0.3.2 — 2026-10-07

- Read the installed release version from plugin details; remove the duplicated
  README version label that became stale during candidate preparation.
- Browser behavior is unchanged from candidate 0.3.1. No configuration or
  operational-history migration is required.

## 0.3.1 — 2026-10-07

- Support browser tools that create an empty tab and then navigate it, including
  Chrome's current documented API. Keep URL-at-creation tools supported.
- Record the exact tab before navigation, preserve setup diagnostics and verify
  cleanup after failed navigation. Changed tabs remain untouched; uncertain
  actions are not repeated.
- Playlist policy, browser permissions and operational history are unchanged.
  No configuration or data migration is required.

## 0.3.0 — 2026-10-07

- Replace the official YouTube icon with original queue artwork. Plugin identity and saved-data locations stay unchanged.
- Prepare public installation and support instructions, explicit installation-and-use terms, and bundled configuration examples.
- Start first-time setup with a separate playlist and chosen channels. Create local validated settings without overwriting existing settings, then preview before applying changes. Watch Later remains an explicit later choice with separate history.
- Starter settings propose the latest three eligible videos per chosen channel published in the last 30 days, with no expiry and unpinned oldest-first viewing. Users review or change these settings before applying.
- Existing playlist rules, browser permissions and stored history are preserved; no scheduler or data migration is introduced.

## 0.2.16 — 2026-10-07

- Include the generic browser-tool connection and verified cleanup fixes
  described below. Version 0.2.15 was not published because release validation
  exposed a timing-dependent test; its test clock is now deterministic.
- Browser behavior, channel rules and operational history are unchanged from
  the tested 0.2.15 candidate. No configuration or data migration is required.

## 0.2.15 — 2026-10-07

- Bundle a generic browser-tool connection that creates the intended URL directly
  and records its exact tab before acquiring JavaScript access.
- Preserve the first setup failure as creation, connection or binding diagnostics;
  keep cleanup errors separate and never infer absence after uncertain creation.
- Provide sequential bounded bridge servicing without background file watchers.
  Agents supply the available tool's documented primitives; YouTube logic and
  playlist policy remain shared. No configuration or history migration.

## 0.2.14 — 2026-10-06

- Verify temporary-page disappearance with bounded fresh reads after a single
  close request, including delayed closure and lost acknowledgements.
- Preserve and relinquish changed pages. Keep disconnected or unverifiable pages
  tracked with lifecycle receipts and explicit read-only cleanup reconciliation.
- Report cleanup failure separately from completed playlist work, retain the
  original failure, and never repeat playlist edits to resolve browser cleanup.
- Keep Safari and Chrome acceptance mandatory before stable publication. No
  playlist-rule or operational-history migration is required.

## 0.2.13 — 2026-10-06

- Move YouTube startup, collection, cache coordination, polling and edits into
  one browser-independent client with an injected main-page JavaScript runner.
- Keep the existing Safari controller and add an explicit local controller
  bridge for capable browser tools, with optional bounded CDP transfer.
- Document advanced browser permissions. Keep existing YAML valid; browser
  identity is an optional legacy hint, not a new channel rule. No data migration.
- Reject expired or uncertain bridge requests without replay, preserve changed
  pages and keep browser selection in recovery/inspection command suggestions.
- Apply one timeout budget across all CDP transfer steps and stop later steps
  when the caller abandons a request. Keep browser-tool acquisition user-owned;
  the agent checks capabilities and explains only relevant advanced permissions.

## 0.2.12 — 2026-10-05

### Changed

- Use the original full-color YouTube icon for the plugin card, composer and skill icons, preserving its artwork, proportions and clear space. Include artwork attribution and independent-project notice.
- Playlist behavior, channel rules, permissions, dependencies and stored history are unchanged. No configuration or data migration is needed.

## 0.2.11 — 2026-10-04

### Changed

- Renamed the product to **YouTube Playlists**, the plugin ID and standalone console command to `youtube-playlists`.
- Preserved the `$manage-youtube-playlists` skill entrypoint and all playlist rules, lifecycle behavior, saved-plan format and dependency versions.
- Kept configuration, runtimes, cache, history, plans and journals in the existing `info.komarovsky.codex-plugin-youtube-playlist-management` namespace. No data move or reset is required.
- Install `youtube-playlists@b2a48b`, enable it for verification against existing settings, then remove the old `manage-youtube-playlists` copy after verifying it. Enable only one copy because the skill entrypoint is shared. The rename itself does not update any YouTube playlist.

## 0.2.10 — 2026-10-01

### Fixed

- Include the expiry of queued count-window overflow in a saved preview's validity deadline. A removal can change from retryable overflow to terminal expiry even when the playlist action IDs remain the same; the preview now advertises that boundary correctly.
- Account for known scheduled uploads when their publication can change the selected window or an existing entry's treatment. Preserve metadata-saving checks for full oldest-first and held-refill windows, inclusive lookback limits, and exceptions or paused channels.
- Explain rejected previews with their deadline, changed fields and a bounded sample of affected videos and removal reasons. Retain sanitized diagnostics in ordinary reports and local run logs; all existing apply and recovery guards remain strict.
- No YAML or history migration is needed. Update the marketplace plugin, start a fresh task and create a new preview. Saved plans from earlier versions cannot be applied under the updated planner.

## 0.2.9 — 2026-10-01

### Fixed

- Restore authenticated requests in Safari sessions with only YouTube's third-party signing cookie. Generate the main authorization signature as well as the third-party signature, and follow YouTube's first matching cookie rule. Credentials remain inside the page; account, playlist and session checks remain strict.
- Report explicitly logged-out API responses as sign-in failures before interpreting missing account headers or private playlists. A successful HTTP response can still be unauthenticated, even when the page appears signed in.
- No YAML or history migration is needed. Update the marketplace plugin and start a fresh task before refreshing your playlist.

## 0.2.8 — 2026-09-30

### Fixed

- Recognize matching compact/full upload-age pairs such as `1d ago` / `1 day ago` in YouTube's Videos listings. Unknown, conflicting or ambiguous labels still require normal metadata checks; approximate ages remain conservative exclusion bounds rather than exact publication dates.
- Refresh catalog evidence from older parser versions across all listing pages once, then resume incremental discovery. Keep previously fetched player metadata and playlist history. Queue count limits still cannot guarantee an equal number of metadata requests when evidence overlaps or is unknown; request pacing and channel policies are unchanged.

## 0.2.7 — 2026-09-30

### Changed

- Channel discovery now uses best effort. Known videos omitted by YouTube remain cached, including after repeated matching omissions; this does not record a dismissal. Candidates without current watch status are skipped for that run and reconsidered later.
- A scoped inconsistent channel catalog pauses that channel's additions and retention changes while other channels update. Independently verified fully watched entries can still be cleaned up. Successful refreshes include concise warnings and saved diagnostics for discovery gaps.
- Candidate watch checks follow one fresh-root pagination chain for the channel instead of replaying cached continuation tokens. This may read more listing pages, but avoids repeated scans while filling successive vacancies and reuses verified metadata.
- Complete target membership, account checks, manual removals, rate limits, request compatibility and verified writes remain strict. No YAML change is needed. Saved plans from older versions require a fresh preview.

## 0.2.6 — 2026-09-28

### Changed

- New YouTube JavaScript builds no longer block a compatible session. The plugin owns its limited API request construction and session-bound signing inside Safari, without minified native request builders or a per-build allowlist.
- Each run checks the active session, client context, allowed requests and required responses. Real incompatibilities stop the update and explain that the plugin may need an update. Sign-in failures, account changes, throttling and network failures retain separate explanations.
- Request signing and credentials remain inside the current Safari page. The client binds the session index, user and delegated account, and checks them before dispatch, including after asynchronous signing.
- Existing playlist ownership, ordering, journal, readback and uncertain-write recovery remain in force. A failure after dispatch can leave partial or uncertain work; recover from the journal before another update. No configuration change is required.

## 0.2.5 — 2026-09-28

### Fixed

- Videos removed solely to enforce a channel's count limit remain eligible for later selection. Watching or dismissing a selected video can now refill the window from previously queued overflow as well as never-added candidates.
- Confirmation, response-loss recovery and lifecycle migration preserve this distinction. Manual/explicit dismissals, time expiry, other terminal removals and kept exceptions retain their existing behavior.
- The first complete observation repairs old count-overflow dismissals only when saved plans, observations and confirmed removals prove the cause. Later observed returns, later removals and missing or ambiguous evidence remain protected. A local SQLite backup and repair event preserve the audit trail. Preview/collection can update this local history, but make no YouTube edits without an authorized apply.
- Saved plans from earlier versions must be collected and planned again. Update the marketplace plugin and start a fresh Codex task before refreshing; no YAML change or manual dismissal reset is required.

## 0.2.4 — 2026-09-26

### Changed

- Show **Leon.id Komarovsky** as both the plugin author and developer in the Codex listing.
- Update current marketplace installation and update instructions.
- Playlist rules, runtime behavior and external configuration/history are unchanged. Install this version from the marketplace after that marketplace is available; verify the new copy before removing any prior installation.

## 0.2.3 — 2026-09-25

### Fixed

- Added reviewed adapter profiles for YouTube's 25 September 2026 page builds, including their renamed native registries, transport tokens, signers, configuration getters, endpoint maps and request-builder methods.
- Hide command-owned Safari windows during a run and recover read-only collection up to twice if its page disappears, rechecking the account and playlist while reusing saved metadata. Playlist edits are never replayed by this recovery.
- Kept unknown-build rejection, in-page session signing, the request target allowlist and verified playlist writes unchanged.

## 0.2.2 — 2026-09-22

### Fixed

- Prevented large, read-only Safari status and catalog-checkpoint transfers from failing at the ordinary 60-second AppleScript command deadline. These safe polling reads now have a bounded five-minute deadline, while command starts and playlist mutations retain the shorter limit and are never replayed automatically.
- Reported AppleScript host timeouts separately from missing permissions or changed pages, including the bounded timeout value without exposing page data.

## 0.2.1 — 2026-09-21

### Fixed

- Added a reviewed adapter profile for YouTube's 21 September 2026 page build, including its renamed native registry, transport token, signer, configuration getter, endpoint map and request-builder method.
- Preserved exact-build rejection, in-page session signing, endpoint allowlisting and safe startup diagnostics. No playlist rule or external-data format changed.

## 0.2.0 — 2026-09-20

### Changed

- Renamed the plugin ID to `manage-youtube-playlists`, the primary skill to `manage-youtube-playlists`, and the console command to `manage-youtube-playlists`.
- Kept the display name **Manage YouTube Playlists** and preserved the established `info.komarovsky.codex-plugin-youtube-playlist-management` application-support namespace so existing settings, history and cache remain available.
- Users updating from 0.1.9 needed to install the renamed `manage-youtube-playlists` identity from their existing distribution, verify that it loaded their settings, and then remove the prior `youtube-playlist-management` installation.
- After updating, start a fresh Codex task so the new plugin and skill identities load.

Playlist rules and YouTube write behavior are unchanged. Version 0.1.10 was an unpublished candidate under the superseded identity and was never released.

## 0.1.9 — 2026-09-20

### Added

- Added a task-oriented quick start, capability summary, data-and-effects disclosure, recovery guidance and public changelog.
- Added recognizable plugin and skill icons plus a clear skill card for playlist management.

### Changed

- Rewrote marketplace descriptions, capabilities and starter prompts for faster scanning.
- Moved release history out of the consumer README into this changelog.
- After updating, start a fresh Codex task so the current listing and skill metadata load.

Playlist rules, external settings, history and YouTube write behavior are unchanged.

## 0.1.8 — 2026-09-19

### Changed

- Changed the advertised plugin ID from `codex-plugin-youtube-playlist-management` to `youtube-playlist-management` while retaining the prefixed source-repository name and existing external data namespace.
- Users of 0.1.7 or earlier under the historical ID needed to remove that qualified installation and install the renamed `youtube-playlist-management` identity from their existing distribution.

## 0.1.7 — 2026-09-19

### Added

- Added the canonical private GitHub repository to the plugin card and the standard distribution disclaimer.

## 0.1.6 — 2026-09-19

### Fixed

- Added a reviewed adapter profile for YouTube's 19 September 2026 page build, including its renamed endpoint-map and request-builder methods.
- Preserved fail-closed behavior for unknown builds and startup diagnostics without native exception contents or credentials.

## 0.1.5 — 2026-09-18

### Fixed

- Classified Safari's retained invisible, zero-tab window record as released after verified cleanup.
- Kept visible, nonempty or unverifiable windows as attention-required failures.

## 0.1.4 — 2026-09-17

### Fixed

- Added reviewed support for YouTube's 17 September 2026 page build.
- Added clearer adapter-startup and missing-playlist diagnostics.

## 0.1.3 — 2026-09-16

### Added

- Published the first portable private plugin package with its skill, deterministic runtime, pinned dependency setup and external settings import.
- Kept configuration, history, cache and operational data outside the installed package under the namespaced application-support directory.
