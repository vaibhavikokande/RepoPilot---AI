"""AI Debugging Assistant orchestrator coordinating error parsing, context retrieval, and LLM analysis."""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.debug_assistant.context_locator import ContextLocator
from app.debug_assistant.error_parser import parse_error
from app.debug_assistant.models import (
    DebugExecutionError,
    DebugRequest,
    DebugResponse,
    DebugValidationError,
    ParsedError,
    PossibleCause,
    RetrievedContext,
    SourceEvidence,
)
from app.debug_assistant.prompt_builder import DebugPromptBuilder
from app.debug_assistant.validator import DebugValidator
from app.rag.generator import BaseLLMGenerator, MockLLMGenerator, get_llm_generator
from app.schemas.repository import RepositoryInfo

logger = logging.getLogger(__name__)


class DebugAssistant:
    """Orchestrates AI-driven error analysis, source context retrieval, and evidence-grounded debugging."""

    def __init__(
        self,
        llm_generator: Optional[BaseLLMGenerator] = None,
        context_locator: Optional[ContextLocator] = None,
        prompt_builder: Optional[DebugPromptBuilder] = None,
        validator: Optional[DebugValidator] = None,
    ):
        self.llm_generator = llm_generator or get_llm_generator()
        self.context_locator = context_locator or ContextLocator()
        self.prompt_builder = prompt_builder or DebugPromptBuilder()
        self.validator = validator or DebugValidator()

    async def diagnose_error(
        self,
        repo_path: Path,
        repo_info: RepositoryInfo,
        request: DebugRequest,
    ) -> DebugResponse:
        """Execute end-to-end debugging analysis on the submitted error or stack trace.

        Args:
            repo_path: Cloned repository workspace root.
            repo_info: Repository metadata.
            request: DebugRequest containing error message and optional context.

        Returns:
            DebugResponse with structured root cause, evidence, and recommendations.
        """
        debug_id = f"dbg_{uuid.uuid4().hex[:12]}"
        warnings: List[str] = []

        # 1. Validate payload length
        if len(request.error_message) > 15_000:
            raise DebugValidationError("Error message exceeds maximum allowed limit of 15,000 characters.")

        # 2. Step A: Parse error or stack trace
        parsed_error = parse_error(
            error_text=request.error_message,
            language_hint=request.language,
        )

        # 3. Step B & C: Locate relevant source code context
        context = self.context_locator.locate_context(
            repo_path=repo_path,
            parsed_error=parsed_error,
            user_file_path=request.file_path,
        )

        if context.missing_files:
            warnings.append(
                f"Referenced files could not be located in repository workspace: {', '.join(context.missing_files[:5])}"
            )

        # 4. Step D: Synthesize diagnosis via LLM or deterministic fallback
        is_mock = isinstance(self.llm_generator, MockLLMGenerator)
        llm_result: Optional[Dict[str, Any]] = None

        if not is_mock:
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(
                request=request,
                parsed_error=parsed_error,
                context=context,
            )

            try:
                raw_response = await self.llm_generator.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=2048,
                )
                llm_result = self._extract_json_response(raw_response)
            except Exception as exc:
                logger.warning("LLM generation or parsing failed for debug analysis: %s. Falling back to deterministic engine.", exc)
                warnings.append(f"AI synthesis encountered an issue ({type(exc).__name__}); generated deterministic diagnosis fallback.")

        # If LLM is mock or failed, execute deterministic diagnosis fallback
        if llm_result is None:
            llm_result = self._generate_deterministic_diagnosis(
                request=request,
                parsed_error=parsed_error,
                context=context,
            )

        # 5. Extract and validate fields
        error_type = (
            llm_result.get("error_type")
            or parsed_error.error_type
            or "ApplicationError"
        )
        error_summary = self.validator.redact_secrets(
            llm_result.get("error_summary") or f"Execution failure with message: {parsed_error.error_message}"
        )
        root_cause = self.validator.redact_secrets(
            llm_result.get("root_cause") or "The error occurred during execution based on the provided stack trace."
        )

        raw_confidence = llm_result.get("confidence", "medium")
        confidence = self.validator.validate_confidence(raw_confidence, context)

        # Build possible causes
        raw_causes = llm_result.get("possible_causes", [])
        parsed_causes: List[PossibleCause] = []
        for i, c in enumerate(raw_causes, start=1):
            if isinstance(c, dict):
                parsed_causes.append(
                    PossibleCause(
                        rank=c.get("rank", i),
                        title=c.get("title", f"Hypothesis {i}"),
                        explanation=c.get("explanation", ""),
                        confidence=c.get("confidence", "medium"),
                        supporting_evidence=c.get("supporting_evidence", []),
                    )
                )
        possible_causes = self.validator.sanitize_causes(parsed_causes)

        # Recommended steps
        raw_steps = llm_result.get("recommended_steps", [])
        recommended_steps = [
            self.validator.redact_secrets(str(s)) for s in raw_steps if s
        ]
        if not recommended_steps:
            recommended_steps = [
                "1. Verify input parameters and argument values passed to the failing function.",
                "2. Reproduce the failure locally in a safe testing environment with isolated unit tests.",
                "3. Check for unhandled edge cases (e.g. None/null values, zero denominators, or missing keys).",
            ]

        # Suggested fix
        raw_fix = llm_result.get("suggested_fix")
        suggested_fix = (
            self.validator.redact_secrets(raw_fix)
            if raw_fix and isinstance(raw_fix, str) and raw_fix.strip()
            else None
        )

        # Missing information and limitations
        missing_info = [
            self.validator.redact_secrets(str(m))
            for m in llm_result.get("missing_information", [])
            if m
        ]
        if context.missing_files and not any("missing files" in m.lower() for m in missing_info):
            missing_info.append(
                f"Source files outside repository workspace: {', '.join(context.missing_files[:3])}"
            )

        limitations = [
            self.validator.redact_secrets(str(l))
            for l in llm_result.get("limitations", [])
            if l
        ]
        if not any("static analysis" in l.lower() for l in limitations):
            limitations.append(
                "This diagnosis was performed via static analysis of repository files; runtime memory and live variable state were not observed."
            )

        # Related files
        suggested_related = llm_result.get("related_files", [])
        related_files = self.validator.filter_related_files(suggested_related, context)

        return DebugResponse(
            debug_id=debug_id,
            repository=repo_info,
            error_type=error_type,
            error_summary=error_summary,
            root_cause=root_cause,
            confidence=confidence,
            confidence_note="Confidence represents the assistant's assessment based on static analysis of available code and stack trace evidence, not a guarantee.",
            evidence=context.evidence_items,
            related_files=related_files,
            possible_causes=possible_causes,
            recommended_steps=recommended_steps,
            suggested_fix=suggested_fix,
            missing_information=missing_info,
            limitations=limitations,
            parsed_error=parsed_error,
            status="completed",
            warnings=warnings,
        )

    def _extract_json_response(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON object from LLM output, handling markdown blocks."""
        cleaned = text.strip()

        # Handle ```json ... ``` blocks
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        # Handle direct JSON substring
        if not (cleaned.startswith("{") and cleaned.endswith("}")):
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        return json.loads(cleaned)

    def _generate_deterministic_diagnosis(
        self,
        request: DebugRequest,
        parsed_error: ParsedError,
        context: RetrievedContext,
    ) -> Dict[str, Any]:
        """Generate high-quality, evidence-grounded diagnosis without external API calls."""
        err_type = parsed_error.error_type or "RuntimeError"
        err_msg = parsed_error.error_message or "An unhandled exception occurred."

        # Analyze frames to find the innermost application failure point
        innermost_frame = None
        for frame in reversed(parsed_error.frames):
            if frame.is_application_code and frame.file_path:
                innermost_frame = frame
                break
        if not innermost_frame and parsed_error.frames:
            innermost_frame = parsed_error.frames[-1]

        # Construct specific diagnosis based on error type and evidence
        evidence_file = innermost_frame.file_path if innermost_frame else "unknown"
        evidence_line = innermost_frame.line_number if innermost_frame else None
        evidence_func = innermost_frame.function_name if innermost_frame else None

        line_str = f"at line {evidence_line}" if evidence_line else ""
        func_str = f"in function '{evidence_func}'" if evidence_func else ""
        loc_str = f"{evidence_file} {line_str} {func_str}".strip()

        error_summary = (
            f"A {err_type} was raised during execution: {err_msg}"
        )

        root_cause = (
            f"The failure appears to originate at {loc_str}. "
            f"The application encountered an unexpected runtime condition where {err_msg}."
        )

        confidence = "high" if context.has_exact_source else "medium"

        possible_causes = [
            {
                "rank": 1,
                "title": f"Unhandled {err_type} condition",
                "explanation": (
                    f"Execution reached {loc_str} where an operation failed because the expected prerequisites were not met. "
                    f"Error detail: {err_msg}."
                ),
                "confidence": confidence,
                "supporting_evidence": [loc_str] if loc_str else [],
            },
            {
                "rank": 2,
                "title": "Unexpected input or edge-case parameters",
                "explanation": (
                    "Caller passed unexpected arguments (such as None, an invalid type, an empty collection, or a zero value) "
                    "that were not validated prior to processing."
                ),
                "confidence": "medium",
                "supporting_evidence": ["Caller input parameters"],
            },
        ]

        recommended_steps = [
            f"1. Inspect {evidence_file} around line {evidence_line or 1} to verify variable values at runtime.",
            "2. Add input validation or defensive boundary checks before executing the operation.",
            f"3. Add a unit test specifically reproducing the condition that produces '{err_msg}'.",
            "4. Consider wrapping the critical block with specific exception handling if recovery is possible.",
        ]

        suggested_fix = None
        if "zerodivision" in err_type.lower():
            suggested_fix = (
                "# Defensive check before division:\n"
                "if divisor == 0:\n"
                "    raise ValueError('Divisor cannot be zero.')\n"
                "result = dividend / divisor"
            )
        elif "keyerror" in err_type.lower():
            suggested_fix = (
                "# Safe dictionary access:\n"
                "value = data.get(key, default_value)\n"
                "# Or explicit membership check:\n"
                "if key in data:\n"
                "    value = data[key]"
            )
        elif "typeerror" in err_type.lower() and "none" in err_msg.lower():
            suggested_fix = (
                "# Null / None check before operation:\n"
                "if item is None:\n"
                "    return default_value\n"
                "result = item.operation()"
            )

        missing_info = [
            "Runtime variable values at the moment the exception occurred",
            "Full application logs prior to the failure",
        ]

        limitations = [
            "Diagnosis is based on static inspection of repository source files and the submitted stack trace.",
            "Runtime environmental configuration, database state, and live inputs were not directly observed.",
        ]

        return {
            "error_type": err_type,
            "error_summary": error_summary,
            "root_cause": root_cause,
            "confidence": confidence,
            "possible_causes": possible_causes,
            "recommended_steps": recommended_steps,
            "suggested_fix": suggested_fix,
            "missing_information": missing_info,
            "limitations": limitations,
            "related_files": context.related_files,
        }
