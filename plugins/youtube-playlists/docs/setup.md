# Agent setup and command reference

These instructions are for the agent and maintainers. The agent checks the
existing runtime, invokes commands and connects an available browser controller.
Users request a preview or refresh in normal language; do not ask them to copy
these commands or implement the bridge. Browser-tool choice and installation
are outside this plugin's setup. Report missing access using the
[agent browser-access requirements](browser-control.md), without prescribing a
browser plugin.

Use an existing Python 3.11+ interpreter and the actual installed plugin root.
If none is available, report that prerequisite; do not install a system runtime.
The examples below use `PYTHON` and `PLUGIN_ROOT` as explanatory placeholders,
not names to copy literally. All script paths may be absolute; no source
checkout or particular working directory is required.

```text
PYTHON PLUGIN_ROOT/scripts/run.py doctor
PYTHON PLUGIN_ROOT/scripts/run.py setup
PYTHON PLUGIN_ROOT/scripts/run.py import-config --source /absolute/path/development.yaml
PYTHON PLUGIN_ROOT/scripts/run.py import-config --source /absolute/path/watch-later.yaml
PYTHON PLUGIN_ROOT/scripts/run.py doctor
```

Setup installs pinned wheel dependencies into a keyed virtual environment under
`~/Library/Application Support/info.komarovsky.codex-plugin-youtube-playlist-management/runtimes/`.
It uses no system installation. Another setup cannot use the same lock. A failed
new install is cleaned up; an interrupted incomplete environment requires explicit
`setup --repair`. Normal operations never install dependencies.

Import validates the source and copies its target and shared channel rules into
the external `config/` directory, with editor schemas. It verifies identical
resolved settings and retains the original storage paths. It does not move,
reset or open playlist databases. Repeating an identical import is harmless;
conflicting existing settings stop the import. Subsequent edits belong in the
external YAML, not the source checkout. Preserve comments when editing.

For a new user without settings, establish the intended account, development
playlist, channels and choices with them, then create external YAML against
[the schema](../youtube_playlist_manager/schemas/settings.schema.json). Never
invent bindings or silently substitute Watch Later. The CLI default is the
external `config/development.yaml`; a missing file stops safely.

Follow [first-time setup](onboarding.md) for the separate-playlist flow.
`init-config` creates local validated settings from explicit owner, playlist and
source-channel IDs without browser access or YouTube writes. It proposes a
30-day/latest-three window without expiry, preserves existing files, and uses
separate account/playlist history paths. Use `--help` for decided overrides;
review the rules and preview before applying. Existing profiles need no reset.

`doctor` checks local dependencies, the optional Safari installation and available config
files only. It does not open a browser or certify the signed-in account. `validate`
checks a chosen profile; a collection verifies its actual account and playlist.

One shared YouTube client uses JavaScript in the selected signed-in page. Normal
commands use the built-in Safari controller; another capable browser tool can
supply `--javascript-bridge DIRECTORY` before the command name. See
[agent browser-access requirements](browser-control.md) for capability checks
and the permissions relevant to the selected controller.
Existing YAML needs no migration, and browser selection does not change rules.

```text
PYTHON PLUGIN_ROOT/scripts/run.py --config /absolute/path/profile.yaml validate
PYTHON PLUGIN_ROOT/scripts/run.py --config /absolute/path/profile.yaml refresh
PYTHON PLUGIN_ROOT/scripts/run.py --config /absolute/path/profile.yaml refresh --apply
PYTHON PLUGIN_ROOT/scripts/run.py --config /absolute/path/profile.yaml status
PYTHON PLUGIN_ROOT/scripts/run.py --config /absolute/path/profile.yaml decisions
PYTHON PLUGIN_ROOT/scripts/run.py --config /absolute/path/profile.yaml recover
PYTHON PLUGIN_ROOT/scripts/run.py --config /absolute/path/profile.yaml analytics --days 30
```

Use the CLI's `--help` for further options. Analytics defaults to Europe/Lisbon;
select the intended timezone explicitly when needed. Each playlist has a
separate state directory. Configuration is policy, never operational history.

## Recovery and removal

For missing permissions, sign-in, content warnings, API changes or cooldowns,
inspect the reported blocker and saved diagnostic. Do not bypass it or repeat an
uncertain write. `recover` reads back a pending operation before further writes.
Each run checks the active session, client context, allowed requests and required
responses. A new YouTube JavaScript build alone does not stop the plugin. Actual
compatibility failures include a safe optional build identifier and failing stage
in the output and local logs, and explain that the plugin may need an update.
Sign-in failures, changed accounts, rate limits and network problems have their
own explanations. An API response that explicitly reports a logged-out session
is a sign-in failure, even if the page itself still appears signed in. Its
missing account header or private playlist does not establish an API change or
a deleted playlist. Repeatedly retrying cannot repair a changed API contract.
If YouTube reports that the configured playlist does not
exist, choose a replacement explicitly. Creating a replacement development
playlist uses a new state directory; the previous playlist's history stays intact.
The CLI hides command-owned Safari windows while it runs and reports cleanup
failures; borrowed windows and unrelated tabs remain open. If a command-owned
page disappears during read-only collection, it may recheck the account and
playlist and resume from saved metadata, with at most two recoveries. Playlist
edits are never replayed by that path. Do not prevent system sleep.
Safari may retain an invisible window record after its tabs close. A verified
hidden, zero-tab record counts as released and is logged explicitly. A visible
empty window, remaining tabs or an unverifiable close still needs attention.

Removing the plugin or updating its cache does not delete external config,
cache, history or environments. To erase local data, first agree the exact
external directories with the user and stop active runs. Erasing history loses
dismissals, addition clocks and recovery evidence; it does not undo YouTube
changes. Code rollback alone does not restore a database or playlist snapshot.
