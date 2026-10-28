---
name: official-upload-parity-experiments
description: Official Harbor Upload Parity Experiments workflow, packaged with local safeguards. Create or reuse Hugging Face dataset PRs for `harborframework/parity-experiments` and upload Harbor parity/oracle result folders efficiently with sparse checkout, raw git pushes, and Git LFS. Creation and uploads require explicit destination/content approval.
---

# Official Harbor Upload Parity Experiments

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
