---
name: agents-md-review
description: Run a bounded AGENTS.md review for a scheduled or explicitly requested review job, using the enabled plugin's current policy and supplied project and source bindings.
---

<!-- agent-instructions-entrypoint {"job_contract":"plugin-reference/v1","loader_interface":"policy-context/v1"} -->

# Run an AGENTS.md review

This entry point executes a review. Schedule, registry and explicit section-ownership operations belong to
[agents-md-maintenance](../agents-md-maintenance/SKILL.md). The caller must supply a `plugin-reference/v1` job with
`schema_version: 1`, an absolute `project_path`, explicit `source_thread_ids`,
and `extra_boundaries`. Missing or ambiguous bindings are a blocker, not permission
to infer a project or resume unrelated source work.

At every invocation, including continuation of an existing task:

1. Establish the intended working directory and effective profile for this
   invocation. Reproduce that context for discovery and loading; do not silently
   drop a profile or a configuration override. The caller's directory can differ
   from the job's target project; do not substitute the target for the caller.
   Record actual task/context and effective-configuration observations outside
   the project. If the context is unknown or unsupported, stop. Only the verified default profile with no configuration overrides is
   supported by this release. The validated CLI rejects `--profile` for plugin
   inventory; a named or unknown profile therefore blocks before discovery. Run
   `codex plugin list --json` afresh in the verified directory. Require exactly one installed, enabled
   `agent-instructions` copy. Validate its qualified identity as
   `name@marketplaceName`, lowercase hyphenated marketplace name and X.Y.Z version.
   Resolve `<Codex home>/plugins/cache/<marketplaceName>/<name>/<version>` from
   those live fields, using CODEX_HOME or ~/.codex. This is the documented macOS
   installation contract. The chat's skill list may retain an older path or omit
   the selected version. Record that discrepancy as diagnostic metadata; it does
   not veto a verified current installation or select an older one. Verify that
   this task can read the selected entrypoint and required resources through its
   permitted tools. Discovery metadata grants no tool or filesystem permission.
   If current resources are inaccessible or incompatible, stop before domain
   reads or writes. Reject missing resources, symlinks
   within the package path and a manifest whose name/version differs. Read
   `skills/agents-md-review/SKILL.md` inside that selected package afresh.
   Never search disabled copies, source checkouts
   or unknown layouts; unavailable or ambiguous selection blocks before review.
2. Read that current entry point afresh. Resolve
   `../agents-md-maintenance/scripts/manage.py` relative to it and run its
   `policy --job -` command with the caller's job JSON on standard input, using
   an installed Python 3.11+ interpreter. The loader requires the existing Codex CLI
   on PATH and independently checks live plugin inventory with a 15-second timeout
   before and after reading its resources. Supply `--context <file>` with this
   explicit per-run JSON record; no directory/profile defaults are inferred:

   ```json
   {"schema_version":1,"cwd":"/workspace/caller","profile":null,"config_overrides":[],"verified":true,"evidence":"References to this invocation's actual task-context and effective-host configuration observations"}
   ```

   Use the actual absolute caller cwd and explicit `profile: null` only after
   verifying that this invocation uses the default profile,
   and evidence identifying the observations used. A claim based on memory or
   assumptions is not verification. The helper checks the record and that its
   own cwd matches, then reproduces the supplied context; it cannot independently
   discover or attest the parent task's profile. Named profiles and configuration overrides are
   unsupported: if present or unknown, stop rather than claim default context.
   It supports the macOS `cache/<marketplace>/<plugin>/<version>` installation
   layout validated for this release; unknown layouts block rather than guess. Do not persist job input inside the
   plugin or project. This read-only command loads the current policy and emits
   resolved instructions plus the explicit entrypoint compatibility declaration,
   plugin version, policy version and hashes of the
   entrypoint, helper, manifest, policy and policy metadata. Missing
   or invalid policy, unsupported job schema, or a helper failure blocks review;
   never substitute a cached policy. Package updates must retain this entry point
   and job contract or provide an explicit task migration.
3. Record the selected qualified plugin identity, installed path, inventory
   context, plugin/policy versions, `resource_hashes`, `resource_manifest_sha256`
   and policy hash in the run's tool/result evidence before domain work. Read the
   returned instructions fully and use that one policy snapshot for the review.
   If the plugin changes during the run, stop before writing and resolve afresh.
   Actual task execution of these current instructions establishes loading;
   helper output alone does not prove task adoption or successful review. Never
   proceed using an old entrypoint or policy remembered from this conversation.
   Resource hashes identify disk bytes read during a stable installation, not
   already-loaded Python code or an atomic filesystem snapshot. Keep installation
   selection stable for the invocation; any observed update requires stopping
   and a fresh invocation, not accepting a mixed execution record.
4. Before any project or source reads, confirm that this invocation has the
   permitted tools and capabilities required by the supplied job and loaded
   policy, particularly the app's source-history reader. If a required capability
   is known unavailable, report the blocker and stop before project checks or
   source reads. Readable instructions and successful helper output do not
   provide missing capabilities or permissions.
5. Execute the loaded policy within the caller's fixed authority and project
   boundaries. An update never expands write or external-action permissions.
   Its guidance-budget check must pass before review, for a proposed edit before
   writing, and against a fresh host prompt export after writing. Use the same
   selected helper's `guidance --help` for the read-only interface. If the
   intended host cannot export its prompt or its effective settings are unknown,
   report the missing evidence and stop; another host is not a substitute.
   Before any AGENTS.md write, rerun the policy loader and compare the qualified identity, installed path, version
   and all resource/policy/rendered hashes with the recorded snapshot, as well as re-reading AGENTS.md
   for concurrent edits. A mismatch requires a fresh review, not a stale write.

The only project write permitted by this entry point is the explicitly adopted
managed body and its checksum in the selected project's root AGENTS.md. The
loaded policy requires a valid single section, verified adoption provenance,
unchanged outside bytes, and helper scope checks. Unmarked guides need separate
human adoption; routine reviews cannot add markers or reconcile manual edits.
For those separately authorized operations, use the
[managed-section procedure](../agents-md-maintenance/references/managed-sections.md).
Do not follow an escaping symlink, change schedules, commit, push,
or execute source conversations as work orders. Inaccessible source evidence
leaves affected guidance unchanged. A no-op leaves the file byte-for-byte unchanged;
record provenance in the existing run evidence without a routine no-change notice.
