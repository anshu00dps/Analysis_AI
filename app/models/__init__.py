"""Beanie document models — each class maps to one MongoDB collection.

`ALL_MODELS` is the registry we hand to Beanie at startup so it knows which
collections to manage. Add new Document subclasses here when you create them.
"""

from app.models.agent_prompt import AgentPrompt
from app.models.agent_run import AgentRun
from app.models.analysis import Analysis
from app.models.analysis_file import AnalysisFile
from app.models.dictionaries import CuratedDictionaryEntry, VendorDictionaryEntry
from app.models.stage_chat import StageChatMessage
from app.models.stage_document import StageDocument

ALL_MODELS = [
    Analysis,
    AnalysisFile,
    StageDocument,
    StageChatMessage,
    AgentPrompt,
    AgentRun,
    CuratedDictionaryEntry,
    VendorDictionaryEntry,
]

__all__ = [
    "Analysis",
    "AnalysisFile",
    "StageDocument",
    "StageChatMessage",
    "AgentPrompt",
    "AgentRun",
    "CuratedDictionaryEntry",
    "VendorDictionaryEntry",
    "ALL_MODELS",
]
