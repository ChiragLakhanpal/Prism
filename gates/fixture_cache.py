"""The fixture database's cache (ticket 119): a build whose inputs have not changed keeps the database.

gates/build_fixture.py calls start() before it imports anything else. start() waits until no other
build of the same database is running, since the gate's two python lanes both start with the build.
Then it reads the key beside the database, data/out/fixture.inputs.json. When every file and folder
the key names still hashes the same, and the database still holds the bytes the build wrote, start()
says so and ends the process, so the database stays as it is. Otherwise it records every file and
folder under the repo that the build reads from then on, and write() saves their hashes as the new
key once the build has swapped the new database in.

So the key holds what the build actually read: the recorded files, the table definitions and the
folders they sit in, the config files, the code it imported, the build script itself, and uv.lock,
which pins the packages. A file the build never reads, such as a screen test, never rebuilds it.
The key compares bytes, never modification times, so a fresh checkout or a switch between branches
rebuilds only when an input differs.

This file uses only the standard library, so it runs before the build imports the readers.
"""

import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path

ALWAYS = ("uv.lock",)  # read by uv, not by the build, but it pins every package the build imports
# Folders whose files are never the build's inputs: the packages, the build's own output, git, caches and scratch.
LEFT_OUT = (".venv", ".git", "data/out", ".gate-tmp", "node_modules")
WRITES = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
# The import system reads compiled modules and lists package folders on its own. The key holds each
# imported module's source instead, so a new module file that nothing imports never rebuilds the database.
IMPORT_SYSTEM = "<frozen importlib"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Cache:
    def __init__(self, database, root):
        self.database = Path(database)
        self.root = Path(root).resolve()
        self.key = self.database.with_name(f"{self.database.stem}.inputs.json")
        self.lock = self.database.with_name(f"{self.database.stem}.lock")
        self.opened, self.listed = set(), set()
        self.recording = False
        self._held = None

    def name(self, path):
        """A path as the key writes it: relative to the root, with forward slashes."""
        return Path(path).resolve().relative_to(self.root).as_posix()

    def hold(self):
        """Wait until no other build of this database is running. The lock lasts until the process ends."""
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._held = open(self.lock, "a")
        try:
            fcntl.flock(self._held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another build of the fixture database is running, so this build waits for it to finish.",
                  flush=True)
            fcntl.flock(self._held, fcntl.LOCK_EX)

    def changed(self):
        """Why the database must be built again, as a short phrase, or None when the key still holds."""
        if not self.database.is_file():
            return f"there is no {self.name(self.database)}"
        try:
            key = json.loads(self.key.read_text())
        except (OSError, ValueError):
            return f"there is no key at {self.name(self.key)}"
        if key.get("python") != sys.version:
            return "Python's version changed"
        for name, digest in key.get("files", {}).items():
            path = self.root / name
            if (sha256(path) if path.is_file() else None) != digest:
                return f"{name} changed"
        for name, digest in key.get("folders", {}).items():
            if self.listing(self.root / name) != digest:
                return f"the files in {name} changed"
        if Path(f"{self.database}.wal").exists() or sha256(self.database) != key.get("database"):
            return f"{self.name(self.database)} changed after its build"
        return None

    @staticmethod
    def listing(folder):
        """A hash of a folder's file names, or None when it is missing. Hidden files and compiled modules are left
        out, so a .DS_Store, a __pycache__ folder or the gate's .gate-tmp never builds the database again."""
        try:
            names = sorted(name for name in os.listdir(folder) if not name.startswith(".") and name != "__pycache__")
        except OSError:
            return None
        return hashlib.sha256("\n".join(names).encode()).hexdigest()

    def inside(self, path):
        """The path's name in the key when the build's reading of it counts as an input, else None."""
        try:
            name = Path(os.path.abspath(os.fsdecode(path))).resolve().relative_to(self.root).as_posix()
        except (TypeError, ValueError, OSError):
            return None
        if "__pycache__" in name.split("/") or any(name == folder or name.startswith(folder + "/")
                                                   for folder in LEFT_OUT):
            return None
        return name

    def record(self):
        """Note every file the process reads and every folder it lists from now on."""
        self.recording = True
        sys.addaudithook(self._audit)

    def _audit(self, event, args):
        """Python calls this before each audited action. An error raised here would stop that action, so it only
        reads what it is given."""
        if not self.recording or event not in ("open", "os.listdir", "os.scandir"):
            return
        caller = sys._getframe(0).f_back  # the code that opened or listed, or None when no Python code did
        if caller is not None and caller.f_code.co_filename.startswith(IMPORT_SYSTEM):
            return
        if event == "open":
            path, mode, flags = args
            if isinstance(path, int) or (mode is not None and any(letter in mode for letter in "wax+")):
                return
            if mode is None and flags & WRITES:
                return
            self.opened.add(path)
        elif args and args[0] is not None and not isinstance(args[0], int):
            self.listed.add(args[0])

    def write(self):
        """Save the hashes of what the build read, of the modules it ran, and of the new database."""
        self.recording = False
        modules = [getattr(module, "__file__", None) for module in list(sys.modules.values())]
        files = {name for name in map(self.inside, [*self.opened, *filter(None, modules)]) if name}
        files |= {name for name in ALWAYS if (self.root / name).exists()}
        folders = {name for name in map(self.inside, self.listed) if name}
        key = {
            "about": "What the last build of the fixture database read (gates/fixture_cache.py). Delete this file "
                     "to build the database again.",
            "python": sys.version,
            "database": sha256(self.database),
            "files": {name: sha256(self.root / name) if (self.root / name).is_file() else None
                      for name in sorted(files - folders)},
            "folders": {name: self.listing(self.root / name) for name in sorted(folders)},
        }
        written = self.key.with_name(self.key.name + ".writing")
        written.write_text(json.dumps(key, indent=1) + "\n")
        os.replace(written, self.key)


def start(database, root):
    """Hold the build's lock, then end the process when the database is up to date, or start recording.

    Returns the Cache, whose write() the build calls once the new database is in place.
    """
    cache = Cache(database, root)
    cache.hold()
    reason = cache.changed()
    if reason is None:
        print(f"None of the files the last build read has changed, so the build kept "
              f"{cache.name(cache.database)} as it was ({cache.name(cache.key)} lists them).", flush=True)
        sys.exit(0)
    print(f"The build makes {cache.name(cache.database)} again, because {reason}.", flush=True)
    cache.record()
    return cache
