from __future__ import annotations

import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import requests


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker がインストールされていません")
def test_generated_app_docker_compose(cli_generation: Path) -> None:
    zip_path = cli_generation / "app.zip"
    assert zip_path.exists()

    with TemporaryDirectory() as tmpdir:
        extract_dir = Path(tmpdir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        compose_file = extract_dir / "docker" / "docker-compose.yml"
        assert compose_file.exists()

        env = dict(**os.environ)
        env.setdefault("COMPOSE_PROJECT_NAME", f"demo-platform-{int(time.time())}")

        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "--build"],
            cwd=extract_dir,
            check=True,
            env=env,
        )

        try:
            _wait_for_http("http://127.0.0.1:8000/", timeout=120)
            response = requests.post(
                "http://127.0.0.1:8000/api/invoice/verify",
                json={
                    "invoiceNumber": "INV-DOCKER-001",
                    "vendorName": "Docker Corp",
                    "amount": 1200000,
                    "currency": "JPY",
                    "issueDate": "2024-04-01",
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            assert payload["invoice_number"] == "INV-DOCKER-001"
        finally:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down", "-v"],
                cwd=extract_dir,
                check=False,
                env=env,
            )


def _wait_for_http(url: str, timeout: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                return
        except requests.RequestException:
            time.sleep(2)
    raise RuntimeError(f"Timeout waiting for {url}")

