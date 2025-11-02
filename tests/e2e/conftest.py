from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


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
    subprocess.run(cmd, check=True)
    return Path("output") / "cli-llm-user" / "invoice-validation-llm"


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
    subprocess.run(cmd, check=True)
    return Path("output") / "cli-llm-validation" / "invoice-validation-llm-job"

