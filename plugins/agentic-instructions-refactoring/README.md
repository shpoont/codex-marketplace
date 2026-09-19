# Agentic Instructions Refactoring

Make AI agent instructions clearer and easier to maintain: find worthwhile changes, then apply the ones you select. Use it for an agent's instruction files or a local Codex setup containing `AGENTS.md`, skills, plugin guidance and references.

| Skill | Result |
|---|---|
| [Find Refactoring Opportunities](skills/find-refactoring-opportunities/SKILL.md) | Proposals with locations, reasons and verification limits. Leaves target instructions unchanged. |
| [Refactor Instructions](skills/refactor-instructions/SKILL.md) | Implements selected findings using the preceding review and presents revised instructions. |

## Requirements

Use Codex with plugin support, access to the target instruction sources, and permission to edit the selected files when refactoring. The supported release target is Codex desktop and CLI on macOS. Other clients and platforms are outside the current acceptance scope.

The plugin adds no connector, account, API key, paid service, executable or runtime dependency. Your existing Codex access and model usage still apply. It cannot expose instructions that a host or another application does not make available. An app name alone may need clarification.

## Install

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git
codex plugin add agentic-instructions-refactoring@shpoont-public
```

Skip the first command if the marketplace is already configured. Start a fresh task after installation. If the plugin is not listed, check the [public marketplace](https://github.com/shpoont/codex-marketplace) for availability; these commands do not publish an unreleased version.

## Discover, select, refactor

For a local assistant setup:

```text
Use $find-refactoring-opportunities for my local Codex setup.
```

For a custom agent:

```text
Use $find-refactoring-opportunities for the agent instructions in this repository.
```

Expect proposals explaining what could change, where and why. Existing defects and unresolved policy choices should be distinguished from refactoring. Review coverage gaps before treating a review as complete.

Choose findings, then continue in **the same task**:

```text
Use $refactor-instructions to implement findings 1 and 3 from the review above.
Keep the approval rules and role-specific exceptions unchanged.
```

Expect edits limited to the selected findings, followed by revised instructions, an explanation and verification limits. Review the actual diff before adopting changes. The second skill uses the discovery context; a separate handoff document is unnecessary.

### Small example

Two skills repeat “Prepare a draft; sending requires the user's explicit request.” The template skill has a 100-word default; customer replies have a 200-word default.

Discovery might propose one shared sending rule with explicit loading instructions in both skills, retaining the different length defaults locally. Select that finding to implement it. Verify that each skill still loads the shared rule and preserves its exceptions: fewer copies alone do not establish a useful improvement.

This illustrates a possible refactor, not a claimed test result or a prescribed architecture.

## Limits and common problems

- Start with discovery. Supply its findings and your selection before implementation.
- Missing, inaccessible or read-only files limit the work. Resolve access or identify an editable maintained source. Third-party installed packages may be replaced on update.
- Conflicting requirements may need an owner decision. Refactoring should not silently decide policy or introduce an unacknowledged behavior change.
- Workflows described inside reviewed instructions are material to inspect, not requests to execute them.
- Preserving intended behavior is the aim, not a proven guarantee. The plugin does not establish better agent decisions or make shorter instructions automatically better. Test affected behavior where it matters.

## Update, removal and recovery

If version 0.1.2 or earlier is installed under the historical prefixed ID, migrate it explicitly:

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin remove codex-plugin-agentic-instructions-refactoring@shpoont-public
codex plugin add agentic-instructions-refactoring@shpoont-public
```

For later updates under the current ID, refresh the catalog, install its current package, then start a fresh task:

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin add agentic-instructions-refactoring@shpoont-public
```

Remove this plugin with:

```sh
codex plugin remove agentic-instructions-refactoring@shpoont-public
```

Removal does not undo changes to your instructions. Keep a restorable copy before refactoring and use your version-control diff or backup to restore affected files.

If an update is unusable, remove the plugin and report the version and failure. Maintainers can restore a prior package through marketplace recovery. After they confirm recovery, refresh, reinstall and check a fresh task. Avoid enabling personal, development and public copies together: their skill names overlap and selection may be ambiguous.

## Data and support

Discovery reads target instructions; refactoring can persist edits to selected files. The plugin itself has no telemetry, external service or separate data store. Your Codex host and model process content under their own settings and may retain conversation or tool history. Uninstallation does not remove that history or edited target files.

Maintained by Shpoont. Report problems through [public marketplace Issues](https://github.com/shpoont/codex-marketplace/issues), including version, client/platform, expected result and a minimal sanitized example. Do not attach private instructions, credentials or unredacted traces to public issues.

## Version 0.1.3

Changes the advertised plugin ID from `codex-plugin-agentic-instructions-refactoring` to `agentic-instructions-refactoring`, adds the audience-accessible GitHub website, and adds the standard distribution disclaimer required by the Shpoont marketplace. Existing users must remove the old qualified plugin and install the new qualified ID after 0.1.3 is published. The source repository keeps its prefixed name. The skill instructions and their UI metadata are unchanged from version 0.1.2.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.

## Distribution terms

Copyright © 2026 Shpoont. Distributed under the [MIT License](LICENSE), using the [standard MIT text](https://opensource.org/license/mit).
