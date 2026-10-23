"""Ports for the server and the web app.

Each takes its port from an environment variable (STRATA_SERVER_PORT, STRATA_WEB_PORT) and
picks a free port when the variable is unset, so copies from several worktrees can run
side by side.

`python -m strata.ports 2` prints two different free ports, one per line.
"""

import contextlib
import os
import socket
import sys


def port_from_env(name: str) -> int:
    """The port in the named variable, or 0, which asks the system for a free port when binding."""
    value = os.environ.get(name, "").strip()
    return int(value) if value else 0


def free_ports(count: int, host: str = "127.0.0.1") -> list[int]:
    """Free ports, all different, because each socket stays open until all are chosen."""
    with contextlib.ExitStack() as stack:
        probes = [stack.enter_context(socket.socket()) for _ in range(count)]
        for probe in probes:
            probe.bind((host, 0))
        return [probe.getsockname()[1] for probe in probes]


if __name__ == "__main__":
    print("\n".join(str(port) for port in free_ports(int(sys.argv[1]) if len(sys.argv) > 1 else 1)))
