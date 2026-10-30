# Privacy

Expert Roles is a local file-management workflow. The Python helper makes no
network requests, sends no telemetry, and requires no account or service
credentials. Downloading the plugin uses the configured marketplace connection.

## What it reads and returns

The helper reads bundled role files, the selected personal Codex home, native
agent files and relevant personal/project Codex configurations to identify role
registrations and conflicts. It parses configuration locally; unrelated values
and credentials are not returned or stored by the manager.

Command output can include expert names, local file paths, content digests,
library provenance, ownership and conflict or recovery status. Review that
output before sharing it. When run through Codex, output and task context are
handled by your configured Codex client and account; the helper's lack of
network requests does not mean that your Codex conversation stays on the device.

## What it stores and changes

An explicit apply operation can create one selected personal role or remove an
unchanged role that the manager previously created. Existing manual files are
not adopted or overwritten. The helper never edits Codex configuration or
unrelated roles.

Ownership records, the library license, an operation lock and any recovery
files live in `expert-roles/` under the selected Codex home. Records use relative
role destinations and library version, commit and digest provenance. A failed
operation can retain staged or captured role contents for explicit recovery.
See the [README](README.md#failure-recovery-and-removal) before changing them.

Removing a managed role clears its ownership entry. The management directory
and license can remain. Uninstalling the plugin does not automatically remove
native roles, management records or recovery data. There is no remote deletion
service or background retention process.

## Support

The maintainer receives no local files or diagnostic output automatically. If
you choose to post an issue, share only the minimum needed and exclude secrets,
private role instructions, personal data and raw traces. Public issues are
visible to others. Use the [support tracker](https://github.com/shpoont/codex-marketplace/issues).
