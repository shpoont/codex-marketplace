---
name: official-harbor-exec
description: 'Official Harbor Exec workflow, packaged with local safeguards. Use when working with Harbor''s `harbor exec` CLI workflow: compiling files, directories, or globs into Harbor tasks; running map jobs; configuring artifacts and existence-only verification; using map-reduce; writing or reviewing ExecConfig YAML/JSON/TOML; or debugging command behavior, config validation, and job outputs.'
---

# Official Harbor Exec

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
