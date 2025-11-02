from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page

from .utils.process import ManagedProcess, start_backend, start_frontend

# Get the workspace root directory
WORKSPACE_ROOT = Path(__file__).parent.parent.parent


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
    output_root = WORKSPACE_ROOT / "output"
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
    env = dict(os.environ)
    env["PYTHONPATH"] = str(WORKSPACE_ROOT)
    subprocess.run(cmd, check=True, cwd=WORKSPACE_ROOT, env=env)
    return WORKSPACE_ROOT / "output" / "demo-user" / "invoice-verification-mvp"


@pytest.fixture(scope="session")
def cli_generation_llm(clean_output_root) -> Path:  # type: ignore[override]
    cmd = [
        sys.executable,
        "-m",
        "backend.cli",
        "generate",
        "--config",
        "config/examples/invoice_llm.yaml",
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(WORKSPACE_ROOT)
    subprocess.run(cmd, check=True, cwd=WORKSPACE_ROOT, env=env)
    return WORKSPACE_ROOT / "output" / "cli-llm-user" / "invoice-validation-llm"


@pytest.fixture(scope="session")
def cli_generation_validation_llm(clean_output_root) -> Path:  # type: ignore[override]
    cmd = [
        sys.executable,
        "-m",
        "backend.cli",
        "generate",
        "--config",
        "config/examples/invoice_validation_llm.yaml",
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(WORKSPACE_ROOT)
    subprocess.run(cmd, check=True, cwd=WORKSPACE_ROOT, env=env)
    return WORKSPACE_ROOT / "output" / "cli-llm-validation" / "invoice-validation-llm-job"


# Additional fixtures for Task B smoke tests
@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("BASE_URL", "http://localhost:5173")


@pytest.fixture
def page_with_base_url(page: Page, base_url: str):
    """Page fixture that navigates to base_url for smoke tests."""
    page.goto(base_url)
    return page
