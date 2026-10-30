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

PACKAGE = Path(__file__).resolve().parents[3]
PLUGIN = "expert-roles"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class Conflict(Exception):
    """A condition requiring an explicit user decision; never force past it."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path):
    """Read only a regular, non-symlink file, including at the open boundary."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Conflict(f"Expected a regular file: {path}")
        return stream.read()


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
        if not isinstance(value, dict) or value.get("schema") != 1 or value.get("operation") not in ("install", "remove"):
            raise Conflict("Invalid recovery record; preserve it for review")
        self.validate_entry(value.get("name"), value.get("entry"))
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
        self.storage.mkdir(parents=True, exist_ok=True, mode=0o700)
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

    def apply(self, operation, name):
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
