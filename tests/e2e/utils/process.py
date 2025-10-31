"""Helpers for managing background processes in tests."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

import requests


class ManagedProcess:
    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self._proc = proc

    def terminate(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()


def start_backend(port: int = 8100) -> ManagedProcess:
    env = _base_env()
    env["PYTHONPATH"] = str(Path("backend").resolve())
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(cmd, cwd="backend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _wait_for_http(f"http://127.0.0.1:{port}/", timeout=30)
    return ManagedProcess(proc)


def start_frontend(port: int = 5173, backend_url: str = "http://127.0.0.1:8100/api") -> ManagedProcess:
    env = _base_env()
    env["VITE_BACKEND_URL"] = backend_url
    env["BACKEND_HOST"] = backend_url.rsplit("/api", 1)[0]
    cmd = ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)]
    proc = subprocess.Popen(cmd, cwd="frontend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _wait_for_http(f"http://127.0.0.1:{port}/", timeout=45)
    return ManagedProcess(proc)


def _base_env() -> Mapping[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("APP_ENV", "test")
    return env


def _wait_for_http(url: str, timeout: int = 30) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code < 500:
                return
        except requests.RequestException:
            time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {url}")

