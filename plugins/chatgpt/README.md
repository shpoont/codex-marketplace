# ChatGPT

## Purpose

Use native ChatGPT conversation tools first, with your signed-in browser's UI for
gaps such as choosing Pro for a new chat or running Deep research. Submit your
supplied prompt and return the completed answer or report with its chat link.
This compact bridge can be retired when equivalent native support is available.

**Version:** 0.1.7.

## Requirements and installation

Use a Codex client that supports skills and exposes native ChatGPT chat tools
where available. Browser operations use an existing browser provider with access
to `chatgpt.com` in a signed-in session; no particular browser plugin is required.
The requested model, thinking
level or Deep research feature must be available to that ChatGPT account and
workspace. Normal service allowances and plan limits apply. The plugin adds no
subscription, model entitlement, API key, server or executable dependency.

When this package is available in the marketplace, install it with:

```sh
codex plugin marketplace add shpoont/codex-marketplace --ref main
codex plugin add chatgpt@b2a48b
```

Then start a fresh chat and try this read-only request:

> Use $chatgpt to open my most recent ChatGPT conversation and return its link without sending a message.

The expected result is the identified conversation and its link. If the target
is ambiguous, the assistant should identify what is missing before acting.

## What you can ask

- Resume the exact chat at a supplied conversation URL.
- Send your existing prompt once, keeping its meaning and formatting intact.
- Select an explicitly requested model or thinking level, including the latest
  available Pro when you ask for it.
- Start Deep research, check its plan, and read its finished report with sources.
- Monitor a run and return its actual result, status and stable chat URL.

For a supplied prompt without a conversation target, the plugin starts a fresh
ordinary ChatGPT chat. It resumes an existing chat when you request one.

For example:

> Use Pro in ChatGPT to answer: What are three ways to reduce meeting overload?

> Use Deep research in ChatGPT to compare solar and wind power costs, with sources.

The plugin does not create or edit images. It does not write prompts for you,
change plans or account settings, or substitute another model for a missing one.
Its official app icon identifies the external ChatGPT service; see the
[third-party notices](THIRD_PARTY_NOTICES.md) for attribution and mark terms.

## Data and effects

Authorized native chat or browser tools may read the intended conversation, its
messages, current model and tool state, research progress, report content,
citations and chat URL. Sending submits your supplied prompt to ChatGPT and
adds a user turn. Starting Deep research can consume the account's allowance
and use the selected web, file or connected-app sources.

Reading, opening or monitoring a chat does not authorize sending. Source changes
are applied only when you request them. The package has no plugin-owned server,
telemetry or credential store. ChatGPT, your browser and the assistant host keep
their own data and history under their settings and policies. Requested report
exports or saved results create files at the chosen destination.

When work ends, including after a failure, the assistant closes browser tabs it
opened unless you explicitly ask to keep them open. Pre-existing tabs and created
ChatGPT conversations are preserved; any incomplete cleanup is reported.

See [privacy](PRIVACY.md), [terms](TERMS.md) and the [license](LICENSE).

## Limitations and failures

Controls vary by account, workspace and rollout. The assistant inspects current
choices and confirms the applied model and mode instead of following a fixed
click sequence. Explicit model versions and unspecified settings are preserved.
"Latest Pro" uses the newest available family with Pro; ambiguity or missing
access requires a clear blocker report. Model-switch and limit notices must be
reported. It must not silently substitute settings, retry a possibly submitted
prompt, or treat a partial answer or elapsed time as completion.

For read or navigation failures, the assistant can inspect the current page,
wait for content, correct a locator or return to the confirmed task tab, and
reload the same chat. It checks the intended tab as well as the window. Recovery
respects an explicit time limit and stays brief while useful steps remain;
it adds no fixed timeout to ordinary use. Normal answer or research waits can
take longer. Unresolved access or targeting is reported.

Native reads may return summaries, a limited set of turns or clipped text. The
inspected reader has a 20,000-character maximum per message; older-turn pagination
does not retrieve the missing tail of that message. The assistant checks current
limits, retrieves needed pages where supported and uses the same chat's browser
view or verified UI export for content the native tools cannot provide. Retrieval
completeness is reported separately from whether the run finished. A reconstructed
native history turn labeled completed alone does not prove generation has ended.

Multiline prompts require safe insertion and a full-content check before one
submission. Structure-bearing formatting must not be flattened. Deep research
requires its completed report, including content and sources; a plan or initial
"research started" message is insufficient. Reading uses visible report surfaces
or verified UI exports. The completed report can be inside an iframe and absent
from an outer chat read; the assistant checks supported frame reads, accessible
UI or screenshots before treating the body as inaccessible.
The routine workflow has no private web API dependency
and does not modify the desktop app. Native-app restrictions remain in effect.

Account sign-in and feature access are your responsibility. A model limit or
missing control does not authorize changing an account, plan or subscription.

## Update, remove and recover

Use the supported client controls to update this marketplace installation.
Start a fresh chat after an update and confirm the intended version is available.
If another copy exposes the same skill name, select one intended installation
before using it.

Remove the plugin with:

```sh
codex plugin remove chatgpt@b2a48b
```

Removal does not delete ChatGPT conversations or files you exported. Manage
those through ChatGPT or your filesystem. If a run was interrupted, reopen its
recorded conversation URL and inspect the newest turn before deciding whether
anything needs sending. Do not resend merely because monitoring stopped.

For package problems, use the [public issue tracker](https://github.com/shpoont/codex-marketplace/issues)
and provide the plugin version and observed failure without credentials or
private transcripts. The [changelog](CHANGELOG.md) describes user-visible changes.

## License and affiliation

The [Installation and Use License](LICENSE) permits download, installation,
execution and copies needed for operation and backup. Modification, derivative
versions and redistribution require separate written permission.
Public availability alone is not an open-source license. Third-party services
retain their own terms and trademarks; see [notices](THIRD_PARTY_NOTICES.md).

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
