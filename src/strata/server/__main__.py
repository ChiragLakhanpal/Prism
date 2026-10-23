"""Start the server: `uv run python -m strata.server`.

It listens on STRATA_SERVER_HOST (127.0.0.1 by default) and STRATA_SERVER_PORT, or on a
free port when no port is set. It binds the socket itself before it starts, so the port
it prints is the port it holds.
"""

import os
import socket

import uvicorn

from strata.ports import port_from_env


def main() -> None:
    host = os.environ.get("STRATA_SERVER_HOST", "").strip() or "127.0.0.1"
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    listener = socket.socket(family, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port_from_env("STRATA_SERVER_PORT")))
    print(f"Strata's server is listening at http://{host}:{listener.getsockname()[1]}", flush=True)
    config = uvicorn.Config("strata.server.app:create_app", factory=True, log_level="warning")
    uvicorn.Server(config).run(sockets=[listener])


if __name__ == "__main__":
    main()
