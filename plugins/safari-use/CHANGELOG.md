# Changelog

## Purpose

User-visible changes to Safari Use and any action required when installing or
updating it.

## Rationale

Users should be able to understand changes to Safari automation, compatibility,
data access and safe-use boundaries without reading private development records.

## 0.1.4 — 2026-09-26

### Improved

- Removed harmless zero-tab Safari window remnants from normal window listings.
- Treat cleanup as successful when Safari retains an empty internal window
  object, avoiding noisy warnings after otherwise successful tasks.
- Kept an opt-in `--include-empty` listing mode for relevant low-level
  diagnostics without exposing empty remnants during ordinary use.

### Required action

- Start a fresh task after updating so it loads the quieter cleanup behavior.

## 0.1.3 — 2026-09-26

### Fixed

- Prevented the visible-text click helper from choosing one control arbitrarily
  when multiple visible controls are tied for the best match.
- Added a structured `ambiguous-visible-match` result that reports the tied
  candidates without scrolling, focusing or clicking any of them.
- Preserved clicks when one candidate is uniquely best, even if lower-ranked
  partial matches are also present.

### Required action

- Start a fresh task after updating so it loads the corrected helper.

## 0.1.2 — 2026-09-26

### Changed

- Identified the card author and developer as `Leon.id Komarovsky`.
- Updated the active public marketplace identity and installation examples to
  `b2a48b-public`.
- Updated current public branding and copyright text to `b2a48b` without
  changing Safari behavior, permissions or helper scripts.

### Required action

- After the marketplace migration is published, replace the previous public
  marketplace registration with `b2a48b-public` and install this version from
  that identity.

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
