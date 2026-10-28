---
name: official-create-adapter
description: Official Harbor Create Adapter workflow, packaged with local safeguards. Scaffold a new Harbor benchmark adapter by running `harbor adapter init` and then guide implementation using the Adapters Agent Guide as the authoritative spec.
---

# Official Harbor Create Adapter

1. Read and apply the [package safeguards](../../references/official-skill-policy.md)
   in a completed first step before opening the upstream guide. Do not fetch
   these two documents concurrently.
2. Then read and follow the [official upstream guide](upstream/guide.md) for this
   workflow, within the user's authorized scope and the verified installed contract.
   Upstream examples and defaults do not override the package safeguards.
3. Resolve guide-relative references and helpers from `upstream/` in this
   installed skill. Use the policy's prefixed names for cross-skill routing.

This independently maintained entrypoint adds the `official-` slug, Official
display name and package safeguard loading. The upstream SKILL.md is preserved
byte-for-byte as `upstream/guide.md`; its original frontmatter is reference data.
Supporting upstream files are unchanged. See the
[origin and hashes](../../licenses/harbor-provenance.json) and
[Apache-2.0 license](../../licenses/harbor-Apache-2.0.txt).
