"""Documentation validator, secret redactor, and Markdown section parser."""

import re
from typing import List, Optional, Set, Tuple

from app.doc_generator.models import CollectedDocContext, DocSection


class DocValidator:
    """Validates generated documentation for grounding, section hierarchy, and security."""

    @staticmethod
    def redact_secrets(text: Optional[str]) -> str:
        """Sanitize API tokens, passwords, and sensitive strings from Markdown."""
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

    def parse_title_and_sections(
        self, markdown_text: str
    ) -> Tuple[str, str, List[DocSection]]:
        """Parse title, executive summary, and structured sections from Markdown."""
        lines = markdown_text.strip().splitlines()

        title = "Technical Documentation"
        summary = ""
        sections: List[DocSection] = []

        # Find main H1 title
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                title = stripped[2:].strip()
                # Find executive summary under title before next heading
                summary_lines = []
                for sub_line in lines[idx + 1 :]:
                    sub_strip = sub_line.strip()
                    if sub_strip.startswith("#"):
                        break
                    if sub_strip:
                        summary_lines.append(sub_strip)
                    if len(summary_lines) >= 3:
                        break
                summary = " ".join(summary_lines)[:350]
                break

        # Parse H2 sections
        current_section_title: Optional[str] = None
        current_section_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## ") and not stripped.startswith("### "):
                if current_section_title:
                    sections.append(
                        DocSection(
                            title=current_section_title,
                            content="\n".join(current_section_lines).strip(),
                        )
                    )
                current_section_title = stripped[3:].strip()
                current_section_lines = []
            elif current_section_title is not None:
                current_section_lines.append(line)

        # Append last section
        if current_section_title:
            sections.append(
                DocSection(
                    title=current_section_title,
                    content="\n".join(current_section_lines).strip(),
                )
            )

        if not summary and sections:
            summary = sections[0].content[:250].replace("\n", " ").strip()
        if not summary:
            summary = f"Technical documentation covering {title}."

        return title, summary, sections

    def check_unverified_items(
        self, markdown_text: str, context: CollectedDocContext
    ) -> Tuple[List[str], List[str]]:
        """Find unverified claims and identify missing information notes."""
        unverified: List[str] = []
        missing: List[str] = list(context.missing_elements)

        # Detect '[Requires Confirmation]' tags
        for match in re.finditer(r"\[Requires Confirmation(?::\s*([^\]]+))?\]", markdown_text, re.IGNORECASE):
            detail = match.group(1) or "Configuration or command requiring verification"
            unverified.append(detail.strip())

        # Check for placeholder markers like 'TODO', 'FIXME', 'TBD'
        for match in re.finditer(r"\b(TODO|FIXME|TBD|PLACEHOLDER)\b:?\s*([^\n]+)", markdown_text, re.IGNORECASE):
            unverified.append(match.group(2).strip()[:100])

        return sorted(list(set(unverified))), sorted(list(set(missing)))
