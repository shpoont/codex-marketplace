# Changelog

## Purpose

User-visible changes to Safari Use and any action required when installing or
updating it.

## Rationale

Users should be able to understand changes to Safari automation, compatibility,
data access and safe-use boundaries without reading private development records.

## 0.1.1 — 2026-09-24

### Changed

- Reframed the marketplace card around letting an agent use Safari for practical
  web tasks in the user's existing browser session.
- Replaced implementation-led listing copy with concrete jobs: inspecting pages
  and tabs, reading visible content, clicking visible controls and verifying
  page changes.
- Updated the visible skill row and starter prompts to match the broader,
  user-facing presentation while preserving the established Safari procedure,
  helper scripts and window/focus boundaries.

### Required action

- None. Existing Safari and macOS permission requirements are unchanged.

## 0.1.0 — 2026-09-23

### Added

- Packaged the established Safari Use workflow for installation from the public
  marketplace.
- Added explicit Safari window-ID targeting, live tab and page inspection,
  visible-control clicking and observe → act → observe verification.
- Added explicit handling for real zero-tab windows and cleanup results,
  including the `empty_window_persisted` blocker.
- Documented read-only advisory Tab Group inspection, signed-in Safari session
  effects, permissions, limitations, removal and recovery.
- Added public listing metadata and visual assets without changing the original
  Safari procedure or four helper scripts.
- Added the MIT License selected by the owner for the distributed package.
- Presented the Safari skill with a concise user-facing result and natural first
  request instead of internal implementation instructions.

### Required action

- Enable Safari's **Allow JavaScript from Apple Events** setting and grant macOS
  Automation permission before using page probes or clicks.
