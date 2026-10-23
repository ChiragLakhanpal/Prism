"""The gate runs these tests on pytest-xdist workers, in their own lane. The network guard in the
root conftest.py must reach those workers too."""

import socket

import pytest


def test_a_test_in_the_ops_lane_cannot_reach_an_outside_host():
    with pytest.raises(RuntimeError, match="The offline tests may not"):
        socket.create_connection(("pypi.org", 443), timeout=1)
