"""Code chunking engine for extracting semantically bounded code units."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.code_intelligence.models import CodeChunk, CodeEntity, CodeFile

logger = logging.getLogger(__name__)

# Maximum lines per chunk for fallback windowing if an entity or file is huge
MAX_CHUNK_LINES = 300


class CodeChunker:
    """Extracts semantic, self-contained code chunks from analyzed repository files."""

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate token count for code or text using standard character/token ratio.

        Code typically averages ~3.5 to 4.0 characters per token.
        """
        if not text:
            return 0
        return max(1, round(len(text) / 3.8))

    @classmethod
    def build_context_header(
        cls,
        file_path: str,
        entity_name: str,
        entity_type: str,
        start_line: int,
        end_line: int,
        parent: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> str:
        """Build a descriptive contextual header for downstream search and LLM prompts."""
        header_parts = [f"File: {file_path}"]
        if parent:
            header_parts.append(f"Scope: {parent}")

        type_label = entity_type.replace("_", " ").title()
        header_parts.append(f"{type_label}: {entity_name}")
        header_parts.append(f"Lines: {start_line}-{end_line}")

        if signature:
            header_parts.append(f"Signature: {signature}")

        return " | ".join(header_parts)

    def chunk_repository(
        self,
        repo_path: Path,
        code_files: List[CodeFile],
    ) -> List[CodeChunk]:
        """Convert all analyzed repository files and entities into CodeChunks.

        Args:
            repo_path: Root Path of the cloned repository.
            code_files: List of CodeFile instances previously analyzed.

        Returns:
            List of CodeChunk instances.
        """
        chunks: List[CodeChunk] = []

        for code_file in code_files:
            file_chunks = self.chunk_file(repo_path, code_file)
            chunks.extend(file_chunks)

        return chunks

    def chunk_file(
        self,
        repo_path: Path,
        code_file: CodeFile,
    ) -> List[CodeChunk]:
        """Generate semantic chunks for a single analyzed file.

        Args:
            repo_path: Root Path of the repository.
            code_file: Analyzed CodeFile metadata and entity list.

        Returns:
            List of CodeChunk instances for this file.
        """
        full_path = repo_path / code_file.path
        if not full_path.is_file():
            return []

        try:
            content = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = full_path.read_text(encoding="latin-1")
            except Exception as exc:
                logger.warning("Failed to read file for chunking %s: %s", code_file.path, exc)
                return []

        lines = content.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return []

        chunks: List[CodeChunk] = []

        # If entities are present, create chunks for each entity
        if code_file.entities:
            for entity in code_file.entities:
                chunk = self._create_entity_chunk(
                    code_file=code_file,
                    entity=entity,
                    lines=lines,
                    total_lines=total_lines,
                )
                if chunk:
                    chunks.append(chunk)

        # If no entities were detected (e.g. procedural script or config file), create module chunk
        if not chunks:
            module_chunk = self._create_file_module_chunk(code_file, lines, total_lines)
            if module_chunk:
                chunks.append(module_chunk)

        return chunks

    def _create_entity_chunk(
        self,
        code_file: CodeFile,
        entity: CodeEntity,
        lines: List[str],
        total_lines: int,
    ) -> Optional[CodeChunk]:
        """Extract lines and construct a CodeChunk for an individual AST entity."""
        start_idx = max(0, entity.start_line - 1)
        end_idx = min(total_lines, max(start_idx + 1, entity.end_line))

        chunk_lines = lines[start_idx:end_idx]
        code_content = "\n".join(chunk_lines)

        scope_prefix = f"{entity.parent}." if entity.parent else ""
        chunk_id = f"{code_file.path}#{scope_prefix}{entity.name}#L{entity.start_line}-L{entity.end_line}"

        context_header = self.build_context_header(
            file_path=code_file.path,
            entity_name=entity.name,
            entity_type=entity.type,
            start_line=entity.start_line,
            end_line=entity.end_line,
            parent=entity.parent,
            signature=entity.signature,
        )

        tokens_estimate = self.estimate_tokens(code_content)

        return CodeChunk(
            chunk_id=chunk_id,
            file_path=code_file.path,
            entity_name=entity.name,
            entity_type=entity.type,
            language=code_file.language,
            start_line=entity.start_line,
            end_line=entity.end_line,
            signature=entity.signature,
            docstring=entity.docstring,
            parent=entity.parent,
            parameters=entity.parameters,
            return_type=entity.return_type,
            decorators=entity.decorators,
            visibility=entity.visibility,
            code_content=code_content,
            context_header=context_header,
            tokens_estimate=tokens_estimate,
        )

    def _create_file_module_chunk(
        self,
        code_file: CodeFile,
        lines: List[str],
        total_lines: int,
    ) -> Optional[CodeChunk]:
        """Create a fallback module chunk when a file has no AST entities."""
        name = Path(code_file.path).stem
        chunk_id = f"{code_file.path}#{name}#L1-L{total_lines}"
        code_content = "\n".join(lines[:MAX_CHUNK_LINES])

        context_header = self.build_context_header(
            file_path=code_file.path,
            entity_name=name,
            entity_type="file_module",
            start_line=1,
            end_line=min(total_lines, MAX_CHUNK_LINES),
            parent=None,
            signature=None,
        )

        return CodeChunk(
            chunk_id=chunk_id,
            file_path=code_file.path,
            entity_name=name,
            entity_type="file_module",
            language=code_file.language,
            start_line=1,
            end_line=min(total_lines, MAX_CHUNK_LINES),
            signature=None,
            docstring=None,
            parent=None,
            parameters=[],
            return_type=None,
            decorators=[],
            visibility=None,
            code_content=code_content,
            context_header=context_header,
            tokens_estimate=self.estimate_tokens(code_content),
        )
