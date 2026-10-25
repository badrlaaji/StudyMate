"""LLM call tracing with MLflow (optional): latency, tokens and 429 errors per request.

On only when MLFLOW_TRACKING_URI is set, e.g. a local MLflow server:
  uv run mlflow server --backend-store-uri sqlite:///data/mlflow.db
      --artifacts-destination data/mlflow-artifacts --port 5000
Off (default, tests, CI): every span is a no-op and MLflow is never imported.
"""

import os
from contextlib import nullcontext

from config import load_env

EXPERIMENT = "studymate-llm"
# MLflow sends usage statistics and prints hints by default: keep everything local.
QUIET = {"MLFLOW_DISABLE_TELEMETRY": "true", "DO_NOT_TRACK": "true"}
QUIET |= {"MLFLOW_DISABLE_AGENT_HINT": "1"}


def enabled() -> bool:
    """True when a tracking server is configured."""
    load_env()
    return bool(os.environ.get("MLFLOW_TRACKING_URI"))


def load_mlflow():
    """Import MLflow with its telemetry and hints switched off."""
    for key, value in QUIET.items():
        os.environ.setdefault(key, value)
    import mlflow

    return mlflow


def setup() -> bool:
    """Point MLflow at the tracking server and the experiment; False when off."""
    if not enabled():
        return False
    mlflow = load_mlflow()
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(EXPERIMENT)
    return True


def span(name: str, span_type: str, attributes: dict | None = None):
    """A traced block (MLflow span), or a no-op block when tracing is off."""
    if not enabled():
        return nullcontext(None)
    mlflow = load_mlflow()
    return mlflow.start_span(name=name, span_type=span_type, attributes=attributes)


def set_attributes(current, values: dict) -> None:
    """Add attributes to a span; nothing when tracing is off."""
    if current is not None:
        current.set_attributes(values)
