"""AI Technical Documentation Generator orchestrating context collection, LLM synthesis, and validation."""

import datetime
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.doc_generator.context_collector import ContextCollector
from app.doc_generator.models import (
    CollectedDocContext,
    DocAudience,
    DocDetailLevel,
    DocExecutionError,
    DocGenerateRequest,
    DocGenerateResponse,
    DocMetadata,
    DocType,
    DocValidationError,
)
from app.doc_generator.prompt_builder import DocPromptBuilder
from app.doc_generator.store import document_store
from app.doc_generator.validator import DocValidator
from app.rag.generator import BaseLLMGenerator, MockLLMGenerator, get_llm_generator
from app.schemas.repository import RepositoryInfo

logger = logging.getLogger(__name__)


class DocGenerator:
    """Orchestrates technical documentation generation based on repository source evidence."""

    def __init__(
        self,
        llm_generator: Optional[BaseLLMGenerator] = None,
        collector: Optional[ContextCollector] = None,
        prompt_builder: Optional[DocPromptBuilder] = None,
        validator: Optional[DocValidator] = None,
    ):
        self.llm_generator = llm_generator or get_llm_generator()
        self.collector = collector or ContextCollector()
        self.prompt_builder = prompt_builder or DocPromptBuilder()
        self.validator = validator or DocValidator()

    async def generate_documentation(
        self,
        repo_path: Path,
        repo_info: RepositoryInfo,
        request: DocGenerateRequest,
    ) -> DocGenerateResponse:
        """Execute end-to-end documentation synthesis for the requested document type.

        Args:
            repo_path: Cloned repository workspace root.
            repo_info: Repository metadata.
            request: DocGenerateRequest with document type and options.

        Returns:
            DocGenerateResponse with verified Markdown content, sections, and metadata.
        """
        start_time = time.time()
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        warnings: List[str] = []

        # 1. Collect repository context
        context = self.collector.collect_context(
            repo_path=repo_path,
            doc_type=request.doc_type,
            target_path=request.target_path,
            target_symbol=request.target_symbol,
        )

        if context.missing_elements:
            warnings.extend(context.missing_elements)

        # 2. Synthesize documentation
        is_mock = isinstance(self.llm_generator, MockLLMGenerator)
        raw_markdown: Optional[str] = None
        model_name = getattr(self.llm_generator, "model", "mock-gpt-4o")

        if not is_mock:
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(
                repo_info=repo_info,
                context=context,
                audience=request.audience,
                detail_level=request.detail_level,
                user_instructions=request.user_instructions,
                target_path=request.target_path,
                target_symbol=request.target_symbol,
            )

            try:
                raw_markdown = await self.llm_generator.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=3000,
                )
            except Exception as exc:
                logger.warning(
                    "LLM documentation generation failed: %s. Using deterministic documentation engine.", exc
                )
                warnings.append(
                    f"AI generator encountered an issue ({type(exc).__name__}); generated verified deterministic documentation."
                )

        if not raw_markdown or not raw_markdown.strip():
            raw_markdown = self._generate_deterministic_doc(
                repo_info=repo_info,
                context=context,
                request=request,
            )

        # 3. Sanitize secrets
        clean_markdown = self.validator.redact_secrets(raw_markdown)

        # 4. Parse sections and check unverified items
        title, summary, sections = self.validator.parse_title_and_sections(clean_markdown)
        unverified_items, missing_info = self.validator.check_unverified_items(clean_markdown, context)

        duration = round(time.time() - start_time, 2)
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        metadata = DocMetadata(
            doc_type=request.doc_type.value,
            audience=request.audience.value,
            detail_level=request.detail_level.value,
            model=model_name,
            generation_time_seconds=duration,
            source_files_count=len(context.source_files_used),
            created_at=created_at,
        )

        response = DocGenerateResponse(
            document_id=document_id,
            repository=repo_info,
            doc_type=request.doc_type,
            title=title,
            content=clean_markdown,
            summary=summary,
            sections=sections,
            source_files_used=context.source_files_used,
            missing_information=missing_info,
            unverified_items=unverified_items,
            metadata=metadata,
            status="completed",
            warnings=warnings,
        )

        # Save to store for retrieval by ID
        document_store.save(response)

        return response

    def _generate_deterministic_doc(
        self,
        repo_info: RepositoryInfo,
        context: CollectedDocContext,
        request: DocGenerateRequest,
    ) -> str:
        """Synthesize verified, structured Markdown documentation derived purely from static evidence."""
        dt = request.doc_type
        repo_name = repo_info.name
        branch = repo_info.default_branch or "main"

        if dt == DocType.README:
            return self._build_deterministic_readme(repo_name, branch, context)
        elif dt == DocType.ARCHITECTURE:
            return self._build_deterministic_architecture(repo_name, context)
        elif dt == DocType.API_REFERENCE:
            return self._build_deterministic_api_reference(repo_name, context)
        elif dt == DocType.FUNCTION_REFERENCE:
            return self._build_deterministic_function_reference(repo_name, context, request.target_symbol)
        elif dt == DocType.SETUP_GUIDE:
            return self._build_deterministic_setup_guide(repo_name, context)
        elif dt == DocType.MODULE:
            return self._build_deterministic_module_doc(repo_name, context, request.target_path)
        else:  # PROJECT_OVERVIEW and fallback
            return self._build_deterministic_overview(repo_name, context)

    def _build_deterministic_readme(
        self, repo_name: str, branch: str, context: CollectedDocContext
    ) -> str:
        manifest_langs = []
        if "package.json" in context.manifest_files:
            manifest_langs.append("Node.js / TypeScript")
        if any(f in context.manifest_files for f in ("requirements.txt", "pyproject.toml", "setup.py")):
            manifest_langs.append("Python")

        lang_summary = ", ".join(manifest_langs) if manifest_langs else "Multi-language"

        test_line = (
            f"- Test framework: `{', '.join(context.test_frameworks)}`"
            if context.test_frameworks
            else "- Testing: [Requires Confirmation]"
        )

        routes_summary = ""
        if context.discovered_routes:
            routes_summary = (
                f"\n## API Endpoints\n\n"
                f"The repository provides {len(context.discovered_routes)} discoverable API endpoints:\n\n"
                + "\n".join([f"- `{r.method} {r.path}` (handler `{r.handler_name}`)" for r in context.discovered_routes[:10]])
                + "\n"
            )

        return (
            f"# {repo_name}\n\n"
            f"Technical documentation and project guide for `{repo_name}`.\n\n"
            f"## Overview\n\n"
            f"`{repo_name}` is a {lang_summary} repository configured with default branch `{branch}`.\n\n"
            f"## Technology Stack\n\n"
            f"- Languages & Runtimes: {lang_summary}\n"
            f"- Manifests detected: {', '.join(context.manifest_files.keys()) or 'None'}\n"
            f"{test_line}\n\n"
            f"## Repository Structure\n\n"
            f"```text\n{context.file_tree_summary[:1200]}\n```\n"
            f"{routes_summary}\n"
            f"## Getting Started\n\n"
            f"### Prerequisites\n\n"
            f"Ensure required runtime environments ({lang_summary}) are installed on your host system.\n\n"
            f"### Installation\n\n"
            + ("```bash\n# Python installation\npip install -r requirements.txt\n```\n\n" if "requirements.txt" in context.manifest_files else "")
            + ("```bash\n# Node.js installation\nnpm install\n```\n\n" if "package.json" in context.manifest_files else "")
            + f"### Running Tests\n\n"
            + ("```bash\npytest\n```\n\n" if "pytest" in context.test_frameworks else "```bash\n# [Requires Confirmation: test execution command]\n```\n\n")
            + f"## License & Contributing\n\n"
            f"Refer to repository files for contribution and license terms."
        )

    def _build_deterministic_architecture(
        self, repo_name: str, context: CollectedDocContext
    ) -> str:
        # Build a valid Mermaid diagram based on actual discovered directories and components
        mermaid_nodes = []
        mermaid_links = []

        has_frontend = "frontend" in context.file_tree_summary
        has_backend = "backend" in context.file_tree_summary or "app" in context.file_tree_summary

        if has_frontend and has_backend:
            mermaid_nodes.append("  Client[Client / Frontend]")
            mermaid_nodes.append("  API[Backend API Gateway]")
            mermaid_links.append("  Client -->|HTTP / JSON| API")
            if context.discovered_routes:
                mermaid_nodes.append("  Endpoints[Discovered Endpoints]")
                mermaid_links.append("  API --> Endpoints")
        else:
            mermaid_nodes.append(f"  Root[{repo_name}]")
            if context.discovered_routes:
                mermaid_nodes.append("  API[API Endpoints]")
                mermaid_links.append("  Root --> API")

        mermaid_block = "```mermaid\ngraph TD\n" + "\n".join(mermaid_nodes + mermaid_links) + "\n```"

        routes_table = ""
        if context.discovered_routes:
            routes_table = (
                "\n### Discovered Route Handlers\n\n"
                "| Method | Path | Handler | Location |\n"
                "| :--- | :--- | :--- | :--- |\n"
                + "\n".join([f"| `{r.method}` | `{r.path}` | `{r.handler_name}` | `{r.file_path}:{r.line_number}` |" for r in context.discovered_routes[:15]])
                + "\n"
            )

        return (
            f"# {repo_name} — Architecture Overview\n\n"
            f"Architectural structure and component flow of `{repo_name}` based on static codebase analysis.\n\n"
            f"## System Architecture\n\n"
            f"{mermaid_block}\n\n"
            f"## Component Breakdown\n\n"
            f"### Directory Structure\n\n"
            f"```text\n{context.file_tree_summary[:1000]}\n```\n"
            f"{routes_table}\n"
            f"## Environment and Configuration\n\n"
            + (f"Referenced Environment Variables:\n" + "\n".join([f"- `{v}`" for v in context.environment_vars]) if context.environment_vars else "No specific environment variables discovered in code.")
        )

    def _build_deterministic_api_reference(
        self, repo_name: str, context: CollectedDocContext
    ) -> str:
        if not context.discovered_routes:
            return (
                f"# {repo_name} — API Reference\n\n"
                f"No explicit HTTP routes were discovered during static inspection of `{repo_name}`.\n\n"
                f"## Discovered Code Symbols\n\n"
                + "\n".join([f"- `{s.symbol_type}` `{s.name}` in `{s.file_path}`" for s in context.discovered_symbols[:20]])
            )

        rows = [
            f"## `{r.method} {r.path}`\n\n"
            f"- **Handler**: `{r.handler_name}()`\n"
            f"- **Location**: `{r.file_path}:{r.line_number}`\n"
            + (f"- **Description**: {r.docstring}\n" if r.docstring else "")
            for r in context.discovered_routes
        ]

        return (
            f"# {repo_name} — API Reference\n\n"
            f"Discovered REST API endpoints and handlers in `{repo_name}`.\n\n"
            + "\n".join(rows)
        )

    def _build_deterministic_function_reference(
        self, repo_name: str, context: CollectedDocContext, target_symbol: Optional[str]
    ) -> str:
        symbols_to_doc = context.discovered_symbols
        if target_symbol:
            symbols_to_doc = [s for s in symbols_to_doc if target_symbol in s.name]

        if not symbols_to_doc:
            return (
                f"# {repo_name} — Function Reference\n\n"
                f"No matching function or class symbols were found for target '{target_symbol or 'all'}'.\n"
            )

        blocks = []
        for s in symbols_to_doc[:25]:
            doc_str = s.docstring or "No docstring provided in source."
            blocks.append(
                f"## `{s.name}`\n\n"
                f"- **Type**: `{s.symbol_type}`\n"
                f"- **Defined in**: `{s.file_path}:{s.start_line}`\n"
                f"- **Signature**: `{s.signature or s.name}`\n\n"
                f"### Description\n\n{doc_str}\n"
            )

        return (
            f"# {repo_name} — Function Reference\n\n"
            f"Code reference for functions and classes in `{repo_name}`.\n\n"
            + "\n".join(blocks)
        )

    def _build_deterministic_setup_guide(
        self, repo_name: str, context: CollectedDocContext
    ) -> str:
        env_section = (
            "## Configuration & Environment Variables\n\n"
            "The following environment variables are referenced in source code:\n\n"
            + "\n".join([f"- `{v}`" for v in context.environment_vars])
            if context.environment_vars
            else "## Configuration\n\nNo environment variable references were detected."
        )

        return (
            f"# {repo_name} — Setup and Installation Guide\n\n"
            f"Step-by-step instructions for installing and running `{repo_name}`.\n\n"
            f"## Prerequisites\n\n"
            f"Review manifests: {', '.join(context.manifest_files.keys()) or 'No manifests detected'}.\n\n"
            f"## Installation\n\n"
            + ("```bash\npip install -r requirements.txt\n```\n\n" if "requirements.txt" in context.manifest_files else "")
            + ("```bash\nnpm install\n```\n\n" if "package.json" in context.manifest_files else "")
            + f"{env_section}\n\n"
            f"## Verification\n\n"
            + (f"Run tests with `{', '.join(context.test_frameworks)}`." if context.test_frameworks else "Verify installation according to project scripts.")
        )

    def _build_deterministic_module_doc(
        self, repo_name: str, context: CollectedDocContext, target_path: Optional[str]
    ) -> str:
        path_label = target_path or "Module"
        content_preview = (
            f"### Target Source Code\n\n```\n{context.target_content[:2000]}\n```\n"
            if context.target_content
            else ""
        )

        return (
            f"# {repo_name} — Module Documentation: {path_label}\n\n"
            f"Technical documentation for `{path_label}`.\n\n"
            f"## Overview\n\n"
            f"Source module within `{repo_name}`.\n\n"
            f"{content_preview}"
        )

    def _build_deterministic_overview(
        self, repo_name: str, context: CollectedDocContext
    ) -> str:
        return (
            f"# {repo_name} — Project Overview\n\n"
            f"High-level technical overview of `{repo_name}`.\n\n"
            f"## Summary\n\n"
            f"Repository contains {len(context.source_files_used)} analyzed files.\n\n"
            f"## Discovered Endpoints\n\n"
            f"Total discovered API routes: {len(context.discovered_routes)}.\n\n"
            f"## Structure\n\n"
            f"```text\n{context.file_tree_summary[:1000]}\n```\n"
        )
