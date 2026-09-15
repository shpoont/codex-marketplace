# Shpoont Plugins

Public marketplace for released Codex plugins maintained by shpoont.

## Catalog

The marketplace is defined in [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json).
Its identifier is `shpoont-public`, and its display name is
**Shpoont Plugins**.

The catalog currently contains no plugins. Each plugin is developed in its own
private source repository; this marketplace contains the deployable release
files under `plugins/<plugin-name>/`. Catalog entries use local paths within
this repository. Installing a package does not require access to its source repo.

## Register the marketplace

Once the catalog has been committed and pushed to GitHub, run:

```sh
codex plugin marketplace add shpoont/codex-marketplace-public --ref main
```

Use the Codex app's Plugins Directory to browse and install plugins
as they become available.

## Refresh the catalog

```sh
codex plugin marketplace upgrade shpoont-public
```

Test public release candidates in the private `shpoont-public-development`
marketplace, hosted in `codex-marketplace-public-development`. The matching stable source
tag requests promotion of that exact tested package. Package files and the
catalog are published together; private source history is not exported.

Plugins intended to remain private are released through `shpoont-private`,
hosted in `codex-marketplace-private`.

Release procedures and tooling belong in the separate private
`codex-plugins-operations` repository. Initial tooling has been reviewed;
live releases have not been activated.

See the [OpenAI marketplace documentation](https://developers.openai.com/plugins/build/plugins#marketplace-metadata)
for the catalog format.
