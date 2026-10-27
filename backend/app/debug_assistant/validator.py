"""Grounding validator, line range validation, and secret redaction for debugging."""

import logging
import re
from typing import List, Optional, Set

from app.debug_assistant.models import (
    PossibleCause,
    RetrievedContext,
    SourceEvidence,
)

logger = logging.getLogger(__name__)

VALID_CONFIDENCE_LEVELS: Set[str] = {"high", "medium", "low"}


class DebugValidator:
    """Validates debugging analysis outputs for grounding, sanity, and security redactions."""

    @staticmethod
    def redact_secrets(text: Optional[str]) -> str:
        """Sanitize API tokens, passwords, and sensitive strings from text."""
        if not text:
            return ""

        sanitized = text
        sanitized = re.sub(r"sk-[a-zA-Z0-9_\-]{20,}", "[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"ghp_[a-zA-Z0-9_\-]{20,}", "[REDACTED_GITHUB_TOKEN]", sanitized)
        sanitized = re.sub(r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]", sanitized)
        sanitized = re.sub(
            r"(password|secret|token|api_key|access_token)\s*=\s*['\"][^'\"]{8,}['\"]",
            r"\1='[REDACTED_SECRET]'",
            sanitized,
            flags=re.IGNORECASE,
        )
        return sanitized

    def sanitize_causes(self, causes: List[PossibleCause]) -> List[PossibleCause]:
        """Sanitize secrets and ensure consistent rank and confidence for possible causes."""
        sanitized_causes = []
        for i, c in enumerate(causes, start=1):
            conf = c.confidence.lower().strip() if c.confidence else "medium"
            if conf not in VALID_CONFIDENCE_LEVELS:
                conf = "medium"

            sanitized_causes.append(
                PossibleCause(
                    rank=i,
                    title=self.redact_secrets(c.title),
                    explanation=self.redact_secrets(c.explanation),
                    confidence=conf,
                    supporting_evidence=[
                        self.redact_secrets(ev) for ev in c.supporting_evidence
                    ],
                )
            )
        return sanitized_causes

    def validate_confidence(
        self,
        reported_confidence: str,
        context: RetrievedContext,
    ) -> str:
        """Verify that reported confidence is well-calibrated against evidence availability.

        If no matching repository files were found, confidence cannot be 'high'.
        """
        conf = reported_confidence.lower().strip() if reported_confidence else "medium"
        if conf not in VALID_CONFIDENCE_LEVELS:
            conf = "medium"

        # If we have no exact source code from the repository, downgrade 'high' to 'medium' or 'low'
        if not context.has_exact_source and conf == "high":
            logger.info("Downgrading confidence from 'high' to 'medium' due to lack of repository source evidence.")
            conf = "medium"

        return conf

    def filter_related_files(
        self,
        suggested_files: List[str],
        context: RetrievedContext,
    ) -> List[str]:
        """Ensure related_files list contains only valid repository-relative files."""
        known_valid = set(context.related_files)
        evidence_files = {e.file_path for e in context.evidence_items}
        all_valid = known_valid | evidence_files

        if not all_valid:
            # If no files were located in repo, keep only non-empty strings sanitized
            return [
                self.redact_secrets(f)
                for f in suggested_files
                if f and not f.startswith("/") and ".." not in f
            ][:10]

        # Filter suggested files against valid files or return all valid files if suggestions are empty
        filtered = [f for f in suggested_files if f in all_valid]
        if not filtered:
            return sorted(list(all_valid))
        return sorted(list(set(filtered)))
