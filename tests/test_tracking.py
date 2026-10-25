"""The live MLflow tracker (src/strata/estimates/tracking.py), with MLflow stood in for: the gate's machine
has no workspace."""

from __future__ import annotations

import sys
import types


def test_the_tracker_makes_the_experiment_s_folder_before_mlflow_makes_the_experiment(monkeypatch):
    """On October 25, 2026 the first live backtest stopped with "NOT_FOUND: Parent directory does not exist:
    /Shared/strata": MLflow makes the experiment but not its folder, and a fresh workspace has no
    /Shared/strata."""
    from strata.estimates.tracking import MlflowTracker

    calls = []
    fake = types.ModuleType("mlflow")
    fake.set_tracking_uri = lambda uri: calls.append(("tracking", uri))
    fake.set_registry_uri = lambda uri: calls.append(("registry", uri))
    fake.set_experiment = lambda name: (calls.append(("experiment", name)), types.SimpleNamespace(experiment_id="7"))[1]
    tracking = types.ModuleType("mlflow.tracking")
    tracking.MlflowClient = lambda: object()
    fake.tracking = tracking
    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.tracking", tracking)

    tracker = MlflowTracker("/Shared/strata/time_estimate", mkdirs=lambda path: calls.append(("mkdirs", path)))

    assert tracker.experiment_id == "7"
    assert calls == [("tracking", "databricks"), ("registry", "databricks-uc"), ("mkdirs", "/Shared/strata"),
                     ("experiment", "/Shared/strata/time_estimate")]
