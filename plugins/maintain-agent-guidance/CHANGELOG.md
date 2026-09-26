# Changelog

## Purpose

Explain user-visible changes to Maintain Agent Guidance and any action users
must take when installing or updating it.

## Rationale

Users should be able to understand how a release affects capabilities,
compatibility, setup, data and safe use without reading development records.

## 0.2.1 — 2026-09-26

### Changed

- Shows `Leon.id Komarovsky` as both author and developer on the plugin card.
- Uses the `b2a48b-public` marketplace name in installation and recovery
  instructions. The public GitHub repository and support URLs are unchanged.

Users with an existing installation should follow the marketplace migration
instructions before updating. Review policy, saved task references, project
registry and root-AGENTS.md-only authority are unchanged; no schedule rewrite
is required for this release.

## 0.2.0 — 2026-09-20

### Changed

- Renames the plugin from AGENTS.md Self-Improvement to Maintain Agent Guidance
  and changes its installed ID to `maintain-agent-guidance`.
- Moves the default private registry to
  `$CODEX_HOME/maintain-agent-guidance/projects.json`.
- Updates saved reference wrappers to select the new plugin identity while
  retaining the stable `$agents-md-review` entry point and
  `plugin-reference/v1` job contract.

Existing users must install the renamed plugin, move their registry to the new
path and synchronize each saved review prompt once. Schedule IDs, recurrence,
destinations, notifications, project bindings and fixed authority stay the same.
After the migrated schedules pass audit, remove the old plugin copy and old
registry path.

## 0.1.7 — 2026-09-20

### Added

- Adds a complete consumer guide, public changelog, marketplace logo and
  deliberate presentation metadata for both bundled skills.
- Adds three distinct starter requests and clearer marketplace capabilities for
  auditing schedules, adding reviews and migrating saved tasks.

### Changed

- Rewrites listing and README copy around user results, effects, limitations,
  recovery and support.
- Links the plugin website to its public marketplace package and support to the
  public marketplace issue tracker.

No schedule migration is required. Review policy 1.0.0, task wrappers, runtime
selection and the root-AGENTS.md-only write boundary are unchanged.

## 0.1.5 — 2026-09-19

### Changed

- Linked the public marketplace package and added the standard distribution
  disclaimer.

Runtime policy and review behavior were unchanged.

## 0.1.4 — 2026-09-18

### Fixed

- Resolved the enabled installed package from fresh Codex CLI inventory even
  when an existing task's skill catalog still described an older version.
- Rejected stale helpers, mismatched manifests, symlinked resources and unknown
  installation layouts before review.

Existing 0.1.3 reference wrappers required one synchronization to adopt the
live-inventory discovery contract.

## 0.1.3 — 2026-09-18

### Added

- Added the stable `agents-md-review` execution entry point and
  `plugin-reference/v1` task contract.
- Added live policy loading with installed version, policy version and SHA-256
  provenance.

### Changed

- Scheduled tasks retain project bindings and fixed authority while loading
  shared policy from the enabled plugin. Legacy copied-policy schedules require
  a one-time migration.

## 0.1.2 — 2026-09-18

### Added

- Added consumer documentation, the MIT license, data-handling details and a
  public support route.

### Changed

- Documented installed use, support, data handling and failure boundaries.

## 0.1.1 — 2026-09-17

### Changed

- Standardized scheduled task names as `Improve <project> AGENTS.md`.

## 0.1.0 — 2026-09-11

### Added

- Added the external project registry, deterministic task rendering and
  read-only schedule drift audit.
- Added bounded review policy with a root-AGENTS.md-only write boundary and
  byte-for-byte no-op behavior when evidence does not support a change.
