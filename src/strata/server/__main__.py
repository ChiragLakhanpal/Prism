"""Start the server: `uv run python -m strata.server`.

It listens on STRATA_SERVER_HOST (127.0.0.1 by default) and STRATA_SERVER_PORT. With no port
set, it takes DATABRICKS_APP_PORT, the port a Databricks App must listen on, and on this
computer a free port. It binds the socket itself before it starts, so the port it prints is the
port it holds. The app reads the rest of its settings from the environment
(src/strata/server/settings.py).
"""

import os
import socket

import uvicorn

from strata.ports import port_from_env


def main() -> None:
    host = os.environ.get("STRATA_SERVER_HOST", "").strip() or "127.0.0.1"
    port = port_from_env("STRATA_SERVER_PORT") or port_from_env("DATABRICKS_APP_PORT")
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    listener = socket.socket(family, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    shown = f"[{host}]" if family == socket.AF_INET6 else host  # an IPv6 address needs brackets in a URL
    print(f"Strata's server is listening at http://{shown}:{listener.getsockname()[1]}", flush=True)
    config = uvicorn.Config("strata.server.settings:app_from_env", factory=True, log_level="warning")
    uvicorn.Server(config).run(sockets=[listener])


if __name__ == "__main__":
    main()
