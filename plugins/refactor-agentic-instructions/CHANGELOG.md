# Changelog

User-visible changes to Refactor Agentic Instructions and any action required when installing or updating it.

## 0.2.0 — 2026-09-20

### Changed

- Aligned the plugin ID with the marketplace name as `refactor-agentic-instructions`.
- Kept the two skill IDs, discovery-first workflow and refactoring behavior unchanged.

### Action required

- This version uses a new installation identity. Remove `agentic-instructions-refactoring@shpoont-public` if it is installed, then install `refactor-agentic-instructions@shpoont-public` and start a fresh task.

## 0.1.7 — 2026-09-20

### Changed

- Renamed the marketplace display name to **Refactor Agentic Instructions**.
- Kept the plugin ID, discovery-first workflow and refactoring behavior unchanged.
- After updating, start a fresh task so Codex loads the current package.

## 0.1.6 — 2026-09-20

### Changed

- Updated the public website and support destinations.
- Removed maintainer-only distribution details from the user documentation.
- Preserved the requirement that refactoring follows discovery and an explicit selection in the same task.
- After updating, start a fresh task so Codex loads the current package.

## 0.1.5 — 2026-09-20

### Fixed

- The refactoring skill now stops when the current task lacks a preceding discovery result or an explicit user-selected finding. It no longer inspects or edits the target to invent its own scope.

### Changed

- Added dedicated marketplace support and dark-theme brand metadata.
- After updating to this version, start a fresh task so Codex loads the corrected refactoring boundary.

## 0.1.4 — 2026-09-20

### Added

- Added recognizable icons for the plugin, discovery skill and refactoring skill.
- Added a task-oriented quick start, capability summary, data-and-effects disclosure and public changelog.

### Changed

- Rewrote marketplace descriptions, capabilities and starter prompts for faster scanning.
- Renamed the visible skill cards to `Review Agent Instructions` and `Apply Instruction Refactors` and clarified their one-line descriptions.
- After updating to this version, start a fresh task so Codex loads the current skill metadata.

## 0.1.3 — 2026-09-19

### Changed

- Standardized the advertised plugin ID.
- Added an audience-accessible public package page and the standard distribution disclaimer.
- Earlier installations may need to remove the old qualified plugin before installing `agentic-instructions-refactoring@shpoont-public`.

## 0.1.2 — 2026-09-19

### Added

- Published the first public marketplace release with separate skills for discovering instruction-refactoring opportunities and applying user-selected findings in the same task.
- Documented support for repository agents and local Codex instruction setups without adding connector, account or runtime dependencies.
