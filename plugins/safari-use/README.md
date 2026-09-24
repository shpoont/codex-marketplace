# Safari Use

## Purpose

Let your agent use Safari to carry out web tasks in your existing browser
session. Use Safari Use to inspect pages and tabs, read visible content, click
visible controls and verify page changes without silently switching to another
window.

## Quick start

### Requirements

- Codex desktop or CLI with plugin support on macOS.
- Safari with **Allow JavaScript from Apple Events** enabled when a task needs
  page inspection or page-local actions.
- macOS Automation permission for the process running Codex or the helpers.
- No additional account, API credential, paid service or package install.

### Install

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git
codex plugin add safari-use@shpoont-public
```

Skip marketplace setup when Shpoont Public is already configured. Start a fresh
task after installation.

### Try it

```text
Use Safari to inspect this webpage and summarize its visible content.
```

Expected result: the task creates and records a dedicated Safari window ID,
summarizes the current page and keeps later browser work pinned to that same
window without intentionally bringing Safari forward.

## Capabilities

| Capability | Result and material effect |
| --- | --- |
| Inspect pages and tabs | Reads live window IDs, tab indexes, URLs and titles without choosing a window by frontmost position. |
| Read visible content | Runs page-local JavaScript in the current tab of one explicit window and returns structured observations. |
| Click visible controls | Finds a visible matching control, clicks one best candidate and reports what was acted on. This changes the page. |
| Verify page changes | Re-observes the targeted page or window after each action and reports the actual state. |
| Use signed-in sessions | Uses the browser session already available to Safari without copying or storing its credentials. |
| Inspect Tab Groups | Reads Safari's private tab metadata only as advisory state and cross-checks it with live windows. |

## Use the plugin

For a normal task, Safari Use creates a dedicated Safari window, lists all
windows, records the new window ID and keeps every later operation pinned to it.
It observes the page, performs one requested action and observes again before
claiming success.

You can explicitly ask it to reuse an existing Safari window:

```text
Use my Safari session to check this signed-in page without bringing Safari forward.
```

Because an existing window may contain signed-in or private state, identify the
intended window and approve reuse explicitly. If the requested work would need
another existing window or would require Safari to steal focus, the plugin stops
and asks instead of switching silently.

For an end-to-end browser task:

```text
Use Safari to click the visible Continue button and verify the result.
```

The task should report URLs, titles and concrete changed state while avoiding
sensitive page content in its output.

## Data and effects

- **Reads:** live Safari window and tab metadata; the current page's DOM and
  JavaScript-visible state when page probes are used; optionally Safari's local
  `SafariTabs.db` metadata in read-only mode for advisory Tab Group identity.
- **Changes:** requested page state through JavaScript or clicks, and Safari
  windows when a dedicated window is created or closed. A click can trigger the
  same account or service action it would trigger manually.
- **Existing sessions:** Safari cookies and signed-in state remain in Safari.
  The plugin does not copy or store those credentials, but page actions can use
  the session already available to Safari.
- **External transmission:** none added by this plugin. Safari loads the sites
  you visit, and Codex processes observations under the host's existing model
  and retention settings.
- **Local storage and telemetry:** no plugin-specific data store or telemetry.
  Temporary JavaScript files are removed by the helpers. Safari and Codex may
  retain their own history.
- **After removal:** page changes, account actions, Safari history and any
  windows already created can remain. Removing the plugin does not undo them.

## Limitations

- Safari only; other browsers and non-macOS platforms are outside the supported
  scope.
- JavaScript probing needs Safari's Apple Events setting and macOS Automation
  permission. Resolve a denied permission instead of treating it as page
  success.
- A JavaScript helper cannot run in a real zero-tab Safari window. Window listing
  remains valid and reports that state explicitly.
- Safari can keep a zero-tab window object after close. The
  `empty_window_persisted` classification is a cleanup blocker, not success.
- Named Tab Group identity comes from a private Safari database that may lag or
  change. It is never modified and ambiguous mappings remain uncertain.
- Page structure can change. A missing or ambiguous visible control requires a
  new observation; the plugin does not claim a click that it did not verify.
- Some workflows may require Safari to become frontmost. The plugin stops for
  explicit approval before doing that.

## Update, removal and recovery

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin add safari-use@shpoont-public
codex plugin remove safari-use@shpoont-public
```

Start a fresh task after updating. Do not enable multiple copies of Safari Use
together because they expose the same skill name. Removal deletes the installed
package but does not undo browser or account changes already made.

If an update is unusable, stop browser work, remove the plugin and report the
version and sanitized failure. After maintainers confirm marketplace recovery,
upgrade the marketplace, reinstall and verify a fresh harmless task before
resuming consequential actions.

## Support

Report problems through [public marketplace Issues](https://github.com/shpoont/codex-marketplace/issues).
Include plugin version, Codex version, macOS and Safari versions, the expected
result, the actual result and a minimal sanitized example. Do not attach cookies,
credentials, personal page data, private instructions or raw traces.

## Version and license

Current version: `0.1.1`. See the [public changelog](CHANGELOG.md) for user-visible
changes and required actions.

Copyright © 2026 Shpoont. Distributed under the [MIT License](LICENSE).

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
