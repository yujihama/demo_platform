"""Render project artifacts from Jinja2 templates."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, StrictUndefined


class TemplateRenderer:
    def __init__(self, template_root: Path) -> None:
        if not template_root.exists():
            raise FileNotFoundError(f"Template root does not exist: {template_root}")
        self._template_root = template_root
        self._environment = Environment(
            loader=FileSystemLoader(str(template_root)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def render_to_directory(self, destination: Path, context: Dict[str, Any]) -> None:
        destination.mkdir(parents=True, exist_ok=True)

        for template_path in self._template_root.rglob("*"):
            if template_path.is_dir():
                continue

            relative_path = template_path.relative_to(self._template_root)
            target_path = destination / relative_path

            if template_path.suffix == ".j2":
                target_path = target_path.with_suffix("")
                template_name = relative_path.as_posix()  # Use forward slashes for Jinja2
                template = self._environment.get_template(template_name)
                rendered = template.render(**context)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(rendered, encoding="utf-8")
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(template_path, target_path)

