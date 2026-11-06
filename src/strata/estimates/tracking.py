"""Where backtests, models and model cards are kept: MLflow and Unity Catalog on the workspace, and an
offline stand-in in the gate.

Both trackers have the same methods, so the replay harness and the backtests never know which one
they have:

- start_run(name, params) opens a run and returns its id; log_metrics, log_text, log_model and end_run
  fill it.
- register(run_id, name, card, summary) registers the run's model under a three-part Unity Catalog
  name, with a description that points to its model card and gives summary, the track-record
  sentence the card was written with, and returns the new version; set_alias and alias_version move
  and read an alias such as champion.

OfflineTracker keeps everything in memory with run ids such as offline-run-0001, so a test can read
back what was logged. MlflowTracker is the live adapter: it imports MLflow only when it is made, logs
to the experiment config/models.toml names, and registers in Unity Catalog. No day-one test has run
MLflow or Unity Catalog models on Free Edition yet, so ops/estimates/backtest_live.py is a workspace
step (docs/workspace-catchup.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Callable

MODEL_CARD = "model_card.md"


@dataclass
class OfflineRun:
    name: str
    params: dict[str, Any]
    metrics: dict[str, float] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)
    model: Any = None
    ended: bool = False


@dataclass
class OfflineVersion:
    version: int
    run_id: str
    card: str
    summary: str
    what: str  # what the model is, in the words Unity Catalog's description uses


class OfflineTracker:
    """MLflow and Unity Catalog's stand-in for the offline gate: everything stays in this object."""

    name = "offline"

    def __init__(self):
        self.runs: dict[str, OfflineRun] = {}
        self.models: dict[str, list[OfflineVersion]] = {}
        self.aliases: dict[tuple[str, str], int] = {}

    def start_run(self, name: str, params: dict[str, Any]) -> str:
        run_id = f"offline-run-{len(self.runs) + 1:04d}"
        self.runs[run_id] = OfflineRun(name, dict(params))
        return run_id

    def log_metrics(self, run_id: str, metrics: dict[str, float]) -> None:
        self.runs[run_id].metrics.update({key: float(value) for key, value in metrics.items()})

    def log_text(self, run_id: str, text: str, path: str) -> None:
        self.runs[run_id].texts[path] = text

    def log_model(self, run_id: str, model) -> None:
        self.runs[run_id].model = model

    def end_run(self, run_id: str) -> None:
        self.runs[run_id].ended = True

    def register(self, run_id: str, name: str, card: str, summary: str, what: str) -> int:
        versions = self.models.setdefault(name, [])
        versions.append(OfflineVersion(len(versions) + 1, run_id, card, summary, what))
        return versions[-1].version

    def set_alias(self, name: str, alias: str, version: int) -> None:
        self.aliases[(name, alias)] = version

    def alias_version(self, name: str, alias: str) -> int | None:
        return self.aliases.get((name, alias))

    def model_text(self, name: str, alias: str, path: str) -> str | None:
        """A text the run of the version an alias holds logged, such as model_state.json, or None."""
        version = self.alias_version(name, alias)
        if version is None:
            return None
        return self.runs[self.models[name][version - 1].run_id].texts.get(path)


class MlflowTracker:
    """MLflow on the workspace: runs in an experiment, models registered in Unity Catalog.

    The Databricks host and sign-in come from the environment MLflow reads (DATABRICKS_HOST with
    DATABRICKS_TOKEN, or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET), which
    ops/estimates/backtest_live.py sets from the env file."""

    name = "mlflow"

    def __init__(self, experiment: str, mkdirs: Callable[[str], Any] | None = None):
        """experiment is the experiment's workspace path, such as /Shared/strata/time_estimate. MLflow makes
        the experiment but not its folder, and a fresh workspace has no /Shared/strata, so the folder is
        made first: with mkdirs(path), or with the Databricks SDK's workspace client when none is given."""
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri("databricks")
        mlflow.set_registry_uri("databricks-uc")
        self.mlflow, self.client = mlflow, MlflowClient()
        (mkdirs or self._sdk_mkdirs)(str(PurePosixPath(experiment).parent))
        self.experiment_id = mlflow.set_experiment(experiment).experiment_id
        self._models: dict[str, str] = {}  # run id -> the logged model's URI

    @staticmethod
    def _sdk_mkdirs(path: str) -> None:
        from databricks.sdk import WorkspaceClient

        WorkspaceClient().workspace.mkdirs(path)

    def start_run(self, name: str, params: dict[str, Any]) -> str:
        run = self.client.create_run(self.experiment_id, run_name=name)
        for key, value in params.items():
            self.client.log_param(run.info.run_id, key, str(value)[:6000])
        return run.info.run_id

    def log_metrics(self, run_id: str, metrics: dict[str, float]) -> None:
        for key, value in metrics.items():
            self.client.log_metric(run_id, key, float(value))

    def log_text(self, run_id: str, text: str, path: str) -> None:
        self.client.log_text(run_id, text, path)

    def log_model(self, run_id: str, model) -> None:
        """The XGBoost booster with its signature, which Unity Catalog requires, and the rest of the
        model (its calibration, vocabularies and training range) as model_state.json beside it. A rebidding
        model (ticket 28) is logged as a Python function model over its model_state.json, which its backtest
        logged first, since it may be a logistic regression with no booster."""
        from mlflow.models import infer_signature

        if hasattr(model, "pyfunc_inputs"):
            example = model.pyfunc_inputs()
            with self.mlflow.start_run(run_id=run_id):
                info = self.mlflow.pyfunc.log_model(name="model", python_model=_rebidding_pyfunc(model.state_json()),
                                                    signature=infer_signature(example, model.chances(example.to_dict("records"))),
                                                    input_example=example)
            self._models[run_id] = info.model_uri
            return
        example = model.example_inputs()
        signature = infer_signature(example, model.learner.predict(example))
        with self.mlflow.start_run(run_id=run_id):
            info = self.mlflow.xgboost.log_model(model.learner.booster, name="model", signature=signature,
                                                 input_example=example)
        self.client.log_text(run_id, model.state_json(), "model_state.json")
        self._models[run_id] = info.model_uri

    def end_run(self, run_id: str) -> None:
        self.client.set_terminated(run_id)

    def register(self, run_id: str, name: str, card: str, summary: str, what: str) -> int:
        """The run's model as a new version. The card itself is the run's model_card.md, which the
        backtest logged; Unity Catalog's descriptions say what the model is (what, the caller's words), point
        to the card, whatever its length, and give the track-record sentence."""
        version = self.mlflow.register_model(self._models[run_id], name)
        pointer = f"Prism's {what}. The model card is {MODEL_CARD} in MLflow run {run_id}. {summary}"
        self.client.update_registered_model(name, description=pointer)
        self.client.update_model_version(name, version.version, description=pointer)
        return int(version.version)

    def set_alias(self, name: str, alias: str, version: int) -> None:
        self.client.set_registered_model_alias(name, alias, str(version))

    def alias_version(self, name: str, alias: str) -> int | None:
        from mlflow.exceptions import MlflowException

        try:
            return int(self.client.get_model_version_by_alias(name, alias).version)
        except MlflowException:  # no such model, or no version holds the alias
            return None

    def model_text(self, name: str, alias: str, path: str) -> str | None:
        """A text the run of the version an alias holds logged, such as model_state.json, or None."""
        from mlflow.exceptions import MlflowException

        try:
            run_id = self.client.get_model_version_by_alias(name, alias).run_id
            return self.mlflow.artifacts.load_text(f"runs:/{run_id}/{path}")
        except MlflowException:
            return None


def _rebidding_pyfunc(state: str):
    """A Python function model that gives a rebidding model's chances from its model_state.json (ticket 28)."""
    import mlflow.pyfunc

    class RebiddingChance(mlflow.pyfunc.PythonModel):
        def __init__(self, text: str):
            self.text = text

        def predict(self, context, model_input, params=None):
            from strata.estimates.rebidding_model import RebiddingModel

            return RebiddingModel.from_state(self.text).chances(model_input.to_dict("records"))

    return RebiddingChance(state)
