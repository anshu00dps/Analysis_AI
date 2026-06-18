"""Shared enumerations.

Subclassing `str, Enum` makes these JSON-serializable and comparable to plain strings,
so they work transparently in MongoDB documents and FastAPI responses.
"""

from enum import Enum


class Stage(str, Enum):
    BRD = "brd"
    PROMPT = "prompt"
    PLANNING = "planning"
    NOTEBOOK = "notebook"


# Order used to advance brd -> prompt -> planning -> notebook -> (completed).
STAGE_ORDER: list[Stage] = [Stage.BRD, Stage.PROMPT, Stage.PLANNING, Stage.NOTEBOOK]


class AnalysisStatus(str, Enum):
    CREATED = "created"
    SANITIZATION = "sanitization"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(str, Enum):
    CURATED = "curated"
    VENDOR = "vendor"


class DocumentAuthor(str, Enum):
    AGENT = "agent"
    MANUAL_EDIT = "manual_edit"


class ChatRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
