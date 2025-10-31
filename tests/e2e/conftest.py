from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from .utils.process import ManagedProcess, start_backend, start_frontend


@pytest.fixture(scope="session")
def backend_server() -> ManagedProcess:
    process = start_backend(port=8100)
    yield process
    process.terminate()


@pytest.fixture(scope="session")
def frontend_server(backend_server: ManagedProcess) -> ManagedProcess:
    process = start_frontend(port=5173, backend_url="http://127.0.0.1:8100/api")
    yield process
    process.terminate()


@pytest.fixture(scope="session")
def prepare_environment(frontend_server: ManagedProcess) -> None:  # noqa: PT004
    """Ensure front/backend servers are running before tests start."""
    yield None


@pytest.fixture(scope="session")
def clean_output_root() -> None:
    output_root = Path("output")
    if output_root.exists():
        shutil.rmtree(output_root)
    yield None


@pytest.fixture(scope="session")
def cli_generation(clean_output_root) -> Path:  # type: ignore[override]
    cmd = [
        sys.executable,
        "-m",
        "backend.cli",
        "generate",
        "--config",
        "config/examples/invoice.yaml",
    ]
    subprocess.run(cmd, check=True)
    return Path("output") / "demo-user" / "invoice-verification-mvp"

