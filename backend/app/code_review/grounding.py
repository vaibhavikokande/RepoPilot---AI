"""Grounding validator and secret redaction for code review findings."""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.code_review.models import CodeReviewFinding, EvidenceContext

logger = logging.getLogger(__name__)

VALID_CATEGORIES: Set[str] = {
    "correctness",
    "security",
    "performance",
    "maintainability",
    "readability",
    "testing",
}

VALID_SEVERITIES: Set[str] = {
    "critical",
    "high",
    "medium",
    "low",
    "info",
}

VALID_CONFIDENCES: Set[str] = {
    "high",
    "medium",
    "low",
}


class GroundingValidator:
    """Verifies that review findings correspond to real source lines and code evidence."""

    @staticmethod
    def redact_secrets(text: Optional[str]) -> str:
        """Sanitize sensitive credentials, API keys, and private tokens from text."""
        if not text:
            return ""

        sanitized = text
        # Redact common API key and token formats
        sanitized = re.sub(r"sk-[a-zA-Z0-9_\-]{20,}", "[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"ghp_[a-zA-Z0-9_\-]{20,}", "[REDACTED_GITHUB_TOKEN]", sanitized)
        sanitized = re.sub(r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]", sanitized)
        sanitized = re.sub(
            r"(password|secret|token|api_key|access_token)\s*=\s*['\"][^'\"]{8,}['\"]",
            r"\1 = '[REDACTED_SECRET]'",
            sanitized,
            flags=re.IGNORECASE,
        )
        return sanitized

    @staticmethod
    def ground_findings(
        raw_findings: List[Dict[str, Any]],
        context: EvidenceContext,
    ) -> List[CodeReviewFinding]:
        """Validate, verify, and ground raw LLM findings against source code evidence.

        Args:
            raw_findings: Parsed JSON finding dictionaries from LLM output.
            context: EvidenceContext containing actual file lines and content.

        Returns:
            List of validated, grounded CodeReviewFinding objects.
        """
        grounded: List[CodeReviewFinding] = []
        counter = 1
        lines = context.content.splitlines()

        for raw in raw_findings:
            if not isinstance(raw, dict):
                continue

            title = str(raw.get("title", "")).strip()
            problem = str(raw.get("problem", "")).strip()
            if not title or not problem:
                continue

            # Category validation
            cat_raw = str(raw.get("category", "")).lower().strip()
            category = cat_raw if cat_raw in VALID_CATEGORIES else "maintainability"

            # Severity validation
            sev_raw = str(raw.get("severity", "")).lower().strip()
            severity = sev_raw if sev_raw in VALID_SEVERITIES else "medium"

            # Confidence validation
            conf_raw = str(raw.get("confidence", "")).lower().strip()
            confidence = conf_raw if conf_raw in VALID_CONFIDENCES else "medium"

            # Line range extraction & grounding
            try:
                start_l = int(raw.get("start_line", context.start_line))
                end_l = int(raw.get("end_line", start_l))
            except (ValueError, TypeError):
                start_l = context.start_line
                end_l = context.end_line

            # Evidence handling
            evidence = str(raw.get("evidence", "")).strip()

            # Verify line numbers against actual file boundaries
            is_verified = True
            if start_l < 1 or end_l > context.total_lines or start_l > end_l:
                # Attempt to locate evidence snippet in the source to correct line numbers
                corrected = GroundingValidator._locate_snippet_in_content(evidence, lines, context.start_line)
                if corrected:
                    start_l, end_l = corrected
                else:
                    # Clamp safely to context bounds
                    start_l = max(1, min(start_l, context.total_lines))
                    end_l = max(start_l, min(end_l, context.total_lines))
                    is_verified = False

            # If evidence is empty, try to extract line from source
            if not evidence and 1 <= start_l <= len(lines):
                evidence = lines[start_l - 1].strip()

            # Recommendation & Suggested Change
            recommendation = str(raw.get("recommendation", "")).strip()
            if not recommendation:
                recommendation = "Review and refactor the flagged code according to best practices."

            suggested_change = raw.get("suggested_change")
            if suggested_change is not None:
                suggested_change = GroundingValidator.redact_secrets(str(suggested_change).strip())

            # Apply secret redaction across all text fields
            redacted_title = GroundingValidator.redact_secrets(title)
            redacted_problem = GroundingValidator.redact_secrets(problem)
            redacted_evidence = GroundingValidator.redact_secrets(evidence)
            redacted_rec = GroundingValidator.redact_secrets(recommendation)

            grounded.append(
                CodeReviewFinding(
                    finding_id=f"cr_ai_{counter}",
                    title=redacted_title,
                    category=category,
                    severity=severity,
                    confidence=confidence,
                    file_path=context.file_path,
                    start_line=start_l,
                    end_line=end_l,
                    entity_name=context.entity_name,
                    problem=redacted_problem,
                    evidence=redacted_evidence,
                    recommendation=redacted_rec,
                    suggested_change=suggested_change if suggested_change else None,
                    source="ai_review",
                    is_verified=is_verified,
                )
            )
            counter += 1

        return grounded

    @staticmethod
    def _locate_snippet_in_content(
        snippet: str,
        lines: List[str],
        offset_line: int = 1,
    ) -> Optional[Tuple[int, int]]:
        """Attempt to find a multi-line or single-line code snippet within source lines."""
        if not snippet or len(snippet.strip()) < 4:
            return None

        clean_snippet = snippet.strip()
        snippet_first_line = clean_snippet.splitlines()[0].strip()

        for idx, line in enumerate(lines, offset_line):
            if snippet_first_line in line:
                snippet_line_count = len(clean_snippet.splitlines())
                return (idx, idx + snippet_line_count - 1)

        return None
