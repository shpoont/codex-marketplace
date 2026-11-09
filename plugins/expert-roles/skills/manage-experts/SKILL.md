---
name: manage-experts
description: List Expert Roles, inspect versions and ownership, or install, update, explicitly adopt and remove one selected personal expert while preserving user edits. Use for managing personal native Expert Roles in Codex; project writes and expert invocation are outside this workflow.
---

# Manage Expert Roles

Use the bundled deterministic helper for all inspection and changes. Do not
copy, rewrite, register, invoke or delete roles yourself. Expert wording belongs
to the [canonical library](https://github.com/shpoont/expert-roles).

## Locate and inspect

1. Locate this installed skill's directory and its `scripts/manage.py`.
   Resolve resources relative to this skill, never from a remembered checkout,
   cache version or current working directory.
2. Use an available Python 3.12+ interpreter on macOS or Linux. The helper uses
   only the standard library. If unavailable, report the prerequisite; do not
   install or upgrade system software.
3. Run the helper with `list` or `status` as appropriate. Commands return JSON.
   For example, with `SKILL_DIR` set to this skill's actual absolute directory:

   ```sh
   python "$SKILL_DIR/scripts/manage.py" list
   python "$SKILL_DIR/scripts/manage.py" status
   ```

The personal destination is `CODEX_HOME/agents`, or `~/.codex/agents` when
`CODEX_HOME` is unset. An explicit absolute `--codex-home` before the command
overrides it. Never substitute the author's home or infer another user's root.
`--project` selects a directory to inspect for conflicting project definitions;
it never selects a write destination. By default the helper inspects the current
directory and ancestor `.codex` directories, including personal registrations.

Report the bundled release separately from installed records. `manual-match`
means verified matching bytes without plugin ownership. `modified` means the
recorded version no longer establishes current contents. Report inspection
issues and pending recovery; do not claim an active role from file presence.

## Change one selected personal expert

Use the exact expert ID from `list`; one command accepts one expert.

```sh
python "$SKILL_DIR/scripts/manage.py" install steve-jobs
python "$SKILL_DIR/scripts/manage.py" install steve-jobs --apply
python "$SKILL_DIR/scripts/manage.py" remove steve-jobs
python "$SKILL_DIR/scripts/manage.py" remove steve-jobs --apply
```

Without `--apply`, these commands only preview. Explain the selected expert,
destination and outcome. A clear user request to install or remove that expert
authorizes the matching apply operation; honor any preview-only or no-install
constraint. Do not convert an inspection request into a write.

Install never overwrites or adopts an existing file. Only an unchanged
plugin-managed file can be removed. Project definitions,
explicit registrations, duplicates, edits, unsafe paths or incomplete inspection
block changes. Explain the conflict; do not rename, merge, delete, modify
configuration or use a different installation method to bypass it.

The helper records ownership and library provenance in `CODEX_HOME/expert-roles`
(using the same home default). It preserves the library license there. It does
not change model choices, permissions, settings or unrelated roles.

## Update or adopt one selected personal expert

Plugin upgrades do not update personal roles. Use `update` for one unchanged
managed role. For a manual file, `--adopt` is an explicit ownership decision:
the helper accepts only exact bytes from a reviewed canonical release. Unknown
or edited files require a user decision; never normalize or replace them yourself.

```sh
python "$SKILL_DIR/scripts/manage.py" update steve-jobs
python "$SKILL_DIR/scripts/manage.py" update steve-jobs --adopt
```

These are read-only previews. Report current and target versions/hashes, the
ownership change, and that successful updates retain no original backup. A request
to update an existing manual expert must explicitly authorize adoption before applying it. For an
authorized update, take `plan_sha256` from that preview and pass it unchanged:

```sh
python "$SKILL_DIR/scripts/manage.py" update steve-jobs --adopt --expect-plan "$PLAN_SHA256" --apply
```

Omit `--adopt` for a managed role. Changed bytes, modes, provenance, destination
or project context invalidate the preview. Do not silently substitute a new
preview hash after an apply refusal. Each command changes only its selected role;
update a requested set only by selecting those IDs, never all bundled experts.
Updates keep a captured original outside discovery only while pending. Successful
completion removes it; version/hash history remains without a rollback copy.

## Recovery and limits

On failure, do not claim nothing changed: a journal or staged/captured file may
remain. Run `status` or `recover` to inspect. `recover --apply` explicitly resumes
the recorded operation after checking ownership, bytes and conflicts. Use it
only when resuming that operation is authorized. Changed or ambiguous recovery
files are preserved for a user decision; never discard them to force progress.

Project writes, multi-expert commands and cleanup of older retained backups are
deferred. Successful updates automatically remove their own temporary files.
Complete pending updates with the helper that started them before changing the
bundle; another version may require the original reviewed snapshot.
Remove managed roles before uninstalling the plugin; uninstalling the package
alone leaves native roles and management records. Reinstalling this manager can
inspect those records again.

Native Codex discovery and invocation require a separate fresh-session check.
Report filesystem results as filesystem results. Do not run experts or claim
runtime verification as part of managing files. See the [package README](../../README.md)
for scope, requirements and support.
