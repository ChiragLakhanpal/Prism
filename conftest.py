"""Every Python test runs with the network off, wherever it lives.

The gate runs the Python tests in more than one pytest process, in separate lanes, and the python
and ops lanes hand their tests to pytest-xdist workers. This file sits at the root, so pytest loads
it in each of them. tests/test_offline.py and ops/dayone/tests/test_network_off.py check that it
reaches the workers.

It also gives pytest the --shard option, which the gate's python-1 and python-2 lanes pass (ticket 119).
`--shard=1/2` sorts the test files under the paths pytest was given by their paths from the root and runs
the first half of them; `--shard=2/2` runs the second half. With an odd number of files, the first half
has one file fewer. The split reads only the files' names, so it is the same on every computer and in
every run, and tests/test_gate.py checks that the two lanes run every test file once.
"""

import fnmatch
import os
import socket
from pathlib import Path

import pytest

LEFT_OUT = pytest.StashKey[frozenset]()  # the test files the other shards run

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", None, ""}


class NetworkIsOff(RuntimeError):
    pass


def _local(address):
    if isinstance(address, (str, bytes)):  # a Unix socket path
        return True
    return address[0] in LOCAL_HOSTS


def _guard(original):
    def connect(self, address, *args, **kwargs):
        if self.family != socket.AF_UNIX and not _local(address):
            raise NetworkIsOff(f"The offline tests may not reach {address[0]}.")
        return original(self, address, *args, **kwargs)
    return connect


@pytest.fixture(autouse=True, scope="session")
def network_off():
    """Any connection to a host other than this computer fails the test that made it."""
    originals = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
    socket.socket.connect = _guard(originals[0])
    socket.socket.connect_ex = _guard(originals[1])

    def getaddrinfo(host, *args, **kwargs):
        if host not in LOCAL_HOSTS:
            raise NetworkIsOff(f"The offline tests may not look up {host}.")
        return originals[2](host, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo
    yield
    socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = originals


def pytest_addoption(parser):
    parser.addoption("--shard", metavar="K/N", default=None,
                     help="run only part K of N of the test files, split by their paths in name order (the gate's "
                          "python lanes pass 1/2 and 2/2)")


def shard_of(value):
    """(K, N) from "K/N", such as (1, 2) from "1/2"."""
    try:
        current, total = (int(part) for part in value.split("/"))
    except ValueError:
        current = total = 0
    if not 1 <= current <= total:
        raise pytest.UsageError(f"--shard takes a part and a number of parts, such as 1/2, not {value}.")
    return current, total


def test_files(config):
    """Every file under the paths pytest was given whose name pytest's python_files patterns match, sorted by its
    path from the root. It skips the folders pytest skips: hidden ones, __pycache__ and those norecursedirs names."""
    patterns, skipped = config.getini("python_files"), config.getini("norecursedirs")
    found = set()
    for arg in config.args:
        # Made absolute as pytest makes the paths it collects, without following links, so the two compare equal
        path = Path(os.path.abspath(Path(config.invocation_params.dir, arg.split("::")[0])))
        if path.is_file():
            found.add(path)
            continue
        for folder, folders, files in os.walk(path):
            folders[:] = [name for name in folders if not name.startswith(".") and name != "__pycache__"
                          and not any(fnmatch.fnmatch(name, pattern) for pattern in skipped)]
            found.update(Path(folder, name) for name in files
                         if any(fnmatch.fnmatch(name, pattern) for pattern in patterns))
    return sorted(found, key=lambda file: Path(os.path.relpath(file, config.rootpath)).as_posix())


def pytest_configure(config):
    if config.getoption("shard") is None:
        return
    current, total = shard_of(config.getoption("shard"))
    files = test_files(config)
    start, end = (current - 1) * len(files) // total, current * len(files) // total
    config.stash[LEFT_OUT] = frozenset(files[:start] + files[end:])


def pytest_ignore_collect(collection_path, config):
    """Leave out the test files another shard runs."""
    if collection_path in config.stash.get(LEFT_OUT, ()):
        return True
    return None
