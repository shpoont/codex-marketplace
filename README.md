# b2a48b

Public production marketplace for b2a48b Codex plugins.

## Catalog

[marketplace.json](.agents/plugins/marketplace.json) lists available plugins.
The marketplace identity is `b2a48b-public`; its display name is **b2a48b**.
Each catalog entry points to a complete installable package under
`plugins/<plugin-id>/`. Everything an end user needs to understand, install,
use, update and remove a listed plugin is published in this repository.

## Register, install and update

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git --ref main
codex plugin list --marketplace b2a48b-public
```

Choose a plugin from the catalog and replace `PLUGIN_ID` below with its name:

```sh
codex plugin add PLUGIN_ID@b2a48b-public
codex plugin marketplace upgrade b2a48b-public
codex plugin add PLUGIN_ID@b2a48b-public
```

Refreshing the catalog and updating an installed plugin are separate operations.
Start a fresh Codex task after installation or update and follow the selected
plugin's README for prerequisites, prompts, supported clients and verification.
Use the qualified identity to distinguish copies from different marketplaces.

To uninstall a selected plugin:

```sh
codex plugin remove PLUGIN_ID@b2a48b-public
```

## Support

Report problems in [marketplace Issues](https://github.com/shpoont/codex-marketplace/issues).
