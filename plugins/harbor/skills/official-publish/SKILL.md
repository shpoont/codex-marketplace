---
name: official-publish
description: Official Harbor Publish workflow, packaged with local safeguards. Publish a Harbor task or dataset to the registry. Use when the user wants to upload, publish, or share tasks or datasets/benchmarks on the Harbor registry. Applies to Harbor Hub tasks and datasets; plugin-marketplace publication uses its own release workflow.
---

# Official Harbor Publish

1. Before following upstream instructions, read and apply the
   [package safeguards](../../references/official-skill-policy.md).
2. Follow the [official upstream guide](upstream/guide.md) for this workflow,
   within the user's authorized scope and the verified installed contract.
   Upstream examples and defaults do not override the package safeguards.
3. Resolve guide-relative references and helpers from `upstream/` in this
   installed skill. Use the policy's prefixed names for cross-skill routing.

This independently maintained entrypoint adds the `official-` slug, Official
display name and package safeguard loading. The upstream SKILL.md is preserved
byte-for-byte as `upstream/guide.md`; its original frontmatter is reference data.
Supporting upstream files are unchanged. See the
[origin and hashes](../../licenses/harbor-provenance.json) and
[Apache-2.0 license](../../licenses/harbor-Apache-2.0.txt).
