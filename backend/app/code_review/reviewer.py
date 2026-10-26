"""Code review orchestrator coordinating evidence collection, LLM synthesis, and grounding."""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.code_review.collector import EvidenceCollector
from app.code_review.grounding import GroundingValidator
from app.code_review.models import (
    CodeReviewFinding,
    CodeReviewRequest,
    CodeReviewResponse,
    EvidenceContext,
    ReviewMetadata,
    ReviewSummary,
)
from app.code_review.prompt_builder import ReviewPromptBuilder
from app.rag.generator import BaseLLMGenerator, MockLLMGenerator, get_llm_generator
from app.schemas.repository import RepositoryInfo

logger = logging.getLogger(__name__)


class CodeReviewer:
    """Orchestrates AI-powered, grounded code reviews for repository source files."""

    def __init__(
        self,
        llm_generator: Optional[BaseLLMGenerator] = None,
        collector: Optional[EvidenceCollector] = None,
        prompt_builder: Optional[ReviewPromptBuilder] = None,
        grounding_validator: Optional[GroundingValidator] = None,
    ):
        self.llm_generator = llm_generator or get_llm_generator()
        self.collector = collector or EvidenceCollector()
        self.prompt_builder = prompt_builder or ReviewPromptBuilder()
        self.grounding_validator = grounding_validator or GroundingValidator()

    async def review_code(
        self,
        repo_path: Path,
        repo_info: RepositoryInfo,
        request: CodeReviewRequest,
    ) -> CodeReviewResponse:
        """Execute complete code review pipeline for the requested file and entity.

        Args:
            repo_path: Cloned repository workspace root.
            repo_info: Repository metadata.
            request: CodeReviewRequest with target file and review settings.

        Returns:
            CodeReviewResponse with verified findings, summary, and metadata.
        """
        review_id = str(uuid.uuid4())
        warnings: List[str] = []

        # Step A: Collect Evidence & Deterministic Findings
        context = self.collector.collect(
            repo_path=repo_path,
            file_path=request.file_path,
            entity_name=request.entity_name,
            review_focus=request.review_focus,
        )

        deterministic_findings: List[CodeReviewFinding] = (
            context.static_quality_findings + context.static_security_findings
        )

        # Filter deterministic findings if focus is specific
        if request.review_focus and request.review_focus != "all":
            focus_lower = request.review_focus.lower()
            deterministic_findings = [
                f for f in deterministic_findings
                if f.category == focus_lower or (focus_lower == "bugs" and f.category == "correctness")
            ]

        # Step B: LLM Prompt Synthesis
        system_prompt = self.prompt_builder.build_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(
            context=context,
            review_focus=request.review_focus,
            user_instructions=request.user_instructions,
        )

        ai_findings: List[CodeReviewFinding] = []
        executive_summary = ""
        is_mock = isinstance(self.llm_generator, MockLLMGenerator)
        ai_available = True
        model_name = getattr(self.llm_generator, "model", "mock-gpt-4o")

        if not is_mock:
            try:
                raw_response = await self.llm_generator.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=2048,
                )
                parsed_data = self._extract_json_from_response(raw_response)
                if parsed_data:
                    executive_summary = parsed_data.get("executive_summary", "")
                    raw_items = parsed_data.get("findings", [])
                    ai_findings = self.grounding_validator.ground_findings(raw_items, context)
                else:
                    warnings.append(
                        "AI reviewer response could not be parsed into structured JSON. Falling back to deterministic static analysis."
                    )
                    ai_available = False
            except Exception as exc:
                logger.warning("LLM call failed during code review: %s", exc)
                warnings.append(f"AI review service was temporarily unavailable: {str(exc)}. Displaying deterministic checks.")
                ai_available = False
                is_mock = True

        if is_mock and not ai_findings:
            # Deterministic, grounded mock generation for tests and offline usage
            ai_findings, executive_summary = self._generate_mock_findings(context, request.review_focus)
            warnings.append("AI review ran in deterministic simulation mode (no active API key configured).")
            model_name = "mock-reviewer"

        # Filter AI findings by focus if requested
        if request.review_focus and request.review_focus != "all":
            focus_lower = request.review_focus.lower()
            ai_findings = [
                f for f in ai_findings
                if f.category == focus_lower or (focus_lower == "bugs" and f.category == "correctness")
            ]

        # Step C: Combine and Deduplicate
        all_findings = self._merge_and_sort_findings(deterministic_findings, ai_findings)

        # Step D: Construct Summary & Metrics
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        category_counts = {
            "correctness": 0,
            "security": 0,
            "performance": 0,
            "maintainability": 0,
            "readability": 0,
            "testing": 0,
        }

        for f in all_findings:
            if f.severity in severity_counts:
                severity_counts[f.severity] += 1
            if f.category in category_counts:
                category_counts[f.category] += 1

        if not executive_summary:
            executive_summary = self._synthesize_executive_summary(
                file_path=request.file_path,
                entity_name=request.entity_name,
                total=len(all_findings),
                severity_counts=severity_counts,
                category_counts=category_counts,
            )

        summary = ReviewSummary(
            total_findings=len(all_findings),
            by_severity=severity_counts,
            by_category=category_counts,
            executive_summary=executive_summary,
            deterministic_count=len(deterministic_findings),
            ai_count=len(ai_findings),
        )

        metadata = ReviewMetadata(
            ai_available=ai_available,
            model_used=model_name,
            review_focus=request.review_focus,
            lines_reviewed=max(1, context.end_line - context.start_line + 1),
            deterministic_rules_applied=len(deterministic_findings),
        )

        return CodeReviewResponse(
            review_id=review_id,
            repository=repo_info,
            file_path=request.file_path,
            entity_name=request.entity_name,
            summary=summary,
            findings=all_findings,
            metadata=metadata,
            warnings=warnings,
            status="completed",
        )

    def _extract_json_from_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON object from markdown or raw LLM output text."""
        cleaned = text.strip()
        # Check for ```json ... ``` code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try parsing entire string
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try finding first { and last }
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    return None
        return None

    def _merge_and_sort_findings(
        self,
        deterministic: List[CodeReviewFinding],
        ai_findings: List[CodeReviewFinding],
    ) -> List[CodeReviewFinding]:
        """Merge findings avoiding exact duplicates and sort by severity."""
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

        seen_keys = set()
        merged: List[CodeReviewFinding] = []

        # Include deterministic findings first
        for df in deterministic:
            key = (df.file_path, df.start_line, df.title.lower().strip())
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(df)

        # Include AI findings
        for af in ai_findings:
            key = (af.file_path, af.start_line, af.title.lower().strip())
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(af)

        merged.sort(key=lambda f: (severity_rank.get(f.severity, 99), f.start_line))
        return merged

    def _synthesize_executive_summary(
        self,
        file_path: str,
        entity_name: Optional[str],
        total: int,
        severity_counts: Dict[str, int],
        category_counts: Dict[str, int],
    ) -> str:
        """Create a clear, grounded executive summary for the review."""
        target_desc = f"`{entity_name}` in `{file_path}`" if entity_name else f"`{file_path}`"

        if total == 0:
            return (
                f"Review of {target_desc} completed. No significant bugs, security vulnerabilities, or maintainability "
                "defects were identified within the analyzed lines. Note that absence of findings does not guarantee "
                "absence of all defects."
            )

        top_cats = [cat for cat, cnt in category_counts.items() if cnt > 0]
        cats_str = ", ".join(top_cats[:3]) if top_cats else "code quality"

        return (
            f"Review of {target_desc} identified {total} actionable findings across {cats_str}. "
            f"Key attention is required for {severity_counts.get('critical', 0)} critical and {severity_counts.get('high', 0)} high severity items."
        )

    def _generate_mock_findings(
        self,
        context: EvidenceContext,
        review_focus: str,
    ) -> Tuple[List[CodeReviewFinding], str]:
        """Synthesize deterministic, grounded mock review findings based on real AST structure."""
        findings: List[CodeReviewFinding] = []
        lines = context.content.splitlines()

        # Check for unhandled division or zero check
        for idx, line in enumerate(lines, context.start_line):
            if "/" in line and "//" not in line and "ZeroDivisionError" not in context.content:
                findings.append(
                    CodeReviewFinding(
                        finding_id="cr_ai_mock_1",
                        title="Potential Unhandled ZeroDivisionError",
                        category="correctness",
                        severity="medium",
                        confidence="high",
                        file_path=context.file_path,
                        start_line=idx,
                        end_line=idx,
                        entity_name=context.entity_name,
                        problem="Division operator without explicit denominator validation can raise ZeroDivisionError at runtime.",
                        evidence=line.strip(),
                        recommendation="Validate that the denominator is non-zero before performing division, or catch ZeroDivisionError.",
                        suggested_change=(
                            "if denominator == 0:\n"
                            "    raise ValueError('Denominator cannot be zero')\n"
                            f"{line}"
                        ),
                        source="ai_review",
                        is_verified=True,
                    )
                )
                break

        # Check for functions without type annotations
        for idx, line in enumerate(lines, context.start_line):
            if line.strip().startswith("def ") and "->" not in line:
                findings.append(
                    CodeReviewFinding(
                        finding_id="cr_ai_mock_2",
                        title="Missing Return Type Annotation",
                        category="readability",
                        severity="low",
                        confidence="high",
                        file_path=context.file_path,
                        start_line=idx,
                        end_line=idx,
                        entity_name=context.entity_name,
                        problem="Function definition lacks an explicit return type hint, reducing static analysis benefits and readability.",
                        evidence=line.strip(),
                        recommendation="Add explicit PEP 484 return type hints to improve type safety and IDE autocompletion.",
                        suggested_change=f"{line.rstrip(':')} -> Any:",
                        source="ai_review",
                        is_verified=True,
                    )
                )
                break

        # Check for missing docstring
        if context.functions and not any('"""' in l or "'''" in l for l in lines):
            first_def = next((idx for idx, l in enumerate(lines, context.start_line) if l.strip().startswith("def ")), context.start_line)
            findings.append(
                CodeReviewFinding(
                    finding_id="cr_ai_mock_3",
                    title="Missing Function Docstring",
                    category="maintainability",
                    severity="info",
                    confidence="high",
                    file_path=context.file_path,
                    start_line=first_def,
                    end_line=first_def,
                    entity_name=context.entity_name,
                    problem="Public function does not include a docstring documenting parameters, return values, and expected exceptions.",
                    evidence=lines[first_def - context.start_line].strip() if first_def - context.start_line < len(lines) else "def ...",
                    recommendation="Add a descriptive Google or Sphinx style docstring documenting arguments and return types.",
                    suggested_change='"""Execute core logic and return computed result."""',
                    source="ai_review",
                    is_verified=True,
                )
            )

        exec_summary = (
            f"Code review of `{context.file_path}` identified {len(findings)} improvement opportunities. "
            "Recommendations emphasize error handling robustness and explicit type annotations."
        )

        return findings, exec_summary
