"""Tests for the Code Intelligence Engine: parsers, tree builder, and analyzer."""

import tempfile
from pathlib import Path

from app.code_intelligence.analyzer import CodeIntelligenceAnalyzer
from app.code_intelligence.parser import JavaScriptTypeScriptParser, PythonParser
from app.code_intelligence.tree_builder import CodebaseTreeBuilder


class TestPythonParser:
    """Test suite for Python AST parsing."""

    def test_extract_classes_methods_and_functions(self) -> None:
        code = '''"""Module docstring."""
import math
from typing import List, Optional

API_KEY = "xyz"

@decorator_one
class Calculator:
    """A simple calculator."""

    def __init__(self, precision: int = 2):
        """Init doc."""
        self.precision = precision

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return round(a + b, self.precision)

    def _internal_helper(self):
        pass

def standalone_helper(x: int) -> bool:
    """Check value."""
    return x > 0

async def async_fetch_data(url: str) -> dict:
    return {}
'''
        parser = PythonParser()
        entities, imports = parser.parse_source(code, "services/calc.py", "Python")

        # 1. Imports
        assert len(imports) == 2
        assert imports[0].module == "math"
        assert imports[1].module == "typing"
        assert "List" in imports[1].imported_names

        # 2. Classes
        classes = [e for e in entities if e.type == "class"]
        assert len(classes) == 1
        calc_class = classes[0]
        assert calc_class.name == "Calculator"
        assert calc_class.docstring == "A simple calculator."
        assert calc_class.start_line == 8
        assert calc_class.end_line >= 19
        assert "@decorator_one" in calc_class.decorators

        # 3. Methods
        methods = [e for e in entities if e.type == "method"]
        assert len(methods) == 3
        method_names = [m.name for m in methods]
        assert "__init__" in method_names
        assert "add" in method_names
        assert "_internal_helper" in method_names

        add_method = next(m for m in methods if m.name == "add")
        assert add_method.parent == "Calculator"
        assert add_method.docstring == "Add two numbers."
        assert "def add(self, a: float, b: float) -> float" in (add_method.signature or "")
        assert add_method.visibility == "public"

        helper_method = next(m for m in methods if m.name == "_internal_helper")
        assert helper_method.visibility == "protected"

        # 4. Top-level functions
        functions = [e for e in entities if e.type == "function"]
        assert len(functions) == 2
        func_names = [f.name for f in functions]
        assert "standalone_helper" in func_names
        assert "async_fetch_data" in func_names

        helper_func = next(f for f in functions if f.name == "standalone_helper")
        assert helper_func.docstring == "Check value."
        assert helper_func.parent is None
        assert helper_func.return_type == "bool"

        async_func = next(f for f in functions if f.name == "async_fetch_data")
        assert "async def async_fetch_data" in (async_func.signature or "")

        # 5. Constants / variables
        variables = [e for e in entities if e.type == "variable"]
        assert len(variables) >= 1
        assert any(v.name == "API_KEY" for v in variables)


class TestJavaScriptTypeScriptParser:
    """Test suite for JavaScript and TypeScript parsing via Tree-sitter."""

    def test_typescript_parsing(self) -> None:
        code = '''import { useState, useEffect } from 'react';
import axios from 'axios';

export interface UserDTO {
  id: number;
  name: string;
}

export type UserRole = "admin" | "viewer";

export class UserService {
  getUser(id: number): UserDTO {
    return { id, name: "Alice" };
  }
}

export function formatUserName(user: UserDTO): string {
  return user.name.toUpperCase();
}

export const helperArrow = (x: number) => x * 2;
'''
        parser = JavaScriptTypeScriptParser()
        entities, imports = parser.parse_source(code, "src/userService.ts", "TypeScript")

        # 1. Imports
        assert len(imports) == 2
        assert any(i.module == "react" for i in imports)
        assert any(i.module == "axios" for i in imports)

        # 2. Interface
        interfaces = [e for e in entities if e.type == "interface"]
        assert len(interfaces) == 1
        assert interfaces[0].name == "UserDTO"
        assert interfaces[0].start_line >= 4

        # 3. Type alias
        types = [e for e in entities if e.type == "type_alias"]
        assert len(types) == 1
        assert types[0].name == "UserRole"

        # 4. Class & methods
        classes = [e for e in entities if e.type == "class"]
        assert len(classes) == 1
        assert classes[0].name == "UserService"

        methods = [e for e in entities if e.type == "method"]
        assert len(methods) == 1
        assert methods[0].name == "getUser"
        assert methods[0].parent == "UserService"

        # 5. Functions (declaration & arrow)
        functions = [e for e in entities if e.type == "function"]
        func_names = [f.name for f in functions]
        assert "formatUserName" in func_names
        assert "helperArrow" in func_names


class TestAnalyzerAndTreeBuilder:
    """Test suite for CodeIntelligenceAnalyzer and CodebaseTreeBuilder."""

    def test_analyzer_on_sample_repo(self, sample_repo_path: Path) -> None:
        analyzer = CodeIntelligenceAnalyzer()
        (
            summary,
            files,
            entities,
            dependencies,
            tree,
            errors,
        ) = analyzer.analyze_repository(sample_repo_path)

        assert summary.files_analyzed >= 3  # app/main.py, app/services.py, frontend/index.ts, tests/test_main.py
        assert summary.classes >= 2  # UserService, UserClient
        assert summary.functions >= 2  # create_app, render, test_create_app
        assert summary.methods >= 3  # __init__, get_status, create_user, getUser
        assert summary.imports >= 3
        assert summary.files_with_errors == 0
        assert len(errors) == 0

        # Check dependencies
        internal_deps = [d for d in dependencies if d.is_internal]
        assert len(internal_deps) > 0

        # Check tree
        assert len(tree) > 0
        root_dir_names = {node.name for node in tree}
        assert "app" in root_dir_names or "frontend" in root_dir_names

    def test_analyzer_handles_syntax_error_gracefully(self) -> None:
        """Invalid syntax should be caught as FileParseError and not crash analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Valid file
            (temp_path / "good.py").write_text("def ok(): pass\n", encoding="utf-8")
            # File with blatant syntax error
            (temp_path / "bad.py").write_text("def broken(x\n  print 1 2 3\n", encoding="utf-8")

            analyzer = CodeIntelligenceAnalyzer()
            summary, files, entities, deps, tree, errors = analyzer.analyze_repository(temp_path)

            assert summary.files_analyzed == 1
            assert summary.files_with_errors == 1
            assert len(errors) == 1
            assert errors[0].path == "bad.py"
            assert errors[0].error_type == "SyntaxError"
            assert len(entities) == 1
            assert entities[0].name == "ok"
