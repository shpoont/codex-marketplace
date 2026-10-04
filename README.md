# b2a48b

Marketplace for b2a48b Codex plugins.

## Catalog

[marketplace.json](.agents/plugins/marketplace.json) lists available plugins.
The marketplace identity is `b2a48b`; its display name is **b2a48b**.
Each catalog entry points to a complete installable package under
`plugins/<plugin-id>/`. Everything an end user needs to understand, install,
use, update and remove a listed plugin is published in this repository.

## Register, install and update

If this repository is already registered under another marketplace name, remove
its installed plugin copies and that registration before adding it again. Use
`codex plugin list` and `codex plugin marketplace list` to identify those names.

Remove each old copy, then remove the old registration once:

```sh
codex plugin remove PLUGIN_ID@OLD_MARKETPLACE_ID
codex plugin marketplace remove OLD_MARKETPLACE_ID
```

Use the commands below to register the current name and reinstall each plugin.

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git --ref main
codex plugin list --marketplace b2a48b
```

Choose a plugin from the catalog and replace `PLUGIN_ID` below with its name:

```sh
codex plugin add PLUGIN_ID@b2a48b
codex plugin marketplace upgrade b2a48b
codex plugin add PLUGIN_ID@b2a48b
```

Refreshing the catalog and updating an installed plugin are separate operations.
Start a fresh Codex task after installation or update and follow the selected
plugin's README for prerequisites, prompts, supported clients and verification.
Use the qualified identity to distinguish copies from different marketplaces.

To uninstall a selected plugin:

```sh
codex plugin remove PLUGIN_ID@b2a48b
```

## Renamed plugins

| Previous plugin ID | Current plugin ID |
| --- | --- |
| `refactor-agentic-instructions` | [`agent-instructions-refactoring`](plugins/agent-instructions-refactoring/README.md) |

For an older installation, follow the current plugin README to install and
select its replacement. Verify the new copy before removing the old one.
The replacement uses a new plugin ID; updating the old copy does not rename it.

## Support

Report problems in [marketplace Issues](https://github.com/shpoont/codex-marketplace/issues).
