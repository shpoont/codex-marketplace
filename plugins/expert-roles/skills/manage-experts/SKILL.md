---
name: manage-experts
description: List bundled Expert Roles, inspect personal native-agent installations and versions, or install and remove one selected expert while preserving manual roles and user edits. Use for managing Expert Roles in Codex; updates, adoption and project installation are not supported yet.
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

Existing files are never overwritten or adopted, even when byte-identical.
Only an unchanged plugin-created file can be removed. Project definitions,
explicit registrations, duplicates, edits, unsafe paths or incomplete inspection
block changes. Explain the conflict; do not rename, merge, delete, modify
configuration or use a different installation method to bypass it.

The helper records ownership and library provenance in `CODEX_HOME/expert-roles`
(using the same home default). It preserves the library license there. It does
not change model choices, permissions, settings or unrelated roles.

## Recovery and limits

On failure, do not claim nothing changed: a journal or staged/captured file may
remain. Run `status` or `recover` to inspect. `recover --apply` explicitly resumes
the recorded operation after checking ownership, bytes and conflicts. Use it
only when resuming that operation is authorized. Changed or ambiguous recovery
files are preserved for a user decision; never discard them to force progress.

Updates, manual-role adoption, project writes, multi-expert operations and
automatic cleanup are deferred. Plugin upgrades do not update installed roles.
Remove managed roles before uninstalling the plugin; uninstalling the package
alone leaves native roles and management records. Reinstalling this manager can
inspect those records again.

Native Codex discovery and invocation require a separate fresh-session check.
Report filesystem results as filesystem results. Do not run experts or claim
runtime verification as part of managing files. See the [package README](../../README.md)
for scope, requirements and support.
