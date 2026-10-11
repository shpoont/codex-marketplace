#!/usr/bin/env python3
"""Computer-agnostic convenience wrapper for local Kokoro via MLX Audio."""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "mlx-community/Kokoro-82M-bf16"
DEFAULT_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"


def _executable_exists(candidate: str) -> str | None:
    expanded = os.path.expanduser(candidate)
    if os.path.sep in expanded or (os.path.altsep and os.path.altsep in expanded):
        return expanded if Path(expanded).exists() else None
    return shutil.which(expanded)


def resolve_tts_command(explicit: str | None, python_executable: str | None) -> list[str]:
    """Resolve to either an entrypoint command or `python -m` module form."""
    if explicit:
        found = _executable_exists(explicit)
        if not found:
            raise SystemExit(f"--tts-cli does not exist or is not on PATH: {explicit}")
        return [found]

    if os.environ.get("KOKORO_MLX_TTS"):
        found = _executable_exists(os.environ["KOKORO_MLX_TTS"])
        if not found:
            raise SystemExit("KOKORO_MLX_TTS is set but does not exist or is not on PATH")
        return [found]

    found = shutil.which("mlx_audio.tts.generate")
    if found:
        return [found]

    py_candidates = [python_executable, os.environ.get("KOKORO_PYTHON"), sys.executable, shutil.which("python3"), shutil.which("python")]
    for py in py_candidates:
        if not py:
            continue
        py_found = _executable_exists(py)
        if not py_found:
            continue
        probe = subprocess.run([py_found, "-c", "import mlx_audio.tts.generate"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode == 0:
            return [py_found, "-m", "mlx_audio.tts.generate"]

    raise SystemExit(
        "Could not find mlx_audio.tts.generate. Activate a Kokoro-capable environment, "
        "pass --tts-cli, pass --python, or set KOKORO_MLX_TTS/KOKORO_PYTHON."
    )


def quote_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local Kokoro TTS audio via MLX Audio.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--output", required=True, help="Output audio path, usually .wav.")
    parser.add_argument("--tts-cli", help="Path/name for mlx_audio.tts.generate. Overrides PATH discovery.")
    parser.add_argument("--python", help="Python executable that can run `-m mlx_audio.tts.generate` if no CLI entrypoint is available.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Kokoro model repo/path. Default: {DEFAULT_MODEL}")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Kokoro voice or comma-separated voice blend. Default: {DEFAULT_VOICE}")
    parser.add_argument("--lang-code", default=DEFAULT_LANG_CODE, help=f"Kokoro language code/alias. Default: {DEFAULT_LANG_CODE}")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier.")
    parser.add_argument("--audio-format", help="Override audio format. Defaults to output extension without dot, or wav.")
    parser.add_argument("--no-join", action="store_true", help="Do not pass --join_audio; may create one file per segment.")
    parser.add_argument("--play", action="store_true", help="Ask the underlying CLI to play audio if supported.")
    parser.add_argument("--stream", action="store_true", help="Ask the underlying CLI to stream audio if supported.")
    parser.add_argument("--save", action="store_true", help="Ask the underlying CLI to save streamed audio if supported.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved command without running it.")
    args = parser.parse_args()

    if args.save and not args.stream:
        parser.error("--save requires --stream")

    out = Path(args.output).expanduser().resolve()
    audio_format = args.audio_format or (out.suffix[1:] if out.suffix else "wav")
    file_prefix = out.stem

    cmd = [
        *resolve_tts_command(args.tts_cli, args.python),
        "--model", args.model,
        "--text", args.text,
        "--voice", args.voice,
        "--lang_code", args.lang_code,
        "--speed", str(args.speed),
        "--output_path", str(out.parent),
        "--file_prefix", file_prefix,
        "--audio_format", audio_format,
    ]
    if not args.no_join:
        cmd.append("--join_audio")
    if args.play:
        cmd.append("--play")
    if args.stream:
        cmd.append("--stream")
    if args.save:
        cmd.append("--save")

    print(quote_cmd(cmd))
    if args.dry_run:
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, text=True)
    if proc.returncode != 0:
        return proc.returncode

    expected = out.parent / f"{file_prefix}.{audio_format}"
    if expected != out and expected.exists():
        expected.replace(out)

    if args.no_join:
        segments = sorted(out.parent.glob(f"{file_prefix}_*.{audio_format}"))
        nonempty_segments = [p for p in segments if p.exists() and p.stat().st_size > 0]
        if nonempty_segments:
            for segment in nonempty_segments:
                print(f"Generated segment: {segment}")
            return 0
        # Some generators may still create the exact file even without join.
        if out.exists() and out.stat().st_size > 0:
            print(f"Generated: {out}")
            return 0
        print(
            f"Expected one or more segment files matching {file_prefix}_*.{audio_format}, but none were created.",
            file=sys.stderr,
        )
        return 1

    if not args.stream and (not out.exists() or out.stat().st_size == 0):
        print(f"Expected output was not created or is empty: {out}", file=sys.stderr)
        return 1
    if out.exists():
        print(f"Generated: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
