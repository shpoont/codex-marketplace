# Changelog

## Purpose

Describe user-visible changes and any actions required when Expert Roles is
released or updated.

## Rationale

Users should be able to understand capabilities, compatibility, setup and data
effects from the distributed documentation.

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
