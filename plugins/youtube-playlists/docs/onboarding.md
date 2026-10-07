# First-time setup

This guide is for the agent. The user describes what they want in ordinary
language; the agent handles commands, identities and external YAML.

1. Read the installed skill and browser-access reference. Run `doctor` with an
   existing Python 3.11+ runtime. Use explicit `setup` if dependencies are missing.
   Stop and explain missing runtime/browser access rather than installing a
   system runtime, prescribing a browser plugin or changing permissions yourself.
2. Check for existing settings. If present, identify the user's intended profile
   and preserve its bindings, rules and history. This starter flow is for a new
   profile, not an automatic reset for someone upgrading.
3. Observe the active YouTube owner and resolve the few channels the user chooses
   to their stable IDs. Use observed page identity/channel links or YouTube's
   account/channel settings. Do not ask them to paste credentials, accept a
   guessed account, choose all subscriptions, or infer policy from video titles.
4. Propose a separate private playlist, a small number of chosen channels, and
   the starter rules below. Get the user's agreement on the actual creation or
   reuse. Create through the chosen available browser controller, or reuse an
   explicitly selected playlist. Verify the owner, playlist ID, private visibility
   and complete empty membership before using it as a fresh sample. Do not
   substitute Watch Later. Existing nonempty targets need a normal preview of
   their existing entries and applicable decisions rather than an empty-sample
   assumption.
5. Initialize local settings with the observed bindings. This command performs
   no browser operation and does not establish that an account/target is valid:

   ```text
   PYTHON PLUGIN_ROOT/scripts/run.py init-config --account-channel-id OWNER_ID --playlist-id PLAYLIST_ID --playlist-name "Chosen playlist name" --channel "SOURCE_ID=Chosen channel name"
   ```

   Add `--channel` for each chosen source. The command uses `development.yaml`
   in the external configuration directory. `--profile starter.yaml` chooses a
   different filename and `--directory /absolute/external/config` isolates a
   new profile when needed. It refuses Watch Later and invalid, unresolved or
   conflicting settings. Identical repeated initialization preserves the files.
   No cache, state database or playlist entry is created by this command.
6. Validate the saved profile and run `--config PATH refresh` without `--apply`.
   The collection verifies the actual account, ownership and playlist membership.
   Report counts, proposed removals/additions/order and any warnings or blockers.
   A cold channel scan may still be slow even with a small count limit; do not
   promise that a three-video queue needs only three metadata requests.
7. Apply only after authorization for the actual target and rules. Verify the
   final result and cleanup. Explain how another manual refresh refills watched
   slots; no scheduler is installed.

## Starter rules to propose

- Published within the last 30 days; choose the latest three eligible unwatched
  normal videos per selected channel.
- No time expiry. Partially watched videos remain eligible. Shorts, clips,
  live content and fully watched videos are excluded by the existing rules.
- Channels are unpinned, so selected videos from all of them are mixed by
  publication date, oldest first. Selection and viewing order are different.
- Unknown addition times use first observation; an observed returned dismissed
  video starts a new stay. Existing user conventions remain unchanged.
- Viewer-discretion warnings stop for attention by default. Do not change that
  choice or accept a content warning for the user automatically.

`init-config` accepts `--lookback`, `--maximum-count` and `--selection` for other
decided bounded starter choices. An all-history/unlimited request uses an
explicit validated edit afterward; the command never guesses those preferences.
The [complete fictional example](example.yaml), [configuration guide](configuration-examples.md)
and [schema](../youtube_playlist_manager/schemas/settings.schema.json) explain
the other choices.

## Moving to Watch Later

Switch only on the user's explicit request. Create a new external production
profile with `playlist_id: WL`, the same verified owner and chosen channel
rules, and a distinct account/playlist data directory. Reuse that account's
metadata cache if desired. Preserve the separate playlist and its state; a
configuration change does not migrate history. Preview Watch Later's actual
membership, including manual entries and any keep/remove decisions, before
an authorized apply. An unavailable starter playlist is not permission to
substitute Watch Later.
