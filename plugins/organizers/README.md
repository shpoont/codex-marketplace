# Organizers

Organizers currently includes **Mail Organizer**: help making sense of accumulated
email and deciding what deserves your attention, what you can clear away and
what needs action.

## Mail Organizer

Mail Organizer can help you:

- **Handle routine mail together.** Review related notifications, newsletters or
  updates as a group, rather than making the same decision repeatedly.
- **Understand what matters.** Get the essential request, dates and relevant
  context without piecing everything together yourself.
- **Turn email into action.** Discuss a message, prepare a reply or request a task
  in another system when the appropriate tools are connected.
- **Reduce recurring clutter.** Unsubscribe from unwanted mail where supported,
  rather than only deleting what has already arrived.

The aim is fewer repetitive decisions and useful help with complicated ones,
not simply an empty Inbox. Time savings are not guaranteed.

## Quick start

### Requirements

- Codex desktop with plugin support. CLI commands below manage installation;
  other clients are not currently claimed as supported.
- A connected mail account and tools authorized to read it. The plugin supplies
  guidance, not a mail connector or account credentials.
- Suitable connected tools and separate authorization for changes or actions in
  other services. No additional plugin runtime or paid subscription is included;
  ordinary Codex and connected-service usage limits or charges still apply.

### Install

Skip the first command if this marketplace is already registered:

```sh
codex plugin marketplace add shpoont/codex-marketplace --ref main
codex plugin add organizers@b2a48b
```

Start a fresh chat and try:

> Use $mail-organizer to organize my inbox and suggest handling before making changes.

Expect a question about the account or messages to include when needed, then an
email or related group with a summary and suggested handling. Nothing should be
moved, deleted, sent or otherwise changed without your approval.

## What to expect

Choose an Inbox, folder, selected messages or date range and mention preferences
that matter. Mail Organizer presents one email or related group, explains its
recommendation and waits for your decision. You can approve it, change it, ask
questions or handle some messages differently. For example:

> Archive these updates, but keep the message asking for a decision. Help me
> understand the options and draft a reply.

Depending on the available tools, handling can include archiving, moving,
supported labels or folders, deletion, unsubscribing, replies and external
follow-up. Proposals explain actual targets and material effects, including read
state where supported. An organizational marker alone does not authorize moving
messages out of Inbox; unclear destinations or effects require clarification.

After approved actions, it checks the results, reports anything unfinished and
presents the next proposal. You can pause or stop at any time. Continuing the
conversation does not grant permission to handle further messages automatically.

## Privacy and data

The package contains instructions, fixed method references, presentation metadata
and an icon. It includes no executable helper, MCP server, hook, background job,
telemetry endpoint or plugin-operated storage service.

During use, Codex and your connected tools can read message contents, attachments
and related context as needed. Approved actions can change mail or create, change
or send information in another service. Their access, processing, retention and
deletion follow the host and connected services' own settings and policies.

Decisions, results and unfinished work may be retained in the chat and local
working records. Removing the plugin does not delete those records, revoke your
service connections or undo completed actions. Manage those separately through
the relevant client, workspace or service. Do not include private mail or
credentials in support reports.

## Limitations and recovery

Large collections and actions involving other services can take time. Mail
Organizer reports partial coverage; reviewing one group does not mean the whole
Inbox has been reviewed. Moving a message does not finish the work it describes.

If a connection, permission or required capability is unavailable, the affected
work remains unfinished. Reconnect the intended account or choose another
supported action. If a result is uncertain, check the actual mail or external
record before retrying. Do not repeat an uncertain send or deletion blindly.

This version includes mail only. It uses bundled Mail Processing v1.2.0 and
A Simple Method for Processing Unorganized Items v1.4.0 without fetching changing
method text during use. Its approval and record-keeping behavior is guidance,
not an enforced transaction system or guarantee against mistakes.

## Update and removal

```sh
codex plugin marketplace upgrade b2a48b
codex plugin add organizers@b2a48b
codex plugin remove organizers@b2a48b
```

Start a fresh chat after an update. If another copy is installed, select one
intended copy before use. If an update behaves incorrectly, stop using it and
disable or remove it through Codex, then report the version and sanitized
problem. Check affected messages before resuming; removal does not reverse them.

## Support

Use the [marketplace issue tracker](https://github.com/shpoont/codex-marketplace/issues).
Include the plugin version, client, expected result, actual result and a minimal
sanitized example. Do not attach credentials, personal data or raw traces.

## Terms and license

Current package version: `0.1.5`. See the [changelog](CHANGELOG.md).

The [Installation and Use License](LICENSE) permits installation and use of this
plugin. Modification, derivative versions and redistribution require separate
written permission. Your own configuration and operational data remain ordinary
permitted use. Public availability does not make the whole plugin open source.

The bundled method documents retain their MIT License and unchanged
[copyright and license notice](skills/mail-organizer/references/LICENSE).
The plugin's restrictions do not override those rights. See the
[third-party notices](THIRD_PARTY_NOTICES.md) for separately licensed material.
Use of Codex and connected services remains subject to their own terms,
permissions, availability and usage limits; the plugin grants no service access
or additional quota.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
