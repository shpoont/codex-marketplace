---
name: speech-generation
description: Use local Kokoro text-to-speech in a computer-agnostic way. Trigger when Codex needs to generate, batch, validate, compare, or package non-cloud Kokoro TTS audio; choose Kokoro voices/languages; tune speed; fix recurring pronunciations; make listener packs; or write repeatable Kokoro/MLX commands without relying on machine-specific paths.
---

# Kokoro TTS

## Operating rule

Use Kokoro locally. Do not use cloud TTS. Do not switch to another model if Kokoro fails unless the user explicitly approves the fallback.

Keep the workflow computer-agnostic:

- Do not hard-code personal paths in commands, docs, or generated scripts.
- Prefer `python -m mlx_audio.tts.generate` or `mlx_audio.tts.generate` discovered from the active environment.
- If using the wrapper, discover the runner from `--tts-cli`, `KOKORO_MLX_TTS`, `PATH`, `--python`, `KOKORO_PYTHON`, or the current Python only.
- If a local environment is not active, state the blocker and ask how to locate the Kokoro-capable Python/MLX environment.
- Write outputs to the user-requested path; otherwise create a new timestamped folder under the current working directory or the OS temp/downloads location available on that machine.

## Kokoro capability surface

Kokoro is fixed-voice TTS, not voice cloning. Treat these as the important knobs:

- **Text**: the script to synthesize.
- **Model**: usually `mlx-community/Kokoro-82M-bf16`, unless the local setup documents a different Kokoro model.
- **Voice**: Kokoro voice name, for example `af_sarah` or `am_puck`.
  User-preferred English defaults are female `af_sarah` ("Sarah") and male
  `am_puck` ("Puck"). When the user asks for a default female voice, use
  `af_sarah`; when the user asks for a default male voice, use `am_puck`.
  Multiple voices can be comma-separated in MLX Kokoro and are averaged by the
  pipeline.
- **Language code**: Kokoro G2P language code or alias. Common MLX Kokoro codes: `a`/`en`/`en-us`, `b`/`en-gb`, `e`/`es`, `f`/`fr`/`fr-fr`, `h`/`hi`, `i`/`it`, `p`/`pt` or `pt-br`, `j`/`ja`, `z`/`zh`.
- **Speed**: speech speed multiplier, default `1.0`.
- **Segmentation**: the MLX Kokoro API supports a `split_pattern`; use the Python API when custom segmentation matters. For long non-English/eSpeak-backed text, prefer explicit newline/sentence chunks and validate output because local G2P may warn about truncation.
- **Output**: WAV by default; use another local audio format only when the installed audio writer supports it.
- **Playback / generic streaming flags**: `--play` is playback. The installed generic MLX CLI may expose `--stream`/`--save`, but do not present Kokoro as true interval-streaming TTS unless verified in that install; `--save` requires `--stream`.
- **Pronunciation/phonemes**: use Kokoro-style pronunciation hints such as `[word](/IPA/)` when supported by the active G2P, or the Python API for raw phoneme generation.

Before relying on any specific voice/language pair, inspect the local Kokoro voice files/docs or run a short smoke test. Language/voice mismatch can generate warnings or poor output.

## Pronunciation normalization

For recurring mispronunciations, prefer a small TTS-only pronunciation lexicon
before using IPA hints. Normalize the script copy that is sent to Kokoro, not the
source article, transcript, or user-facing written output.

- Prefer natural text rewrites, punctuation, or spelling variants that Kokoro
  reads well: for example, try `A.I.`/`OpenAI` before IPA for AI/OpenAI cases.
- Keep replacements narrow and reviewed. Avoid broad rules that rewrite normal
  prose or all instances of common words.
- Use Kokoro-style `[word](/IPA/)` only as an exception for stubborn terms after
  a smoke test, because IPA can be more brittle and can sound less natural.
- Apply the lexicon before segmentation/chunking so every generated segment uses
  the same pronunciation policy.
- Add proper nouns, acronyms, product names, and foreign terms only when there
  is evidence from listening or transcription that the default G2P is wrong.

For the full strategy, precedence rules, and examples, read
`references/pronunciation-normalization.md`.

## Standard CLI pattern

Use this pattern when `mlx_audio.tts.generate` is available on `PATH`:

```bash
mlx_audio.tts.generate \
  --model mlx-community/Kokoro-82M-bf16 \
  --text "Here is the short version. Everything else stays the same." \
  --voice af_sarah \
  --lang_code a \
  --speed 1.0 \
  --output_path ./kokoro-output \
  --file_prefix sample_001 \
  --audio_format wav \
  --join_audio
```

Equivalent module form:

```bash
python -m mlx_audio.tts.generate --model mlx-community/Kokoro-82M-bf16 --text "Hello." --voice af_sarah --lang_code a --output_path ./kokoro-output --file_prefix hello --audio_format wav --join_audio
```

## Optional wrapper

The bundled wrapper is only a convenience layer. It intentionally stays computer-agnostic and finds the TTS runner from `--tts-cli`, `KOKORO_MLX_TTS`, `PATH`, `--python`, `KOKORO_PYTHON`, or the current Python module path.

```bash
scripts/kokoro_tts.py \
  --text "Here is the short version." \
  --output ./kokoro-output/sample_001.wav \
  --voice af_sarah \
  --lang-code a \
  --speed 1.0
```

Use the raw CLI/API instead of the wrapper when you need a feature the wrapper does not expose. For the complete Kokoro feature checklist, read `references/kokoro-feature-surface.md`.

## Python API pattern for advanced features

Use the Python API for model reuse across many samples, custom `split_pattern`, or features not exposed by the installed CLI:

```python
from mlx_audio.tts.utils import load_model
from mlx_audio.tts.generate import generate_audio

model = load_model("mlx-community/Kokoro-82M-bf16")
generate_audio(
    model=model,
    text="First paragraph.\nSecond paragraph.",
    voice="af_sarah",
    lang_code="a",
    speed=1.0,
    output_path="./kokoro-output",
    file_prefix="sample_001",
    audio_format="wav",
    join_audio=True,
    split_pattern=r"\n+",
)
```

## Feature coverage rule

For simple generation, the wrapper should be enough. For full Kokoro coverage, use this decision:

| Need | Use |
|---|---|
| One sample, batch of normal text, voice/language/speed/output | `scripts/kokoro_tts.py` or standard MLX CLI |
| Separate per-segment files instead of a joined file | wrapper with `--no-join`; expect `prefix_000.wav`, `prefix_001.wav`, etc. |
| Playback with `--play` | wrapper or raw CLI |
| Generic `--stream`/`--save` flags, if verified in the installed MLX CLI | wrapper or raw CLI; remember `--save` requires `--stream` |
| Recurring acronyms, names, brands, or foreign terms sound wrong | TTS-only pronunciation lexicon first; then IPA hints for exceptions |
| Custom segmentation with `split_pattern` | Python API |
| Phoneme/chunk inspection, quiet G2P, raw phoneme synthesis, token timestamps where available | Python API and `KokoroPipeline` |
| Exact voice inventory/grades/language caveats | `references/kokoro-feature-surface.md` plus local model snapshot |

## Workflow

1. Determine the task shape: one sample, batch, long narration, comparison pack, or mobile/Telegram packaging.
2. Discover the local Kokoro runner without hard-coded paths: `which mlx_audio.tts.generate`, `python -m mlx_audio.tts.generate --help`, wrapper `--python`, `KOKORO_PYTHON`, or a user-provided venv command.
3. Choose model, voice, language code, speed, and output format explicitly.
4. Apply a narrow pronunciation lexicon when recurring words are known to render poorly.
5. Generate to a new output path; never overwrite existing user files unless asked.
6. Verify existence and nonzero size for every expected output.
7. When available, verify duration with `ffprobe`; otherwise say duration verification was skipped.
8. For quality claims, use either a listener score sheet or local transcription. Do not assert subjective quality from generation success alone.

## Batch/listener packs

When creating a listening pack:

- Keep listener-facing filenames model-neutral if comparing models.
- Put model answers in a separate answers manifest.
- Include `intended_text`, `what_to_listen_for`, and score columns in the CSV.
- Use `N/A` for score columns that do not apply.
- Include the exact generation parameters in the answers manifest, not in the blind CSV.

## Environment prerequisites

A working Kokoro environment needs `mlx_audio`/MLX plus Kokoro text processing dependencies. MLX Kokoro imports `misaki`; English uses `misaki.en` plus espeak fallback support, several non-English codes use espeak-backed G2P, and Japanese/Mandarin may require optional `misaki[ja]` / `misaki[zh]` extras depending on the install. If import or G2P fails, report the missing dependency instead of using another model.

## Optional user-managed setup

Do not install or upgrade packages automatically. If `mlx_audio.tts.generate` is
missing and the user wants a local setup, suggest `pipx` as one option:

```bash
pipx install --python "$(command -v python3 || command -v python)" 'mlx-audio[tts]'
pipx inject mlx-audio misaki num2words phonemizer spacy
```

If the machine uses a known Python manager, the user may substitute that Python
explicitly, for example `--python "$HOME/.asdf/shims/python"`.

After user-managed setup, verify without assuming success:

```bash
mlx_audio.tts.generate --help
tts_cli="$(command -v mlx_audio.tts.generate)"
tts_python="$(head -1 "$tts_cli" | sed 's/^#!//')"
"$tts_python" - <<'PY'
import importlib.util
for name in ["mlx_audio", "mlx", "misaki.en", "misaki.espeak"]:
    print(name, "OK" if importlib.util.find_spec(name) else "missing")
PY
```

Kokoro can work without `espeak-ng` for many English texts, but may warn or fail
on out-of-dictionary words. If that happens, report the blocker. Suggest
installing/enabling `espeak-ng` only as an optional user-managed/system step,
then set `PHONEMIZER_ESPEAK_LIBRARY` to the readable `libespeak-ng*.dylib`
before running Kokoro.

## Generic MLX flags that are not Kokoro controls

The shared `mlx_audio.tts.generate --help` may list options for other models. Do not treat these as Kokoro features unless local Kokoro code proves otherwise: `--prompt`, `--instruct`, `--ref_audio`, `--ref_text`, `--exaggeration`, `--cfg_scale`, `--ddpm_steps`, `--temperature`, `--top_p`, `--top_k`, `--repetition_penalty`, `--gender`, `--pitch`, `--sigma`, and `--use_zero_spk_emb`.

## Validation commands

```bash
test -s ./kokoro-output/sample_001.wav
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 ./kokoro-output/sample_001.wav
```

If `ffprobe` is missing, run only the size check and state that duration was not verified.

## Boundaries

- Do not present Kokoro as supporting emotion tags, dialogue roles, laughter tags, or real-time calling unless the local Kokoro documentation explicitly supports that feature. Use punctuation, text wording, voice, and speed for basic prosody only.
- Do not call Kokoro voice selection “voice cloning.”
- Do not hide failures with path-specific fallbacks. If the environment cannot run Kokoro, stop and report the blocker.
