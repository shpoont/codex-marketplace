# Shpoont Public Release Test

Read the version and marker from this installed package. This permanent test
plugin helps an operator check which package a client has loaded during a
release or update. Its output alone does not prove marketplace identity,
publication success or the health of the wider release system.

## Requirements

- Codex with Git-backed plugin marketplaces. The baseline was verified with
  Codex CLI 0.154.0 on macOS; desktop presentation and other clients have not
  been verified for this plugin.
- Git and access to the public marketplace for installation.

The skill itself needs no credentials, extra runtime, external service or paid
service beyond the Codex client used to run it. It only reads packaged data.

## Install

Add the marketplace and install the explicitly qualified plugin:

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace-public.git --ref main
codex plugin add public-release-test@shpoont-public
codex plugin list --marketplace shpoont-public
```

These commands install the version currently published in that marketplace.
Start a fresh task after installation and check the reported installed version.

Public-development testing uses a separate, access-controlled marketplace.
Operators should select one channel explicitly and check that channel in the
plugin list; the marker does not distinguish public from development copies.

## Use

Ask: **Run the public release check.**

You can also ask: **Which version and marker of the Shpoont Public Release
Test plugin is installed?**

For this package, the expected response is:

```text
SHPOONT PUBLIC RELEASE TEST | version 0.1.1 | marker shpoont-public-002
```

The skill reads [release-marker.json](release-marker.json) at runtime. That file,
not this example, supplies the answer. It makes no marketplace changes and
does not start publication.

## Files

| Path | Purpose |
| --- | --- |
| [.codex-plugin/plugin.json](.codex-plugin/plugin.json) | Identity, version and display metadata |
| [skills/public-release-check/SKILL.md](skills/public-release-check/SKILL.md) | Trigger, reading procedure, output and failure handling |
| [release-marker.json](release-marker.json) | Installed version and recognizable release marker |
| README.md | Consumer instructions, changes and license status |

## Update and remove

Refresh the selected marketplace, install its currently selected package and
start a fresh task:

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin add public-release-test@shpoont-public
codex plugin list --marketplace shpoont-public
```

Run the check again and compare the installed version with the expected release.
A source edit or refreshed catalog alone is not proof that the installed package
changed. To remove this plugin:

```sh
codex plugin remove public-release-test@shpoont-public
```

The plugin creates no persistent application data to clean up. Marketplace
registration is shared with other plugins and can remain configured.

## Troubleshooting and support

- **Plugin unavailable:** check the marketplace registration, repository access
  and qualified name, then refresh the marketplace and open a fresh task.
- **Old version or wrong channel:** inspect the qualified plugin list and repeat
  the update steps. Do not edit the installed marker to make a test pass.
- **Missing, unreadable or invalid marker:** the check should report failure.
  Reinstall the selected package and report the problem if it persists.
- **Release or recovery failure:** Shpoont owns marketplace recovery. Operators
  restore a verified version through the release process and verify the client
  again; consumers should not move tags or edit marketplace receipts.

Report a problem through the [public marketplace issue tracker](https://github.com/shpoont/codex-marketplace-public/issues).
Include the client version, qualified plugin name, expected/observed version
and error. Do not include credentials or unrelated conversation content.

## Data and permissions

The workflow reads its skill and marker files and returns their contents in the
conversation. It writes no files and initiates no network requests. Marketplace
installation and refresh use GitHub through the client; normal Codex conversation
processing follows the client's own configuration. The plugin has no telemetry,
server, credential store, background process or bundled third-party code.

## Release notes

- **0.1.1:** complete consumer setup, update, removal, troubleshooting and support
  documentation; clarify the check's scope and reject invalid marker data.
  Marker changes to `shpoont-public-002` for update verification.
- **0.1.0:** initial installed-version and marker check.

## License status

No open-source license is specified for this package. It bundles no third-party
code requiring additional notices. Shpoont is the contact for licensing questions.
