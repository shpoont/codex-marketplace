---
name: public-release-check
description: Check the version and marker of the installed Shpoont Public Release Test plugin when asked to run its release check.
---

Read [the installed release marker](../../release-marker.json). Use its actual
`version` and `marker` values to return exactly:

```text
SHPOONT PUBLIC RELEASE TEST | version <version> | marker <marker>
```

If the file is missing or unreadable, report that failure. Do not substitute an
expected version or marker. This checks the installed package's contents; it
does not establish which marketplace supplied it or prove the release workflow
succeeded. Check marketplace identity separately if the user asks.
