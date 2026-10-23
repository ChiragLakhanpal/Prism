"""The offline tests cannot reach the network, so a test that needs it fails in the gate."""

import socket

import pytest

from conftest import NetworkIsOff


def test_a_test_cannot_reach_an_outside_host():
    with pytest.raises(NetworkIsOff):
        socket.create_connection(("pypi.org", 443), timeout=1)


def test_a_test_cannot_reach_an_outside_address():
    with pytest.raises(NetworkIsOff):
        socket.create_connection(("93.184.215.14", 443), timeout=1)


def test_a_test_can_still_reach_this_computer():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        with socket.create_connection(server.getsockname(), timeout=1):
            pass
