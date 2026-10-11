# Whisper feature surface

Use this reference when a task needs details beyond basic local transcription.

## Confirmed core `mlx_whisper` capabilities

The inspected `mlx_whisper` CLI/Python API supports these features, and requires `ffmpeg` to load ordinary audio files:

- Local MLX-converted Whisper model selection with `--model` / `path_or_hf_repo` as a converted local directory or Hugging Face repo. A plain OpenAI/PyTorch repo or short model name is not enough unless the local package resolves it to converted weights.
- One or more audio file inputs; `-` reads audio from stdin in the CLI. Prefer the wrapper for batches, or run one raw CLI invocation per file.
- Output formats: `txt`, `vtt`, `srt`, `tsv`, `json`, `all`.
- Output directory and output base name.
- Task selection: `transcribe` or `translate` to English.
- Language auto-detection or explicit language code/name.
- CLI decode controls: `temperature`, `best_of`, `length_penalty`, `suppress_tokens`, `fp16`/fp32.
- Context/prompting: `initial_prompt` and `condition_on_previous_text`.
- Fallback/failure thresholds: `compression_ratio_threshold`, `logprob_threshold`, `no_speech_threshold`.
- Segment timestamps in JSON/subtitle outputs.
- Word timestamps with `word_timestamps=True` / raw CLI `--word-timestamps True` / wrapper `--word-timestamps`.
- Subtitle word highlighting and line shaping when word timestamps are enabled: `highlight_words`, `max_line_width`, `max_line_count`, `max_words_per_line`.
- Punctuation attachment controls for word timestamps: `prepend_punctuations`, `append_punctuations`.
- Hallucination mitigation over silence with `hallucination_silence_threshold` when word timestamps are enabled.
- Time clipping with `clip_timestamps` as `start,end,start,end,...` seconds.
- Python API inputs as file path, NumPy array, or MLX array; arrays should already be mono 16 kHz waveforms.
- Python API result dictionary with `text`, `segments`, and detected/used `language`.

## Raw CLI vs wrapper syntax

- Raw `mlx_whisper` booleans require explicit values: `--verbose False`, `--word-timestamps True`, `--highlight-words True`, `--condition-on-previous-text False`, `--fp16 False`.
- Wrapper booleans are regular flags: `--word-timestamps`, `--highlight-words`, `--no-condition-on-previous-text`, `--fp32`, `--verbose`.
- The wrapper is quiet by default and passes raw `--verbose False`. Add wrapper `--verbose` only when detailed segment/progress output is useful.
- The wrapper refuses existing outputs unless `--overwrite` is explicit and verifies newly generated files.

## Main output format behavior

- `txt`: plain segment text lines.
- `json`: full result object; best for audit, timestamps, word timings, and downstream processing.
- `srt`/`vtt`: subtitles with segment timestamps, or word-level timing when word timestamps are enabled.
- `tsv`: `start`, `end`, `text` rows with millisecond timings.
- `all`: writes every supported format.

## Important option dependencies

- `highlight_words`, `max_line_width`, `max_line_count`, and `max_words_per_line` require word timestamps in the CLI.
- `max_line_count` has no effect without `max_line_width`.
- `max_words_per_line` has no effect if `max_line_width` is set.
- Word-level timestamps on `translate` may be unreliable.
- `condition_on_previous_text=False` can reduce repetition/failure loops but may reduce consistency across windows.
- `initial_prompt` is context biasing, not guaranteed vocabulary enforcement.
- In the inspected `mlx_whisper` path, `beam_size`/`patience` are not usable: `patience` requires `beam_size`, and beam search may be unimplemented. Do not claim or use beam/patience unless the active install proves support.

## Python API-only controls

Use `mlx_whisper.transcribe(...)` directly for lower-level decode controls not exposed safely by the wrapper/CLI, after confirming the active install supports the option. Do not rely on beam search or patience unless a live smoke test proves they work in that installation. Useful API-only controls can include:

- `sample_len`
- `prefix`
- `suppress_blank`
- `without_timestamps`
- `max_initial_timestamp`
- temperature fallback tuples
- in-process model reuse and array inputs

## Common model choice guidance

- `mlx-community/whisper-tiny`: fastest/smallest smoke-test default; lower accuracy.
- Larger or quantized MLX Whisper repos usually improve accuracy at higher runtime/memory cost. Verify model availability in the active environment before use.
- Use the same model for before/after comparisons; changing models changes accuracy and timing.

## Language handling

Whisper can auto-detect language on multilingual models. Prefer explicit `--language` when the user knows the language, especially for short clips, code-switching, or low-quality audio.

Common codes for this user context:

- English: `en`
- Portuguese: `pt`
- Russian: `ru`
- Hebrew: `he`

## Not core Whisper features

Do not claim these unless separate tooling is explicitly added:

- Speaker diarization or speaker names.
- Voice identification or speaker verification.
- Emotion detection.
- Audio cleanup, source separation, denoising, or dereverberation.
- True live microphone/call transcription loop. Whisper can process files/chunks, but capture, VAD, streaming orchestration, and call integration are separate systems.
- Forced alignment to supplied text. The separate `mlx_audio.stt.generate` surface may expose alignment-oriented options for non-Whisper models; do not conflate it with `mlx_whisper`.

## Environment prerequisites

`mlx_whisper` shells out to `ffmpeg` for audio loading. If transcription fails with `FileNotFoundError: ffmpeg`, activate/install ffmpeg or pass a machine-local ffmpeg path through the wrapper/environment; do not bake that path into reusable skill docs.

## Quality and audit guidance

- Always preserve the source audio path and output paths in the final answer.
- Prefer JSON when the transcript may need review or downstream analysis.
- For user-facing summaries, quote only small excerpts and point to the full transcript file.
- For sensitive/private audio, keep processing local and do not upload.
- If the transcript looks hallucinated around silence/music/noise, rerun with word timestamps and consider `condition_on_previous_text=False`, explicit language, or clipping.
