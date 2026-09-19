# AGENTS.md Self-Improvement

Keep project instructions useful through scheduled, evidence-based AGENTS.md
reviews. Register projects, manage their review schedules, and detect differences
in saved task bindings while reviewers load the current installed policy.

Maintained by **Shpoont**. Version **0.1.5**; review policy **1.0.0**.

## Requirements

- Codex desktop on macOS with local projects, automation management and task
  history tools. Other platforms and CLI-only schedule management have not been
  validated for this release.
- An existing Codex account/session and available model usage. Model usage is
  governed by your Codex plan; the plugin adds no subscription or paid service.
- Python **3.11+** and the Codex CLI (`codex` on PATH) already installed.
  Runtime review-policy loading uses `codex plugin list --json` to verify the
  current enabled installation (15-second timeout). This release validates the
  macOS `<Codex home>/plugins/cache/<marketplace>/<plugin>/<version>` layout and blocks on unknown
  layouts. Offline render/audit use only the Python standard library;
  the helper does not install dependencies or download code.
- Explicit source conversations accessible through your Codex account, and a
  project whose root AGENTS.md the reviewer may edit.

Scheduling uses Codex's tools. There is no separate scheduler; local scheduled
work depends on the app, computer and project being available. Python-only
rendering and configuration auditing do not prove that a scheduled review ran.

## Install and try

Once this version is listed in the public marketplace, install with your existing
Codex CLI. If the marketplace is already registered, refresh it instead of
adding it again.

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git --ref main
codex plugin add agents-md-self-improvement@shpoont-public --json
```

Start a new Codex desktop task and ask:

> Use $agents-md-maintenance to list my managed projects and audit their review schedules.

On first use there may be no registry. The expected response is to explain the
setup need, not invent projects or create a schedule. To add a project, provide
its actual path, source task IDs, intended schedule and timezone:

> Add this project to AGENTS.md self-improvement using these source conversations, with a daily review at 09:00 in my timezone.

Codex resolves the actual project, source history and destination before
creating a schedule. If the source already has an unrelated heartbeat, select
an independent reviewer or another destination. Registration alone does not
schedule anything. Existing reviewers are adopted only after scope checks.

Other requests:

- “Audit all AGENTS.md review tasks.”
- “Synchronize the outdated review instructions for this project.”
- “Pause this project's AGENTS.md review.”
- “Remove this project's AGENTS.md review schedule.”

Task names use `Improve <project> AGENTS.md`, taking the project directory name.
Audit is read-only. Synchronization changes selected task bindings or migrates
old copied-policy prompts while preserving schedule, destination and settings.

## Live policy references

New reviewers contain a stable `$agents-md-review` entry-point reference, project
path, source task IDs, project boundaries and fixed AGENTS-only authority. They
resolve the single enabled plugin and load its current policy on every run,
including resumed tasks. Version 0.1.4 uses current CLI inventory and validates
the matching installed cache and manifest, independently of the task's possibly
stale skill catalog. Codex home is CODEX_HOME or ~/.codex; no versioned path is
saved in the task. Run evidence records the qualified installation, plugin
version, policy version and SHA-256. A changed policy is re-read before any write.

Updating the enabled plugin intentionally updates these reviewers on their next
invocation. It cannot expand their permissions. Missing, disabled, ambiguous or
incompatible installations block review without editing; old cached instructions
and disabled copies are never substitutes. The management skill manages schedules;
the separate review skill executes the bounded review.

Copied-policy schedules need migration; 0.1.3 reference wrappers also need one
synchronization to adopt the live inventory resolution method. Request:

> Migrate my AGENTS.md review schedules to use the current plugin policy.

Audit reports those as `migration-required`. Migration preserves IDs, recurrence,
destinations, notifications and authorized project exceptions. Future policy-only
updates then need no prompt synchronization. Changes to per-project bindings or
the task contract still require a reviewed schedule update.

## What reviewers change

Reviewers use selected conversations to identify durable, actionable guidance:
verified commands, repository conventions and corrections to demonstrated
mistakes. They may edit only the selected project's **root AGENTS.md**. They
cannot resume implementation work, change code or schedules, commit, push,
publish or perform paid operations.

With no substantive improvement, the file stays byte-for-byte unchanged and no
routine unchanged-status notification is requested. Missing or contradictory
evidence is a blocker. Reviewing meaningful diffs remains useful; the plugin
does not guarantee improved model performance.

## Data and privacy

Project paths, source task IDs, schedule IDs, destinations and extra boundaries
live in `$CODEX_HOME/agents-md-self-improvement/projects.json`, defaulting to
`~/.codex/agents-md-self-improvement/projects.json`. Keep the registry outside
repositories and plugin caches. The bundled
[example](skills/agents-md-maintenance/assets/projects.example.json) is synthetic.

Codex retains scheduled prompts and run history through its normal account and
application behavior. Codex reads task history and relevant project material
during reviews. The offline render/audit helper reads the registry, bundled
resources and saved
automation files locally. Runtime policy loading also calls the existing Codex
CLI for current installation inventory; normal Codex account/access behavior
applies. The helper writes no state, telemetry or logs. Audit output includes
registry keys, automation IDs,
status and prompt hashes; rendered prompts contain paths, task IDs and boundaries.
Treat these outputs as private.

Removing the plugin does not delete the registry, schedules, review history or
AGENTS.md edits. Reference-based schedules stop without editing if the plugin
is unavailable; legacy copied-policy schedules can continue independently.
Remove schedules through Codex first; delete registry records
only after verifying they are no longer needed. Use Codex's controls for task
and history deletion. Never include private registries, paths, conversation
excerpts or credentials in public support reports.

## Helper and failures

Resolve `skills/agents-md-maintenance/scripts/manage.py` inside the actual
installed package, without depending on a source checkout. Run
`python3 <absolute-helper-path> --help`. Supported commands:

```text
audit --registry <absolute-registry-path> --automations-dir <absolute-directory>
render --registry <absolute-registry-path> --project <registered-key>
policy --job <job-json-path-or-dash-for-stdin>
```

`policy --job -` reads review-job JSON from standard input and emits the current
resolved policy plus provenance; it does not perform a review or edit AGENTS.md.
The execution skill owns the bounded review. Audit exits **0** for current task
references, **1** for findings, **2** for invalid input. A paused task can have
current instructions. Complete reference wrappers and destinations are compared;
the current policy
hash is reported separately and is not pinned in the saved task.

| Problem | Response |
| --- | --- |
| No registry or invalid JSON | Explain setup/validation failure; do not invent bindings. |
| Python below 3.11 | Select an already installed supported interpreter. |
| Missing automation/history tools | Explain the missing capability; do not edit scheduler files directly. |
| Inaccessible source history | Leave affected guidance unchanged and identify the missing evidence. |
| Duplicate, missing or misdirected review | Reconcile identity and destination before changing it. |
| Uncertain scheduling write | Read back state; never blindly retry creation. |

## Updates, removal and recovery

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin add agents-md-self-improvement@shpoont-public --json
```

Audit after updating. Reference-based tasks load the new installed policy at their
next invocation without rewriting their saved prompts. Synchronize changed job
bindings or explicitly migrate legacy tasks. Version 0.1.5 retains review policy
1.0.0 and the version 0.1.4 runtime behavior. Keep only one marketplace copy
enabled.

```sh
codex plugin remove agents-md-self-improvement@shpoont-public
```

Uninstalling does **not** delete schedules. Reference-based reviews block until
the plugin is available again; legacy copied-policy tasks remain self-contained.
Pause/remove schedules separately when intended. For a broken
installation, reinstall from the intended marketplace and audit before creating
replacements. Preserve the external registry and reconcile uncertain writes
instead of resetting state.

## Support, license and changes

Report issues at [Shpoont marketplace support](https://github.com/shpoont/codex-marketplace/issues).
Include plugin version, Codex client/version, Python version and a sanitized
reproduction. Consumers need no access to the private source repository.

Distributed under the [MIT License](LICENSE). No third-party runtime libraries
are vendored. Python and Codex are prerequisites with their own terms.

Version 0.1.5 adds the public marketplace package website and standard
distribution disclaimer required by production-readiness version 5; runtime
policy and review behavior are unchanged. Version 0.1.4 resolves the current
installed entrypoint from live inventory even
when an existing task's skill catalog is stale, and rejects symlinked or mismatched
installation resources. Version 0.1.3 introduces the `agents-md-review` execution entry point, live policy
loading with provenance and enabled-installation checks, stable task wrappers,
and explicit migration of legacy schedules. Version 0.1.2 prepared public
distribution with consumer documentation, MIT licensing and support ownership,
and clarified skill discovery, installed paths and desktop capabilities while
retaining its preceding runtime helper and review policy. Version 0.1.1
standardized task names; 0.1.0 introduced the
external registry, rendering and read-only drift audit.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
