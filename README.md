# Shpoont Plugins

Public marketplace for released Codex plugins maintained by shpoont.

## Catalog

The marketplace is defined in [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json).
Its identifier is `shpoont-public`, and its display name is
**Shpoont Plugins**.

The catalog is active and includes the permanent
[public release-test plugin](plugins/public-release-test/README.md). Its
[current release receipt](.releases/current/public-release-test.json) identifies
the selected version and package checksum. The catalog is the complete list of
available plugins.

Each plugin is developed in its own private source repository. This public
repository contains the shipped files, including skill instructions, under
`plugins/<plugin-name>/`. Catalog entries use local paths within this repository;
installation requires no access to private source or operations repositories.

## Register the marketplace

Add the marketplace and install its release-test plugin:

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace-public.git --ref main
codex plugin add public-release-test@shpoont-public
codex plugin list --marketplace shpoont-public
```

Start a fresh Codex task and ask **Run the public release check.** Follow the
plugin's README for its expected output, troubleshooting and supported clients.
Installation and updates have been verified with Codex CLI on macOS; desktop
presentation has not been separately verified.

## Refresh and update

```sh
codex plugin marketplace upgrade shpoont-public
codex plugin add public-release-test@shpoont-public
codex plugin list --marketplace shpoont-public
```

Refreshing the catalog and updating an installed plugin are separate steps.
Start a fresh task after updating. Use the fully qualified plugin name to select
the intended marketplace when testing development and public versions.

## Publication and access

Test public release candidates in the private `shpoont-public-development`
marketplace, hosted in `codex-marketplace-public-development`. The matching stable source
tag requests promotion of that exact tested package. Package files and the
catalog are published together; private source history is not exported.

Plugins intended to remain private are released through `shpoont-private`,
hosted in `codex-marketplace-private`.

Release procedures and tooling belong in the separate private
`codex-plugins-operations` repository. Tag-based publication is active. Only the
selected deployable files and public version receipts are published here;
source history, test evidence and full publication records stay private.

Report installation or plugin problems in this repository's
[issue tracker](https://github.com/shpoont/codex-marketplace-public/issues).

See the [OpenAI marketplace documentation](https://developers.openai.com/plugins/build/plugins#marketplace-metadata)
for the catalog format.
