#!/usr/bin/env python3
"""Render task references, load current review policy, and audit schedules read-only."""
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
MARKER = "Maintain Agent Guidance review"
LEGACY_MARKERS = ("AGENTS.md self-improvement review",)
CONTRACT = "Task contract: plugin-reference/v1"
PLUGIN = "maintain-agent-guidance"
REVIEW_SKILL = "agents-md-review"
KEY = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")
PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


class InputError(ValueError):
    """A bounded error safe to report without echoing private input."""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        "Resolve using fresh `codex plugin list --json`, not a remembered skill catalog. "
        f"Require exactly one installed=true, enabled=true entry named {PLUGIN}; "
        "validate pluginId as name@marketplaceName, marketplaceName as a lowercase "
        "hyphenated name and version as X.Y.Z. The supported installed package is "
        "<Codex home>/plugins/cache/<marketplaceName>/<name>/<version>, where Codex home "
        "is CODEX_HOME or ~/.codex. These are live inventory fields, never saved versions. "
        "Reject missing files or symlinked package paths; check .codex-plugin/plugin.json "
        "matches that name/version, then read skills/agents-md-review/SKILL.md there "
        "and follow it. A stale available-skills catalog does not select another copy. "
        "Unknown cache layouts block; do not search source directories.\n\n"
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
    resources = [package / relative for relative in (
        ".codex-plugin/plugin.json", "skills/agents-md-review/SKILL.md",
        "skills/agents-md-maintenance/scripts/manage.py",
        "skills/agents-md-maintenance/assets/review.md",
        "skills/agents-md-maintenance/assets/template.json")]
    if any(not p.is_file() or p.resolve() != p for p in resources):
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


def current_inventory() -> dict:
    try:
        result = subprocess.run(["codex", "plugin", "list", "--json"],
                                capture_output=True, text=True, timeout=15, check=True)
        return json.loads(result.stdout)
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        raise InputError("current Codex plugin inventory unavailable") from None


def load_policy(job: dict, inventory: dict | None = None) -> dict:
    project = validate_job(job)
    package = ASSETS.parent.parent.parent
    try:
        manifest = json.loads((package / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        if manifest.get("name") != PLUGIN or not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
            raise ValueError
        if not (package / "skills" / REVIEW_SKILL / "SKILL.md").is_file():
            raise ValueError
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
        raise InputError("review plugin identity or entry point unavailable") from None
    identity = selected_installation(current_inventory() if inventory is None else inventory,
                                     package, manifest["version"])
    body, version = template()
    rendered = render_policy(project, body, version)
    return {"plugin": PLUGIN, "qualified_plugin": identity, "plugin_version": manifest["version"],
            "installed_package": str(package), "task_contract": "plugin-reference/v1",
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
        elif task["prompt"] != expected:
            status = "outdated"
        else:
            status = "current"
        finding["instruction_status"] = status
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
        sub.add_argument("--registry", type=Path, default=root / "maintain-agent-guidance/projects.json")
        if command == "audit":
            sub.add_argument("--automations-dir", type=Path, default=root / "automations")
        else:
            sub.add_argument("--project", required=True)
    policy = subs.add_parser("policy", help="Load current installed policy for a review job; never write")
    policy.add_argument("--job", required=True, help="Job JSON file, or - for standard input")
    args = parser.parse_args(argv)
    try:
        if args.command == "policy":
            try:
                job = json.loads(sys.stdin.read() if args.job == "-" else Path(args.job).read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise InputError("review job could not be read as JSON") from None
            print(json.dumps(load_policy(job), indent=2))
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
