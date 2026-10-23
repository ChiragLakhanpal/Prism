"""Shared test setup: the network is off, and the fixture database is built once per run."""

import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
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


@pytest.fixture(scope="session")
def fixture_db():
    """The fixture database. The gate builds it first; a lone pytest run builds it when it is missing."""
    if not FIXTURE_DB.exists():
        subprocess.run([sys.executable, str(ROOT / "gates" / "build_fixture.py")], check=True)
    return FIXTURE_DB
