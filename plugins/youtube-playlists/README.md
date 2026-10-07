# YouTube Playlists

## Purpose

Organize a configured YouTube viewing queue with channel rules, local history
and verified updates. Use it to build channel backlogs, maintain rolling windows,
order videos, remove watched entries and understand why each item is present.
It runs on demand and installs no scheduler.

## Quick start

### Requirements

- Codex desktop on macOS with plugin support.
- An existing Python 3.11 or newer runtime; the agent checks and uses it.
- A browser signed in to the intended YouTube account, using the English
  YouTube interface, with an available browser-control tool that can execute
  JavaScript in the page.
- No YouTube API key, exported cookie, connector, payment or subscription is required.

Ask the plugin to check your available browser access. Some controllers require
advanced permissions; the agent explains the specific permission if needed.
Browser-tool choice and installation are up to you. The plugin does not require
a particular browser plugin. Credentials remain in the selected browser.

### Install

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git
codex plugin add youtube-playlists@b2a48b
```

Skip marketplace setup when `b2a48b` is already configured. Start a
fresh task after installation. The marketplace repository URL still uses the
GitHub owner `shpoont`; Codex identifies the catalog as `b2a48b`.

### Try it

```text
Set up a separate viewing playlist with a few channels I choose.
```

Expected result: guided setup of a separate private playlist with a few channels
that you choose, followed by a preview of the proposed videos and order. Setup
asks before creating the playlist; adding/removing/reordering videos requires a
separate authorized apply. Existing users can request a preview of their existing
profile instead.

The starter proposal selects the latest three eligible unwatched videos per
chosen channel published in the last 30 days, with no expiry. They are mixed by
publication date, oldest first. You can change those rules before applying.
See [configuration examples](docs/configuration-examples.md).

## Capabilities

| Capability | Result and material effect |
| --- | --- |
| Preview playlist changes | Collects current evidence and saves a plan without changing YouTube. |
| Apply channel rules | Adds, removes and retains eligible videos only after an explicitly authorized apply. |
| Organize viewing order | Places pinned groups first and maintains the configured viewing order with verified moves. |
| Resolve video exceptions | Presents concrete keep/remove decisions and records the selected exception locally. |
| Recover uncertain writes | Reads YouTube and the durable journal before deciding whether any further action is safe. |

## Use the plugin

1. Ask it to set up a separate playlist or use/import your existing settings.
   It validates the YAML and keeps personal configuration outside the plugin.
   Your existing settings and history are preserved; starter choices do not
   replace them.
2. Preview the configured target. Review proposed additions, removals, moves,
   decisions and blockers. A preview authorizes no live write.
3. Ask to refresh the configured playlist only when you want the current plan
   applied. The deterministic runtime rechecks evidence, writes in bounded
   batches and verifies the final membership and order.
4. When the result needs attention, answer the reported choice or investigate
   the diagnostic. The plugin does not invent a fallback route.
5. Move to Watch Later only when you explicitly request it. That profile has its
   own history; the separate playlist and its history remain intact. The first
   Watch Later preview accounts for existing manual entries and any decisions.

Representative requests:

```text
Refresh my configured YouTube playlist and verify the final order.
```

```text
Explain why this video was added, removed, or placed here.
```

See [channel rules](docs/rules.md) for configuration behavior. Technical setup
and commands are in the [agent reference](docs/setup.md); the agent handles them.

## Data and effects

- **Reads:** the configured YouTube account, subscriptions, channel catalogs,
  playlist membership, video metadata and watch progress through the selected browser page; local
  YAML, cache, history, plans, journals and diagnostics.
- **Changes:** the selected YouTube playlist only after an authorized apply;
  local configuration only after an authorized edit or import; local operational
  history during validation, collection, preview, apply and recovery.
- **External transmission:** authenticated YouTube reads and writes remain in
  the signed-in browser session. Dependency setup downloads pinned wheels from PyPI.
- **Accounts and credentials:** a signed-in YouTube account in the selected browser. The plugin
  neither exports cookies nor stores credentials.
- **Storage and retention:** settings, cache, playlist history, plans, logs and
  the dependency runtime live under
  `~/Library/Application Support/info.komarovsky.codex-plugin-youtube-playlist-management/`,
  or the external paths selected by the user's settings. They remain until the
  user removes them.
- **Telemetry:** operational metrics and diagnostics are stored locally. There
  is no plugin-owned remote telemetry service.
- **After removal:** external settings and history, prior YouTube changes and
  Codex host history remain. Removing the plugin does not undo them.

Diagnostics can contain personal channel and video information. Review them
before sharing.

## Limitations

- The shared client is browser independent. Safari control is built in for
  macOS; another capable browser tool can supply the same page execution.
  A restricted evaluator cannot replace main-page
  execution. Stable releases require installed acceptance in both Safari and
  Chrome using the shared client. Other browsers, operating systems and locales
  still need their own acceptance checks.
- YouTube's private web API can change. New page builds remain usable while the
  required session, request and response checks pass. Actual incompatibilities
  stop affected work and report the failure; they may require a plugin update.
- Cold catalog scans and rate limits can make a run slow. Changes between two
  observations cannot always be reconstructed.
- Catalog discovery uses best effort: known videos omitted by YouTube remain
  cached, and candidates without current watch status wait for a later run.
  A scoped catalog failure pauses that channel's additions and retention changes
  while other channels update. Successful runs report these gaps as warnings;
  they can temporarily miss uploads, leave slots empty or select an approximate
  oldest/latest set. Account checks, complete playlist membership, manual
  dismissals and write verification remain strict.
- A preview never authorizes writes. A missing or ambiguous target, unresolved
  rule, uncertain write, account mismatch or cleanup failure requires attention.
- The plugin cannot roll back a completed YouTube change or a database merely by
  installing an older package.

## Update, removal and recovery

Update the catalog and reinstall its current package:

```sh
codex plugin marketplace upgrade b2a48b
codex plugin add youtube-playlists@b2a48b
```

Start a fresh task after updating. If another copy is installed, identify it,
verify the intended copy against your existing settings, and enable only one
copy. The agent can help remove an explicitly selected preceding installation.
The stable skill is `$manage-youtube-playlists`; the command is `youtube-playlists`.
Configuration, cache and history stay in the existing external namespace.
Updating or changing the installation does not move data or edit YouTube.

Remove the plugin with:

```sh
codex plugin remove youtube-playlists@b2a48b
```

Removal leaves external settings and history intact. To remove that data too,
first confirm the active paths in your YAML, then delete those external files
separately; this cannot undo YouTube changes.

After an uncertain playlist write, use the same profile and run `recover` before
collecting or applying again. If an update is unusable, remove it and report the
version and failure. After maintainers restore or republish the marketplace
package, upgrade the marketplace, reinstall and verify it in a fresh task.

## Support

Report problems through the [support issue tracker](https://github.com/shpoont/codex-marketplace/issues).
Include plugin version, Codex version, macOS version, expected result, actual
result, run ID and a minimal sanitized example. Do not attach credentials,
cookies, personal playlist data, private instructions or raw traces.

## Version and license

Check the version in the installed plugin's details. See the
[public changelog](CHANGELOG.md) for changes and required user actions.

The [installation-and-use license](LICENSE) permits installation and use of the
plugin. It grants no permission to modify or redistribute the plugin. Editing
your personal YAML settings and operational data remains ordinary permitted use.
[Third-party notices](THIRD_PARTY_NOTICES.md) describe separately licensed
material; dependencies are downloaded into the external runtime.

The queue icon is original vector artwork created for this plugin and covered
by its installation-and-use license. YouTube and Google names and content remain
their respective owners' property. This independent plugin is not affiliated
with, endorsed by or sponsored by YouTube or Google.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
