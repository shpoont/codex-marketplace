#!/usr/bin/env python3
"""Computer-agnostic convenience wrapper for local Whisper via mlx-whisper."""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_MODEL = "mlx-community/whisper-tiny"
FORMATS = {"txt", "vtt", "srt", "tsv", "json", "all"}
TASKS = {"transcribe", "translate"}


def _executable_exists(candidate: str) -> str | None:
    expanded = os.path.expanduser(candidate)
    if os.path.sep in expanded or (os.path.altsep and os.path.altsep in expanded):
        return expanded if Path(expanded).exists() else None
    return shutil.which(expanded)


def resolve_whisper_command(explicit_cli: str | None, python_executable: str | None) -> list[str]:
    """Resolve to either an entrypoint command or `python -m mlx_whisper.cli`."""
    if explicit_cli:
        found = _executable_exists(explicit_cli)
        if not found:
            raise SystemExit(f"--whisper-cli does not exist or is not on PATH: {explicit_cli}")
        return [found]

    if os.environ.get("WHISPER_CLI"):
        found = _executable_exists(os.environ["WHISPER_CLI"])
        if not found:
            raise SystemExit("WHISPER_CLI is set but does not exist or is not on PATH")
        return [found]

    found = shutil.which("mlx_whisper")
    if found:
        return [found]

    py_candidates = [
        python_executable,
        os.environ.get("WHISPER_PYTHON"),
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for py in py_candidates:
        if not py:
            continue
        py_found = _executable_exists(py)
        if not py_found:
            continue
        probe = subprocess.run(
            [py_found, "-c", "import mlx_whisper.cli"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if probe.returncode == 0:
            return [py_found, "-m", "mlx_whisper.cli"]

    raise SystemExit(
        "Could not find mlx_whisper. Activate a Whisper-capable environment, "
        "pass --whisper-cli, pass --python, or set WHISPER_CLI/WHISPER_PYTHON."
    )


def quote_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in cmd)


def prepare_ffmpeg_env(explicit_ffmpeg: str | None) -> dict[str, str]:
    """Return an environment where ffmpeg is discoverable, or fail clearly."""
    env = os.environ.copy()
    candidate = explicit_ffmpeg or os.environ.get("WHISPER_FFMPEG")
    if candidate:
        expanded = os.path.expanduser(candidate)
        if os.path.sep in expanded or (os.path.altsep and os.path.altsep in expanded):
            p = Path(expanded)
            if not p.exists():
                raise SystemExit(f"ffmpeg path does not exist: {expanded}")
            ffmpeg_dir = str(p.parent if p.name == "ffmpeg" else p)
            env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
        else:
            found = shutil.which(expanded, path=env.get("PATH"))
            if not found:
                raise SystemExit(f"ffmpeg executable is not on PATH: {expanded}")
    if not shutil.which("ffmpeg", path=env.get("PATH")):
        raise SystemExit(
            "ffmpeg is required by mlx_whisper audio loading but was not found. "
            "Install/activate ffmpeg, pass --ffmpeg /path/to/ffmpeg (or its bin dir), "
            "or set WHISPER_FFMPEG."
        )
    return env


def add_opt(cmd: list[str], flag: str, value: object | None) -> None:
    if value is not None:
        cmd.extend([flag, str(value)])


def audio_arg_for_subprocess(audio: str) -> str:
    if audio == "-":
        return audio
    return str(Path(audio).expanduser())


def expected_outputs_for_audio(audio: str, output_dir: Path, output_format: str, output_name: str | None) -> list[Path]:
    exts = ["txt", "vtt", "srt", "tsv", "json"] if output_format == "all" else [output_format]
    base = output_name or ("content" if audio == "-" else Path(audio).expanduser().stem)
    return [output_dir / f"{base}.{ext}" for ext in exts]


def expected_outputs(audio_paths: list[str], output_dir: Path, output_format: str, output_name: str | None) -> list[Path]:
    outputs: list[Path] = []
    for audio in audio_paths:
        outputs.extend(expected_outputs_for_audio(audio, output_dir, output_format, output_name))
    return outputs


def build_command(runner: list[str], audio: str, output_dir: Path, args: argparse.Namespace) -> list[str]:
    cmd = [
        *runner,
        audio_arg_for_subprocess(audio),
        "--model", args.model,
        "--output-dir", str(output_dir),
        "--output-format", args.output_format,
        "--task", args.task,
    ]
    add_opt(cmd, "--output-name", args.output_name)
    add_opt(cmd, "--language", args.language)
    add_opt(cmd, "--initial-prompt", args.initial_prompt)
    add_opt(cmd, "--temperature", args.temperature)
    add_opt(cmd, "--best-of", args.best_of)
    add_opt(cmd, "--length-penalty", args.length_penalty)
    add_opt(cmd, "--suppress-tokens", args.suppress_tokens)
    if args.no_condition_on_previous_text:
        cmd.extend(["--condition-on-previous-text", "False"])
    if args.fp32:
        cmd.extend(["--fp16", "False"])
    add_opt(cmd, "--compression-ratio-threshold", args.compression_ratio_threshold)
    add_opt(cmd, "--logprob-threshold", args.logprob_threshold)
    add_opt(cmd, "--no-speech-threshold", args.no_speech_threshold)
    if args.word_timestamps:
        cmd.extend(["--word-timestamps", "True"])
    add_opt(cmd, "--prepend-punctuations", args.prepend_punctuations)
    add_opt(cmd, "--append-punctuations", args.append_punctuations)
    if args.highlight_words:
        cmd.extend(["--highlight-words", "True"])
    add_opt(cmd, "--max-line-width", args.max_line_width)
    add_opt(cmd, "--max-line-count", args.max_line_count)
    add_opt(cmd, "--max-words-per-line", args.max_words_per_line)
    add_opt(cmd, "--hallucination-silence-threshold", args.hallucination_silence_threshold)
    add_opt(cmd, "--clip-timestamps", args.clip_timestamps)
    cmd.extend(["--verbose", "True" if args.verbose else "False"])
    return cmd


def check_unique_outputs(paths: list[Path]) -> None:
    seen: dict[Path, int] = {}
    duplicates: list[Path] = []
    for p in paths:
        seen[p] = seen.get(p, 0) + 1
    duplicates = [p for p, count in seen.items() if count > 1]
    if duplicates:
        raise SystemExit(
            "Multiple inputs would write the same output path. Use unique input stems, "
            "separate output directories, or process files one at a time:\n"
            + "\n".join(f"  {p}" for p in duplicates)
        )


def verify_outputs(paths: list[Path], start_ns: int) -> tuple[list[Path], list[Path]]:
    missing = [p for p in paths if not p.exists()]
    stale = [p for p in paths if p.exists() and p.stat().st_mtime_ns < start_ns]
    return missing, stale


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe local audio through mlx-whisper.")
    parser.add_argument("audio", nargs="+", help="Audio file(s) to transcribe, or '-' for stdin.")
    parser.add_argument("--output-dir", required=True, help="Directory for transcript outputs.")
    parser.add_argument("--output-name", help="Base output name. Only allowed with one input.")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing expected transcript files.")
    parser.add_argument("--whisper-cli", help="Path/name for mlx_whisper. Overrides PATH discovery.")
    parser.add_argument("--python", help="Python executable that can run `-m mlx_whisper.cli` if no CLI entrypoint is available.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"MLX-converted Whisper model repo/path. Default: {DEFAULT_MODEL}")
    parser.add_argument("--ffmpeg", help="Path to ffmpeg executable or a directory containing it. Overrides/augments PATH.")
    parser.add_argument("--output-format", choices=sorted(FORMATS), default="txt")
    parser.add_argument("--task", choices=sorted(TASKS), default="transcribe")
    parser.add_argument("--language", help="Language code/name. Omit for auto-detect.")
    parser.add_argument("--initial-prompt", help="Optional prompt/context for first window.")
    parser.add_argument("--temperature", type=float, help="Sampling temperature.")
    parser.add_argument("--best-of", type=int, help="Number of candidates with non-zero temperature.")
    parser.add_argument("--patience", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--length-penalty", type=float, help="Token length penalty.")
    parser.add_argument("--suppress-tokens", help="Comma-separated token ids; -1 suppresses most special characters.")
    parser.add_argument("--no-condition-on-previous-text", action="store_true", help="Pass --condition-on-previous-text False.")
    parser.add_argument("--fp32", action="store_true", help="Pass --fp16 False.")
    parser.add_argument("--compression-ratio-threshold", help="Float or None.")
    parser.add_argument("--logprob-threshold", help="Float or None.")
    parser.add_argument("--no-speech-threshold", help="Float or None.")
    parser.add_argument("--word-timestamps", action="store_true", help="Enable word-level timestamps.")
    parser.add_argument("--prepend-punctuations", help="Punctuation to merge with the next word when word timestamps are enabled.")
    parser.add_argument("--append-punctuations", help="Punctuation to merge with the previous word when word timestamps are enabled.")
    parser.add_argument("--highlight-words", action="store_true", help="Highlight words in SRT/VTT; requires --word-timestamps.")
    parser.add_argument("--max-line-width", type=int, help="Subtitle max line width; requires --word-timestamps.")
    parser.add_argument("--max-line-count", type=int, help="Subtitle max line count; requires --word-timestamps and --max-line-width to matter.")
    parser.add_argument("--max-words-per-line", type=int, help="Subtitle max words per line; requires --word-timestamps and no --max-line-width.")
    parser.add_argument("--hallucination-silence-threshold", help="Float or None; requires word timestamps.")
    parser.add_argument("--clip-timestamps", help="Comma-separated start,end,start,end seconds.")
    parser.add_argument("--verbose", action="store_true", help="Print verbose mlx_whisper progress/segments. Default passes --verbose False.")
    parser.add_argument("--quiet", action="store_true", help="Accepted for compatibility; wrapper is quiet by default.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved command(s) without running them or creating output dirs.")
    args = parser.parse_args()

    if args.output_name and len(args.audio) != 1:
        parser.error("--output-name is only allowed with exactly one input to avoid overwriting outputs")
    if args.audio.count("-") and len(args.audio) != 1:
        parser.error("stdin input '-' is only allowed as the sole input")
    if args.patience is not None:
        parser.error("--patience is not exposed safely by this mlx_whisper path; verify a newer install supports beam search before using beam/patience")
    if args.verbose and args.quiet:
        parser.error("--verbose and --quiet are mutually exclusive")
    if any(v is not None for v in [args.max_line_width, args.max_line_count, args.max_words_per_line]) or args.highlight_words:
        if not args.word_timestamps:
            parser.error("subtitle word layout/highlight options require --word-timestamps")
    if args.max_line_count and not args.max_line_width:
        parser.error("--max-line-count has no effect without --max-line-width")
    if args.max_words_per_line and args.max_line_width:
        parser.error("--max-words-per-line has no effect with --max-line-width")

    output_dir = Path(args.output_dir).expanduser().resolve()
    outputs = expected_outputs(args.audio, output_dir, args.output_format, args.output_name)
    check_unique_outputs(outputs)

    runner = resolve_whisper_command(args.whisper_cli, args.python)
    commands = [build_command(runner, audio, output_dir, args) for audio in args.audio]
    for cmd in commands:
        print(quote_cmd(cmd))
    if args.dry_run:
        return 0

    for audio in args.audio:
        if audio != "-" and not Path(audio).expanduser().exists():
            print(f"Input audio does not exist: {audio}", file=sys.stderr)
            return 1

    existing = [p for p in outputs if p.exists()]
    if existing and not args.overwrite:
        print("Refusing to overwrite existing transcript output(s). Pass --overwrite if replacement is intended:", file=sys.stderr)
        for p in existing:
            print(f"  {p}", file=sys.stderr)
        return 1

    env = prepare_ffmpeg_env(args.ffmpeg)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for audio, cmd in zip(args.audio, commands):
        expected = expected_outputs_for_audio(audio, output_dir, args.output_format, args.output_name)
        start_ns = time.time_ns()
        proc = subprocess.run(cmd, text=True, env=env)
        if proc.returncode != 0:
            return proc.returncode
        missing, stale = verify_outputs(expected, start_ns)
        if missing or stale:
            if missing:
                print("Expected transcript output(s) missing:", file=sys.stderr)
                for p in missing:
                    print(f"  {p}", file=sys.stderr)
            if stale:
                print("Expected transcript output(s) were not freshly written:", file=sys.stderr)
                for p in stale:
                    print(f"  {p}", file=sys.stderr)
            return 1
        generated.extend(expected)

    for p in generated:
        print(f"Generated: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
