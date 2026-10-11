# Speech

Create spoken audio from text and turn recorded speech into text locally.
Use Generation for Kokoro narration and Recognition for Whisper transcripts,
English translations and timed subtitles.

## Quick start

### Requirements

- Codex with local skill/script support on macOS with Apple silicon.
- An existing Python environment with MLX Audio and Kokoro dependencies for
  Generation, or MLX Whisper and ffmpeg for Recognition.
- Compatible downloaded model weights and voice files. The skills help locate
  an environment; installing Speech does not install engines or models.
- No speech-service account, API key or payment is required. Initial dependency,
  model or voice downloads may need internet access. Inference runs locally.

### Install

Once Speech is available in the marketplace:

```sh
codex plugin marketplace add shpoont/codex-marketplace --ref main
codex plugin add speech@b2a48b
```

Skip marketplace setup if already configured, then start a fresh chat. If you
already have standalone speech skills, keep one enabled provider for each job.
Verify the replacement before explicitly removing any older copy.

### Try it

```text
Say “Hello, this is a local speech sample” using Sarah and save a new WAV file.
```

Expected result: a new non-empty local WAV file, its absolute path and the voice
used. If the Kokoro environment or voice is missing, Speech reports the blocker.

## Capabilities

| Skill | Result and material effect |
| --- | --- |
| Generation (`speech-generation`) | Writes local Kokoro audio with chosen voice, language and speed; can prepare batch/listener packs. |
| Recognition (`speech-recognition`) | Reads local audio and writes transcripts, timestamped JSON, SRT/VTT/TSV or English translations. |

Generation is TTS (text to speech). Recognition is STT (speech to text).

## Use the plugin

Tell Speech the text or audio input, desired result and destination. It discovers
the existing engine, chooses the requested parameters and verifies output files.
For example:

```text
Transcribe the audio file I provided and save a new transcript with timestamps.
```

```text
Create English subtitles for the Portuguese recording I provided.
```

Generation prefers `af_sarah` (Sarah) for a default female English voice and
`am_puck` (Puck) for a default male English voice. The low-level Kokoro wrapper
retains its `af_heart` default when `--voice` is omitted, so specify the voice
when using it directly. Its usual model is `mlx-community/Kokoro-82M-bf16`,
language `a` and speed `1.0`. Recognition defaults to
`mlx-community/whisper-tiny`, source-language transcription and language detection;
choose a language explicitly for known or short recordings.

Read each [Generation](skills/speech-generation/SKILL.md) or
[Recognition](skills/speech-recognition/SKILL.md) procedure for commands and
advanced controls. Scripts are relative to their own skill directory and retain
their non-executable mode; invoke them with the active Python interpreter, such
as `python scripts/kokoro_tts.py` or `python scripts/whisper_stt.py`, followed by
the documented arguments.

Always choose a new output path unless replacement was explicitly requested.
The Whisper wrapper refuses existing transcripts without `--overwrite`. The
Kokoro wrapper relies on selecting a new path; it does not enforce an overwrite
guard itself. Do not run it against an existing user file unintentionally.

## Data and effects

The plugin reads the text/audio you provide and local model/voice files. It
writes audio, transcripts, subtitles and any requested validation or listener
files to the chosen local destination. Your original input is retained.
Playback occurs only when requested. No cloud speech processing, plugin
telemetry, account changes or external messages are performed.

An engine may download missing models or voices from Hugging Face. Downloads
can send repository/file identifiers and normal connection metadata; the plugin
does not upload your script or recording for inference. For offline use, ensure
all required dependencies, models, voices and language resources are cached.

Outputs remain until you remove them. Engine caches are managed by your local
environment. Removing Speech does not delete outputs, input files or caches.
Treat private recordings and transcripts as sensitive local files.

## Limitations and failures

- MLX requires Apple silicon; this package does not supply Windows, Linux or
  Intel inference support.
- Kokoro uses fixed voices. Voice cloning, diarization, speaker identification,
  audio enhancement and a live microphone/calling stack are outside scope.
- Voice/language availability and pronunciation vary with the local setup.
  Missing dependencies, ffmpeg, weights or G2P resources require user action;
  Speech stops rather than silently changing engines or using a cloud service.
- A successful run does not establish accurate transcription or natural speech.
  Inspect text/timings or listen before relying on a quality claim.
- Whisper translation targets English. Word timings for translated speech can
  be unreliable. Long text may need deliberate segmentation for Kokoro.

## Update, removal and recovery

```sh
codex plugin marketplace upgrade b2a48b
codex plugin add speech@b2a48b
codex plugin remove speech@b2a48b
```

Start a fresh chat after an update or removal. Verify the qualified plugin and
avoid competing enabled speech copies. If an update fails, stop using the
affected workflow, report it, and reinstall the recovered marketplace version
after support confirms it. Keep your existing outputs and engine environment;
reinstallation does not restore overwritten files.

## Support

Use [marketplace Issues](https://github.com/shpoont/codex-marketplace/issues).
Include version, client/platform, engine version, expected result, actual result
and a small sanitized example. Do not post private recordings, transcripts or
credentials.

## Version and license

Package version: `0.1.0`. See the [changelog](CHANGELOG.md).
The [Installation and Use License](LICENSE) permits installation, execution and
backup for your own use; modification and redistribution require separate
permission. Dependencies retain their licenses. See
[third-party notices](THIRD_PARTY_NOTICES.md).

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
