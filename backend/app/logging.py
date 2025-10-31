"""Centralised logging configuration for the platform."""

from __future__ import annotations

import sys
from typing import Optional

from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        colorize=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )


__all__ = ["configure_logging", "logger"]

