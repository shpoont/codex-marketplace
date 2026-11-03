#!/usr/bin/env python3
"""Personal native-role management. No network, configuration edits or role execution."""

import os
import sys

if sys.version_info < (3, 12):
    raise SystemExit("Expert Roles requires Python 3.12 or newer")
if sys.platform not in ("darwin", "linux"):
    raise SystemExit("Expert Roles currently supports macOS and Linux only")

import argparse
from contextlib import contextmanager
import errno
import fcntl
import hashlib
import json
from pathlib import Path
import re
import stat
import tempfile
import tomllib
import uuid

PACKAGE = Path(__file__).resolve().parents[3]
PLUGIN = "expert-roles"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
RECOGNIZED_SHA256 = "76e4677ee352c614c2462679cf6fbde20105515d2c036912e74aed66f08f97e4"


class Conflict(Exception):
    """A condition requiring an explicit user decision; never force past it."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_file(path):
    """Read only a regular, non-symlink file, including at the open boundary."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise Conflict(f"Expected a regular file: {path}")
        return stream.read(), stat.S_IMODE(info.st_mode)


def regular_bytes(path):
    return regular_file(path)[0]


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value):
        raise Conflict("Unrecognized library version")
    return tuple(int(part) for part in value.split("."))


def check_directory(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise Conflict(f"Symlink directory requires a decision: {part}")
        if part.exists() and not part.is_dir():
            raise Conflict(f"Expected a directory: {part}")


def atomic_json(path, value):
    """Persist a complete JSON file and its directory before the next operation."""
    if path.is_symlink():
        raise Conflict(f"Refusing a symlink: {path}")
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_directory(path):
    check_directory(path)
    missing = []
    for part in (path, *path.parents):
        if part.exists():
            break
        missing.append(part)
    for part in reversed(missing):
        part.mkdir(mode=0o700, exist_ok=True)
        check_directory(part)
        sync_directory(part.parent)


def raise_io(error):
    raise error


class Manager:
    def __init__(self, codex_home=None, project=None, package=PACKAGE):
        configured = codex_home if codex_home is not None else os.environ.get("CODEX_HOME")
        if configured is not None and not str(configured).strip():
            raise Conflict("CODEX_HOME must not be empty")
        root = Path(configured).expanduser() if configured is not None else Path.home() / ".codex"
        if not root.is_absolute():
            raise Conflict("Use an absolute CODEX_HOME or --codex-home path")
        if root.is_symlink():
            raise Conflict("The selected Codex home is a symlink; choose its intended directory explicitly")
        # Resolve platform aliases in ancestors (for example the OS temporary root).
        self.home = root.resolve()
        self.agents = self.home / "agents"
        self.storage = self.home / "expert-roles"
        self.state_file = self.storage / "state.json"
        self.journal_file = self.storage / "pending.json"
        self.project = Path(project or Path.cwd()).resolve()
        self.package = Path(package)
        self.snapshot = json.loads(regular_bytes(self.package / "library/snapshot.json"))
        self.exports = {}
        self.payloads = {}
        for filename, expected in self.snapshot["files"].items():
            if not re.fullmatch(r"expert-[a-z0-9]+(?:-[a-z0-9]+)*\.toml", filename):
                raise Conflict("Invalid snapshot filename")
            data = regular_bytes(self.package / "library/codex" / filename)
            if digest(data) != expected:
                raise Conflict(f"Bundled export failed integrity check: {filename}")
            role = tomllib.loads(data.decode())
            name = role["name"]
            if name != filename.removesuffix(".toml") or name in self.exports:
                raise Conflict("Snapshot role name does not match its unique filename")
            self.exports[name] = role
            self.payloads[name] = data
        self.license = regular_bytes(self.package / "library/LICENSE")
        if digest(self.license) != self.snapshot["license_sha256"]:
            raise Conflict("Bundled library license failed integrity check")
        self.recognized = []
        historical = self.package / "library/recognized-releases.json"
        if os.path.lexists(historical):
            data = regular_bytes(historical)
            if digest(data) != RECOGNIZED_SHA256:
                raise Conflict("Recognized-release catalog failed integrity check")
            catalog = json.loads(data)
            if catalog["schema"] != 1 or catalog["repository"] != self.snapshot["repository"]:
                raise Conflict("Unrecognized historical library catalog")
            self.recognized = catalog["releases"]

    def name(self, value):
        name = value if value.startswith("expert-") else f"expert-{value}"
        if not SLUG.fullmatch(name) or name not in self.exports:
            raise Conflict("Choose an expert ID from the bundled list")
        return name

    def read_json(self, path, default):
        try:
            return json.loads(regular_bytes(path))
        except FileNotFoundError:
            return default

    def state(self):
        check_directory(self.storage)
        state = self.read_json(self.state_file, {"schema": 1, "owner": PLUGIN, "roles": {}})
        if not isinstance(state, dict) or state.get("schema") != 1 or state.get("owner") != PLUGIN:
            raise Conflict("Unrecognized ownership record; preserve it for review")
        roles = state.get("roles")
        if not isinstance(roles, dict):
            raise Conflict("Invalid ownership record")
        for name, entry in roles.items():
            self.validate_entry(name, entry)
        return state

    def validate_entry(self, name, entry):
        if not isinstance(name, str) or not SLUG.fullmatch(name) or not name.startswith("expert-"):
            raise Conflict("Invalid ownership identity")
        if not isinstance(entry, dict) or entry.get("path") != f"agents/{name}.toml":
            raise Conflict("Invalid ownership destination")
        if (entry.get("origin") != "created" or entry.get("scope") != "personal"
                or not isinstance(entry.get("sha256"), str) or not DIGEST.fullmatch(entry["sha256"])
                or not isinstance(entry.get("revision"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", entry["revision"])
                or not isinstance(entry.get("version"), str)
                or entry.get("repository") != self.snapshot["repository"]):
            raise Conflict("Invalid ownership provenance")

    def pending(self):
        check_directory(self.storage)
        value = self.read_json(self.journal_file, None)
        if value is None:
            return None
        if not isinstance(value, dict) or value.get("schema") != 1 or value.get("operation") not in ("install", "remove", "update"):
            raise Conflict("Invalid recovery record; preserve it for review")
        self.validate_entry(value.get("name"), value.get("entry"))
        if value["operation"] == "update":
            self.validate_update(value)
        return value

    def inventory(self):
        """Read personal and ancestor-project definitions; never edit configuration."""
        found, issues = {}, []
        folders = [("personal", self.home)]
        folders.extend(("project", parent / ".codex") for parent in (self.project, *self.project.parents)
                       if parent / ".codex" != self.home)
        for scope, folder in folders:
            directory = folder / "agents"
            try:
                check_directory(directory)
                for root, dirs, files in (os.walk(directory, followlinks=False, onerror=raise_io)
                                          if directory.exists() else ()):
                    for subdir in dirs:
                        if (Path(root) / subdir).is_symlink():
                            raise Conflict(f"Cannot inspect symlink agent directory: {Path(root) / subdir}")
                    for filename in sorted(files):
                        if not filename.endswith(".toml"):
                            continue
                        path = Path(root) / filename
                        data = regular_bytes(path)
                        role = tomllib.loads(data.decode())
                        name = role.get("name")
                        if not isinstance(name, str) or not name.strip():
                            raise Conflict(f"Agent file has no name: {path}")
                        name = name.strip()
                        found.setdefault(name, []).append({"scope": scope, "path": str(path), "sha256": digest(data)})
                config = folder / "config.toml"
                if os.path.lexists(config):
                    parsed = tomllib.loads(regular_bytes(config).decode())
                    registrations = parsed.get("agents", {})
                    if not isinstance(registrations, dict):
                        raise Conflict("Invalid agent configuration table")
                    for alias, value in registrations.items():
                        if not isinstance(value, dict):
                            continue
                        names = {alias}
                        reference = value.get("config_file")
                        if reference:
                            path = Path(reference).expanduser()
                            path = path if path.is_absolute() else folder / path
                            declared = tomllib.loads(regular_bytes(path).decode()).get("name")
                            if declared is not None:
                                if not isinstance(declared, str):
                                    raise Conflict("Invalid explicitly registered agent name")
                                if declared.strip():
                                    names.add(declared.strip())
                        # Protect the user's configured alias as well as the effective file name.
                        # Keep this conservative protection even when the loader favors the file name.
                        for name in names:
                            found.setdefault(name, []).append({"scope": scope, "path": str(config), "registration": True})
            except (OSError, ValueError, TypeError, UnicodeError, Conflict) as exc:
                # TOML errors can contain user data; never echo parser excerpts.
                issues.append(f"Cannot safely inspect {scope} agents or configuration ({type(exc).__name__})")
        return found, issues

    def status(self):
        state = self.state()
        check_directory(self.agents)
        found, issues = self.inventory()
        rows = []
        names = sorted(set(self.exports) | set(state["roles"]) | {n for n in found if n.startswith("expert-")})
        for name in names:
            definitions = found.get(name, [])
            entry = state["roles"].get(name)
            path = self.agents / f"{name}.toml"
            own = [d for d in definitions if d["path"] == str(path)]
            status = "available"
            version = None
            if entry:
                version = entry["version"]
                status = "managed" if own and own[0].get("sha256") == entry["sha256"] else "modified" if os.path.lexists(path) else "missing"
            elif definitions:
                expected = digest(self.payloads[name]) if name in self.payloads else None
                status = "manual-match" if len(definitions) == 1 and definitions[0].get("sha256") == expected else "unmanaged"
                if status == "manual-match":
                    version = self.snapshot["version"]
            if (len(definitions) > 1 or any(d["scope"] == "project" for d in definitions)
                    or (entry and any(d["path"] != str(path) for d in definitions))):
                status = "conflict"
            rows.append({"name": name, "status": status, "library_version": version,
                         "owned": bool(entry), "definitions": definitions})
        return {"roles": rows, "inspection_issues": issues, "pending": self.pending()}

    def plan(self, operation, name):
        status = self.status()
        if status["pending"]:
            raise Conflict("An interrupted operation is pending; inspect status and run recover explicitly")
        if status["inspection_issues"]:
            raise Conflict("Agent inspection is incomplete; resolve the reported issues before writing")
        row = next(row for row in status["roles"] if row["name"] == name)
        if operation == "install":
            if row["status"] == "managed":
                return "already-managed"
            if row["status"] != "available" or os.path.lexists(self.agents / f"{name}.toml"):
                raise Conflict(f"{name} is {row['status']}; existing files and registrations are never adopted or replaced")
        elif not row["owned"]:
            raise Conflict(f"{name} is not plugin-owned; no files will be removed")
        elif row["status"] not in ("managed", "missing"):
            raise Conflict(f"{name} is {row['status']}; preserve it for review")
        return "ready"

    @contextmanager
    def lock(self):
        check_directory(self.home)
        check_directory(self.storage)
        durable_directory(self.storage)
        fd = os.open(self.storage / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise Conflict("Invalid operation lock")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Conflict("Another Expert Roles operation is running") from exc
            yield
        finally:
            os.close(fd)

    def entry(self, name):
        return {"path": f"agents/{name}.toml", "scope": "personal", "origin": "created",
                "repository": self.snapshot["repository"], "revision": self.snapshot["revision"],
                "version": self.snapshot["version"], "sha256": digest(self.payloads[name])}

    def apply(self, operation, name, *, adopt=False, expected_plan=None):
        if operation == "update":
            return self.apply_update(name, adopt=adopt, expected_plan=expected_plan)
        # No lock/state directories are created for a rejected or idempotent plan.
        outcome = self.plan(operation, name)
        if outcome != "ready":
            return outcome
        with self.lock():
            outcome = self.plan(operation, name)
            if outcome != "ready":
                return outcome
            for filename in ("payload", "removed"):
                if os.path.lexists(self.storage / filename):
                    raise Conflict("Unrecognized transaction file; preserve it for review")
            state = self.state()
            entry = self.entry(name) if operation == "install" else state["roles"][name]
            atomic_json(self.journal_file, {"schema": 1, "operation": operation, "name": name, "entry": entry})
            return self.finish()

    def exclusive_write(self, path, data):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(path.parent)

    def finish(self):
        """Replay only a provable pending operation, never infer ownership from bytes."""
        pending = self.pending()
        if pending is None:
            return "nothing-pending"
        if pending["operation"] == "update":
            return self.finish_update(pending)
        name, entry, operation = pending["name"], pending["entry"], pending["operation"]
        path = self.agents / f"{name}.toml"
        state = self.state()
        existing = state["roles"].get(name)
        if existing is not None and existing != entry:
            raise Conflict("Ownership changed during the interrupted operation")
        check_directory(self.agents)
        found, issues = self.inventory()
        if issues or any(d["path"] != str(path) for d in found.get(name, [])):
            raise Conflict("Resolve competing definitions or inspection issues before recovery")
        if operation == "install":
            if existing is None:
                payload = self.storage / "payload"
                if not os.path.lexists(payload):
                    if os.path.lexists(path):
                        raise Conflict("An unowned file appeared during installation; preserve it")
                    data = self.payloads.get(name)
                    if data is None or digest(data) != entry["sha256"]:
                        raise Conflict("Recovery needs the original reviewed plugin snapshot")
                    self.exclusive_write(payload, data)
                if digest(regular_bytes(payload)) != entry["sha256"]:
                    raise Conflict("Staged bytes changed; preserve them for review")
                license_path = self.storage / "library-LICENSE"
                if os.path.lexists(license_path):
                    if regular_bytes(license_path) != self.license:
                        raise Conflict("Existing library license differs; preserve it for review")
                else:
                    self.exclusive_write(license_path, self.license)
                self.agents.mkdir(mode=0o700, exist_ok=True)
                # Exclusive atomic publication: never overwrite a file created since preflight.
                if not os.path.lexists(path):
                    os.link(payload, path, follow_symlinks=False)
                    sync_directory(self.agents)
                if path.is_symlink() or not os.path.samefile(payload, path):
                    raise Conflict("An unowned file appeared during installation; preserve it")
                if digest(regular_bytes(path)) != entry["sha256"]:
                    raise Conflict("Installed bytes changed; preserve them for review")
                state["roles"][name] = entry
                atomic_json(self.state_file, state)
            elif digest(regular_bytes(path)) != entry["sha256"]:
                raise Conflict("Installed bytes changed; preserve them for review")
        else:
            removed = self.storage / "removed"
            if os.path.lexists(removed):
                if os.path.lexists(path) or digest(regular_bytes(removed)) != entry["sha256"]:
                    raise Conflict("Removal conflict; preserve the role and captured file for review")
            elif os.path.lexists(path):
                if existing is None or digest(regular_bytes(path)) != entry["sha256"]:
                    raise Conflict("Role changed or ownership is absent; preserve it for review")
                os.rename(path, removed)
                sync_directory(self.agents)
                sync_directory(self.storage)
                if digest(regular_bytes(removed)) != entry["sha256"]:
                    # Restore without overwriting if an editor raced with removal.
                    os.link(removed, path, follow_symlinks=False)
                    sync_directory(self.agents)
                    raise Conflict("Role changed during removal; original bytes restored, captured copy retained")
            state["roles"].pop(name, None)
            atomic_json(self.state_file, state)
        for filename in ("payload", "removed"):
            extra = self.storage / filename
            if os.path.lexists(extra):
                if digest(regular_bytes(extra)) != entry["sha256"]:
                    raise Conflict("Transaction bytes changed; preserve them for review")
                extra.unlink()
        sync_directory(self.storage)
        self.journal_file.unlink()
        sync_directory(self.storage)
        return "installed" if operation == "install" else "removed"

    def identify(self, name, sha256):
        """Recognize exact reviewed exports, never a filename or version comment."""
        for release in [self.snapshot, *self.recognized]:
            if release["files"].get(name + ".toml") == sha256:
                return {"repository": self.snapshot["repository"], "version": release["version"],
                        "revision": release["revision"], "sha256": sha256}
        raise Conflict("This file is not an unchanged recognized canonical export; preserve user edits")

    def update_plan(self, name, *, adopt=False):
        status = self.status()
        if status["pending"] or status["inspection_issues"]:
            raise Conflict("Resolve pending recovery or incomplete inspection before updating")
        path = self.agents / (name + ".toml")
        row = next(row for row in status["roles"] if row["name"] == name)
        if row["status"] not in ("managed", "manual-match", "unmanaged") or len(row["definitions"]) != 1:
            raise Conflict(f"{name} is {row['status']}; update needs one unchanged personal definition")
        if row["definitions"][0]["path"] != str(path) or row["definitions"][0].get("registration"):
            raise Conflict("Only the canonical personal filename can be updated; preserve aliases and registrations")
        data, mode = regular_file(path)
        existing = self.state()["roles"].get(name)
        if existing:
            if digest(data) != existing["sha256"]:
                raise Conflict("Managed bytes changed; preserve them for review")
            source = {key: existing[key] for key in ("repository", "version", "revision", "sha256")}
        else:
            if not adopt:
                raise Conflict("This role is unmanaged; explicit --adopt is required to claim an unchanged canonical export")
            source = self.identify(name, digest(data))
        target = self.entry(name)
        if version_tuple(source["version"]) > version_tuple(target["version"]):
            raise Conflict("The installed role is newer than this bundle; downgrades are not supported")
        if source["version"] == target["version"] and any(source[k] != target[k] for k in ("revision", "sha256")):
            raise Conflict("The same library version has different provenance; preserve it for review")
        outcome = "already-current" if existing and all(source[k] == target[k] for k in source) else "ready"
        plan = {"result": outcome, "expert": name, "codex_home": str(self.home), "project": str(self.project),
                "destination": f"agents/{name}.toml",
                "current": dict(source, mode=mode), "target": target,
                "ownership": {"before": "managed" if existing else "unmanaged", "after": "managed", "adopt": not bool(existing)},
                "ownership_record_sha256": digest(json.dumps(existing, sort_keys=True).encode()),
                "backup": f"expert-roles/backups/{name}/{source['sha256']}.toml" if outcome == "ready" else None}
        plan["plan_sha256"] = digest(json.dumps(plan, sort_keys=True).encode())
        return plan

    def apply_update(self, name, *, adopt=False, expected_plan=None):
        def checked_plan():
            plan = self.update_plan(name, adopt=adopt)
            if plan["result"] != "already-current" and (not expected_plan or expected_plan != plan["plan_sha256"]):
                raise Conflict("Update needs --expect-plan from the unchanged preview; preview again after any change")
            return plan
        plan = checked_plan()
        if plan["result"] == "already-current":
            return "already-current"
        with self.lock():
            plan = checked_plan()
            if plan["result"] == "already-current":
                return "already-current"
            if any(os.path.lexists(self.storage / filename) for filename in ("payload", "removed")):
                raise Conflict("Unrecognized transaction file; preserve it for review")
            existing = self.state()["roles"].get(name)
            history = existing.get("history", []) if existing else []
            if not isinstance(history, list):
                raise Conflict("Unrecognized ownership history; preserve it for review")
            entry = dict(plan["target"], history=[*history, dict(plan["current"],
                         backup=plan["backup"], adopted=not bool(existing))])
            # A new canonical file is published by this operation, even when it
            # replaces a manually installed export. Keep v1 ownership compatibility;
            # history explicitly discloses the adoption instead of disguising it.
            pending = {"schema": 1, "operation": "update", "name": name, "entry": entry,
                       "before": dict(plan["current"], entry=existing), "backup": plan["backup"],
                       "transaction": uuid.uuid4().hex, "plan_sha256": plan["plan_sha256"],
                       "approved_preview": plan}
            pending["journal_sha256"] = digest(json.dumps(pending, sort_keys=True).encode())
            self.validate_update(pending)
            atomic_json(self.journal_file, pending)
            return self.finish()

    def validate_update(self, pending):
        if (set(pending) != {"schema", "operation", "name", "entry", "before", "backup", "transaction",
                             "plan_sha256", "approved_preview", "journal_sha256"}
                or digest(json.dumps({k: v for k, v in pending.items() if k != "journal_sha256"},
                                     sort_keys=True).encode()) != pending.get("journal_sha256")):
            raise Conflict("Update recovery record changed or needs its initiating helper; preserve it for review")
        name, before = pending["name"], pending.get("before")
        entry = pending["entry"]
        self.validate_entry(name, entry)
        if (not isinstance(before, dict) or not DIGEST.fullmatch(str(before.get("sha256", "")))
                or before.get("repository") != self.snapshot["repository"]
                or not re.fullmatch(r"[0-9a-f]{40}", str(before.get("revision", "")))
                or type(before.get("mode")) is not int or not 0 <= before["mode"] <= 0o7777
                or not re.fullmatch(r"[0-9a-f]{32}", str(pending.get("transaction", "")))
                or not DIGEST.fullmatch(str(pending.get("plan_sha256", "")))
                or pending.get("backup") != f"expert-roles/backups/{name}/{before['sha256']}.toml"):
            raise Conflict("Invalid update recovery record; preserve it for review")
        version_tuple(before.get("version"))
        if before.get("entry") is not None:
            self.validate_entry(name, before["entry"])
            if any(before[key] != before["entry"][key] for key in ("repository", "version", "revision", "sha256")):
                raise Conflict("Update source and ownership differ")
        elif any(before[k] != self.identify(name, before["sha256"])[k]
                 for k in ("repository", "version", "revision", "sha256")):
            raise Conflict("Unrecognized adoption provenance")
        known_target = self.identify(name, entry["sha256"])
        if (any(entry[k] != known_target[k] for k in known_target)
                or version_tuple(before["version"]) > version_tuple(entry["version"])):
            raise Conflict("Unrecognized update target provenance or downgrade")
        prior_history = before["entry"].get("history", []) if before.get("entry") else []
        history = dict((key, before[key]) for key in ("repository", "version", "revision", "sha256", "mode"))
        history.update(backup=pending["backup"], adopted=before.get("entry") is None)
        if not isinstance(prior_history, list) or entry.get("history") != [*prior_history, history]:
            raise Conflict("Update ownership history differs; preserve it for review")
        preview = pending["approved_preview"]
        if not isinstance(preview, dict):
            raise Conflict("Missing approved update preview; preserve recovery files")
        body = {k: v for k, v in preview.items() if k != "plan_sha256"}
        if (preview.get("plan_sha256") != pending["plan_sha256"]
                or digest(json.dumps(body, sort_keys=True).encode()) != pending["plan_sha256"]):
            raise Conflict("Approved update preview changed; preserve recovery files")
        for key in ("codex_home", "project"):
            if not isinstance(body.get(key), str) or not Path(body[key]).is_absolute():
                raise Conflict("Invalid approved preview context")
        expected = {"result": "ready", "expert": name, "codex_home": body["codex_home"],
                    "project": body["project"], "destination": entry["path"],
                    "current": {k: before[k] for k in ("repository", "version", "revision", "sha256", "mode")},
                    "target": {k: entry[k] for k in ("path", "scope", "origin", "repository", "revision", "version", "sha256")},
                    "ownership": {"before": "managed" if before.get("entry") else "unmanaged",
                                  "after": "managed", "adopt": before.get("entry") is None},
                    "ownership_record_sha256": digest(json.dumps(before.get("entry"), sort_keys=True).encode()),
                    "backup": pending["backup"]}
        if body != expected or set(entry) != set(expected["target"]) | {"history"}:
            raise Conflict("Update transition differs from its approved preview; preserve recovery files")
        # Preview paths are historical context only. Recovery uses this manager's
        # selected home and freshly inspected project, including after relocation.

    def check_update_file(self, path, expected):
        data, mode = regular_file(path)
        if digest(data) != expected["sha256"] or mode != expected["mode"]:
            raise Conflict("Update bytes or mode changed; preserve the role and recovery files")
        return data

    def update_backup(self, pending, source):
        before = pending["before"]
        backup = self.home / pending["backup"]
        check_directory(backup.parent)
        durable_directory(backup.parent)
        if not os.path.lexists(backup):
            self.exclusive_write(backup, self.check_update_file(source, before))
            backup.chmod(0o400)
            sync_directory(backup.parent)
        data, mode = regular_file(backup)
        if digest(data) != before["sha256"] or mode != 0o400:
            raise Conflict("Original backup changed; preserve it for review")
        metadata = {key: before[key] for key in ("repository", "version", "revision", "sha256", "mode")}
        metadata_path = backup.with_suffix(".json")
        if not os.path.lexists(metadata_path):
            self.exclusive_write(metadata_path, (json.dumps(metadata, sort_keys=True) + "\n").encode())
            metadata_path.chmod(0o400)
            sync_directory(backup.parent)
        data, mode = regular_file(metadata_path)
        if json.loads(data) != metadata or mode != 0o400:
            raise Conflict("Backup provenance changed; preserve it for review")

    def finish_update(self, pending):
        name, entry, before = pending["name"], pending["entry"], pending["before"]
        path = self.agents / (name + ".toml")
        state = self.state()
        existing = state["roles"].get(name)
        if existing != before.get("entry") and existing != entry:
            raise Conflict("Ownership changed during the interrupted update")
        check_directory(self.agents)
        found, issues = self.inventory()
        if issues or any(d["path"] != str(path) or d.get("registration") for d in found.get(name, [])):
            raise Conflict("Resolve competing definitions or inspection issues before update recovery")
        workspace = self.storage / "updates" / pending["transaction"]
        check_directory(workspace)
        durable_directory(workspace)
        if self.agents.stat().st_dev != workspace.stat().st_dev:
            raise Conflict("Update requires staging and personal agents on the same filesystem")
        if any(p.name not in ("payload", "captured") for p in workspace.iterdir()):
            raise Conflict("Unrecognized update transaction file; preserve it for review")
        payload, captured = workspace / "payload", workspace / "captured"
        target = dict(entry, mode=before["mode"])
        if existing != entry:
            if not os.path.lexists(payload):
                # Recovery must not substitute different bundle bytes for the
                # recorded target. Keep the initiating helper until pending clears.
                data = self.payloads.get(name)
                if data is None or digest(data) != entry["sha256"]:
                    raise Conflict("Recovery needs the original reviewed plugin snapshot")
                self.exclusive_write(payload, data)
                payload.chmod(before["mode"])
                sync_directory(workspace)
            self.check_update_file(payload, target)
        source = captured if os.path.lexists(captured) else path
        self.update_backup(pending, source)
        license_path = self.storage / "library-LICENSE"
        if os.path.lexists(license_path):
            if regular_bytes(license_path) != self.license:
                raise Conflict("Existing library license differs; preserve it for review")
        else:
            self.exclusive_write(license_path, self.license)
        if existing != entry:
            if not os.path.lexists(captured):
                if os.path.lexists(path) and os.path.samefile(payload, path):
                    raise Conflict("Original capture is missing; preserve the staged and installed files")
                self.check_update_file(path, before)
                os.rename(path, captured)
                sync_directory(self.agents)
                sync_directory(workspace)
            try:
                self.check_update_file(captured, before)
            except Conflict:
                if not os.path.lexists(path):
                    os.link(captured, path, follow_symlinks=False)
                    sync_directory(self.agents)
                raise Conflict("Role changed during capture; original retained/restored, pending evidence preserved")
            if not os.path.lexists(path):
                os.link(payload, path, follow_symlinks=False)
                sync_directory(self.agents)
            if path.is_symlink() or not os.path.samefile(payload, path):
                raise Conflict("An unowned file appeared during update; preserve both files")
            self.check_update_file(path, target)
            self.check_update_file(captured, before)
            state["roles"][name] = entry
            atomic_json(self.state_file, state)
        else:
            self.check_update_file(path, target)
            self.check_update_file(captured, before)
        if os.path.lexists(payload):
            self.check_update_file(payload, target)
            payload.unlink()
            sync_directory(workspace)
        # Retain the captured original, including any future edits through an
        # already-open editor handle. Never discard that evidence as cleanup.
        self.journal_file.unlink()
        sync_directory(self.storage)
        return "updated"

    def recover(self, apply=False):
        pending = self.pending()
        if pending is None or not apply:
            return {"pending": pending, "applied": False}
        with self.lock():
            return {"result": self.finish(), "applied": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", help="Absolute personal Codex home (default: CODEX_HOME, then ~/.codex)")
    parser.add_argument("--project", help="Project directory to inspect for conflicts; never a write destination")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List the bundled canonical experts")
    sub.add_parser("status", help="Inspect personal ownership and project conflicts")
    for operation in ("install", "remove"):
        action = sub.add_parser(operation, help="Preview one personal-role change; --apply writes")
        action.add_argument("expert")
        action.add_argument("--apply", action="store_true")
    update = sub.add_parser("update", help="Preview one personal-role update, optionally adopting an exact canonical export")
    update.add_argument("expert")
    update.add_argument("--adopt", action="store_true", help="Explicitly claim a verified unchanged manual export")
    update.add_argument("--expect-plan", help="SHA256 of the unchanged update preview, required for apply")
    update.add_argument("--apply", action="store_true")
    recovery = sub.add_parser("recover", help="Inspect an interrupted operation; --apply resumes it")
    recovery.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        manager = Manager(args.codex_home, args.project)
        result = {"command": args.command, "scope": "personal", "codex_home": str(manager.home),
                  "library_version": manager.snapshot["version"], "library_revision": manager.snapshot["revision"]}
        if args.command == "list":
            result["experts"] = [{"id": name.removeprefix("expert-"), "name": name,
                                  "description": role["description"]} for name, role in sorted(manager.exports.items())]
        elif args.command == "status":
            result.update(manager.status())
        elif args.command == "recover":
            result.update(manager.recover(args.apply))
        elif args.command == "update":
            name = manager.name(args.expert)
            result.update(manager.update_plan(name, adopt=args.adopt))
            result["applied"] = args.apply
            if args.apply:
                result["result"] = manager.apply("update", name, adopt=args.adopt, expected_plan=args.expect_plan)
        else:
            name = manager.name(args.expert)
            result.update({"expert": name, "applied": args.apply,
                           "result": manager.apply(args.command, name) if args.apply else manager.plan(args.command, name)})
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (Conflict, OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        # Avoid parser excerpts or raw role/configuration content in diagnostics.
        code = errno.errorcode.get(exc.errno, type(exc).__name__) if isinstance(exc, OSError) else type(exc).__name__
        message = str(exc) if isinstance(exc, Conflict) else f"Operation stopped ({code}); inspect status and preserve pending files"
        print(json.dumps({"error": message, "completed": False, "recovery_may_be_needed": True}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
