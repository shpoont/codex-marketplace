# Expert Roles

## Purpose

Browse a reviewed collection of 72 expert roles and manage selected personal
native agents in Codex while preserving manual files and local edits. Canonical
role content comes unchanged from the
[Expert Roles v1.4.0 library](https://github.com/shpoont/expert-roles/tree/611ec7136b52bca5994e93311d2b913af57fb519).

## Rationale

Choose the perspectives you need without maintaining a separate role collection.
The manager preserves canonical wording and treats existing manual roles and
your local edits as files it must protect.

## Install and start

Version `0.1.0` is the first personal-role manager. Install
`expert-roles@b2a48b` from the existing marketplace in your Codex plugin browser.
For the CLI:

```sh
codex plugin marketplace add shpoont/codex-marketplace --ref main
codex plugin add expert-roles@b2a48b
```

Start a new Codex chat after installation. Your first useful request is:

> Show available Expert Roles and inspect my installed expert versions without
> changing anything.

Expect the reviewed expert collection and a report distinguishing manual,
managed and modified files. This request changes nothing. You can also run the
`manage-experts` skill explicitly. The [package page](https://github.com/shpoont/codex-marketplace/tree/main/plugins/expert-roles)
and [support tracker](https://github.com/shpoont/codex-marketplace/issues) provide
public documentation and help.

## Requirements and supported workflow

Use a local Codex client on macOS or Linux, with Python 3.12+ available. The
helper uses the standard library, including POSIX file locking. It needs no
account, service credentials, network
connection, MCP server or system-level dependency installation. Plugin download
uses the marketplace connection; ordinary helper commands run locally.

The `manage-experts` skill supports these requests:

- List the bundled experts and inspect versions and ownership.
- Preview or install one selected expert personally.
- Preview or remove one unchanged plugin-created expert.
- Inspect and explicitly resume an interrupted operation.

Updates, adoption of manual files, project installation, multi-expert operations
and automatic expert invocation are deferred. Installing a file makes no claim
that Codex has loaded or invoked it. A fresh-session native-role check is a
separate verification step after installation is authorized.

## Locations and direct commands

Package resources resolve relative to the helper's installed location, so it
works outside its checkout and from any current directory. Personal destinations
resolve in this order:

1. An explicit absolute `--codex-home` argument.
2. The non-empty absolute `CODEX_HOME` environment variable.
3. `.codex` under the current user's home directory.

Native files go under that directory's `agents/`. Ownership, the library license,
an operation lock and recovery files go under `expert-roles/`, outside agent
discovery. Ownership records contain relative role paths, library version,
commit, digest and the fact that the manager created the file. No author-machine
path or fixed username is used. Relative or empty configured homes are rejected.

For direct use, locate the installed `manage-experts` skill and set `SKILL_DIR`
to its actual absolute directory. Run with an available Python 3.12+ interpreter:

```sh
python "$SKILL_DIR/scripts/manage.py" list
python "$SKILL_DIR/scripts/manage.py" status
python "$SKILL_DIR/scripts/manage.py" install steve-jobs
python "$SKILL_DIR/scripts/manage.py" install steve-jobs --apply
python "$SKILL_DIR/scripts/manage.py" remove steve-jobs
python "$SKILL_DIR/scripts/manage.py" remove steve-jobs --apply
```

All commands return JSON. Install/remove commands preview unless
`--apply` is supplied; each accepts one canonical expert ID from `list`.
Global options such as `--codex-home` must appear before the command.
`--project` changes only which project directory is inspected for conflicts;
it never changes the personal write destination. Without it, the current
working directory and its ancestor `.codex` directories are inspected.

## Ownership, conflicts and data effects

`status` distinguishes available, plugin-managed, missing, modified, unmanaged,
matching-manual and conflicting definitions. `manual-match` means an exact match
to bundled bytes, with no plugin ownership. Existing files are never adopted,
overwritten or removed, including identical manual copies. A modified managed
file retains its recorded library version, but that version no longer verifies
its current contents.

The helper reads native agent files recursively and relevant personal/project
agent registrations. It refuses changes on competing definitions, incomplete
inspection, unsafe paths or user edits. Project configurations are inspected
conservatively without assuming that the project is trusted. Other configuration
layers or per-session overrides may still affect actual host behavior.

Apply operations change only the selected personal role and the manager's own
state. They never edit Codex configuration, model choices, permissions, project
files or unrelated roles. New roles are published without overwriting a file
that appeared after inspection; state records and a pending journal support
recovery. Installation requires hard-link support, with `agents/` and
`expert-roles/` on the same filesystem. An `EXDEV` or unsupported-filesystem
failure leaves the staged data and journal for inspection without creating the
native role. Resolve the filesystem limitation before explicitly resuming;
do not substitute a copy or overwrite operation.
There is no telemetry or runtime network access. Inspection output includes
local paths; review it before sharing.

## Failure, recovery and removal

If a command fails, inspect `status` or `recover` before assuming nothing changed.
A staged or captured file and `pending.json` can remain in the management
directory. Other mutations stop while an operation is pending.

```sh
python "$SKILL_DIR/scripts/manage.py" recover
python "$SKILL_DIR/scripts/manage.py" recover --apply
```

Recovery resumes only the recorded operation after validating ownership, bytes
and conflicts. Identical external bytes do not establish ownership. A changed
or partial recovery file requires a user decision: it is retained, and automatic
recovery stops. Preserve the files and seek support; do not delete the journal,
force an overwrite or change configuration to bypass the conflict. An unrelated
editor does not honor the manager's lock; edit races are detected where possible
and captured data is preserved for review.

Remove managed experts before uninstalling the plugin. Uninstalling the bundle
alone leaves installed native files and management records. Reinstalling the
manager can inspect those records. Upgrading the plugin does not update installed
roles; updates and adoption remain unsupported in this increment.

## Support, version and license

Use the [marketplace issue tracker](https://github.com/shpoont/codex-marketplace/issues).
Describe the expected outcome without credentials, private instructions, personal
data or raw traces. See [CHANGELOG.md](CHANGELOG.md) for versioned changes.
See [Privacy](PRIVACY.md) for local data handling and [Terms](TERMS.md) for the
license and use conditions.

Canonical role files retain the MIT notice in [library/LICENSE](library/LICENSE),
which is also preserved with managed installations. The integration code and instructions also use the [MIT license](LICENSE).
Keep both notices with redistributed copies.
These AI roles interpret publicly documented expert work; they do not represent
or carry endorsements from the named people or their estates or organizations.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
