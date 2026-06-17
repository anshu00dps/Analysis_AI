"""Minimal logging setup.

A single place to configure how the app logs. We keep it simple for now (a console
handler with timestamps); later phases can route this to files or structured JSON.
"""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
