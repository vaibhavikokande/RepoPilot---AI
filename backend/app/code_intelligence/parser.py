"""AST-based source code parsers for Python, JavaScript, and TypeScript."""

import ast
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

from app.code_intelligence.models import CodeEntity, CodeImport

logger = logging.getLogger(__name__)

# Tree-sitter imports (lazy-loaded or conditional fallback)
_TREE_SITTER_AVAILABLE = False
try:
    from tree_sitter import Language, Node, Parser
    import tree_sitter_javascript as ts_js
    import tree_sitter_typescript as ts_ts

    _JS_LANGUAGE = Language(ts_js.language())
    _TS_LANGUAGE = Language(ts_ts.language_typescript())
    _TSX_LANGUAGE = Language(ts_ts.language_tsx())
    _TREE_SITTER_AVAILABLE = True
except Exception as ts_exc:
    logger.warning("Tree-sitter parser initialization error: %s", ts_exc)


class BaseCodeParser(ABC):
    """Abstract base class for language-specific AST parsers."""

    @abstractmethod
    def can_parse(self, language: str, file_path: Path) -> bool:
        """Return True if this parser can process the given language and path."""
        pass

    @abstractmethod
    def parse_source(
        self, content: str, relative_path: str, language: str
    ) -> Tuple[List[CodeEntity], List[CodeImport]]:
        """Parse source code string into structured entities and imports."""
        pass


class PythonParser(BaseCodeParser):
    """Parser for Python source code using standard library ast module."""

    SUPPORTED_EXTENSIONS = {".py", ".pyw"}

    def can_parse(self, language: str, file_path: Path) -> bool:
        return language.lower() == "python" or file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse_source(
        self, content: str, relative_path: str, language: str = "Python"
    ) -> Tuple[List[CodeEntity], List[CodeImport]]:
        entities: List[CodeEntity] = []
        imports: List[CodeImport] = []

        # Parse AST; syntax errors raise SyntaxError
        tree = ast.parse(content, filename=relative_path)

        def _format_expr(node: Optional[ast.AST]) -> Optional[str]:
            if node is None:
                return None
            try:
                return ast.unparse(node)
            except Exception:
                return None

        def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
            prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
            params = []
            for arg in node.args.args:
                p = arg.arg
                if arg.annotation:
                    ann = _format_expr(arg.annotation)
                    if ann:
                        p += f": {ann}"
                params.append(p)

            if node.args.vararg:
                params.append(f"*{node.args.vararg.arg}")
            if node.args.kwarg:
                params.append(f"**{node.args.kwarg.arg}")

            sig = f"{prefix}{node.name}({', '.join(params)})"
            if node.returns:
                ret = _format_expr(node.returns)
                if ret:
                    sig += f" -> {ret}"
            return sig

        def _get_decorators(decorator_list: List[ast.expr]) -> List[str]:
            decs = []
            for dec in decorator_list:
                s = _format_expr(dec)
                if s:
                    decs.append(f"@{s}")
            return decs

        def _get_visibility(name: str) -> str:
            if name.startswith("__") and not name.endswith("__"):
                return "private"
            if name.startswith("_"):
                return "protected"
            return "public"

        for node in tree.body:
            # 1. Top-level Classes
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                class_entity = CodeEntity(
                    name=node.name,
                    type="class",
                    file_path=relative_path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    signature=f"class {node.name}" + (
                        f"({', '.join(_format_expr(b) or '' for b in node.bases)})"
                        if node.bases else ""
                    ),
                    docstring=docstring,
                    parent=None,
                    decorators=_get_decorators(node.decorator_list),
                    visibility=_get_visibility(node.name),
                )
                entities.append(class_entity)

                # Class methods
                for class_child in node.body:
                    if isinstance(class_child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(class_child)
                        method_params = [a.arg for a in class_child.args.args]
                        method_entity = CodeEntity(
                            name=class_child.name,
                            type="method",
                            file_path=relative_path,
                            start_line=class_child.lineno,
                            end_line=getattr(class_child, "end_lineno", class_child.lineno),
                            signature=_format_signature(class_child),
                            docstring=method_doc,
                            parent=node.name,
                            decorators=_get_decorators(class_child.decorator_list),
                            parameters=method_params,
                            return_type=_format_expr(class_child.returns),
                            visibility=_get_visibility(class_child.name),
                        )
                        entities.append(method_entity)

            # 2. Top-level Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_doc = ast.get_docstring(node)
                func_params = [a.arg for a in node.args.args]
                func_entity = CodeEntity(
                    name=node.name,
                    type="function",
                    file_path=relative_path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    signature=_format_signature(node),
                    docstring=func_doc,
                    parent=None,
                    decorators=_get_decorators(node.decorator_list),
                    parameters=func_params,
                    return_type=_format_expr(node.returns),
                    visibility=_get_visibility(node.name),
                )
                entities.append(func_entity)

            # 3. Import statements
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        CodeImport(
                            module=alias.name,
                            imported_names=[alias.name],
                            alias=alias.asname,
                            is_relative=False,
                            line_number=node.lineno,
                            source_file=relative_path,
                        )
                    )

            # 4. ImportFrom statements
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                is_rel = node.level > 0
                names = [alias.name for alias in node.names]
                imports.append(
                    CodeImport(
                        module=module_name,
                        imported_names=names,
                        alias=node.names[0].asname if len(node.names) == 1 else None,
                        is_relative=is_rel,
                        line_number=node.lineno,
                        source_file=relative_path,
                    )
                )

            # 5. Top-level Constants & Variables
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and (target.id.isupper() or len(target.id) > 1):
                        entities.append(
                            CodeEntity(
                                name=target.id,
                                type="variable",
                                file_path=relative_path,
                                start_line=node.lineno,
                                end_line=getattr(node, "end_lineno", node.lineno),
                                signature=f"{target.id} = ...",
                                parent=None,
                                visibility="public",
                            )
                        )
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    ann_str = _format_expr(node.annotation) or "Any"
                    entities.append(
                        CodeEntity(
                            name=node.target.id,
                            type="variable",
                            file_path=relative_path,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            signature=f"{node.target.id}: {ann_str}",
                            return_type=ann_str,
                            parent=None,
                            visibility="public",
                        )
                    )

        return entities, imports


class JavaScriptTypeScriptParser(BaseCodeParser):
    """Parser for JavaScript and TypeScript using tree-sitter grammars."""

    SUPPORTED_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}

    def can_parse(self, language: str, file_path: Path) -> bool:
        if not _TREE_SITTER_AVAILABLE:
            return False
        lang_lower = language.lower()
        return (
            lang_lower in ("javascript", "typescript")
            or file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

    def _get_tree_sitter_parser(self, file_path: str, language: str) -> Optional[Parser]:
        if not _TREE_SITTER_AVAILABLE:
            return None

        ext = Path(file_path).suffix.lower()
        if ext == ".tsx":
            return Parser(_TSX_LANGUAGE)
        elif ext in (".ts",) or language.lower() == "typescript":
            return Parser(_TS_LANGUAGE)
        else:
            return Parser(_JS_LANGUAGE)

    def parse_source(
        self, content: str, relative_path: str, language: str
    ) -> Tuple[List[CodeEntity], List[CodeImport]]:
        if not _TREE_SITTER_AVAILABLE:
            return [], []

        ts_parser = self._get_tree_sitter_parser(relative_path, language)
        if not ts_parser:
            return [], []

        entities: List[CodeEntity] = []
        imports: List[CodeImport] = []

        content_bytes = content.encode("utf-8")
        tree = ts_parser.parse(content_bytes)
        root = tree.root_node

        def _node_text(n: Optional[Node]) -> str:
            if n is None:
                return ""
            return content_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace")

        def _get_line_numbers(n: Node) -> Tuple[int, int]:
            return n.start_point[0] + 1, n.end_point[0] + 1

        def _traverse(node: Node, parent_class: Optional[str] = None):
            node_type = node.type

            # 1. Function Declaration
            if node_type == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = _node_text(name_node) or "anonymous"
                start_l, end_l = _get_line_numbers(node)
                params_node = node.child_by_field_name("parameters")
                params_text = _node_text(params_node)
                ret_node = node.child_by_field_name("return_type")
                ret_type = _node_text(ret_node) or None

                sig = f"function {name}{params_text}"
                if ret_type:
                    sig += f": {ret_type}"

                entities.append(
                    CodeEntity(
                        name=name,
                        type="function",
                        file_path=relative_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig,
                        parent=None,
                        return_type=ret_type,
                    )
                )

            # 2. Class Declaration
            elif node_type == "class_declaration":
                name_node = node.child_by_field_name("name")
                class_name = _node_text(name_node) or "AnonymousClass"
                start_l, end_l = _get_line_numbers(node)

                entities.append(
                    CodeEntity(
                        name=class_name,
                        type="class",
                        file_path=relative_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=f"class {class_name}",
                        parent=None,
                    )
                )

                # Process methods inside class_body
                body_node = node.child_by_field_name("body")
                if body_node:
                    for child in body_node.children:
                        if child.type == "method_definition":
                            method_name_node = child.child_by_field_name("name")
                            m_name = _node_text(method_name_node) or "anonymousMethod"
                            m_start, m_end = _get_line_numbers(child)
                            m_params = _node_text(child.child_by_field_name("parameters"))
                            m_ret = _node_text(child.child_by_field_name("return_type")) or None

                            entities.append(
                                CodeEntity(
                                    name=m_name,
                                    type="method",
                                    file_path=relative_path,
                                    start_line=m_start,
                                    end_line=m_end,
                                    signature=f"{m_name}{m_params}" + (f": {m_ret}" if m_ret else ""),
                                    parent=class_name,
                                    return_type=m_ret,
                                )
                            )

            # 3. Interface Declaration (TypeScript)
            elif node_type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                interface_name = _node_text(name_node) or "AnonymousInterface"
                start_l, end_l = _get_line_numbers(node)

                entities.append(
                    CodeEntity(
                        name=interface_name,
                        type="interface",
                        file_path=relative_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=f"interface {interface_name}",
                        parent=None,
                    )
                )

            # 4. Type Alias (TypeScript)
            elif node_type == "type_alias_declaration":
                name_node = node.child_by_field_name("name")
                type_name = _node_text(name_node) or "AnonymousType"
                start_l, end_l = _get_line_numbers(node)

                entities.append(
                    CodeEntity(
                        name=type_name,
                        type="type_alias",
                        file_path=relative_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=f"type {type_name} = ...",
                        parent=None,
                    )
                )

            # 5. Variable declaration containing arrow functions (e.g. const handler = () => {})
            elif node_type in ("lexical_declaration", "variable_declaration"):
                for declarator in node.children:
                    if declarator.type == "variable_declarator":
                        name_node = declarator.child_by_field_name("name")
                        val_node = declarator.child_by_field_name("value")
                        if val_node and val_node.type in ("arrow_function", "function_expression"):
                            var_name = _node_text(name_node)
                            start_l, end_l = _get_line_numbers(declarator)
                            params_node = val_node.child_by_field_name("parameters")
                            params_text = _node_text(params_node) if params_node else "()"
                            ret_node = val_node.child_by_field_name("return_type")
                            ret_type = _node_text(ret_node) or None

                            entities.append(
                                CodeEntity(
                                    name=var_name,
                                    type="function",
                                    file_path=relative_path,
                                    start_line=start_l,
                                    end_line=end_l,
                                    signature=f"const {var_name} = {params_text} => ..." + (f": {ret_type}" if ret_type else ""),
                                    parent=None,
                                    return_type=ret_type,
                                )
                            )

            # 6. Import Statement
            elif node_type == "import_statement":
                source_node = node.child_by_field_name("source")
                raw_source = _node_text(source_node).strip("'\"")
                start_l, _ = _get_line_numbers(node)

                imported_names = []
                clause = node.child_by_field_name("import_clause") or node.child_by_field_name("clause")
                if clause:
                    clause_text = _node_text(clause)
                    cleaned = clause_text.replace("{", "").replace("}", "").strip()
                    imported_names = [n.strip().split()[0] for n in cleaned.split(",") if n.strip()]

                imports.append(
                    CodeImport(
                        module=raw_source,
                        imported_names=imported_names,
                        is_relative=raw_source.startswith("."),
                        line_number=start_l,
                        source_file=relative_path,
                    )
                )

            # Traverse child nodes for export wrappers and top-level statements
            if node_type not in ("class_declaration", "function_declaration", "interface_declaration", "type_alias_declaration"):
                for child in node.children:
                    _traverse(child, parent_class)

        _traverse(root)
        return entities, imports


class CodeParserManager:
    """Dispatches parsing requests to the appropriate language parser."""

    def __init__(self):
        self.parsers: List[BaseCodeParser] = [
            PythonParser(),
            JavaScriptTypeScriptParser(),
        ]

    def get_parser(self, language: str, file_path: Path) -> Optional[BaseCodeParser]:
        """Find an AST parser capable of handling the specified file."""
        for parser in self.parsers:
            if parser.can_parse(language, file_path):
                return parser
        return None
