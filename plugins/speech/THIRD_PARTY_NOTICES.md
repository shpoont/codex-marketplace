# Third-party notices

Speech bundles its skills, documentation, original convenience wrappers and
generated abstract artwork. It does not bundle speech engines, model weights,
voice packs, G2P resources or dependency distributions. No third-party logo or
artwork is included. The Speech license does not replace dependency licenses.

Runtime dependencies are supplied by the user's environment:

| Component | Upstream rights information |
| --- | --- |
| MLX Audio | [MIT license](https://github.com/Blaizzy/mlx-audio/blob/main/LICENSE). |
| MLX / MLX Whisper | [MLX MIT license](https://github.com/ml-explore/mlx/blob/main/LICENSE) and [MLX examples MIT license](https://github.com/ml-explore/mlx-examples/blob/main/LICENSE). |
| Whisper | [MIT license](https://github.com/openai/whisper/blob/main/LICENSE). |
| Kokoro-82M / MLX model | [Kokoro Apache-2.0 license](https://github.com/hexgrad/kokoro/blob/main/LICENSE) and the [converted model card](https://huggingface.co/mlx-community/Kokoro-82M-bf16). Check the actual model and voice distribution used. |
| Misaki and other G2P resources | Licenses of the installed distributions and language resources apply separately. |
| ffmpeg, eSpeak / eSpeak NG | Licenses depend on the installed build and components; use their accompanying notices. |

If a future package bundles third-party material, review distribution rights
and include its required full licenses/notices before shipping that material.
