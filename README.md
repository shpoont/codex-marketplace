# Shpoont Plugins

Public production marketplace for Shpoont Codex plugins.

## Catalog

[marketplace.json](.agents/plugins/marketplace.json) lists available plugins.
The marketplace identity remains `shpoont-public`; its display name is **Shpoont Plugins**.
The catalog is currently empty and ready for the next plugin release.

The original release-test plugins were retired on 2026-09-17. Their packages and
current-release pointers have been removed. Immutable version receipts and Git
history remain as historical records, not installable catalog entries.

Each plugin is developed in a private source repository. Only selected package
files are distributed under `plugins/<plugin-id>/`; catalog entries point to
those local paths. Installation does not require access to private source or
operations repositories.

## Register, install and update

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git --ref main
codex plugin list --marketplace shpoont-public
```

Choose a plugin from the catalog and replace `PLUGIN_ID` below with its name:

```sh
codex plugin add PLUGIN_ID@shpoont-public
codex plugin marketplace upgrade shpoont-public
codex plugin add PLUGIN_ID@shpoont-public
```

Refreshing the catalog and updating an installed plugin are separate operations.
Start a fresh Codex task after installation or update and follow the selected
plugin's README for prerequisites, prompts, supported clients and verification.
Use the qualified identity to distinguish copies from different marketplaces.

To uninstall a selected plugin:

```sh
codex plugin remove PLUGIN_ID@shpoont-public
```

## Publication and support

Public releases promote the exact tested package from `shpoont-public-development`
using a stable source tag at the candidate commit.

The repository names and marketplace identities are separate:

| Marketplace | Repository | Visibility |
| --- | --- | --- |
| `shpoont-public` | `codex-marketplace` | Public |
| `shpoont-public-development` | `codex-marketplace-public-development` | Private |
| `shpoont-private` | `codex-marketplace-private` | Private |

Shared release tooling and private evidence belong in `codex-marketplace-operations`.
Source history and internal test evidence are not published with public packages.
Report problems in [marketplace Issues](https://github.com/shpoont/codex-marketplace/issues).
