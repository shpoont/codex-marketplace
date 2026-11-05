# Agent Instructions

Version 0.5.1 refreshes review instructions from the enabled installation rather
than relying on a chat's older skill list. Managed sections introduced in 0.5.0
remain required; earlier 0.4.5 provides budget checks without managed-section
ownership limits.

## Purpose

Keep AI agent instructions clear, useful and current. Maintain project AGENTS.md
guidance through recurring reviews, or find and apply selected refactoring
changes in instruction files. Scheduled reviews update only an explicitly
adopted managed body and its checksum in the selected root AGENTS.md, preserving
human-maintained text outside it. Manual refactoring requires your selection from preceding discovery
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
codex plugin marketplace add shpoont/codex-marketplace --ref main
codex plugin add agent-instructions@b2a48b --json
```

Skip marketplace setup when it is already configured. Verify the current
installation and its readable entrypoint after installing. If an older
marketplace copy is installed, keep only the intended copy enabled, explicitly
migrate affected review schedules, and verify their saved settings and actual
current-policy execution before removing older copies.
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
| Adopt a managed section | Wrap the exact human-selected legacy range without changing its text; no inferred ownership. |
| Run bounded reviews | Read approved source tasks and update or compact only the adopted section when evidence supports a useful change. |
| Reconcile manual edits | Stop on a body checksum mismatch; accept the exact edited body only after an explicit human decision. |
| Pause or remove schedules | Change only the selected registered review, then read back the saved result. |
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
current policy on each invocation through live inventory and validated current
resources in the verified caller directory. This release supports a verified
default profile with no configuration overrides; named or unknown profiles stop
before review because the validated CLI cannot reproduce them for inventory. A chat's older skill list is diagnostic and cannot select an old copy
or prevent a verified current load. Compatible policy-only updates retain the
saved reference. A plugin identity, entrypoint or loader-contract change needs
an explicit migration. Earlier wrappers that stop on catalog disagreement need
one authorized prompt update; installation alone does not change those tasks.

The management skill owns registry and schedule work. The review skill executes
one supplied `plugin-reference/v1` job. A review reads only approved source
tasks and may edit only the adopted body and checksum in the selected project's
root AGENTS.md. It cannot resume
implementation work, change schedules, commit, push, publish or perform paid
operations. When evidence does not support an improvement, AGENTS.md stays
byte-for-byte unchanged.

### Managed ownership

Select the exact section before adoption:

```text
Let Agent Instructions manage only this AGENTS.md section; preserve the rest.
```

The maintenance skill prepares marker-only adoption, then verifies the complete
file's budget and actual host loading. Its [managed-section operations](skills/agents-md-maintenance/references/managed-sections.md)
define the marker format, read-only helper commands and manual-edit recovery.
Reviews may compact only the adopted body; they preserve useful meaning and
cannot absorb human-maintained text. A body checksum mismatch stops review until
explicit reconciliation. The checksum is not proof of human approval.

Policy 3.0.0 requires explicit adoption before any write to an unmarked legacy
guide. Managed ownership does not itself change saved references, but the
0.5.1 catalog-veto wrapper migration described above is separate. Review targets
need this opt-in before the new policy can write. No schedule changes happen during
adoption. A current over-budget or shadowed guide still blocks an ordinary review
and needs a separately authorized correction.

### Instruction budget checks

Reviews require verified effective host settings and a complete project
instruction chain. The read-only helper's `guidance --help` describes its inputs.
Supply the intended host's project root, working directory,
`project_doc_max_bytes`, ordered fallback filenames and a fresh
`codex debug prompt-input` JSON export from that same host/context. Account for
active profiles and invocation overrides; reading one configuration file alone
does not establish the effective settings. If they or the export are unavailable,
the review stops. No default budget is silently assumed.

`--prompt-input -` accepts the export on standard input, so raw instructions need
not be saved to disk. Use `--candidate -` separately for a draft projection;
candidate and loaded-prompt modes cannot be combined.

The helper counts raw UTF-8 project-source bytes and detects root overrides and
combined-chain exhaustion. Global guidance and prompt framing are excluded from
that count. `--candidate` checks proposed complete root guidance without writing
it; a fitting draft is not proof of loading. After an edit, the current-guidance
check must pass against a fresh host export containing the complete selected
sources in order. This proves only that fresh host snapshot, not adoption by an
existing conversation. The plugin does not increase limits, automatically remove
instructions, or move them into other files. An existing oversized or shadowed
guide needs a separately authorized correction that preserves its meaning.

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
  Codex plugin inventory, supplied host prompt export and applicable project
  instruction chain. Manual discovery reads the requested instruction
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
Guidance checks include source paths, byte counts and hashes. Host prompt exports
can contain private global/project instructions; keep them in temporary private
run evidence outside projects and plugin caches, and never publish them.
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
providers and preserve their saved inputs and authority. Audit the saved
references, then verify that the actual task selects the current installation,
reads its entrypoint and policy, and records their resource hashes before
resuming reviews. Changed job bindings, authority or loader contracts need an
authorized schedule update with saved-state readback.

A continuing chat may retain an older skill list. That list is diagnostic;
current live inventory in the intended directory/profile selects the package.
The task must be able to read and use its current resources through permitted
tools. A path in a skill list or on disk grants no permission. Missing, disabled,
ambiguous, unreadable or incompatible resources stop the review; an old cache,
source checkout or remembered policy is never a fallback. A successful helper
command alone does not prove that a continuing task used the current policy.
A restart is not a required recovery step for this loader contract.

Existing schedules with the earlier catalog-veto wrapper still need an explicit
prompt migration before using this contract. Prepare and inspect the complete
before/after change, preserving IDs, inputs, authority, recurrence, destinations,
status and notifications; apply it through Codex and read back the saved result.
Do not recreate schedules or adopt legacy guides as part of the migration.

Removing the plugin does not remove schedules. Reference-based reviews stop
without editing until a valid copy is enabled again; legacy copied-policy tasks
remain self-contained. Pause or remove schedules through Codex when intended,
then verify saved state before deleting registry records. For a broken
installation, reinstall from `b2a48b`, disable competing copies and audit before
creating any replacement task. If current policy cannot be accessed or used
safely, keep the review blocked and report the specific missing capability.

## Support

Report problems at
[b2a48b marketplace support](https://github.com/shpoont/codex-marketplace/issues).
Include the plugin version, Codex client and macOS version, Python version,
expected result, actual result and a minimal sanitized example. Do not attach
credentials, private instructions, personal data or raw traces.

## Version and license

Current version: `0.5.1`. See the [changelog](CHANGELOG.md) for released
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
