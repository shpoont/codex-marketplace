---
name: speech-recognition
description: Use local Whisper speech-to-text in a computer-agnostic way. Trigger when Codex needs to transcribe, translate, timestamp, subtitle, batch-process, validate, or package non-cloud Whisper/MLX audio transcripts; choose Whisper models/languages/output formats; use word timestamps; or write repeatable local STT commands without machine-specific paths.
---

# Whisper STT

## Operating rule

Use Whisper locally. Do not upload audio to cloud STT APIs unless the user explicitly asks for a cloud service. Do not switch to a different STT model/tool when Whisper fails unless the user approves the fallback.

Keep the workflow computer-agnostic:

- Do not hard-code personal paths in commands, docs, or generated scripts.
- Prefer `mlx_whisper` or `python -m mlx_whisper.cli` discovered from the active environment.
- If using the wrapper, discover the runner from `--whisper-cli`, `WHISPER_CLI`, `PATH`, `--python`, `WHISPER_PYTHON`, the current Python, or `python3`/`python` on `PATH`.
- If a local Whisper environment is not active, state the blocker and ask how to locate the Whisper-capable Python/MLX environment.
- Ensure `ffmpeg` is on `PATH`, or pass wrapper `--ffmpeg` / `WHISPER_FFMPEG`; `mlx_whisper` uses ffmpeg to load ordinary audio files.
- Write outputs to the user-requested path; otherwise create a new timestamped folder under the current working directory or the OS temp/downloads location available on that machine.

## Whisper capability surface

Whisper is speech recognition / speech translation, not diarization. Treat these as the important knobs:

- **Input audio**: one or more files; `mlx_whisper` also supports `-` for stdin.
- **Model**: MLX-converted Whisper model directory or Hugging Face repo, defaulting to `mlx-community/whisper-tiny` unless the local setup prefers another converted model.
- **Task**: `transcribe` preserves source language; `translate` translates speech to English.
- **Language**: omit for auto-detect, or set a language code/name such as `en`, `pt`, `ru`, `he`, `Portuguese`, `Hebrew`.
- **Output formats**: `txt`, `json`, `srt`, `vtt`, `tsv`, or `all`.
- **Timestamps**: segment timestamps are in structured/subtitle outputs; use word timestamps for word-level timings.
- **Prompting/context**: use `--initial-prompt` for names, vocabulary, or desired spelling.
- **Clipping**: use `--clip-timestamps` to process only specific time ranges.
- **Decode controls**: temperature, best-of, length penalty, suppress tokens, condition-on-previous-text, fp16/fp32, and failure thresholds; use the Python API for lower-level controls such as temperature fallback tuples and in-process model reuse. Do not claim beam/patience support unless the active install proves it.

For the complete local feature checklist, read `references/whisper-feature-surface.md`.

## Standard CLI pattern

Use this pattern when `mlx_whisper` is available on `PATH`. Raw `mlx_whisper` booleans require explicit `True`/`False` values.

```bash
mlx_whisper ./audio.wav \
  --model mlx-community/whisper-tiny \
  --output-dir ./whisper-output \
  --output-format json \
  --task transcribe \
  --language en \
  --verbose False
```

Equivalent module form:

```bash
python -m mlx_whisper.cli ./audio.wav --model mlx-community/whisper-tiny --output-dir ./whisper-output --output-format txt --verbose False
```

Prefer one raw CLI invocation per input file, or use the wrapper for batches. Some `mlx_whisper` versions have unsafe multi-input output-name behavior.

## Optional wrapper

The bundled wrapper is a convenience layer around local `mlx_whisper`. It intentionally stays computer-agnostic and finds the runner from `--whisper-cli`, `WHISPER_CLI`, `PATH`, `--python`, `WHISPER_PYTHON`, or the current Python module path.

Wrapper booleans are normal flags, unlike the raw CLI:

```bash
scripts/whisper_stt.py ./audio.wav \
  --output-dir ./whisper-output \
  --output-format json \
  --language en \
  --word-timestamps
```

Wrapper safety behavior:

- Quiet by default: it passes `--verbose False` to `mlx_whisper`; add wrapper `--verbose` only when segment/progress output is wanted.
- Runs one `mlx_whisper` process per input file to avoid raw CLI multi-input output-name pitfalls.
- Refuses to overwrite expected transcript files unless `--overwrite` is explicit.
- Refuses `--output-name` with multiple inputs and duplicate output stems.
- Verifies each expected output was freshly written. Speech clips should normally produce non-empty text; true no-speech clips may validly produce empty transcripts.

Use raw `mlx_whisper` or the Python API when you need a feature the wrapper does not expose. Do not copy resolved absolute executable paths from dry-runs into portable docs.

## Feature coverage rule

| Need | Use |
|---|---|
| One file, multiple files, converted model/language/task/output format | `scripts/whisper_stt.py` or one raw `mlx_whisper` CLI call per file |
| JSON, TXT, SRT, VTT, TSV, or all output formats | wrapper or raw CLI |
| Word timestamps / highlighted SRT/VTT words / subtitle line shaping | wrapper or raw CLI (`True`/`False` values on raw CLI booleans) |
| Initial prompt, clip timestamps, no previous-text conditioning, fp32, thresholds | wrapper or raw CLI |
| Temperature fallback tuple, arrays, in-process model reuse, low-level decode options | Python API `mlx_whisper.transcribe`; verify support before using beam/patience |
| Real-time microphone transcription, diarization, speaker labels | Not core Whisper; require explicit separate tooling |

## Python API pattern for advanced features

Use the Python API for model reuse, arrays, or options not exposed by the CLI. Array inputs should already be mono 16 kHz waveforms; file paths go through ffmpeg for downmix/resampling.

```python
import json
import mlx_whisper

result = mlx_whisper.transcribe(
    "./audio.wav",
    path_or_hf_repo="mlx-community/whisper-tiny",
    language="en",              # omit or None for auto-detect
    task="transcribe",
    word_timestamps=True,
    initial_prompt="Names: Kokoro, Leon, Adam.",
    condition_on_previous_text=True,
    clip_timestamps="0,30",
    verbose=False,
)

with open("./whisper-output/audio.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

## Workflow

1. Determine the task shape: transcript, translation, subtitles, timestamps, clip-only pass, or batch.
2. Discover the local Whisper runner without hard-coded paths: `which mlx_whisper`, `python -m mlx_whisper.cli --help`, wrapper `--python`, `WHISPER_PYTHON`, or a user-provided venv command. Confirm `ffmpeg` is discoverable (`which ffmpeg`) or provide wrapper `--ffmpeg` / `WHISPER_FFMPEG`.
3. Choose model, task, language, output format, and timestamp needs explicitly.
4. Generate to a new output directory; never overwrite existing user files unless asked.
5. Verify expected output files exist and were freshly written; for speech clips, also check transcript size/content. The wrapper checks freshness.
6. For quality-sensitive work, inspect the text and, when available, JSON segment timings; do not claim perfect accuracy from successful execution alone.
7. Report absolute output paths and any failed input paths/logs.

## Environment prerequisites

A working local Whisper environment needs `mlx_whisper`/MLX, an MLX-converted Whisper model, and `ffmpeg`. If `ffmpeg` is missing, audio loading fails before transcription. Use the wrapper `--ffmpeg` option or `WHISPER_FFMPEG` to point to an executable or bin directory without hard-coding that path into the skill.

## Optional user-managed setup

Do not install or upgrade packages automatically. If `mlx_whisper` is missing
and the user wants a local setup, suggest `pipx` as one option:

```bash
pipx install --python "$(command -v python3 || command -v python)" mlx-whisper
```

If the machine uses a known Python manager, the user may substitute that Python
explicitly, for example `--python "$HOME/.asdf/shims/python"`.

`ffmpeg` is still required at runtime. If it is missing, suggest either a
user-managed `ffmpeg` install or a one-off `pkgx` invocation when available:

```bash
pkgx +ffmpeg scripts/whisper_stt.py ./audio.wav \
  --output-dir ./whisper-output \
  --output-format json
```

After user-managed setup, verify without assuming success:

```bash
mlx_whisper --help
pkgx +ffmpeg ffmpeg -version  # if using pkgx for ffmpeg
whisper_cli="$(command -v mlx_whisper)"
whisper_python="$(head -1 "$whisper_cli" | sed 's/^#!//')"
"$whisper_python" - <<'PY'
import importlib.util
for name in ["mlx_whisper", "mlx"]:
    print(name, "OK" if importlib.util.find_spec(name) else "missing")
PY
```

## Validation commands

```bash
test -s ./whisper-output/audio.txt
python - <<'PY'
import json
with open('./whisper-output/audio.json', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('language'), len(data.get('segments', [])), data.get('text', '')[:120])
PY
```

For subtitles:

```bash
test -s ./whisper-output/audio.srt
grep -m 1 -- '-->' ./whisper-output/audio.srt
```

## Boundaries

- Do not present Whisper as diarization, speaker identification, emotion detection, or audio enhancement.
- Do not silently use non-Whisper `mlx_audio.stt.generate` models under this skill. Mention them only as a separate STT surface if the user asks.
- Do not discard source audio or overwrite transcripts unless explicitly requested.
- If transcription is uncertain, say so and preserve timestamps/segments for review.
