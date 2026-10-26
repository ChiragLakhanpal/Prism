"""The workspace scripts' inline dependency lists (ticket 74).

`uv run --script` installs only the packages a script's inline block (# /// script ... # ///) names. On October 26,
2026 `ops/bundle/check.py same-rows` stopped with "No module named 'splink'" on the second session's snapshot: with no
fixture database there, its local half builds the tables in memory and runs the nightly job's tasks, and the tasks
had gained the supplier matching (splink) and the time estimate (numpy, XGBoost) since the list was written. The
second session got the day's comparison only by naming the missing packages with `--with`.

So each script names its packages at the versions the gate tests (the pins below), and check.py names every package
its code imports. Nothing here resolves an environment: the tests read the scripts, pyproject.toml and uv.lock, and
look up which installed package each imported module comes from.
"""

import ast
import re
import sys
import tomllib
from functools import cache
from importlib import metadata
from pathlib import Path

import pytest
from packaging.requirements import Requirement

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = ("ops/bundle/check.py", "ops/agent/refuse_live.py", "ops/agent/ask_live.py")
CHECK = REPO / "ops" / "bundle" / "check.py"
# The folders check.py puts on sys.path, in the order Python then searches them.
CHECK_PATH = (REPO / "ops" / "bundle", REPO / "ops" / "dayone", REPO / "src")
# pyproject.toml installs XGBoost as xgboost-cpu on Linux and as xgboost elsewhere, so a script names both.
FORMS = ({"xgboost", "xgboost-cpu"},)


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def inline_requirements(path: Path) -> list[Requirement]:
    """The packages a script's inline block names, as uv reads them."""
    block = re.search(r"^# /// script\n(.*?)^# ///$", path.read_text(), re.S | re.M).group(1)
    lines = tomllib.loads("".join(line.removeprefix("#").removeprefix(" ") + "\n"
                                  for line in block.splitlines()))["dependencies"]
    return [Requirement(line) for line in lines]


@cache
def project_requirements() -> dict[str, Requirement]:
    """pyproject.toml's packages, the app's and the dev group's, by name."""
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text())
    lines = pyproject["project"]["dependencies"] + [line for group in pyproject["dependency-groups"].values()
                                                    for line in group]
    return {canonical(requirement.name): requirement for requirement in map(Requirement, lines)}


@cache
def locked_versions() -> dict[str, str]:
    """The version of each package uv.lock resolved for the project, which is what the gate's tests run on."""
    return {canonical(package["name"]): package["version"]
            for package in tomllib.loads((REPO / "uv.lock").read_text())["package"]}


def expected_pin(name: str) -> str:
    """The version a script pins: pyproject.toml's own pin, or, where pyproject.toml gives only a floor (numpy>=2.3),
    the version uv.lock resolved."""
    requirement = project_requirements().get(name)
    exact = [spec.version for spec in requirement.specifier if spec.operator == "=="] if requirement else []
    return exact[0] if exact else locked_versions()[name]


@pytest.mark.parametrize("script", SCRIPTS)
def test_a_script_pins_each_package_the_project_holds_at_the_project_s_version(script):
    """A package the project also installs is pinned at the version the gate tests, under pyproject.toml's platform
    condition. Packages only the script installs, such as databricks-sdk, have nothing to match."""
    requirements = inline_requirements(REPO / script)
    held = {canonical(requirement.name) for requirement in requirements}
    wrong = []
    for requirement in requirements:
        name = canonical(requirement.name)
        if name not in locked_versions():
            continue
        project = project_requirements().get(name)
        marker = str(project.marker) if project and project.marker else ""
        if str(requirement.specifier) != f"=={expected_pin(name)}" or str(requirement.marker or "") != marker:
            wrong.append(f"{requirement} should read {requirement.name}=={expected_pin(name)}"
                         + (f"; {marker}" if marker else ""))
    for forms in FORMS:
        if held & forms:
            wrong += [f"{name} is missing beside {', '.join(sorted(held & forms))}" for name in sorted(forms - held)]
    assert wrong == []


# ── check.py names every package its code imports ────────────────────────

class Imports(ast.NodeVisitor):
    """The modules one file imports, at module level and inside functions, and whether it loads modules by name.
    Imports under `if TYPE_CHECKING:` never run, so they are left out."""

    def __init__(self, package: str):
        self.package, self.names, self.by_name = package, [], False

    def visit_If(self, node):
        if isinstance(node.test, ast.Name | ast.Attribute) and ast.unparse(node.test).endswith("TYPE_CHECKING"):
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_Import(self, node):
        self.names += [alias.name for alias in node.names]

    def visit_ImportFrom(self, node):
        if node.level:
            parts = self.package.split(".")[:len(self.package.split(".")) - node.level + 1]
            base = ".".join(parts + ([node.module] if node.module else []))
        else:
            base = node.module
        self.names += [base, *(f"{base}.{alias.name}" for alias in node.names)]

    def visit_Call(self, node):
        if ast.unparse(node.func).split(".")[-1] == "import_module":
            self.by_name = True
        self.generic_visit(node)


def packages_imported(script: Path, path: tuple[Path, ...]) -> set[str]:
    """Every installed package whose modules the script's code imports, at any depth: the script, each module of
    Strata's it imports, and theirs in turn. Imports inside functions count, because they run on the path that needs
    them: splink inside the supplier matching, XGBoost inside the time estimate. A module that loads modules by name
    (the tool registry, the silver transforms, the draft writers) brings in every module of its own package. A
    package this environment lacks, which only a script or a job installs (databricks-sdk, MLflow), is left out."""

    def find(name: str) -> Path | None:
        for root in path:
            base = root.joinpath(*name.split("."))
            for file in (base.with_suffix(".py"), base / "__init__.py"):
                if file.is_file():
                    return file
        return None

    def module_name(file: Path) -> str:
        root = next(root for root in path if file.is_relative_to(root))
        parts = file.relative_to(root).with_suffix("").parts
        return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)

    outside, seen, waiting = set(), set(), [script]
    while waiting:
        file = waiting.pop()
        if file in seen:
            continue
        seen.add(file)
        name = "__main__" if file == script else module_name(file)
        imports = Imports(name if file.name == "__init__.py" else name.rpartition(".")[0])
        imports.visit(ast.parse(file.read_text(), str(file)))
        if imports.by_name:
            waiting += file.parent.rglob("*.py")
        for imported in imports.names:
            if find(imported.split(".")[0]) is None:
                if imported.split(".")[0] not in sys.stdlib_module_names:
                    outside.add(imported)
                continue
            parts = imported.split(".")
            waiting += [found for found in (find(".".join(parts[:end])) for end in range(1, len(parts) + 1)) if found]
    return set().union(*map(owner, outside))


@cache
def distributions() -> dict[str, list[str]]:
    """Each top-level module name of this environment, with the installed packages that provide it."""
    return metadata.packages_distributions()


@cache
def files_of(distribution: str) -> frozenset[str]:
    return frozenset(str(file) for file in metadata.files(distribution) or ())


def owner(module: str) -> set[str]:
    """The installed package a module comes from. Where several share its first name, as opentelemetry's api and sdk
    do, the one whose files hold it; an imported name that is not a module has no owner."""
    names = distributions().get(module.split(".")[0], [])
    if len(names) < 2:
        return {canonical(name) for name in names}
    stem = module.replace(".", "/")
    return {canonical(name) for name in names if {f"{stem}.py", f"{stem}/__init__.py"} & files_of(name)}


def installed_by(requirements: list[Requirement]) -> set[str]:
    """Every package `uv run --script` installs for these requirements: each one and what it requires in turn, read
    from the metadata of the versions this checkout's environment holds."""
    found, waiting = set(), list(requirements)
    while waiting:
        requirement = waiting.pop()
        if canonical(requirement.name) in found:
            continue
        found.add(canonical(requirement.name))
        try:
            needs = metadata.requires(requirement.name) or []
        except metadata.PackageNotFoundError:  # not in this environment: xgboost-cpu off Linux, databricks-sdk
            needs = []
        waiting += [need for need in map(Requirement, needs)
                    if need.marker is None or need.marker.evaluate({"extra": ""})]
    return found


def test_the_check_script_installs_every_package_its_code_imports():
    imported = packages_imported(CHECK, CHECK_PATH)

    # The walk reached the nightly job's tasks, which the in-memory build runs when the fixture database is missing.
    assert {"duckdb", "splink", "numpy", "py3langid"} <= imported
    assert sorted(imported - installed_by(inline_requirements(CHECK))) == []
