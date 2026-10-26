#!/usr/bin/env python3
"""
Structured CLI Logger for `scripts/*.py` (`T20` / `T201` print defense compliant).
Routes standard CLI output and error messages through Python's `logging` module.
"""

from __future__ import annotations

import logging
import sys


def _build_stream_logger(name: str, stream: object, level: int) -> logging.Logger:
    """Create a clean, unprefixed stream logger for CLI table and status output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream)  # type: ignore[arg-type]
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


_STDOUT_LOGGER = _build_stream_logger("porter.cli.stdout", sys.stdout, logging.INFO)
_STDERR_LOGGER = _build_stream_logger("porter.cli.stderr", sys.stderr, logging.ERROR)


def cli_out(message: str = "") -> None:
    """Emit a formatted CLI message to stdout via logging."""
    _STDOUT_LOGGER.info(message)


def cli_err(message: str) -> None:
    """Emit a formatted CLI error message to stderr via logging."""
    _STDERR_LOGGER.error(message)
