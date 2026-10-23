"""The offline tests cannot reach the network, so a test that needs it fails in the gate."""

import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# What the guard in ../conftest.py says when a test reaches past this computer.
REFUSED = "The offline tests may not"


def test_a_test_cannot_reach_an_outside_host():
    with pytest.raises(RuntimeError, match=REFUSED):
        socket.create_connection(("pypi.org", 443), timeout=1)


def test_a_test_cannot_reach_an_outside_address():
    with pytest.raises(RuntimeError, match=REFUSED):
        socket.create_connection(("93.184.215.14", 443), timeout=1)


def test_a_test_can_still_reach_this_computer():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        with socket.create_connection(server.getsockname(), timeout=1):
            pass


def test_a_pytest_run_of_only_the_ops_tests_has_the_network_off_too():
    """The gate runs the ops tests in a pytest process of their own, in their own lane."""
    done = subprocess.run([sys.executable, "-m", "pytest", "--setup-plan", "ops"],
                          cwd=ROOT, capture_output=True, text=True)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "SETUP    S network_off" in done.stdout
