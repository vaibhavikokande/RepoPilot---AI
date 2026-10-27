"""Source code locator and context retriever for the AI debugging assistant."""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.debug_assistant.models import (
    DebugValidationError,
    ParsedError,
    RetrievedContext,
    SourceEvidence,
    StackFrame,
)

logger = logging.getLogger(__name__)

MAX_CONTEXT_LINES = 500
MAX_SNIPPETS = 6
CONTEXT_WINDOW_PADDING = 15  # Lines before and after target line


class ContextLocator:
    """Locates and extracts relevant source code from the repository for debugging."""

    def __init__(self, max_context_lines: int = MAX_CONTEXT_LINES):
        self.max_context_lines = max_context_lines

    def resolve_repo_relative_path(self, repo_path: Path, raw_path: str) -> Optional[str]:
        """Resolve a raw path from a stack trace or request to a valid repo-relative path.

        Handles:
        - Relative paths within repo (e.g. 'app/services/calc.py')
        - Absolute paths containing repo subpaths (e.g. '/var/app/services/calc.py')
        - Windows backslash paths (e.g. 'app\\services\\calc.py')
        - Strips path traversal attempts ('..')

        Returns:
            Normalized repo-relative path string if found within repo, else None.
        """
        if not raw_path or not raw_path.strip():
            return None

        clean_path = raw_path.strip().replace("\\", "/").strip("\"'")

        # Security check: Reject obvious path traversal patterns
        if ".." in clean_path.split("/"):
            logger.warning("Path traversal attempt rejected: %s", clean_path)
            return None

        # 1. Direct relative check
        candidate = (repo_path / clean_path).resolve()
        try:
            rel = candidate.relative_to(repo_path.resolve())
            if candidate.is_file():
                return str(rel).replace("\\", "/")
        except ValueError:
            pass

        # 2. Suffix matching for absolute or nested container paths
        # E.g., if raw_path is '/usr/src/app/backend/main.py', look for 'backend/main.py', 'main.py', etc.
        parts = [p for p in clean_path.split("/") if p and p != "." and p != ".."]
        for i in range(len(parts)):
            subpath = "/".join(parts[i:])
            candidate = (repo_path / subpath).resolve()
            try:
                rel = candidate.relative_to(repo_path.resolve())
                if candidate.is_file():
                    return str(rel).replace("\\", "/")
            except ValueError:
                continue

        return None

    def validate_file_path(self, repo_path: Path, rel_path: str) -> Path:
        """Validate and resolve a relative file path against the repository root.

        Raises:
            DebugValidationError: If path traversal or access outside repo is attempted.
        """
        if not rel_path or not rel_path.strip():
            raise DebugValidationError("File path cannot be empty.")

        clean = rel_path.strip().replace("\\", "/")
        if ".." in clean.split("/") or clean.startswith("/"):
            raise DebugValidationError(f"Invalid path traversal: '{rel_path}' escapes repository boundary.")

        resolved = (repo_path / clean).resolve()
        try:
            resolved.relative_to(repo_path.resolve())
        except ValueError as exc:
            raise DebugValidationError(f"Security error: path '{rel_path}' is outside repository root.") from exc

        return resolved

    def _extract_enclosing_entity(
        self, file_content: str, line_number: int
    ) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        """Attempt to find the enclosing function or class using Python AST.

        Returns:
            Tuple of (entity_name, start_line, end_line) or (None, None, None).
        """
        try:
            tree = ast.parse(file_content)
        except Exception:
            return None, None, None

        best_entity = None
        best_range = (None, None)
        smallest_span = float("inf")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = getattr(node, "lineno", None)
                end = getattr(node, "end_lineno", None)
                if start and end and start <= line_number <= end:
                    span = end - start
                    if span < smallest_span:
                        smallest_span = span
                        best_entity = node.name
                        best_range = (start, end)

        return best_entity, best_range[0], best_range[1]

    def _extract_snippet(
        self,
        file_path: Path,
        rel_path_str: str,
        target_line: Optional[int] = None,
        entity_name_hint: Optional[str] = None,
        relevance_hint: str = "",
    ) -> Optional[SourceEvidence]:
        """Read a file and extract a relevant source slice with line numbers."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Could not read file %s: %s", file_path, exc)
            return None

        lines = content.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return None

        # Determine line range
        start_line = 1
        end_line = total_lines
        detected_entity = None

        if target_line and 1 <= target_line <= total_lines:
            # Check for enclosing function/class
            ast_entity, ast_start, ast_end = self._extract_enclosing_entity(content, target_line)
            detected_entity = ast_entity or entity_name_hint

            if ast_start and ast_end and (ast_end - ast_start <= 60):
                # Use enclosing entity boundaries if reasonably sized
                start_line = max(1, ast_start)
                end_line = min(total_lines, ast_end)
            else:
                # Use window around target line
                start_line = max(1, target_line - CONTEXT_WINDOW_PADDING)
                end_line = min(total_lines, target_line + CONTEXT_WINDOW_PADDING)
        else:
            # First 50 lines for files without target line
            end_line = min(total_lines, 50)

        # Slice lines and format with line numbers
        selected_lines = lines[start_line - 1 : end_line]
        numbered_lines = [
            f"{start_line + idx:4d} | {line}"
            for idx, line in enumerate(selected_lines)
        ]
        snippet_text = "\n".join(numbered_lines)

        relevance = relevance_hint
        if not relevance:
            if target_line:
                relevance = f"Execution point at line {target_line}"
                if detected_entity:
                    relevance += f" in function/class '{detected_entity}'"
            else:
                relevance = "Referenced file in error context"

        return SourceEvidence(
            file_path=rel_path_str,
            start_line=start_line,
            end_line=end_line,
            code_snippet=snippet_text,
            entity_name=detected_entity,
            relevance=relevance,
        )

    def locate_context(
        self,
        repo_path: Path,
        parsed_error: ParsedError,
        user_file_path: Optional[str] = None,
    ) -> RetrievedContext:
        """Locate and assemble all relevant code evidence for the parsed error.

        Prioritizes:
        1. Exact stack trace frames from application code (most recent / innermost first)
        2. User-provided file_path
        3. Other referenced files in parsed error

        Returns:
            RetrievedContext with evidence items and metadata.
        """
        evidence_items: List[SourceEvidence] = []
        related_files_set: Set[str] = set()
        missing_files: List[str] = []
        lines_consumed = 0

        # Step 1: Process stack frames (reverse order to prioritize innermost failure frames)
        frames_to_check = list(reversed(parsed_error.frames)) if parsed_error.frames else []

        for frame in frames_to_check:
            if len(evidence_items) >= MAX_SNIPPETS or lines_consumed >= self.max_context_lines:
                break

            if not frame.file_path:
                continue

            rel_path = self.resolve_repo_relative_path(repo_path, frame.file_path)
            if not rel_path:
                if frame.is_application_code and frame.file_path not in missing_files:
                    missing_files.append(frame.file_path)
                continue

            # Don't duplicate file snippets for the exact same target line
            already_covered = any(
                e.file_path == rel_path and frame.line_number and e.start_line <= frame.line_number <= e.end_line
                for e in evidence_items
            )
            if already_covered:
                related_files_set.add(rel_path)
                continue

            full_path = repo_path / rel_path
            relevance = (
                f"Stack frame line {frame.line_number} in '{frame.function_name}'"
                if frame.function_name and frame.line_number
                else f"Stack frame line {frame.line_number}"
                if frame.line_number
                else "Referenced in stack trace"
            )

            snippet = self._extract_snippet(
                file_path=full_path,
                rel_path_str=rel_path,
                target_line=frame.line_number,
                entity_name_hint=frame.function_name,
                relevance_hint=relevance,
            )

            if snippet:
                evidence_items.append(snippet)
                related_files_set.add(rel_path)
                lines_consumed += (snippet.end_line - snippet.start_line + 1)

        # Step 2: User-provided file path if specified
        if user_file_path and len(evidence_items) < MAX_SNIPPETS and lines_consumed < self.max_context_lines:
            resolved_user_path = self.resolve_repo_relative_path(repo_path, user_file_path)
            if resolved_user_path:
                already_covered = any(e.file_path == resolved_user_path for e in evidence_items)
                if not already_covered:
                    full_path = repo_path / resolved_user_path
                    snippet = self._extract_snippet(
                        file_path=full_path,
                        rel_path_str=resolved_user_path,
                        relevance_hint="User-specified target file for debugging analysis",
                    )
                    if snippet:
                        evidence_items.append(snippet)
                        related_files_set.add(resolved_user_path)
                        lines_consumed += (snippet.end_line - snippet.start_line + 1)
            else:
                if user_file_path not in missing_files:
                    missing_files.append(user_file_path)

        # Step 3: Other file paths mentioned in parsed error
        for fp in parsed_error.file_paths:
            if len(evidence_items) >= MAX_SNIPPETS or lines_consumed >= self.max_context_lines:
                break
            rel_path = self.resolve_repo_relative_path(repo_path, fp)
            if rel_path and rel_path not in related_files_set:
                full_path = repo_path / rel_path
                snippet = self._extract_snippet(
                    file_path=full_path,
                    rel_path_str=rel_path,
                    relevance_hint="File referenced in error text",
                )
                if snippet:
                    evidence_items.append(snippet)
                    related_files_set.add(rel_path)
                    lines_consumed += (snippet.end_line - snippet.start_line + 1)

        # Format context text for prompt
        context_parts = []
        for i, ev in enumerate(evidence_items, start=1):
            entity_str = f" | Entity: {ev.entity_name}" if ev.entity_name else ""
            header = f"--- [Evidence E{i}] File: {ev.file_path} (Lines {ev.start_line}-{ev.end_line}){entity_str} ---"
            relevance_note = f"Relevance: {ev.relevance}"
            context_parts.append(f"{header}\n{relevance_note}\n```\n{ev.code_snippet}\n```")

        context_text = "\n\n".join(context_parts) if context_parts else "No matching repository source files found."

        return RetrievedContext(
            evidence_items=evidence_items,
            related_files=sorted(list(related_files_set)),
            missing_files=missing_files,
            context_text=context_text,
            total_lines=lines_consumed,
            has_exact_source=len(evidence_items) > 0,
        )
