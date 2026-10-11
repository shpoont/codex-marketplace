# Kokoro feature surface

Use this reference when a task needs details beyond basic English `af_heart` generation.

## Confirmed core capabilities

Kokoro/Kokoro-82M is local fixed-voice text-to-speech. In the MLX Audio implementation, Kokoro supports:

- Model selection, normally `mlx-community/Kokoro-82M-bf16` or another compatible Kokoro repo/path.
- Voice selection by name, with lazy voice download/load.
- Voice blending by comma-separated voices, e.g. `af_bella,af_nicole`; MLX averages the loaded voice packs.
- Language-specific G2P through `lang_code`.
- Speed control via `speed`.
- Text segmentation/chunking. MLX CLI can join segments with `--join_audio`; without joining it writes per-segment files such as `prefix_000.wav`. Python API/model call can pass `split_pattern`. The CLI does not expose `split_pattern` directly in the inspected install.
- Python-level phoneme/chunk inspection: `KokoroPipeline(..., model=False)` yields graphemes/phonemes without audio; `generate_from_tokens()` can synthesize raw phoneme strings or pre-tokenized English MTokens. Raw phoneme strings over roughly 510 phoneme characters raise or must be chunked.
- Token/timestamp metadata in Python results where available; MLX joins predicted durations to tokens for English token results.
- Custom pronunciation in Kokoro-style text when supported by the active G2P, e.g. `[Kokoro](/kˈOkəɹO/)` as shown in the official model card.

## Not core Kokoro features

Do not claim these for Kokoro unless a separate wrapper/extension explicitly implements them:

- Zero-shot voice cloning from arbitrary reference audio.
- Dialogue role control like Dia `[S1]`/`[S2]`.
- Nonverbal/emotion tags such as `[laughing]`, `[sigh]`, `[whisper]`.
- Fine-grained emotion/style prompting beyond choosing voice, speed, punctuation, wording, and pronunciation hints.
- Real phone-call agent stack. Kokoro may be fast enough for some local playback, but call routing, streaming I/O, VAD, true interval streaming, and turn-taking are outside Kokoro itself.

## Language codes and aliases

MLX Kokoro maps these aliases/codes:

| Code | Aliases | Language |
|---|---|---|
| `a` | `en`, `en-us` | American English |
| `b` | `en-gb` | British English |
| `e` | `es` | Spanish |
| `f` | `fr`, `fr-fr` | French |
| `h` | `hi` | Hindi |
| `i` | `it` | Italian |
| `p` | `pt`, `pt-br` | Brazilian Portuguese |
| `j` | `ja` | Japanese |
| `z` | `zh` | Mandarin Chinese |

Japanese and Mandarin may require optional G2P extras in some Kokoro installs. English/non-English quality varies by voice and language; validate with a smoke sample.

## Official Kokoro-82M v1.0 voice list

The official `hexgrad/Kokoro-82M` v1.0 voice document lists 54 voices across 8 languages, shown below as 9 voice groups because English is split into American and British groups:

- American English `a`: `af_heart`, `af_alloy`, `af_aoede`, `af_bella`, `af_jessica`, `af_kore`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky`, `am_adam`, `am_echo`, `am_eric`, `am_fenrir`, `am_liam`, `am_michael`, `am_onyx`, `am_puck`, `am_santa`
- British English `b`: `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`
- Japanese `j`: `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`
- Mandarin Chinese `z`: `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`, `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`
- Spanish `e`: `ef_dora`, `em_alex`, `em_santa`
- French `f`: `ff_siwis`
- Hindi `h`: `hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi`
- Italian `i`: `if_sara`, `im_nicola`
- Brazilian Portuguese `p`: `pf_dora`, `pm_alex`, `pm_santa`

This list is model-card-derived; prefer inspecting `voices/*.safetensors` in the local model snapshot or running a smoke test when exact availability matters, because MLX ports or custom repos may contain a subset/superset. In the inspected MLX implementation, voice downloads may come from the model repo or its configured Kokoro voice repo, so local snapshot verification is the safest check.

## Environment and G2P prerequisites

Kokoro needs G2P dependencies in addition to model weights. MLX Kokoro imports `misaki`; English uses `misaki.en` and espeak fallback support; Spanish/French/Hindi/Italian/Portuguese use espeak-backed processing; Japanese and Mandarin may need optional `misaki[ja]` and `misaki[zh]` extras. Missing G2P dependencies are blockers, not reasons to silently switch models.

## Length and quality guidance

Official guidance says voices tend to perform best around 100-200 tokens and can degrade at very short or very long extremes. Mitigations:

- Bundle very short utterances together when possible.
- Chunk long text by sentence/paragraph.
- If long text rushes, chunk smaller or lower `speed`. For non-English/eSpeak-backed languages, explicitly split long text with newlines/sentence chunks and validate because local G2P may warn about truncation.
- Use human listening or local transcription before claiming a language/voice is production-usable.
