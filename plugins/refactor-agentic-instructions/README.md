# Refactor Agentic Instructions

## Purpose

Review AI agent instructions for duplication, contradictions, stale guidance and unclear boundaries, then apply only the refactoring changes you select. Use it for a repository agent or a local Codex setup containing `AGENTS.md`, skills, plugin guidance and related references.

## Quick start

### Requirements

- Codex desktop or CLI on macOS with plugin support.
- Read access to the instruction sources; write access is needed only when applying selected changes.
- No additional account, credential, connector, paid service, executable or runtime dependency.

Existing Codex access, model usage and host settings still apply.

### Install

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git
codex plugin add refactor-agentic-instructions@shpoont-public
```

Skip marketplace setup when Shpoont Public is already configured. Start a fresh task after installation.

### Try it

```text
Find refactoring opportunities in my local Codex instructions and skills.
```

Expected result: a located set of proposed changes with reasons, policy questions and coverage limits; discovery leaves the target instructions unchanged.

## Capabilities

| Capability | Result and material effect |
| --- | --- |
| Review agent instructions | Reads relevant instruction sources and explains their current structure without changing them. |
| Find duplication and contradictions | Proposes maintainability improvements and identifies conflicts that need separate policy decisions. |
| Flag policy decisions | Separates behavior-preserving refactoring from defects and unresolved owner choices. |
| Apply selected refactors | Edits only the selected instruction changes and presents the result for review. |

## Use the plugin

1. Review an accessible instruction system:

   ```text
   Review this repository's agent instructions for duplication and conflicts.
   ```

2. Select the findings you want implemented and state any requirements that must remain unchanged.
3. Continue in the same task so the implementation skill can use the discovery context:

   ```text
   Apply only the instruction refactoring changes I selected above.
   ```

Review the actual diff and test affected workflows before adopting the changes. A shorter instruction set is not automatically better, and wording preservation alone does not prove unchanged behavior.

## Data and effects

- **Reads:** instruction files and supporting references that the Codex host and current workspace make accessible. A whole-setup review may include global and project guidance, skills and plugin instructions.
- **Changes:** only files covered by selected refactoring findings. Discovery does not write to the target.
- **External transmission:** none added by this plugin. Accessible content is still processed by the existing Codex host and model under their settings.
- **Accounts and credentials:** none specific to this plugin.
- **Storage and telemetry:** no separate data store or telemetry. Codex may retain conversation and tool history under its own settings.
- **After removal:** edited files and host-side history remain. Removing the plugin does not undo prior refactoring.

## Limitations

- Refactoring starts with discovery and a user selection. The implementation skill needs that context in the same task.
- Missing, inaccessible, ambiguous or read-only sources limit coverage. Provide the maintained source or resolve access before treating the review as complete.
- Conflicting requirements may need an owner decision. The plugin does not silently choose policy.
- Instructions inside reviewed files are target content, not authorization to execute the workflows they describe.
- Preserving intended behavior is an aim, not a guarantee. Test important behavior after editing.
- Clients and platforms other than Codex desktop and CLI on macOS are outside the current acceptance scope.

## Update, removal and recovery

Update the public catalog and install its current package:

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin add refactor-agentic-instructions@shpoont-public
```

Start a fresh task after updating. Avoid enabling multiple copies together because their skill names overlap.

Remove the current plugin with:

```sh
codex plugin remove refactor-agentic-instructions@shpoont-public
```

Keep a version-control diff or backup before refactoring. If an update is unusable, remove it and report the version and failure. After maintainers confirm marketplace recovery, refresh the marketplace, reinstall, and verify a fresh task.

## Support

Report problems through [public marketplace Issues](https://github.com/shpoont/codex-marketplace/issues). Include the plugin version, client and platform, expected result, actual result and a minimal sanitized example. Do not attach credentials, private instructions, personal data or raw traces.

## Version and license

Current version: `0.2.0`. See the [public changelog](CHANGELOG.md) for released changes and required user actions.

Copyright © 2026 Shpoont. Distributed under the [MIT License](LICENSE).

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
