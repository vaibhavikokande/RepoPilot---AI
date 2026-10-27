"""Repository context collector for AI technical documentation generation."""

import ast
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.doc_generator.models import (
    CollectedDocContext,
    DiscoveredRoute,
    DiscoveredSymbol,
    DocTargetNotFoundError,
    DocType,
    DocValidationError,
)

logger = logging.getLogger(__name__)

# File and directory ignore patterns
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    "chroma_db",
    ".idea",
    ".vscode",
}

MANIFEST_FILES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "Pipfile",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Dockerfile",
    "docker-compose.yml",
}

DOC_FILES = {
    "README.md",
    "README",
    "CONTRIBUTING.md",
    "LICENSE",
    "docs/architecture.md",
}

# Regex patterns for API route detection
PYTHON_ROUTE_RE = re.compile(
    r"@(?:router|app)\.(get|post|put|delete|patch|options|head)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
JS_ROUTE_RE = re.compile(
    r"(?:router|app)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

# Regex for environment variables
ENV_VAR_RE = re.compile(
    r"(?:os\.environ(?:\.get\(|\[)|os\.getenv\(|process\.env\.)[\"']([A-Z0-9_]{3,})[\"']|process\.env\.([A-Z0-9_]{3,})"
)

MAX_MANIFEST_CHARS = 4000
MAX_DOC_CHARS = 4000
MAX_SOURCE_CHARS = 10000


class ContextCollector:
    """Discovers, parses, and formats repository evidence for documentation synthesis."""

    def validate_and_resolve_path(self, repo_path: Path, raw_path: str) -> Path:
        """Validate relative file or directory path within repository boundaries.

        Raises:
            DocValidationError: If path traversal or escape is attempted.
            DocTargetNotFoundError: If path does not exist.
        """
        if not raw_path or not raw_path.strip():
            raise DocValidationError("Path cannot be empty.")

        clean = raw_path.strip().replace("\\", "/")
        if ".." in clean.split("/") or clean.startswith("/"):
            raise DocValidationError(f"Invalid path traversal: '{raw_path}' escapes repository boundary.")

        resolved = (repo_path / clean).resolve()
        try:
            resolved.relative_to(repo_path.resolve())
        except ValueError as exc:
            raise DocValidationError(f"Security error: '{raw_path}' is outside repository root.") from exc

        if not resolved.exists():
            raise DocTargetNotFoundError(f"Target path '{raw_path}' not found in repository.")

        return resolved

    def _generate_tree_summary(self, repo_path: Path, max_depth: int = 3) -> str:
        """Generate a condensed text outline of repository directory structure."""
        lines = []

        def _walk(current: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth or len(lines) >= 60:
                return

            try:
                entries = sorted(
                    [e for e in current.iterdir() if e.name not in IGNORED_DIRS],
                    key=lambda x: (not x.is_dir(), x.name.lower()),
                )
            except Exception:
                return

            for i, entry in enumerate(entries):
                if len(lines) >= 60:
                    lines.append(f"{prefix}└── ... (truncated)")
                    break

                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    _walk(entry, prefix + sub_prefix, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")

        _walk(repo_path)
        return "\n".join(lines)

    def _discover_routes_in_file(
        self, file_path: Path, rel_path: str
    ) -> List[DiscoveredRoute]:
        """Discover HTTP API route definitions in Python or JS/TS file."""
        routes: List[DiscoveredRoute] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return routes

        lines = content.splitlines()

        if file_path.suffix.lower() == ".py":
            for idx, line in enumerate(lines, start=1):
                match = PYTHON_ROUTE_RE.search(line)
                if match:
                    method = match.group(1).upper()
                    path = match.group(2)
                    # Find function name on subsequent lines
                    handler = "handler"
                    docstring = None
                    for next_line in lines[idx : idx + 6]:
                        fn_match = re.search(r"def\s+([A-Za-z0-9_]+)\s*\(", next_line)
                        if fn_match:
                            handler = fn_match.group(1)
                            break
                    routes.append(
                        DiscoveredRoute(
                            method=method,
                            path=path,
                            handler_name=handler,
                            file_path=rel_path,
                            line_number=idx,
                            docstring=docstring,
                        )
                    )
        elif file_path.suffix.lower() in (".js", ".ts", ".jsx", ".tsx"):
            for idx, line in enumerate(lines, start=1):
                match = JS_ROUTE_RE.search(line)
                if match:
                    method = match.group(1).upper()
                    path = match.group(2)
                    routes.append(
                        DiscoveredRoute(
                            method=method,
                            path=path,
                            handler_name="route_handler",
                            file_path=rel_path,
                            line_number=idx,
                        )
                    )

        return routes

    def _discover_symbols_in_python(
        self, file_path: Path, rel_path: str
    ) -> List[DiscoveredSymbol]:
        """Extract classes and functions from a Python file via AST."""
        symbols: List[DiscoveredSymbol] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except Exception:
            return symbols

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                # Form signature string
                args = [a.arg for a in node.args.args]
                sig = f"def {node.name}({', '.join(args)})"
                symbols.append(
                    DiscoveredSymbol(
                        name=node.name,
                        symbol_type="function",
                        file_path=rel_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        signature=sig,
                        docstring=doc,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                symbols.append(
                    DiscoveredSymbol(
                        name=node.name,
                        symbol_type="class",
                        file_path=rel_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        signature=f"class {node.name}",
                        docstring=doc,
                    )
                )
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(item)
                        args = [a.arg for a in item.args.args]
                        symbols.append(
                            DiscoveredSymbol(
                                name=f"{node.name}.{item.name}",
                                symbol_type="method",
                                file_path=rel_path,
                                start_line=item.lineno,
                                end_line=getattr(item, "end_lineno", item.lineno),
                                signature=f"def {item.name}({', '.join(args)})",
                                docstring=method_doc,
                            )
                        )

        return symbols

    def _scan_environment_variables(self, repo_path: Path) -> List[str]:
        """Scan codebase for environment variable references."""
        env_vars: Set[str] = set()

        for ext in ("*.py", "*.js", "*.ts", "*.json", "*.env.example"):
            for p in repo_path.glob(f"**/{ext}"):
                if any(ignored in p.parts for ignored in IGNORED_DIRS):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    for m in ENV_VAR_RE.finditer(text):
                        var = m.group(1) or m.group(2)
                        if var and len(var) >= 3 and not var.startswith("_"):
                            env_vars.add(var)
                except Exception:
                    continue

        return sorted(list(env_vars))[:25]

    def _detect_test_frameworks(self, repo_path: Path) -> List[str]:
        """Detect testing tools configured in the repository."""
        frameworks: Set[str] = set()

        if (repo_path / "pytest.ini").exists() or (repo_path / "tests").exists():
            frameworks.add("pytest")
        if (repo_path / "package.json").exists():
            try:
                pkg_text = (repo_path / "package.json").read_text(encoding="utf-8")
                if "jest" in pkg_text:
                    frameworks.add("jest")
                if "vitest" in pkg_text:
                    frameworks.add("vitest")
                if "playwright" in pkg_text:
                    frameworks.add("playwright")
            except Exception:
                pass

        return sorted(list(frameworks))

    def collect_context(
        self,
        repo_path: Path,
        doc_type: DocType,
        target_path: Optional[str] = None,
        target_symbol: Optional[str] = None,
    ) -> CollectedDocContext:
        """Gather evidence from repository tailored to doc_type."""
        source_files_used: Set[str] = set()
        missing_elements: List[str] = []

        # 1. Collect manifests
        manifests: Dict[str, str] = {}
        for manifest_name in MANIFEST_FILES:
            mf = repo_path / manifest_name
            if mf.is_file():
                try:
                    content = mf.read_text(encoding="utf-8", errors="replace")[:MAX_MANIFEST_CHARS]
                    manifests[manifest_name] = content
                    source_files_used.add(manifest_name)
                except Exception:
                    pass

        # 2. Collect existing documentation
        existing_docs: Dict[str, str] = {}
        for doc_name in DOC_FILES:
            df = repo_path / doc_name
            if df.is_file():
                try:
                    content = df.read_text(encoding="utf-8", errors="replace")[:MAX_DOC_CHARS]
                    existing_docs[doc_name] = content
                    source_files_used.add(doc_name)
                except Exception:
                    pass

        # 3. Directory tree summary
        tree_summary = self._generate_tree_summary(repo_path)

        # 4. Route and Symbol Discovery across core source files
        discovered_routes: List[DiscoveredRoute] = []
        discovered_symbols: List[DiscoveredSymbol] = []

        code_extensions = (".py", ".js", ".ts", ".jsx", ".tsx")
        scanned_count = 0

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                if any(file.endswith(ext) for ext in code_extensions):
                    file_p = Path(root) / file
                    try:
                        rel_p = str(file_p.relative_to(repo_path)).replace("\\", "/")
                    except ValueError:
                        continue

                    # Discover API routes
                    routes = self._discover_routes_in_file(file_p, rel_p)
                    if routes:
                        discovered_routes.extend(routes)
                        source_files_used.add(rel_p)

                    # Discover code symbols
                    if file.endswith(".py") and scanned_count < 25:
                        syms = self._discover_symbols_in_python(file_p, rel_p)
                        if syms:
                            discovered_symbols.extend(syms)
                            source_files_used.add(rel_p)
                        scanned_count += 1

        # 5. Environment variables and test tools
        env_vars = self._scan_environment_variables(repo_path)
        test_frameworks = self._detect_test_frameworks(repo_path)

        # 6. Specific target handling (for MODULE and FUNCTION_REFERENCE)
        target_content = None
        if target_path:
            resolved_target = self.validate_and_resolve_path(repo_path, target_path)
            clean_rel = str(resolved_target.relative_to(repo_path)).replace("\\", "/")
            source_files_used.add(clean_rel)

            if resolved_target.is_file():
                try:
                    raw = resolved_target.read_text(encoding="utf-8", errors="replace")
                    target_content = raw[:MAX_SOURCE_CHARS]
                except Exception as exc:
                    logger.warning("Could not read target file %s: %s", target_path, exc)
            elif resolved_target.is_dir():
                target_content = self._generate_tree_summary(resolved_target, max_depth=2)

        if target_symbol:
            # Look for the target symbol among discovered symbols
            matching_sym = next((s for s in discovered_symbols if s.name == target_symbol), None)
            if not matching_sym and target_content:
                # Search directly in target file content
                match = re.search(
                    rf"(?:def|class)\s+{re.escape(target_symbol)}\s*\(.*?\)(?::|\s*\{{)",
                    target_content,
                    re.DOTALL,
                )
                if not match:
                    missing_elements.append(f"Symbol '{target_symbol}' was not found in scanned sources.")
            elif not matching_sym:
                missing_elements.append(f"Symbol '{target_symbol}' was not found in scanned symbols.")

        return CollectedDocContext(
            doc_type=doc_type,
            manifest_files=manifests,
            existing_docs=existing_docs,
            file_tree_summary=tree_summary,
            discovered_routes=discovered_routes[:40],
            discovered_symbols=discovered_symbols[:50],
            environment_vars=env_vars,
            test_frameworks=test_frameworks,
            target_content=target_content,
            source_files_used=sorted(list(source_files_used)),
            missing_elements=missing_elements,
        )
