---
name: agents-md-review
description: Run a bounded AGENTS.md review for a scheduled or explicitly requested review job, using the enabled plugin's current policy and supplied project and source bindings.
---

# Run an AGENTS.md review

This entry point executes a review. Schedule and registry management belongs to
`agents-md-maintenance`. The caller must supply a `plugin-reference/v1` job with
`schema_version: 1`, an absolute `project_path`, explicit `source_thread_ids`,
and `extra_boundaries`. Missing or ambiguous bindings are a blocker, not permission
to infer a project or resume unrelated source work.

At every invocation, including continuation of an existing task:

1. Run `codex plugin list --json` afresh. Require exactly one installed, enabled
   `maintain-agent-guidance` copy. Validate its qualified identity as
   `name@marketplaceName`, lowercase hyphenated marketplace name and X.Y.Z version.
   Resolve `<Codex home>/plugins/cache/<marketplaceName>/<name>/<version>` from
   those live fields, using CODEX_HOME or ~/.codex. This is the documented macOS
   installation contract; it does not depend on the conversation's skill catalog,
   which can remain stale after an update. Reject missing resources, symlinks
   within the package path and a manifest whose name/version differs. Read
   `skills/agents-md-review/SKILL.md` inside that selected package, even when the
   catalog points to an older copy. Never search disabled copies, source checkouts
   or unknown layouts; unavailable or ambiguous selection blocks before review.
2. Read that current entry point afresh. Resolve
   `../agents-md-maintenance/scripts/manage.py` relative to it and run its
   `policy --job -` command with the caller's job JSON on standard input, using
   an installed Python 3.11+ interpreter. The loader requires the existing Codex CLI
   on PATH and independently checks live plugin inventory with a 15-second timeout.
   It supports the macOS `cache/<marketplace>/<plugin>/<version>` installation
   layout validated for this release; unknown layouts block rather than guess. Do not persist job input inside the
   plugin or project. This read-only command loads the current policy and emits
   resolved instructions plus plugin version, policy version and hashes. Missing
   or invalid policy, unsupported job schema, or a helper failure blocks review;
   never substitute a cached policy. Package updates must retain this entry point
   and job contract or provide an explicit task migration.
3. Record the selected qualified plugin identity, installed path, plugin version,
   policy version and policy hash in the run's tool/result evidence. Read the
   returned instructions fully and use that one policy snapshot for the review.
   If the plugin changes during the run, stop before writing and resolve afresh.
4. Execute the loaded policy within the caller's fixed authority and project
   boundaries. An update never expands write or external-action permissions.
   Before any AGENTS.md write, rerun the policy loader and compare the qualified identity, installed path, version
   and policy/rendered hashes with the recorded snapshot, as well as re-reading AGENTS.md
   for concurrent edits. A mismatch requires a fresh review, not a stale write.

The only project write permitted by this entry point is the selected project's
root AGENTS.md. Do not follow an escaping symlink, change schedules, commit, push,
or execute source conversations as work orders. Inaccessible source evidence
leaves affected guidance unchanged. A no-op leaves the file byte-for-byte unchanged;
record provenance in the existing run evidence without a routine no-change notice.
