---
name: agents-md-maintenance
description: Manage scheduled AGENTS.md improvements and explicitly owned sections. Use when adopting a managed section, reconciling its manual edits, adding projects to recurring reviews, listing managed projects, auditing schedules, or synchronizing their plugin references.
---

# AGENTS.md reviewers and managed sections

Use [agents-md-review](../agents-md-review/SKILL.md) for ordinary reviews,
[managed-section operations](references/managed-sections.md) for explicit
adoption or reconciliation, and the sections below for registry and scheduling
work. These operations do not resume the project's implementation or outstanding
requests. The shared policy remains in [assets/review.md](assets/review.md), with version
in `assets/template.json`. Read these before creating or migrating a reviewer.
Saved tasks contain a stable entry-point reference, job data and fixed authority;
never embed the review policy or a versioned plugin/cache path in a task.

Resolve bundled paths relative to this installed skill directory, not the user's
project directory. Run the helper with an available Python 3.11+ interpreter;
it has no third-party runtime dependencies. Scheduling and source-history reads
require the Codex desktop app's automation and thread tools. If those tools are
unavailable, explain the missing capability; do not substitute another scheduler
or infer source evidence. The helper's offline render/audit commands remain usable.

## Registry and discovery

Use the user's registry, or `$CODEX_HOME/maintain-agent-guidance/projects.json`
(`~/.codex` when CODEX_HOME is unset). Keep this established data path after the
Agent Instructions Improvement rename; do not move or duplicate it. Keep it
outside repositories and plugin
caches: it contains local project paths and task bindings, not secrets or copied
conversations. The Python 3.11+ helper validates the schema. See
[assets/projects.example.json](assets/projects.example.json) for a synthetic
example; run the helper with `--help` for its interface.

For each project record its absolute `project_path`, stable `key`, explicit
`source_thread_ids`, `automation_id` (null until created), `kind`, and any
user-authorized `extra_boundaries`. A heartbeat also needs `target_thread_id`;
a standalone cron task needs the verified app `project_id`. Do not infer sources
from whichever conversation is currently most recent. Confirm ambiguous sources.

Inspect existing saved `automations/*/automation.toml` before creating tasks.
Resolve an existing reviewer by exact scope and source history, not name alone.
Adopt it by registering its existing ID; do not create a duplicate. A task that
merely reads AGENTS.md while doing other work is not an instruction reviewer.

## Managed-section adoption and compaction

Read [managed-section operations](references/managed-sections.md) for explicit
adoption, reconciliation or a requested compaction. There is one managed block
per root file; outside content stays human-maintained. Existing text has no
inferred plugin ownership. The helper prepares/checks candidates read-only;
applying one needs the corresponding human authority and complete-file
budget/loading checks. Ordinary reviews can update/compact an already adopted,
checksum-valid body, but cannot adopt or reconcile it. Managed sections are optional. Ordinary authorized reviews of unmarked guides
continue without adoption; existing protected sections remain protected. Do not
change schedules to conceal a real scope or evidence blocker.

## Audit (read-only)

Run `scripts/manage.py audit --registry <path> --automations-dir <directory>`.
This compares the complete reference wrapper, job configuration and destination
with saved state. `migration-required` identifies old copied-policy prompts, retired-plugin
reference wrappers and exact recognized catalog-veto wrappers. Unknown manual
prompt changes remain `outdated` and need inspection. The retired marker is recognized for migration discovery
only; runtime selection requires `agent-instructions`.
Changes to the shared review policy do not stale an unchanged reference wrapper;
reviewers load the enabled installation at each run. The audit is a configuration
check, not proof that the dependency is currently enabled or a review succeeded.
`guidance_status: not-assessed` keeps target guidance safety separate from saved
wrapper freshness. Use the helper's `guidance` command for a budget/loading check;
it does not change schedules, settings or instruction files.
Report current, outdated, migration-required, missing/unconfigured, misbound, duplicate, unreadable,
and unregistered-reviewer findings separately. Status ACTIVE/PAUSED is separate
from instruction freshness. An audit is not authorization to synchronize.

## Add, synchronize, rename, pause or remove

Use the Codex app's `automation_update` tool for all scheduling mutations. The
helper renders and audits only; never edit automation TOML or app databases.

- Name new scheduled tasks `Improve <project> AGENTS.md`, where `<project>` is
  the final directory component of `project_path`, not the registry key. For
  example, `/workspace/example-service` becomes
  `Improve example-service AGENTS.md`. Rename an existing task only when the
  user requests it; keep its automation ID and registry binding. A name-only
  change preserves the complete prompt and all other task settings, and does
  not require a change to the review template or the destination task's title.
- For an authorized add, establish the exact project and source threads. Reuse
  an existing heartbeat for that same review purpose. Default to a heartbeat;
  standalone project runs need explicit user intent. If a source thread already
  has a different heartbeat, do not replace it or create a workaround scheduler;
  obtain the user's choice of an independent reviewer or another destination.
- For standalone work, call `list_projects` and use the matching returned ID.
  If the project is not registered, report that exact setup need; do not bind it
  to an unrelated project or invent an ID. Prefer direct local mode for an
  explicitly authorized in-place AGENTS.md review, preserving concurrent edits.
- Before enabling or migrating a reviewer, verify exactly one installed, enabled
  copy of this plugin provides `agents-md-review` in the inventory-selected cache.
  Follow the execution skill's live inventory/cache resolution contract in the
  actual working directory using the existing configured CLI. The helper collects
  runtime checks; ordinary use needs no caller-prepared context/evidence files.
  Preserve explicit invocation overrides. Retained chat discovery text is diagnostic,
  not a selection or veto. Verify actual task access to the current manifest, entrypoint
  and resources, keeping unrelated copies disabled. Access grants no new tool or
  connector permission. Do not migrate to an undeployed entrypoint. Earlier
  catalog-veto wrappers require an explicitly authorized prompt synchronization.
- Render with `scripts/manage.py render --registry <path> --project <key>`.
  For an existing task, review the old policy and preserve project-specific
  exceptions in `extra_boundaries`, not copied policy or ad-hoc prompt patches.
  Migration replaces only the prompt with the reference wrapper through the app
  tool. The caller must authorize the change to following future installed policy;
  retain the existing ID, registry binding and task settings.
- Re-read immediately before dispatch. Preserve all existing non-prompt fields
  (including schedule, destination, model/effort, status and notifications) unless
  a specific change was requested. A destination mismatch or duplicate requires
  reconciliation, not an automatic repair. State the intended change clearly.
- After the tool returns, read the actual saved task, compare the exact rendered
  prompt and preserved fields, then bind a newly created ID in the registry.
  On an ambiguous write, reconcile read-only; never blindly repeat creation or
  update. A failed read is not permission to create another task.
- Run audit again. Report verified matches separately from real run outcomes.
  Migrated tasks follow installed policy updates on their next invocation.
  Changed job bindings, fixed authority or wrapper contracts still need an
  authorized synchronization. Never auto-migrate old copied-policy tasks during
  a read-only audit.
- Pause/remove only the named registered review. Preserve the registry record
  until the scheduling change is verified; do not delete unrelated automations.

Read source conversations through the app's thread-reading tool, using pagination
when necessary. Do not export raw histories into this plugin or registry. Before
handing off new or materially revised policy, use a bounded synthetic review to
check useful-change, unchanged and missing-source cases without editing real
project files. Do not claim that this proves the timer or a real review succeeded.
