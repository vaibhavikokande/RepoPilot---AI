"""AI Debugging Assistant package for RepoPilot-AI."""

from app.debug_assistant.assistant import DebugAssistant
from app.debug_assistant.context_locator import ContextLocator
from app.debug_assistant.error_parser import parse_error
from app.debug_assistant.models import (
    DebugError,
    DebugExecutionError,
    DebugRequest,
    DebugResponse,
    DebugSourceNotFoundError,
    DebugValidationError,
    ParsedError,
    PossibleCause,
    RetrievedContext,
    SourceEvidence,
    StackFrame,
)
from app.debug_assistant.prompt_builder import DebugPromptBuilder
from app.debug_assistant.validator import DebugValidator

__all__ = [
    "ContextLocator",
    "DebugAssistant",
    "DebugError",
    "DebugExecutionError",
    "DebugPromptBuilder",
    "DebugRequest",
    "DebugResponse",
    "DebugSourceNotFoundError",
    "DebugValidationError",
    "DebugValidator",
    "ParsedError",
    "PossibleCause",
    "RetrievedContext",
    "SourceEvidence",
    "StackFrame",
    "parse_error",
]
