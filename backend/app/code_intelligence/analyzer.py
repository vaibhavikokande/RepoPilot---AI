"""Code intelligence analysis orchestrator, dependency resolver, and metrics aggregator."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.code_intelligence.models import (
    CodebaseSummary,
    CodeEntity,
    CodeFile,
    CodeImport,
    CodeStructureNode,
    DependencyRelation,
    FileParseError,
)
from app.code_intelligence.parser import CodeParserManager
from app.code_intelligence.tree_builder import CodebaseTreeBuilder
from app.services.scanner_service import IGNORED_DIRECTORIES, IGNORED_EXTENSIONS

logger = logging.getLogger(__name__)

# Maximum file size to analyze (1 MB) to prevent parser stalls on giant minified files
MAX_PARSEABLE_FILE_SIZE_BYTES = 1024 * 1024


class CodeIntelligenceAnalyzer:
    """Orchestrates AST parsing, entity extraction, dependency analysis, and tree building."""

    def __init__(self, parser_manager: Optional[CodeParserManager] = None):
        self.parser_manager = parser_manager or CodeParserManager()

    def analyze_repository(
        self, repo_path: Path
    ) -> Tuple[
        CodebaseSummary,
        List[CodeFile],
        List[CodeEntity],
        List[DependencyRelation],
        List[CodeStructureNode],
        List[FileParseError],
    ]:
        """Statically analyze all supported source files in the repository.

        Args:
            repo_path: Root Path to the cloned repository.

        Returns:
            Tuple of:
            - summary: CodebaseSummary
            - files: List of CodeFile
            - entities: Flat list of all CodeEntity
            - dependencies: List of DependencyRelation
            - codebase_tree: Hierarchical CodeStructureNode tree
            - errors: List of FileParseError
        """
        repo_path = repo_path.resolve()

        analyzed_files: List[CodeFile] = []
        all_entities: List[CodeEntity] = []
        all_imports: List[CodeImport] = []
        parse_errors: List[FileParseError] = []

        total_classes = 0
        total_functions = 0
        total_methods = 0
        total_interfaces = 0
        total_types = 0
        language_file_counts: Dict[str, int] = {}

        # 1. Traverse and discover parseable files
        for root, dirs, files in os.walk(repo_path, topdown=True):
            # Exclude ignored directories in-place
            dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRECTORIES]

            root_path = Path(root)

            for file_name in files:
                ext = Path(file_name).suffix.lower()
                if ext in IGNORED_EXTENSIONS:
                    continue

                full_path = root_path / file_name
                if not full_path.is_file() or full_path.is_symlink():
                    continue

                # Determine language and parser
                language = self._detect_language(ext)
                if not language:
                    continue

                parser = self.parser_manager.get_parser(language, full_path)
                if not parser:
                    continue

                rel_path = str(full_path.relative_to(repo_path))

                # Check file size limit
                try:
                    file_size = full_path.stat().st_size
                except OSError:
                    continue

                if file_size > MAX_PARSEABLE_FILE_SIZE_BYTES:
                    logger.info("Skipping overly large file %s (%d bytes)", rel_path, file_size)
                    continue

                # Read source code safely
                try:
                    content = full_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        content = full_path.read_text(encoding="latin-1")
                    except Exception as read_exc:
                        parse_errors.append(
                            FileParseError(
                                path=rel_path,
                                language=language,
                                error_type="EncodingError",
                                message=f"Unable to read file content: {read_exc}",
                            )
                        )
                        continue

                # Parse AST with defensive error handling (never crash whole repo analysis)
                try:
                    entities, imports = parser.parse_source(content, rel_path, language)
                except SyntaxError as syn_exc:
                    logger.warning("Syntax error parsing %s: %s", rel_path, syn_exc)
                    parse_errors.append(
                        FileParseError(
                            path=rel_path,
                            language=language,
                            error_type="SyntaxError",
                            message=f"Line {syn_exc.lineno}: {syn_exc.msg}" if syn_exc.lineno else str(syn_exc),
                        )
                    )
                    continue
                except Exception as parse_exc:
                    logger.warning("Error parsing %s: %s", rel_path, parse_exc)
                    parse_errors.append(
                        FileParseError(
                            path=rel_path,
                            language=language,
                            error_type=type(parse_exc).__name__,
                            message=str(parse_exc),
                        )
                    )
                    continue

                lines_count = len(content.splitlines())
                code_file = CodeFile(
                    path=rel_path,
                    language=language,
                    size_bytes=file_size,
                    lines=lines_count,
                    entities=entities,
                    imports=imports,
                )

                analyzed_files.append(code_file)
                all_entities.extend(entities)
                all_imports.extend(imports)

                language_file_counts[language] = language_file_counts.get(language, 0) + 1

                # Update counts
                for entity in entities:
                    if entity.type == "class":
                        total_classes += 1
                    elif entity.type == "function":
                        total_functions += 1
                    elif entity.type == "method":
                        total_methods += 1
                    elif entity.type == "interface":
                        total_interfaces += 1
                    elif entity.type == "type_alias":
                        total_types += 1

        # 2. Analyze imports and dependency relationships
        dependencies = self._resolve_dependencies(analyzed_files)

        # 3. Construct hierarchical codebase map
        codebase_tree = CodebaseTreeBuilder.build_codebase_tree(analyzed_files)

        # 4. Assemble quantitative summary
        summary = CodebaseSummary(
            files_analyzed=len(analyzed_files),
            languages=dict(sorted(language_file_counts.items(), key=lambda i: i[1], reverse=True)),
            classes=total_classes,
            functions=total_functions,
            methods=total_methods,
            imports=len(all_imports),
            interfaces=total_interfaces,
            types=total_types,
            files_with_errors=len(parse_errors),
        )

        return summary, analyzed_files, all_entities, dependencies, codebase_tree, parse_errors

    def _resolve_dependencies(
        self, code_files: List[CodeFile]
    ) -> List[DependencyRelation]:
        """Identify internal vs external dependencies across the parsed files."""
        # Index all internal file paths
        known_paths: Set[str] = {cf.path for cf in code_files}

        # Dotted python path lookups (e.g. 'app.services.user' -> 'app/services/user.py')
        python_module_map: Dict[str, str] = {}
        # Path without extension lookups for JS/TS (e.g. 'lib/api' -> 'lib/api.ts')
        no_ext_map: Dict[str, str] = {}

        for p in known_paths:
            path_obj = Path(p)
            ext = path_obj.suffix.lower()
            without_ext = str(path_obj.with_suffix(""))
            no_ext_map[without_ext] = p

            if ext in (".py", ".pyw"):
                dotted = p.replace("/", ".").replace("\\", ".")
                if dotted.endswith(".py"):
                    dotted = dotted[:-3]
                python_module_map[dotted] = p
                # Also support package __init__.py index
                if dotted.endswith(".__init__"):
                    pkg_dotted = dotted[:-9]
                    python_module_map[pkg_dotted] = p

        relations: List[DependencyRelation] = []

        for cf in code_files:
            source_dir = Path(cf.path).parent

            for imp in cf.imports:
                target = imp.module
                resolved_file: Optional[str] = None
                is_internal = False

                if cf.language == "Python":
                    # Check relative python import (e.g. from .utils import ...)
                    if imp.is_relative:
                        # Construct candidate path relative to current file directory
                        candidate_rel = (source_dir / target.replace(".", "/")).as_posix() if target else source_dir.as_posix()
                        if f"{candidate_rel}.py" in known_paths:
                            resolved_file = f"{candidate_rel}.py"
                            is_internal = True
                        elif f"{candidate_rel}/__init__.py" in known_paths:
                            resolved_file = f"{candidate_rel}/__init__.py"
                            is_internal = True
                    else:
                        # Check dotted python lookup
                        if target in python_module_map:
                            resolved_file = python_module_map[target]
                            is_internal = True
                        else:
                            # Check prefix matches (e.g. import app.services)
                            parts = target.split(".")
                            for i in range(len(parts), 0, -1):
                                sub = ".".join(parts[:i])
                                if sub in python_module_map:
                                    resolved_file = python_module_map[sub]
                                    is_internal = True
                                    break

                elif cf.language in ("JavaScript", "TypeScript"):
                    # Check relative JS/TS import (e.g. './api' or '../components/Hero')
                    if imp.is_relative:
                        # Resolve path relative to source directory
                        norm_target = (source_dir / target).resolve()
                        # Reconstruct relative to repo root if possible
                        try:
                            # Target without extension
                            cand_no_ext = (source_dir / target).as_posix()
                            cand_clean = os.path.normpath(cand_no_ext)
                            if cand_clean in no_ext_map:
                                resolved_file = no_ext_map[cand_clean]
                                is_internal = True
                            elif f"{cand_clean}/index" in no_ext_map:
                                resolved_file = no_ext_map[f"{cand_clean}/index"]
                                is_internal = True
                        except Exception:
                            pass

                relations.append(
                    DependencyRelation(
                        source_file=cf.path,
                        target_module=target,
                        imported_symbols=imp.imported_names,
                        resolved_target_file=resolved_file,
                        is_internal=is_internal,
                    )
                )

        return relations

    @staticmethod
    def _detect_language(extension: str) -> Optional[str]:
        """Map supported source file extension to canonical language name."""
        ext = extension.lower()
        if ext in (".py", ".pyw"):
            return "Python"
        elif ext in (".js", ".jsx", ".mjs", ".cjs"):
            return "JavaScript"
        elif ext in (".ts", ".tsx"):
            return "TypeScript"
        return None
