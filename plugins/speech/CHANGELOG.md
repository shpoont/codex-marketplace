# Changelog

## Purpose

Explain changes to Speech and any action needed when installing or updating it.

## Rationale

Users should understand capabilities, compatibility and safe use without
reading development history.

## Unreleased

### Added

- Generation: local Kokoro narration with voice, language, speed and
  pronunciation guidance.
- Recognition: local Whisper transcripts, English translations and timed
  subtitles, with batch output collision and overwrite checks.
- Portable local wrappers and transparent ribbon artwork for Speech and both
  skills.

### Compatibility

- Requires Apple silicon and existing MLX speech environments/models; installing
  Speech does not install or upgrade them.
- Users moving from standalone Kokoro/Whisper skills should verify the new
  workflows before removing older copies and keep one enabled provider per job.
- Existing engine defaults are retained. Choose Sarah/Puck explicitly when
  using the Kokoro wrapper and always select a new output path.
