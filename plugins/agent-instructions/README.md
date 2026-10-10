# Agent Instructions

## Purpose

Keep AI agent instructions clear, useful and current. Maintain project AGENTS.md
guidance through recurring reviews, or find and apply selected refactoring
changes in instruction files. Scheduled reviews update only the selected root
AGENTS.md. Manual refactoring requires your selection from preceding discovery
in the same task.

## Quick start

### Requirements

- Codex desktop on macOS and an existing Codex account/session.
- For recurring reviews: automation and task-history tools, the Codex CLI on
  PATH, Python 3.11+, readable source tasks and a project whose root AGENTS.md
  the reviewer may edit.
- For manual refactoring: access to the instruction sources and an explicit
  selection from preceding discovery in the same task before edits.
- Exactly one enabled provider of these skills.

The helper uses the Python standard library and does not install dependencies.
Schedule execution depends on the Codex app, computer and project being
available.

### Install

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git --ref main
codex plugin add agent-instructions@b2a48b --json
```

Skip marketplace setup when it is already configured. Start a fresh task after
installation. If an older marketplace copy is installed, keep only the new
copy enabled, explicitly migrate existing review schedules, and verify their
settings and executing task's skill catalog before removing older copies.
Agent Instructions Improvement and Agent Instructions Refactoring share skill
names with this plugin; disable competing providers during a supported switch.
Pause affected reviews through Codex before disabling their selected provider,
then restore their intended state after verifying the migration.

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
| Find instruction problems | Inspect the selected agent instructions for duplication, conflicts and stale guidance without changing them or executing their workflows. |
| Apply selected refactors | Apply only findings explicitly selected from preceding discovery in the same task, preserving intended behavior and useful context. |

## Use the plugin

Ask to list managed projects or audit all review schedules first. The registry
lives outside repositories and contains the exact project paths, source task
IDs and schedule bindings needed for reliable matching.

To add a project, provide its real path, the source tasks whose durable guidance
should be reviewed, the intended recurrence and timezone:

```text
Add this project to recurring agent instruction improvements using these source tasks, every day at 09:00 in my timezone.
```

Registration alone does not create a schedule. Codex resolves the actual
project, source history and destination before an authorized scheduling write.
Task names use `Improve <project> AGENTS.md`, where `<project>` is the final
directory name.

Existing copied-policy schedules and wrappers selecting `maintain-agent-guidance`
or `agent-instructions-improvement` need a one-time migration:

```text
Migrate my existing AGENTS.md review tasks to the current plugin policy.
```

Migration preserves schedule IDs, recurrence, destinations, notifications and
project-specific boundaries. Reference-based tasks load the enabled plugin's
current policy on each invocation when the executing task's skill catalog agrees
with the selected installation. Compatible policy-only updates keep saved
prompts unchanged; they still require that catalog agreement. A plugin identity
or entrypoint change requires an explicit migration.

The management skill owns registry and schedule work. The review skill executes
one supplied `plugin-reference/v1` job. A review reads only approved source
tasks and may edit only the selected project's root AGENTS.md. It cannot resume
implementation work, change schedules, commit, push, publish or perform paid
operations. When evidence does not support an improvement, AGENTS.md stays
byte-for-byte unchanged.

### Manual instruction refactoring

Start with discovery:

```text
Find refactoring opportunities in this project's agent instructions.
```

Discovery resolves the target from available project or app evidence and reports
worthwhile opportunities and coverage gaps. It separates behavior-preserving
refactors from defects and unresolved policy choices. It leaves instructions
unchanged and does not execute the workflows they describe.

Select findings in that same task, then request implementation:

```text
Apply only findings 1 and 2 from the discovery above.
```

The refactoring skill requires the preceding discovery result, target,
constraints and explicit selection before inspecting or editing the target.
Missing or ambiguous context stops the operation without inventing a scope.
Only selected changes are applied; review the diff and test important workflows.
An AGENTS.md review job does not supply this separate manual authorization.

## Data and effects

- **Local reads:** the project registry, saved automation definitions, the
  selected project's root AGENTS.md, installed plugin resources and current
  Codex plugin inventory. Manual discovery reads the requested instruction
  sources and relevant host/project evidence; selected refactoring uses the
  established discovery context.
- **Account reads:** source task history explicitly registered for the project.
- **Local writes:** the registry and selected root AGENTS.md only when the user
  authorizes the corresponding operation; scheduling writes go through Codex's
  automation tool. Manual refactoring changes only selected instruction targets
  within the established scope after explicit selection in the same task.
- **External sends:** none by the helper. Codex account and scheduled-task
  behavior follow the app's normal service operation.
- **Storage:** project paths, task IDs, schedule IDs, destinations and extra
  boundaries live in
  `$CODEX_HOME/maintain-agent-guidance/projects.json`, defaulting to
  `~/.codex/maintain-agent-guidance/projects.json`. This established data path stays
  unchanged after the product rename; do not move or duplicate the registry.
- **Telemetry:** none added by the plugin or helper.
- **After removal:** the registry, schedules, task history and earlier AGENTS.md
  or selected refactoring edits remain until removed separately.

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
- Refactoring aims to preserve intended behavior, but discovery can miss
  dependencies or policy conflicts. Review the resulting diff and test workflows
  that depend on the changed instructions.

## Update, removal and recovery

```sh
codex plugin marketplace upgrade b2a48b
codex plugin add agent-instructions@b2a48b --json
codex plugin remove agent-instructions@b2a48b
```

Keep only one marketplace copy enabled. Pause affected reviews while changing
providers, preserve their saved inputs and authority, and start a fresh task
after installing or updating. Audit the saved references and verify the
executing task's catalog agrees with the selected installation before resuming
reviews. Changed job bindings or task authority require an authorized schedule
update.

A continuing Codex desktop chat can retain an older skill catalog after an
update. In macOS desktop testing, fully quitting and reopening Codex refreshed
that chat's catalog; the same unchanged saved job then loaded the new policy
and made only its authorized AGENTS.md change. If a chat reports an
inventory/catalog mismatch, keep the affected review paused, fully quit and
reopen Codex, then verify agreement in that same chat before invoking the saved
job again. If it still disagrees, stop and report the blocker. Automatic
adoption without a restart has not been verified. A restart does not guarantee
compatibility or authorize broader work, and no cache, source or copied-policy
fallback is permitted.

Removing the plugin does not remove schedules. Reference-based reviews stop
without editing until a valid copy is enabled again; legacy copied-policy tasks
remain self-contained. Pause or remove schedules through Codex when intended,
then verify the saved state before deleting registry records. For a broken
installation, reinstall from `b2a48b`, disable competing copies and
audit before creating any replacement task. If the executing task still exposes
an older skill catalog, stop before review and report the mismatch. A successful
helper command alone does not prove that an existing task adopted the update.

## Support

Report problems at
[b2a48b marketplace support](https://github.com/shpoont/codex-marketplace/issues).
Include the plugin version, Codex client and macOS version, Python version,
expected result, actual result and a minimal sanitized example. Do not attach
credentials, private instructions, personal data or raw traces.

## Version and license

Current version: `0.4.2`. See the [changelog](CHANGELOG.md) for released
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
