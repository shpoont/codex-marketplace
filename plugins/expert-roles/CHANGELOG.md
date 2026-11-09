# Changelog

## Purpose

Describe user-visible changes and any actions required when Expert Roles is
released or updated.

## Rationale

Users should be able to understand capabilities, compatibility, setup and data
effects from the distributed documentation.

## 0.2.2 — 2026-11-09

- Bundle the 74 experts from published canonical library v2.0.0. Expert IDs,
  descriptions, nicknames and instructions are unchanged from v1.5.0; only the
  library version comments change in the role files.
- Recognize exact v1.5.0 exports alongside the reviewed earlier releases.
  Existing personal roles, ownership and backups are preserved. A plugin upgrade
  does not install, update or adopt personal roles automatically.

## 0.2.1 — 2026-11-04

- Add Von Glitschka and Yukio Miyamoto from canonical library
  v1.5.0 (74 bundled experts). Existing personal roles are preserved; plugin upgrades do not install
  or update roles automatically.
- Preserve exact historical recognition hashes as the catalogue grows. Refuse
  an incomplete package whose required recognition catalogue is missing.

## 0.2.0 — 2026-11-03

- Add one-expert update previews with a frozen plan hash required for apply.
- Allow explicit adoption of unchanged recognized canonical manual exports;
  preserve edited files and refuse conflicting definitions or downgrades.
- Retain original backups, captured sources and provenance with interrupted
  update recovery. Recovery rechecks the approved preview and journal integrity
  before resuming. Preserve existing schema-1 ownership compatibility.
- Continue bundling unchanged library v1.4.2 exports. Plugin upgrades alone do
  not update personal roles; each update/adoption must be requested explicitly.

## 0.1.2 — 2026-11-02

- Bundle 72 unchanged Codex exports from Expert Roles library v1.4.2, adding
  expert-name nicknames compatible with the current Codex character rule.
  Role IDs, descriptions, instructions and paths are preserved.
- Preserve existing personal files during a plugin upgrade. Earlier manual
  copies may show as `unmanaged` against the new bundle; plugin-created roles
  retain their recorded version and ownership. Personal-role updates remain
  unsupported, so existing roles are not automatically replaced.
- Complete pending operations before upgrading. An interrupted installation
  without staged bytes needs its original reviewed plugin snapshot for recovery.

Naming is verified on Codex CLI 0.166.0. Existing conversations are not renamed;
desktop labels and older-host compatibility remain unverified.

## 0.1.0 — 2026-10-30

First personal-role manager for Codex.

- Bundle 72 unchanged native Codex exports from Expert Roles library v1.4.0,
  with exact commit/digest provenance and its MIT license notice.
- Add personal list/status and one-expert install/remove previews, with an
  explicit apply option and Python 3.12+ requirement on macOS or Linux.
- Recognize exact manual copies without adopting them; preserve existing files,
  user edits and unrelated roles, and report conflicting definitions.
- Record ownership outside agent discovery and retain interrupted-operation
  recovery records. Resolve destinations from the user's configured Codex home.

Updates, manual adoption, project writes and automatic invocation are deferred.
Plugin uninstall alone does not remove native files or management records.
The integration and copied library material use MIT, with both notices included.
