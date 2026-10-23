"""The bundle as the code reads it offline: databricks.yml and the files it includes.

The bundle is the one place that declares the catalog, its schemas and volume, their grants and
the nightly job. The DuckDB build, the local run of the nightly job and the deploy report read
it from here, so none of them keeps a second list. This reader resolves only what those need:
variables to their defaults, and ${resources.<kind>.<key>.name} to that resource's name. Every
other reference, such as ${workspace.file_path}, stays as written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REFERENCE = re.compile(r"\$\{([^}]+)\}")


@dataclass(frozen=True)
class Bundle:
    root: Path
    data: dict

    def resources(self, kind: str) -> dict:
        return self.data.get("resources", {}).get(kind, {})

    def resolve(self, value):
        """value with every variable and resource-name reference replaced, at any depth."""
        if isinstance(value, dict):
            return {key: self.resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, str):
            return REFERENCE.sub(self._lookup, value)
        return value

    def _lookup(self, match: re.Match) -> str:
        parts = match.group(1).split(".")
        if parts[0] == "var" and len(parts) == 2:
            variable = self.data.get("variables", {}).get(parts[1])
            if variable is None or "default" not in variable:
                raise KeyError(f"The bundle has no variable {parts[1]} with a default.")
            return self.resolve(str(variable["default"]))
        if parts[0] == "resources" and len(parts) == 4 and parts[3] == "name":
            return self.resolve(self.resources(parts[1])[parts[2]]["name"])
        return match.group(0)


def load(root: Path = REPO) -> Bundle:
    """databricks.yml with the resources of every file its include patterns match."""
    import yaml

    data = yaml.safe_load((root / "databricks.yml").read_text())
    resources: dict = {}
    parts = [data] + [yaml.safe_load(path.read_text()) or {}
                      for pattern in data.get("include", []) for path in sorted(root.glob(pattern))]
    for part in parts:
        for kind, items in (part.get("resources") or {}).items():
            resources.setdefault(kind, {}).update(items or {})
    return Bundle(root, {**data, "resources": resources})
