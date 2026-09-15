# Shpoont Public Release Test

A permanent test plugin for the Shpoont public marketplace release process.

Ask: **Run the public release check.**

The response reads the version and marker from this installed package. For the
initial package, expect:

```text
SHPOONT PUBLIC RELEASE TEST | version 0.1.0 | marker shpoont-public-001
```

This plugin performs no network requests and needs no credentials. Its response
checks package contents; verify the selected marketplace separately.
