# Maintain Agent Guidance

## Purpose

Keep project AGENTS.md guidance useful through recurring, evidence-based
reviews. Use this plugin to register projects, audit or migrate their review
schedules, and run a bounded review that can update only the selected project's
root AGENTS.md.

## Quick start

### Requirements

- Codex desktop on macOS with automation and task-history tools.
- An existing Codex account/session, the Codex CLI on PATH and Python 3.11+.
- Source tasks that the current account can read and a project whose root
  AGENTS.md the reviewer may edit.
- Exactly one enabled installation of this plugin.

The helper uses the Python standard library and does not install dependencies.
Schedule execution depends on the Codex app, computer and project being
available.

### Install

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git --ref main
codex plugin add maintain-agent-guidance@shpoont-public --json
```

Skip marketplace setup when it is already configured. Start a fresh task after
installation.

### Try it

```text
Audit all of my AGENTS.md review schedules and report any drift.
```

Expected result: the plugin lists registered projects and reports current,
outdated, missing, misbound or duplicate schedules without changing them.

## Capabilities

| Capability | Result and material effect |
| --- | --- |
| Audit AGENTS.md schedules | Compare the external project registry with saved review tasks. Audit is read-only. |
| Add review schedules | Register a verified project and create one Codex scheduled review after explicit authorization. |
| Migrate saved tasks | Replace copied review policy with a stable plugin reference while preserving the task's ID, recurrence and destination. |
| Run bounded reviews | Read approved source tasks and update only the selected project's root AGENTS.md when evidence supports a useful change. |
| Pause or remove schedules | Change only the selected registered review after reading back the saved result. |

## Use the plugin

Ask to list managed projects or audit all review schedules first. The registry
lives outside repositories and contains the exact project paths, source task
IDs and schedule bindings needed for reliable matching.

To add a project, provide its real path, the source tasks whose durable guidance
should be reviewed, the intended recurrence and timezone:

```text
Add this project to recurring agent-guidance reviews using these source tasks, every day at 09:00 in my timezone.
```

Registration alone does not create a schedule. Codex resolves the actual
project, source history and destination before an authorized scheduling write.
Task names use `Improve <project> AGENTS.md`, where `<project>` is the final
directory name.

Existing copied-policy schedules need a one-time migration:

```text
Migrate my existing AGENTS.md review tasks to the current plugin policy.
```

Migration preserves schedule IDs, recurrence, destinations, notifications and
project-specific boundaries. Reference-based tasks then load the enabled
plugin's current policy on each invocation, so a policy-only plugin update does
not require rewriting saved prompts.

The management skill owns registry and schedule work. The review skill executes
one supplied `plugin-reference/v1` job. A review reads only approved source
tasks and may edit only the selected project's root AGENTS.md. It cannot resume
implementation work, change schedules, commit, push, publish or perform paid
operations. When evidence does not support an improvement, AGENTS.md stays
byte-for-byte unchanged.

## Data and effects

- **Local reads:** the project registry, saved automation definitions, the
  selected project's root AGENTS.md, installed plugin resources and current
  Codex plugin inventory.
- **Account reads:** source task history explicitly registered for the project.
- **Local writes:** the registry and selected root AGENTS.md only when the user
  authorizes the corresponding operation; scheduling writes go through Codex's
  automation tool.
- **External sends:** none by the helper. Codex account and scheduled-task
  behavior follow the app's normal service operation.
- **Storage:** project paths, task IDs, schedule IDs, destinations and extra
  boundaries live in
  `$CODEX_HOME/maintain-agent-guidance/projects.json`, defaulting to
  `~/.codex/maintain-agent-guidance/projects.json`.
- **Telemetry:** none added by the plugin or helper.
- **After removal:** the registry, schedules, task history and earlier AGENTS.md
  edits remain until removed separately.

Audit output can include registry keys, automation IDs, status and prompt
hashes; rendered task prompts contain paths, source task IDs and boundaries.
Treat these outputs as private. Do not include registries, paths, conversation
excerpts or credentials in public support reports.

## Limitations

- This release validates Codex desktop on macOS, the installed cache layout
  `<Codex home>/plugins/cache/<marketplace>/<plugin>/<version>`, and a
  15-second `codex plugin list --json` inventory check. Other platforms and
  CLI-only schedule management are unverified.
- Missing, disabled, ambiguous, incompatible or symlinked installations block
  a review. The plugin never falls back to a disabled copy, stale cache or
  unselected local copy.
- Inaccessible or contradictory source evidence leaves affected guidance
  unchanged. A configuration audit does not prove that a timer fired or that a
  review improved model performance.
- A destination already occupied by unrelated heartbeat work requires the user
  to select another destination; the plugin does not replace it or create a
  second scheduler.

## Update, removal and recovery

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin add maintain-agent-guidance@shpoont-public --json
codex plugin remove maintain-agent-guidance@shpoont-public
```

Keep only one marketplace copy enabled and start a fresh task after installing
or updating. Audit after an update; reference-based tasks adopt the new policy
on their next invocation. Changed job bindings or task authority still require
an authorized schedule update.

Removing the plugin does not remove schedules. Reference-based reviews stop
without editing until a valid copy is enabled again; legacy copied-policy tasks
remain self-contained. Pause or remove schedules through Codex when intended,
then verify the saved state before deleting registry records. For a broken
installation, reinstall from `shpoont-public`, disable competing copies and
audit before creating any replacement task.

## Support

Report problems at
[Shpoont marketplace support](https://github.com/shpoont/codex-marketplace/issues).
Include the plugin version, Codex client and macOS version, Python version,
expected result, actual result and a minimal sanitized example. Do not attach
credentials, private instructions, personal data or raw traces.

## Version and license

Current version: `0.2.0`. See the [public changelog](CHANGELOG.md) for released
changes and required user actions. Distributed under the [MIT License](LICENSE).
Python and Codex are prerequisites with their own terms; no third-party runtime
libraries are vendored.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
