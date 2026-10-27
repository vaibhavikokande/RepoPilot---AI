"""AI Documentation Generator package for RepoPilot-AI."""

from app.doc_generator.context_collector import ContextCollector
from app.doc_generator.generator import DocGenerator
from app.doc_generator.models import (
    CollectedDocContext,
    DiscoveredRoute,
    DiscoveredSymbol,
    DocAudience,
    DocDetailLevel,
    DocExecutionError,
    DocGenerateRequest,
    DocGenerateResponse,
    DocGeneratorError,
    DocMetadata,
    DocSection,
    DocTargetNotFoundError,
    DocType,
    DocValidationError,
)
from app.doc_generator.prompt_builder import DocPromptBuilder
from app.doc_generator.store import DocumentStore, document_store
from app.doc_generator.validator import DocValidator

__all__ = [
    "CollectedDocContext",
    "ContextCollector",
    "DiscoveredRoute",
    "DiscoveredSymbol",
    "DocAudience",
    "DocDetailLevel",
    "DocExecutionError",
    "DocGenerateRequest",
    "DocGenerateResponse",
    "DocGenerator",
    "DocGeneratorError",
    "DocMetadata",
    "DocPromptBuilder",
    "DocSection",
    "DocTargetNotFoundError",
    "DocType",
    "DocValidationError",
    "DocValidator",
    "DocumentStore",
    "document_store",
]
