#!/usr/bin/env python3
"""Render task references, inspect guidance, and prepare bounded candidates read-only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import uuid

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MARKER = "Agent Instructions review"
LEGACY_MARKERS = ("Agent Instructions Improvement review", "Maintain Agent Guidance review",
                  "AGENTS.md self-improvement review")
# These markers support migration discovery only, never runtime provider aliases.
CONTRACT = "Task contract: plugin-reference/v1"
PLUGIN = "agent-instructions"
REVIEW_SKILL = "agents-md-review"
ENTRYPOINT_DECLARATION = '<!-- agent-instructions-entrypoint '
ENTRYPOINT_CONTRACT = {"job_contract": "plugin-reference/v1", "loader_interface": "policy-context/v1"}
LEGACY_CATALOG_LOADER_HASH = "de47d013a4fdbc422096392dd64ba1f88c3a340ae6e56d4d80c9902dac0b6097"
REVIEW_RESOURCES = (
    ".codex-plugin/plugin.json", "skills/agents-md-review/SKILL.md",
    "skills/agents-md-maintenance/scripts/manage.py",
    "skills/agents-md-maintenance/assets/review.md",
    "skills/agents-md-maintenance/assets/template.json",
)
KEY = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")
PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


class InputError(ValueError):
    """A bounded error safe to report without echoing private input."""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


MANAGED_BEGIN = b"<!-- BEGIN agent-instructions:managed:v1 sha256="
MANAGED_END = b"<!-- END agent-instructions:managed:v1 -->"
MANAGED_TOKEN = b"agent-instructions:managed"


def valid_guidance_bytes(raw: bytes) -> None:
    try:
        if not isinstance(raw, bytes) or b"\0" in raw:
            raise ValueError
        raw.decode("utf-8")
    except (UnicodeError, ValueError):
        raise InputError("managed guidance must be UTF-8 bytes without NUL characters") from None


def managed_section(raw: bytes, allow_edited: bool = False) -> dict | None:
    """Recognize one exact top-level marker pair; a checksum is not authorization."""
    valid_guidance_bytes(raw)
    events = []
    position = 0
    fence = None
    for line in raw.splitlines(keepends=True):
        text = line.rstrip(b"\r\n")
        if fence:
            if re.fullmatch(rb" {0,3}" + re.escape(fence[:1]) + rb"{" + str(len(fence)).encode() + rb",}[ \t]*", text):
                fence = None
        else:
            opening = re.match(rb" {0,3}(`{3,}|~{3,})(.*)\Z", text)
            if opening and (opening[1].startswith(b"~") or b"`" not in opening[2]):
                fence = opening[1]
            elif MANAGED_TOKEN in text.lower():
                begin = re.fullmatch(re.escape(MANAGED_BEGIN) + rb"([0-9a-f]{64}) -->", text)
                if begin:
                    events.append(("begin", position, position + len(line), begin[1].decode()))
                elif text == MANAGED_END:
                    events.append(("end", position, position + len(line), None))
                else:
                    raise InputError("malformed or unsupported managed-section marker")
        position += len(line)
    if not events:
        return None
    if len(events) != 2 or [e[0] for e in events] != ["begin", "end"]:
        raise InputError("managed section requires exactly one complete, unnested marker pair")
    begin, end = events
    body = raw[begin[2]:end[1]]
    actual = hashlib.sha256(body).hexdigest()
    if actual != begin[3] and not allow_edited:
        raise InputError("managed content was edited; explicit human reconciliation is required")
    return {"start": begin[1], "body_start": begin[2], "body_end": end[1], "end": end[2],
            "body_bytes": len(body), "body_sha256": actual, "recorded_sha256": begin[3],
            "status": "ready" if actual == begin[3] else "edited"}


def managed_baseline(raw: bytes, expected: str) -> None:
    valid_guidance_bytes(raw)
    if (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or hashlib.sha256(raw).hexdigest() != expected):
        raise InputError("managed whole-file baseline changed or its expected SHA-256 is invalid")


def managed_result(original: bytes, candidate: bytes) -> dict:
    return {"schema_version": 1, "changed": original != candidate,
            "original_sha256": hashlib.sha256(original).hexdigest(),
            "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
            "original_bytes": len(original), "candidate_bytes": len(candidate),
            "candidate": candidate.decode("utf-8"),
            "limits": "Candidate only: no files written, human authorization, semantic preservation and full-file host loading must be verified separately."}


def managed_adopt(raw: bytes, expected: str, start_line: int, end_line: int) -> dict:
    """Wrap an explicitly human-selected inclusive line range, never infer ownership."""
    managed_baseline(raw, expected)
    if managed_section(raw) is not None:
        raise InputError("a managed section already exists; adoption cannot expand or replace it")
    lines = raw.splitlines(keepends=True)
    if (type(start_line) is not int or type(end_line) is not int
            or not 1 <= start_line <= end_line <= len(lines)):
        raise InputError("adoption needs a valid explicitly selected inclusive line range")
    body = b"".join(lines[start_line - 1:end_line])
    if not body.endswith(b"\n"):
        raise InputError("selected range must end with a newline; no automatic normalization")
    newline = b"\r\n" if lines[start_line - 1].endswith(b"\r\n") else b"\n"
    marker = MANAGED_BEGIN + hashlib.sha256(body).hexdigest().encode() + b" -->" + newline
    candidate = b"".join(lines[:start_line - 1]) + marker + body + MANAGED_END + newline + b"".join(lines[end_line:])
    section = managed_section(candidate)
    if section is None or section["body_bytes"] != len(body):
        raise InputError("selected adoption range is not an unambiguous top-level section")
    return managed_result(raw, candidate)


def managed_replace(raw: bytes, expected: str, body: bytes) -> dict:
    managed_baseline(raw, expected)
    section = managed_section(raw)
    if section is None:
        raise InputError("managed section absent; explicit human adoption is required")
    valid_guidance_bytes(body)
    if body and not body.endswith(b"\n"):
        raise InputError("managed replacement must end with a newline; no automatic normalization")
    checksum_start = section["start"] + len(MANAGED_BEGIN)
    # Substitute only the digest digits; retain every other accepted marker byte.
    header = (raw[:checksum_start] + hashlib.sha256(body).hexdigest().encode()
              + raw[checksum_start + 64:section["body_start"]])
    candidate = header + body + raw[section["body_end"]:]
    if managed_section(candidate) is None:
        raise InputError("replacement does not retain an unambiguous managed section")
    return managed_result(raw, candidate)


def managed_reconcile(raw: bytes, expected: str) -> dict:
    """Prepare a checksum-only candidate after explicit acceptance of a manual edit."""
    managed_baseline(raw, expected)
    section = managed_section(raw, allow_edited=True)
    if section is None:
        raise InputError("no managed section to reconcile")
    checksum_start = section["start"] + len(MANAGED_BEGIN)
    candidate = (raw[:checksum_start] + section["body_sha256"].encode()
                 + raw[checksum_start + 64:])
    managed_section(candidate)
    return managed_result(raw, candidate)


def managed_check(raw: bytes, expected: str, candidate: bytes) -> dict:
    managed_baseline(raw, expected)
    section = managed_section(raw)
    proposed = managed_section(candidate)
    if section is None or proposed is None:
        raise InputError("managed scope check requires an already adopted section")
    # Check protected spans directly, independently of the candidate constructor.
    old_checksum = section["start"] + len(MANAGED_BEGIN)
    new_checksum = proposed["start"] + len(MANAGED_BEGIN)
    if (raw[:old_checksum] != candidate[:new_checksum]
            or raw[old_checksum + 64:section["body_start"]] != candidate[new_checksum + 64:proposed["body_start"]]
            or raw[section["body_end"]:] != candidate[proposed["body_end"]:]):
        raise InputError("candidate changes bytes outside the managed body or its checksum")
    return {k: v for k, v in {**managed_result(raw, candidate), "scope_check_passed": True}.items() if k != "candidate"}


def read_managed_root(project: Path) -> bytes:
    try:
        target = project / "AGENTS.md"
        if (not project.is_absolute() or project != project.resolve(strict=True)
                or not project.is_dir() or target.is_symlink() or not target.is_file()):
            raise ValueError
        raw = target.read_bytes()
    except (OSError, ValueError):
        raise InputError("managed inspection requires a canonical project and regular non-symlink root AGENTS.md") from None
    valid_guidance_bytes(raw)
    return raw


def guidance_check(project: Path, max_bytes: int, cwd: Path | None = None,
                   fallbacks: tuple[str, ...] = (), candidate: bytes | None = None,
                   prompt_input: list | None = None) -> dict:
    """Check supplied host settings and project files, never infer configuration or write.

    A candidate is a projection. A prompt export can establish a fresh-host
    observation, not adoption by an already-running conversation.
    """
    if type(max_bytes) is not int or max_bytes < 0:
        raise InputError("guidance budget must be a non-negative integer")
    project = Path(project)
    cwd = Path(cwd) if cwd is not None else project
    try:
        if (not project.is_absolute() or project != project.resolve(strict=True)
                or not project.is_dir() or not cwd.is_absolute()
                or cwd != cwd.resolve(strict=True) or not cwd.is_dir()
                or not cwd.is_relative_to(project)):
            raise ValueError
    except (OSError, ValueError):
        raise InputError("guidance project/cwd must be existing canonical directories within the project") from None
    names = ("AGENTS.override.md", "AGENTS.md") + tuple(fallbacks)
    if (any(
            not isinstance(name, str) or name in ("", ".", "..")
            or Path(name).name != name or "/" in name or "\\" in name
            or any(ord(char) < 32 for char in name) for name in names)
            or len(set(names)) != len(names)):
        raise InputError("guidance fallback names must be distinct plain filenames")
    if candidate is not None and prompt_input is not None:
        raise InputError("a candidate projection cannot verify a loaded prompt")

    def read(path):
        if path.is_symlink():
            raise InputError("guidance inspection refuses symlinked instruction files")
        if not path.exists():
            return None
        if not path.is_file():
            raise InputError("guidance instruction path is not a regular file")
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeError):
            raise InputError("guidance file is unreadable or not UTF-8") from None
        if "\0" in text:
            raise InputError("guidance file contains a NUL byte")
        return raw

    target = project / "AGENTS.md"
    original = read(target)
    if candidate is not None:
        try:
            candidate_text = candidate.decode("utf-8")
        except (AttributeError, UnicodeError):
            raise InputError("guidance candidate must be UTF-8 bytes") from None
        if not candidate_text.strip() or "\0" in candidate_text:
            raise InputError("guidance candidate must contain non-empty instructions without NUL bytes")
    directories = [project]
    for part in cwd.relative_to(project).parts:
        directories.append(directories[-1] / part)
    selected = []
    texts = []
    used = 0
    root_selected = None
    for directory in directories:
        for name in names:
            path = directory / name
            raw = candidate if path == target and candidate is not None else read(path)
            if raw is None or not raw.decode("utf-8").strip():
                continue
            if directory == project:
                root_selected = path
            if path == target and candidate is None and raw != original:
                raise InputError("guidance changed during inspection; check again")
            selected.append({"path": str(path), "bytes": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest(),
                             "remaining_before": max(0, max_bytes - used),
                             "exceeds_remaining": len(raw) > max(0, max_bytes - used)})
            texts.append(raw.decode("utf-8").strip())
            used += len(raw)
            break
    problems = []
    if candidate is None and (original is None or not original.decode("utf-8").strip()):
        problems.append("target-missing-or-empty")
    if root_selected != target:
        problems.append("target-not-selected")
    if used > max_bytes:
        problems.append("project-guidance-exceeds-budget")

    loaded = "not-provided"
    if prompt_input is None and candidate is None:
        problems.append("host-export-required")
    if prompt_input is not None:
        if not isinstance(prompt_input, list):
            raise InputError("prompt input must be the JSON list exported by the intended host")
        header = f"# AGENTS.md instructions for {cwd}\n"
        blocks = []
        for message in prompt_input:
            if not isinstance(message, dict) or message.get("type") != "message" or message.get("role") != "user":
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (not isinstance(block, dict) or block.get("type") != "input_text"
                        or not isinstance(block.get("text"), str)):
                    continue
                text = block["text"]
                if text.startswith(header):
                    prefix, opening, remainder = text[len(header):].partition("<INSTRUCTIONS>")
                    body, closing, suffix = remainder.rpartition("</INSTRUCTIONS>")
                    if opening and closing and not prefix.strip() and not suffix.strip():
                        blocks.append(body)
        matched = False
        if len(blocks) == 1 and texts:
            position = 0
            matched = True
            for text in texts:
                start = blocks[0].find(text, position)
                if start < 0:
                    matched = False
                    break
                position = start + len(text)
        loaded = "matches-supplied-host-export" if matched else "missing-or-incomplete"
        if not matched:
            problems.append("loaded-guidance-not-verified")
    snapshot = {"project": str(project), "cwd": str(cwd), "max_bytes": max_bytes,
                "fallback_filenames": list(fallbacks), "sources": selected,
                "original_target_sha256": hashlib.sha256(original).hexdigest() if original is not None else None}
    return {**snapshot, "schema_version": 1,
            "check_kind": "candidate-projection" if candidate is not None else "current-guidance",
            "settings_basis": "caller-supplied effective host settings; not auto-discovered",
            "count_basis": "raw UTF-8 project-source bytes; excludes global guidance and prompt framing",
            "project_guidance_bytes": used, "remaining_bytes": max(0, max_bytes - used),
            "original_target_bytes": len(original) if original is not None else None,
            "problems": problems, "loaded_guidance": loaded,
            "candidate_fits": candidate is not None and not problems,
            "delivery_check_passed": candidate is None and not problems and loaded == "matches-supplied-host-export",
            "snapshot_sha256": digest(json.dumps(snapshot, sort_keys=True)),
            "limits": "A supplied fresh-host export is evidence only for that host/cwd/settings snapshot, not a running chat. No instructions, settings or files are changed."}


def line_text(value, label: str) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > 4096
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or "{{" in value or "}}" in value):
        raise InputError(f"invalid {label}")
    return value


def thread_id(value) -> str:
    value = line_text(value, "thread ID")
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except ValueError:
        raise InputError("invalid thread ID") from None
    return value


def validate_project(p: dict) -> dict:
    if not isinstance(p, dict):
        raise InputError("project must be an object")
    required = {"key", "project_path", "source_thread_ids", "automation_id", "kind", "extra_boundaries"}
    allowed = required | {"target_thread_id", "project_id"}
    if not required <= p.keys() or p.keys() - allowed:
        raise InputError("invalid project fields")
    if not isinstance(p["key"], str) or not KEY.fullmatch(p["key"]):
        raise InputError("invalid project key")
    path = Path(line_text(p["project_path"], "project path"))
    if not path.is_absolute() or ".." in path.parts or len(path.parts) < 3:
        raise InputError("project path must be an absolute scoped directory")
    if str(path) != p["project_path"]:
        raise InputError("project path must be normalized")
    sources = p["source_thread_ids"]
    if not isinstance(sources, list) or not sources:
        raise InputError("source threads are required")
    for source in sources:
        thread_id(source)
    if len(set(sources)) != len(sources):
        raise InputError("duplicate source threads")
    if p["automation_id"] is not None:
        if not isinstance(p["automation_id"], str) or not KEY.fullmatch(p["automation_id"]):
            raise InputError("invalid automation ID")
    if p["kind"] == "heartbeat":
        thread_id(p.get("target_thread_id"))
        if "project_id" in p:
            raise InputError("heartbeat cannot have project_id")
    elif p["kind"] == "cron":
        line_text(p.get("project_id"), "app project ID")
        if "target_thread_id" in p:
            raise InputError("standalone task cannot have target_thread_id")
    else:
        raise InputError("invalid task kind")
    if not isinstance(p["extra_boundaries"], list):
        raise InputError("extra boundaries must be a list")
    for boundary in p["extra_boundaries"]:
        line_text(boundary, "project boundary")
    return p


def load_registry(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise InputError("registry could not be read as JSON") from None
    if (not isinstance(data, dict) or set(data) != {"schema_version", "projects"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or not isinstance(data["projects"], list)):
        raise InputError("invalid registry schema")
    projects = [validate_project(p) for p in data["projects"]]
    for field in ("key", "project_path", "automation_id"):
        values = [p[field] for p in projects if p[field] is not None]
        if len(set(values)) != len(values):
            raise InputError(f"duplicate registry {field}")
    return projects


def template() -> tuple[str, str]:
    try:
        body = (ASSETS / "review.md").read_bytes().decode("utf-8")
        version = json.loads((ASSETS / "template.json").read_text(encoding="utf-8"))["version"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        raise InputError("template could not be loaded") from None
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise InputError("invalid template version")
    return body, version


def render_policy(project: dict, body: str | None = None, version: str | None = None) -> str:
    validate_project(project)
    if body is None or version is None:
        body, version = template()
    fields = {
        "agents_path": str(Path(project["project_path"]) / "AGENTS.md"),
        "source_threads": ", ".join(project["source_thread_ids"]),
        "project_boundaries": "\n".join("- " + s for s in project["extra_boundaries"])
        or "- No additional project-specific permissions are granted.",
    }
    if set(PLACEHOLDER.findall(body)) != set(fields):
        raise InputError("template placeholders do not match supported bindings")
    rendered = PLACEHOLDER.sub(lambda m: fields[m[1]], body).rstrip()
    if "{{" in rendered or "}}" in rendered:
        raise InputError("unresolved template placeholder")
    return (f"{MARKER}\nTemplate version: {version}\n"
            f"Template SHA-256: {digest(body)}\n"
            f"Project: {project['project_path']}\n\n{rendered}")


def validate_job(job: dict) -> dict:
    if (not isinstance(job, dict)
            or set(job) != {"schema_version", "project_path", "source_thread_ids", "extra_boundaries"}
            or type(job["schema_version"]) is not int or job["schema_version"] != 1):
        raise InputError("invalid review job schema")
    return validate_project({
        "key": "review-job", "automation_id": None, "kind": "cron",
        "project_id": "review-job", "project_path": job["project_path"],
        "source_thread_ids": job["source_thread_ids"],
        "extra_boundaries": job["extra_boundaries"],
    })


def render(project: dict) -> str:
    validate_project(project)
    job = {"schema_version": 1, **{key: project[key] for key in
           ("project_path", "source_thread_ids", "extra_boundaries")}}
    return (
        f"{MARKER}\n{CONTRACT}\nProject: {project['project_path']}\n\n"
        f"Use ${REVIEW_SKILL} from the currently enabled {PLUGIN} plugin. "
        "On every run and resumed invocation, resolve the enabled installation and read "
        "its current entry point and review policy afresh. Do not reuse policy from prior "
        "turns. If the plugin is missing, disabled, ambiguous or incompatible, stop and "
        "report the blocker without editing; do not use another copy or a copied policy.\n\n"
        "Resolve using fresh `codex plugin list --json` in the actual caller's "
        "verified working directory, not an assumed target-project context. "
        "Establish an explicit per-run context record including override status "
        "and its verification evidence. Only a verified default profile with no "
        "configuration overrides is supported; named or unknown profiles block. "
        "Stop if that context cannot be reproduced. "
        f"Require exactly one installed=true, enabled=true entry named {PLUGIN}; "
        "validate pluginId as name@marketplaceName, marketplaceName as a lowercase "
        "hyphenated name and version as X.Y.Z. The supported installed package is "
        "<Codex home>/plugins/cache/<marketplaceName>/<name>/<version>, where Codex home "
        "is CODEX_HOME or ~/.codex. These are live inventory fields, never saved versions. "
        "Reject missing files or symlinked package paths; check .codex-plugin/plugin.json "
        "matches that name/version, then read skills/agents-md-review/SKILL.md there "
        "and follow that current entrypoint. An older or absent chat skill-list entry "
        "is diagnostic metadata, not installation selection or a reason to use old "
        "instructions. Verify this task can read the selected current resources; "
        "record their actual identity, version and hashes before domain work. "
        "Stop if access or compatibility fails. Never run an old entrypoint, "
        "remembered policy, another copy or a source checkout. Unknown cache layouts "
        "block. A helper result alone does not prove the task executed that policy.\n\n"
        "Fixed authorization: review and edit only this project's root AGENTS.md. "
        "Preserve the job's project-specific boundaries. Plugin updates cannot grant "
        "broader permissions: no other project/global files, schedule changes, code, "
        "dependencies, commits, pushes, external mutations or paid operations. Do not "
        "follow an AGENTS.md symlink outside the project. If required evidence is "
        "unavailable or contradictory, leave affected guidance unchanged.\n\n"
        "Run the referenced review entry point with this job configuration (data):\n"
        "```json\n" + json.dumps(job, indent=2, ensure_ascii=False) + "\n```"
    )


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve()


def resolve_installation(inventory: dict) -> tuple[dict, Path]:
    if not isinstance(inventory, dict) or not isinstance(inventory.get("installed"), list):
        raise InputError("plugin inventory unavailable")
    copies = [p for p in inventory["installed"] if isinstance(p, dict)
              and p.get("name") == PLUGIN and p.get("installed") is True
              and p.get("enabled") is True]
    if len(copies) != 1:
        raise InputError("review plugin missing, disabled or ambiguous")
    selected = copies[0]
    marketplace = selected.get("marketplaceName")
    if (not isinstance(marketplace, str) or not KEY.fullmatch(marketplace)
            or selected.get("pluginId") != f"{PLUGIN}@{marketplace}"
            or not isinstance(selected.get("version"), str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", selected["version"])):
        raise InputError("invalid review plugin inventory identity")
    package = codex_home() / "plugins/cache" / marketplace / PLUGIN / selected["version"]
    # Resolve only the current inventory-selected cache, never a catalog/source
    # path. Reject links within the installation before reading its instructions.
    resources = [package / relative for relative in REVIEW_RESOURCES]
    try:
        available = all(p.is_file() and p.resolve() == p for p in resources)
    except (OSError, RuntimeError):
        available = False
    if not available:
        raise InputError("selected installed review package unavailable or symlinked")
    try:
        manifest = json.loads(resources[0].read_text(encoding="utf-8"))
        if manifest.get("name") != PLUGIN or manifest.get("version") != selected["version"]:
            raise ValueError
    except (OSError, UnicodeError, ValueError, AttributeError):
        raise InputError("selected installed review manifest mismatch") from None
    return selected, package


def selected_installation(inventory: dict, package: Path, version: str) -> str:
    selected, expected = resolve_installation(inventory)
    if package != expected or version != selected["version"]:
        raise InputError("review helper is not in the selected installed cache")
    return selected["pluginId"]


def current_inventory(cwd: Path | None = None, profile: str | None = None) -> dict:
    if profile is not None:
        raise InputError("named profiles unsupported by the validated Codex plugin inventory interface")
    command = ["codex"]
    if cwd is not None:
        command += ["--cd", str(cwd)]
    command += ["plugin", "list", "--json"]
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True,
                                text=True, timeout=15, check=True)
        return json.loads(result.stdout)
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        raise InputError("current Codex plugin inventory unavailable") from None


def resource_snapshot(package: Path) -> dict[str, bytes]:
    snapshot = {}
    try:
        for relative in REVIEW_RESOURCES:
            path = package / relative
            if not path.is_file() or path.resolve() != path:
                raise InputError("selected installed review resource unavailable or symlinked")
            before = path.stat()
            raw = path.read_bytes()
            after = path.stat()
            fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns")
            if any(getattr(before, key) != getattr(after, key) for key in fields):
                raise InputError("selected installed review resources changed during loading")
            if not raw or b"\0" in raw:
                raise InputError("selected installed review resource empty or invalid")
            raw.decode("utf-8")
            snapshot[relative] = raw
    except (OSError, UnicodeError, RuntimeError):
        raise InputError("selected installed review resources unreadable") from None
    return snapshot


def validate_context(context: dict) -> dict:
    required = {"schema_version", "cwd", "profile", "config_overrides", "verified", "evidence"}
    if (not isinstance(context, dict) or set(context) != required
            or type(context["schema_version"]) is not int or context["schema_version"] != 1
            or context["verified"] is not True or context["config_overrides"] != []):
        raise InputError("verified caller context required; configuration overrides unsupported")
    cwd = Path(line_text(context["cwd"], "caller cwd"))
    if not cwd.is_absolute() or ".." in cwd.parts or str(cwd) != context["cwd"]:
        raise InputError("invalid caller working directory")
    if context["profile"] is not None:
        raise InputError("named profiles unsupported; verified default profile required")
    line_text(context["evidence"], "context verification evidence")
    return context


def entrypoint_contract(entry: str) -> dict:
    parts = entry.split("---\n", 2)
    if (len(parts) != 3 or parts[0] or not re.search(
            r"(?m)^name: ['\"]?agents-md-review['\"]?\s*$", parts[1])):
        raise InputError("selected installed review entry point incompatible")
    declarations = parts[2].lstrip("\n").splitlines()
    declaration = declarations[0] if declarations else ""
    if not declaration.startswith(ENTRYPOINT_DECLARATION) or not declaration.endswith(" -->"):
        raise InputError("selected installed review entry point declaration missing")
    try:
        contract = json.loads(declaration[len(ENTRYPOINT_DECLARATION):-4])
    except ValueError:
        raise InputError("selected installed review entry point declaration invalid") from None
    if contract != ENTRYPOINT_CONTRACT:
        raise InputError("selected installed review entry point incompatible")
    return contract


def load_policy(job: dict, inventory: dict | None = None, context: dict | None = None) -> dict:
    project = validate_job(job)
    context = validate_context(context)
    cwd, profile = Path(context["cwd"]), context["profile"]
    if inventory is None:
        try:
            if (cwd.resolve(strict=True) != cwd or not cwd.is_dir()
                    or cwd != Path.cwd().resolve()):
                raise ValueError
        except (OSError, ValueError, RuntimeError):
            raise InputError("verified caller working directory differs from helper invocation") from None
    package = ASSETS.parent.parent.parent
    try:
        manifest = json.loads((package / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        if manifest.get("name") != PLUGIN or not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
            raise ValueError
        if not (package / "skills" / REVIEW_SKILL / "SKILL.md").is_file():
            raise ValueError
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
        raise InputError("review plugin identity or entry point unavailable") from None
    observed = current_inventory(cwd, profile) if inventory is None else inventory
    identity = selected_installation(observed,
                                     package, manifest["version"])
    resources = resource_snapshot(package)
    entry = resources["skills/agents-md-review/SKILL.md"].decode("utf-8")
    compatibility = entrypoint_contract(entry)
    try:
        current_manifest = json.loads(resources[".codex-plugin/plugin.json"])
        if current_manifest.get("name") != PLUGIN or current_manifest.get("version") != manifest["version"]:
            raise ValueError
        body = resources["skills/agents-md-maintenance/assets/review.md"].decode("utf-8")
        version = json.loads(resources["skills/agents-md-maintenance/assets/template.json"])["version"]
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError
    except (ValueError, KeyError, TypeError, AttributeError):
        raise InputError("selected installed review policy metadata incompatible") from None
    rendered = render_policy(project, body, version)
    rechecked = current_inventory(cwd, profile) if inventory is None else inventory
    if (selected_installation(rechecked, package, manifest["version"]) != identity
            or resource_snapshot(package) != resources):
        raise InputError("selected installed review resources changed during loading")
    hashes = {relative: hashlib.sha256(raw).hexdigest() for relative, raw in resources.items()}
    return {"plugin": PLUGIN, "qualified_plugin": identity, "plugin_version": manifest["version"],
            "installed_package": str(package), "task_contract": "plugin-reference/v1",
            "entrypoint": "skills/agents-md-review/SKILL.md",
            "entrypoint_contract": compatibility,
            "resource_hashes": hashes,
            "resource_manifest_sha256": digest(json.dumps(hashes, sort_keys=True, separators=(",", ":"))),
            "inventory_context": {**context, "basis": "caller-verified evidence; helper reproduces supplied context, not independent discovery" if inventory is None else "synthetic injected inventory; not native context qualification"},
            "resource_hash_scope": "Current disk bytes read during a stable installation; not an attestation of already-loaded interpreter code or an atomic filesystem snapshot",
            "policy_version": version, "policy_sha256": digest(body),
            "rendered_policy_sha256": digest(rendered), "instructions": rendered}


def read_automations(directory: Path) -> tuple[dict, list[dict]]:
    if not directory.is_dir():
        raise InputError("automation directory unavailable")
    tasks, errors = {}, []
    for entry in sorted(directory.iterdir()):
        if not entry.is_dir():
            continue
        file = entry / "automation.toml"
        if not file.exists():
            continue
        if entry.is_symlink() or file.is_symlink():
            errors.append({"automation_id": entry.name, "reason": "symlinked-automation"})
            continue
        try:
            if file.stat().st_size > 262144:
                raise ValueError
            raw = file.read_bytes()
            task = tomllib.loads(raw.decode("utf-8"))
            if (task.get("id") != entry.name or not isinstance(task.get("prompt"), str)
                    or task.get("kind") not in ("heartbeat", "cron")):
                raise ValueError
            tasks[entry.name] = task
        except (OSError, UnicodeError, ValueError):
            errors.append({"automation_id": entry.name, "reason": "unreadable-or-invalid-automation"})
    return tasks, errors


def reviewer_for(prompt: str, path: str) -> bool:
    # A publishing monitor that merely mentions AGENTS.md is not a reviewer.
    return ((prompt.startswith((MARKER,) + LEGACY_MARKERS)
             and f"\nProject: {path}\n" in prompt)
            or prompt.startswith(f"Review {path}/AGENTS.md as a small operating guide"))


def destination_matches(task: dict, project: dict) -> bool:
    if task.get("kind") != project["kind"]:
        return False
    if project["kind"] == "heartbeat":
        return task.get("target_thread_id") == project["target_thread_id"]
    # Check every supplied binding; an ID must not hide contradictory directories.
    if "project_id" in task and task["project_id"] != project["project_id"]:
        return False
    if "cwds" in task and task["cwds"] != [project["project_path"]]:
        return False
    # App versions may persist resolved directories rather than saved project IDs.
    return "project_id" in task or "cwds" in task


def catalog_veto_reference(prompt: str, project: dict) -> bool:
    """Recognize only the old loader with otherwise exact current job/bounds."""
    old, current = prompt.split("\n\n"), render(project).split("\n\n")
    return (len(old) == len(current) and len(old) >= 4
            and old[:2] == current[:2] and old[3:] == current[3:]
            and digest(old[2]) == LEGACY_CATALOG_LOADER_HASH)


def audit(projects: list[dict], directory: Path) -> dict:
    tasks, errors = read_automations(directory)
    body, version = template()
    findings = []
    for project in projects:
        validate_project(project)
        ident = project["automation_id"]
        expected = render(project)
        task = tasks.get(ident)
        candidates = [i for i, t in tasks.items()
                      if reviewer_for(t["prompt"], project["project_path"])]
        conflicts = [i for i in candidates if i != ident]
        finding = {"project": project["key"], "automation_id": ident,
                   "expected_prompt_sha256": digest(expected),
                   "task_status": task.get("status") if task else None,
                   "conflicting_reviewers": conflicts}
        if conflicts:
            status = "reviewer-conflict"
        elif ident is None:
            status = "unconfigured"
        elif any(e["automation_id"] == ident for e in errors):
            status = "unavailable"
        elif task is None:
            status = "missing"
        elif not destination_matches(task, project):
            status = "destination-mismatch"
        elif not reviewer_for(task["prompt"], project["project_path"]):
            status = "scope-mismatch"
        elif task["prompt"].startswith(tuple(marker + "\n" for marker in LEGACY_MARKERS)):
            status = "migration-required"
        elif CONTRACT not in task["prompt"].splitlines()[:2]:
            status = "migration-required"
        elif catalog_veto_reference(task["prompt"], project):
            status = "migration-required"
        elif task["prompt"] != expected:
            status = "outdated"
        else:
            status = "current"
        finding["instruction_status"] = status
        finding["guidance_status"] = "not-assessed"
        finding["policy_loading"] = "current-enabled-plugin-at-run-time"
        if task:
            finding["actual_prompt_sha256"] = digest(task["prompt"])
        findings.append(finding)
    registered = {p["automation_id"] for p in projects}
    unregistered = [i for i, t in tasks.items() if i not in registered and (
        t["prompt"].startswith(tuple(marker + "\n" for marker in (MARKER,) + LEGACY_MARKERS)) or re.match(
            r"Review /[^\n]+/AGENTS\.md as a small operating guide", t["prompt"]))]
    return {"template_version": version, "template_sha256": digest(body),
            "projects": findings, "unregistered_reviewers": unregistered,
            "errors": errors}


def main(argv=None) -> int:
    root = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "render"):
        sub = subs.add_parser(command)
        # Keep durable user state at its established path across product renames.
        sub.add_argument("--registry", type=Path, default=root / "maintain-agent-guidance/projects.json")
        if command == "audit":
            sub.add_argument("--automations-dir", type=Path, default=root / "automations")
        else:
            sub.add_argument("--project", required=True)
    policy = subs.add_parser("policy", help="Load current installed policy for a review job; never write")
    policy.add_argument("--job", required=True, help="Job JSON file, or - for standard input")
    policy.add_argument("--context", required=True, type=Path,
                        help="Per-run verified caller cwd/profile/override/evidence JSON; no inferred defaults")
    guidance = subs.add_parser("guidance", help="Check project instruction budget and supplied host export read-only")
    guidance.add_argument("--project", type=Path, required=True, help="Canonical project root selected by the intended host")
    guidance.add_argument("--cwd", type=Path, help="Intended working directory; defaults to project root")
    guidance.add_argument("--max-bytes", type=int, required=True, help="Verified effective project_doc_max_bytes; never inferred")
    guidance.add_argument("--fallback-filename", action="append", default=[], help="Effective fallback filenames, in order; repeat as needed")
    guidance.add_argument("--candidate", help="Proposed complete root AGENTS.md as a UTF-8 file, or - on standard input; never written")
    guidance.add_argument("--prompt-input", type=Path, help="Fresh codex debug prompt-input JSON file, or - on standard input, from the intended host/cwd/settings; not a model response")
    managed = subs.add_parser("managed", help="Inspect one managed section or prepare/check candidates; never write")
    commands = managed.add_subparsers(dest="managed_command", required=True)
    for name in ("inspect", "adopt", "replace", "reconcile", "check"):
        command = commands.add_parser(name)
        command.add_argument("--project", type=Path, required=True)
        if name != "inspect":
            command.add_argument("--expected-sha256", required=True, help="SHA-256 of the complete freshly read root file")
        if name == "adopt":
            command.add_argument("--start-line", type=int, required=True, help="First human-selected line, inclusive")
            command.add_argument("--end-line", type=int, required=True, help="Last human-selected line, inclusive")
        if name == "replace":
            command.add_argument("--body", type=Path, required=True, help="Proposed managed body as exact UTF-8 bytes")
        if name == "check":
            command.add_argument("--candidate", type=Path, required=True, help="Complete proposed root AGENTS.md")
    args = parser.parse_args(argv)
    try:
        if args.command == "managed":
            raw = read_managed_root(args.project)
            if args.managed_command == "inspect":
                section = managed_section(raw)
                print(json.dumps({"schema_version": 1, "status": "ready" if section else "adoption-required",
                                  "file_sha256": hashlib.sha256(raw).hexdigest(), "section": section,
                                  "limits": "Structure/checksum only, not proof of human adoption or loaded guidance."}, indent=2))
                return 0 if section else 1
            try:
                if args.managed_command == "adopt":
                    result = managed_adopt(raw, args.expected_sha256, args.start_line, args.end_line)
                elif args.managed_command == "replace":
                    result = managed_replace(raw, args.expected_sha256, args.body.read_bytes())
                elif args.managed_command == "reconcile":
                    result = managed_reconcile(raw, args.expected_sha256)
                else:
                    result = managed_check(raw, args.expected_sha256, args.candidate.read_bytes())
            except OSError:
                raise InputError("managed candidate or body could not be read") from None
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "guidance":
            if args.candidate is not None and args.prompt_input is not None:
                raise InputError("a candidate projection cannot verify a loaded prompt")
            try:
                candidate = (sys.stdin.buffer.read() if args.candidate == "-"
                             else Path(args.candidate).read_bytes()) if args.candidate is not None else None
                prompt = json.loads(sys.stdin.read() if str(args.prompt_input) == "-"
                                    else args.prompt_input.read_text(encoding="utf-8")) if args.prompt_input is not None else None
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise InputError("guidance candidate or host prompt export could not be read") from None
            result = guidance_check(args.project, args.max_bytes, args.cwd,
                                    tuple(args.fallback_filename), candidate, prompt)
            print(json.dumps(result, indent=2))
            return int(not (result["candidate_fits"] if args.candidate is not None else result["delivery_check_passed"]))
        if args.command == "policy":
            try:
                job = json.loads(sys.stdin.read() if args.job == "-" else Path(args.job).read_text(encoding="utf-8"))
                context = json.loads(args.context.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise InputError("review job could not be read as JSON") from None
            print(json.dumps(load_policy(job, context=context), indent=2))
            return 0
        projects = load_registry(args.registry)
        if args.command == "render":
            matches = [p for p in projects if p["key"] == args.project]
            if not matches:
                raise InputError("project is not registered")
            sys.stdout.write(render(matches[0]))
            return 0
        result = audit(projects, args.automations_dir)
        print(json.dumps(result, indent=2))
        return int(bool(result["errors"] or result["unregistered_reviewers"] or any(
            p["instruction_status"] != "current" for p in result["projects"])))
    except InputError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
