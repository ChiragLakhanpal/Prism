"""Starting the server: it takes its port from STRATA_SERVER_PORT, or picks a free one,
so copies from several worktrees run side by side."""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager

LISTENING = re.compile(r"http://(?:127\.0\.0\.1|\[::1\]):(\d+)")


@contextmanager
def server(**env):
    process = subprocess.Popen([sys.executable, "-m", "strata.server"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               # Clear the person's own settings, so only what the test gives counts.
                               env={**os.environ, "STRATA_SERVER_PORT": "", "STRATA_SERVER_HOST": "", **env})
    try:
        line = process.stdout.readline()
        match = LISTENING.search(line)
        assert match, f"the server did not say where it listens: {line!r}"
        yield match.group(0)
    finally:
        process.terminate()
        process.wait(timeout=10)


def port_of(address):
    return int(address.rsplit(":", 1)[1])


def health(address):
    deadline = time.monotonic() + 10
    while True:
        try:
            with urllib.request.urlopen(f"{address}/api/health", timeout=2) as response:
                return json.load(response)
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_two_servers_with_no_port_set_start_side_by_side():
    with server() as first, server() as second:
        assert first != second
        assert health(first) == {"status": "ok"}
        assert health(second) == {"status": "ok"}


def test_the_server_listens_on_the_port_it_is_given():
    port = free_port()

    with server(STRATA_SERVER_PORT=str(port)) as listening:
        assert port_of(listening) == port
        assert health(listening) == {"status": "ok"}


def test_the_server_prints_an_ipv6_address_in_brackets_so_it_can_be_opened():
    with server(STRATA_SERVER_HOST="::1") as listening:
        assert listening.startswith("http://[::1]:")
        assert health(listening) == {"status": "ok"}
