"""Keep test databases in a fresh project-local directory on every run."""
import uuid
from pathlib import Path


def pytest_configure(config):
    if config.option.basetemp is None:
        root = Path(__file__).resolve().parents[1] / ".pytest_runs"
        root.mkdir(exist_ok=True)
        config.option.basetemp = str(root / uuid.uuid4().hex)
