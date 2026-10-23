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

LISTENING = re.compile(r"http://127\.0\.0\.1:(\d+)")


@contextmanager
def server(**env):
    process = subprocess.Popen([sys.executable, "-m", "strata.server"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               env={**os.environ, "STRATA_SERVER_PORT": "", **env})
    try:
        line = process.stdout.readline()
        match = LISTENING.search(line)
        assert match, f"the server did not say where it listens: {line!r}"
        yield int(match.group(1))
    finally:
        process.terminate()
        process.wait(timeout=10)


def health(port):
    deadline = time.monotonic() + 10
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
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
        assert listening == port
        assert health(port) == {"status": "ok"}
