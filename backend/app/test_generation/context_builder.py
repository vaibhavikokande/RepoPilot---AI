"""Context builder: locates target function/method in repository AST and retrieves relevant context."""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.schemas.test_generation import TestTarget

logger = logging.getLogger(__name__)

# Maximum characters of context to prevent LLM prompt overflow
MAX_CONTEXT_CHARACTERS = 8000


class ContextBuilderError(Exception):
    """Base error for test generation context retrieval."""
    pass


class EntityNotFoundError(ContextBuilderError):
    """Raised when the specified function or method cannot be found in the file."""
    pass


class UnsupportedLanguageError(ContextBuilderError):
    """Raised when an unsupported language file is requested for test generation."""
    pass


@dataclass
class TargetContext:
    """Rich source and dependency context for test generation."""

    target: TestTarget
    function_source: str
    import_statement: str
    class_context: Optional[str] = None
    module_imports: List[str] = field(default_factory=list)
    helper_snippets: List[str] = field(default_factory=list)
    relative_module_path: str = ""


class ContextBuilder:
    """Locates and extracts target entities and supporting context from Python source files."""

    def build_context(
        self,
        repo_path: Path,
        file_path: str,
        entity_name: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> TargetContext:
        """Extract function source, signature, enclosing class, and module context.

        Args:
            repo_path: Root Path of the cloned repository.
            file_path: Relative path to the target file.
            entity_name: Name of the function or method.
            start_line: Optional 1-indexed starting line to disambiguate.
            end_line: Optional 1-indexed ending line.

        Returns:
            TargetContext populated with target metadata and bounded source snippets.
        """
        # 1. Verify file path safety and existence
        safe_rel_path = Path(file_path).as_posix().lstrip("/")
        full_path = (repo_path / safe_rel_path).resolve()

        try:
            full_path.relative_to(repo_path.resolve())
        except ValueError as exc:
            raise ContextBuilderError(f"File path '{file_path}' traverses outside repository boundary.") from exc

        if not full_path.exists() or not full_path.is_file():
            raise FileNotFoundError(f"Source file '{file_path}' does not exist in repository.")

        if full_path.suffix.lower() != ".py":
            raise UnsupportedLanguageError(
                f"Test generation currently supports Python (.py) files. '{file_path}' has extension '{full_path.suffix}'."
            )

        # 2. Read file content safely
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise ContextBuilderError(f"Could not read source file '{file_path}': {exc}") from exc

        file_lines = content.splitlines(keepends=True)

        # 3. Parse AST to locate entity
        try:
            tree = ast.parse(content, filename=safe_rel_path)
        except SyntaxError as syn_err:
            raise EntityNotFoundError(
                f"File '{file_path}' contains syntax errors on line {syn_err.lineno}: {syn_err.msg}"
            ) from syn_err

        # 4. Extract module-level imports
        module_imports: List[str] = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imp_text = "".join(file_lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)]).strip()
                if imp_text:
                    module_imports.append(imp_text)

        # 5. Search for target entity (functions and class methods)
        found_target: Optional[TestTarget] = None
        target_node: Optional[ast.AST] = None
        enclosing_class_node: Optional[ast.ClassDef] = None

        # Check module-level functions
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == entity_name:
                    if start_line is None or node.lineno == start_line:
                        target_node = node
                        found_target = TestTarget(
                            file_path=safe_rel_path,
                            entity_name=node.name,
                            entity_type="function",
                            parent_class=None,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            signature=self._extract_signature(file_lines, node),
                            docstring=ast.get_docstring(node),
                        )
                        break

            # Check classes for methods
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name == entity_name:
                            if start_line is None or item.lineno == start_line:
                                target_node = item
                                enclosing_class_node = node
                                found_target = TestTarget(
                                    file_path=safe_rel_path,
                                    entity_name=item.name,
                                    entity_type="method",
                                    parent_class=node.name,
                                    start_line=item.lineno,
                                    end_line=getattr(item, "end_lineno", item.lineno),
                                    signature=self._extract_signature(file_lines, item),
                                    docstring=ast.get_docstring(item),
                                )
                                break
                if found_target:
                    break

        if not found_target or not target_node:
            raise EntityNotFoundError(
                f"Function or method '{entity_name}' was not found in '{safe_rel_path}'."
            )

        # 6. Extract function source lines
        func_source = "".join(
            file_lines[found_target.start_line - 1 : found_target.end_line]
        ).strip()

        # 7. Extract class context if target is a method
        class_context_str: Optional[str] = None
        if enclosing_class_node:
            # Capture class declaration and __init__ if present
            class_lines = file_lines[enclosing_class_node.lineno - 1 :]
            # Locate __init__ or class header
            init_code = ""
            for item in enclosing_class_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                    init_code = "".join(
                        file_lines[item.lineno - 1 : getattr(item, "end_lineno", item.lineno)]
                    ).strip()
                    break

            class_header = file_lines[enclosing_class_node.lineno - 1].strip()
            class_doc = ast.get_docstring(enclosing_class_node) or ""
            class_context_str = f"class {enclosing_class_node.name}:\n"
            if class_doc:
                class_context_str += f'    """{class_doc}"""\n'
            if init_code:
                class_context_str += f"    {init_code}\n"

        # 8. Compute module import statement
        module_path = safe_rel_path.replace(".py", "").replace("/", ".").replace("\\", ".")
        # Strip potential leading package prefixes like 'src.' if helpful
        if found_target.entity_type == "method" and found_target.parent_class:
            import_statement = f"from {module_path} import {found_target.parent_class}"
        else:
            import_statement = f"from {module_path} import {found_target.entity_name}"

        # 9. Collect small helper functions in the same file if bounded
        helper_snippets: List[str] = []
        current_len = len(func_source)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != entity_name:
                snippet = "".join(
                    file_lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)]
                ).strip()
                if len(snippet) < 600 and current_len + len(snippet) < MAX_CONTEXT_CHARACTERS:
                    helper_snippets.append(snippet)
                    current_len += len(snippet)

        return TargetContext(
            target=found_target,
            function_source=func_source,
            import_statement=import_statement,
            class_context=class_context_str,
            module_imports=module_imports,
            helper_snippets=helper_snippets,
            relative_module_path=module_path,
        )

    def _extract_signature(self, lines: List[str], node: ast.AST) -> str:
        """Extract signature line from source lines."""
        try:
            start_idx = node.lineno - 1
            sig_lines = []
            for i in range(start_idx, min(start_idx + 6, len(lines))):
                line = lines[i]
                sig_lines.append(line.strip())
                if ":" in line:
                    break
            return " ".join(sig_lines)
        except Exception:
            return f"def {getattr(node, 'name', 'target')}(...)"
