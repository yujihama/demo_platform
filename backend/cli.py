"""Command line interface for running the mock generation pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

import click
import yaml
from rich.console import Console
from rich.table import Table

from .app.config import config_manager
from .app.models import GenerationRequest, GenerationOptions
from .app.services.pipeline import pipeline
from .app.services.workflow_pipeline import workflow_pipeline

console = Console()


def _load_config(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _build_request(data: Dict[str, object]) -> GenerationRequest:
    def require(path: str) -> object:
        cursor: object = data
        for part in path.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                raise click.BadParameter(f"設定ファイルに {path} が存在しません")
            cursor = cursor[part]
        return cursor

    user_id = str(require("user.id"))
    project_id = str(require("project.id"))
    project_name = str(require("project.name"))
    description = str(require("project.description"))

    mock = data.get("mock", {})
    options = data.get("options", {})
    llm_config = data.get("llm", {})

    features = config_manager.features
    requirements_prompt = str(llm_config.get("requirements_prompt") or description)

    raw_use_mock = llm_config.get("use_mock")
    if raw_use_mock is None:
        use_mock = features.agents.use_mock
    elif isinstance(raw_use_mock, str):
        use_mock = raw_use_mock.strip().lower() in {"1", "true", "yes", "on"}
    else:
        use_mock = bool(raw_use_mock)

    return GenerationRequest(
        user_id=user_id,
        project_id=project_id,
        project_name=project_name,
        description=description,
        mock_spec_id=str(mock.get("spec_id", "invoice-verification")),
        options=GenerationOptions(
            include_playwright=bool(options.get("include_playwright", True)),
            include_docker=bool(options.get("include_docker", True)),
            include_logging=bool(options.get("include_logging", True)),
        ),
        requirements_prompt=requirements_prompt,
        use_mock=use_mock,
    )


class ProgressPrinter:
    def __init__(self) -> None:
        self._seen: set[Tuple[str, str]] = set()

    def __call__(self, job) -> None:  # type: ignore[override]
        for step in job.steps:
            key = (step.id, step.status)
            if key in self._seen:
                continue
            self._seen.add(key)
            console.log(f"[{translate_step_status(step.status)}] {step.label} - {step.message or ''}")


@click.group()
def cli() -> None:
    """Demo Platform CLI"""


@cli.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=Path("config/examples/invoice.yaml"),
    show_default=True,
    help="Generation configuration file",
)
def generate(config_path: Path) -> None:
    """Run the generation pipeline (mock or LLM) from the CLI."""

    console.rule("CLI Generation")
    console.log(f"設定ファイルを読み込み中: {config_path}")

    config_data = _load_config(config_path)
    request = _build_request(config_data)
    effective_use_mock = request.use_mock if request.use_mock is not None else config_manager.features.agents.use_mock
    mode_label = "モックパイプライン" if effective_use_mock else "LLMパイプライン"
    console.log(f"実行モード: {mode_label}")

    progress = ProgressPrinter()

    try:
        if effective_use_mock:
            job = pipeline.run_sync(request, progress_callback=progress)
        else:
            job = workflow_pipeline.run_sync(request, progress_callback=progress)
    except Exception as exc:  # pragma: no cover - surfaced to user
        console.print(f"[bold red]生成に失敗しました:[/bold red] {exc}")
        raise SystemExit(1) from exc

    console.rule("生成完了")
    console.print(f"ジョブ ID: [bold]{job.job_id}[/bold]")
    console.print(f"成果物 URL: {job.download_url}")
    if job.output_path:
        console.print(f"ZIP 出力先: {job.output_path}")

    metadata_path = Path(job.output_path).with_name("metadata.json") if job.output_path else None
    if metadata_path and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        table = Table(title="メタデータ概要", show_header=True, header_style="bold")
        table.add_column("キー")
        table.add_column("値")
        table.add_row("generated_at", metadata.get("generated_at", ""))
        table.add_row("project", metadata.get("request", {}).get("project_name", ""))
        table.add_row("user", metadata.get("request", {}).get("user_id", ""))
        console.print(table)

    console.print("[green]CLI 生成が完了しました。[/green]")


def translate_step_status(status: str) -> str:
    return {
        "pending": "待機",
        "running": "進行中",
        "completed": "完了",
        "failed": "失敗",
    }.get(status, status)


if __name__ == "__main__":
    cli()

