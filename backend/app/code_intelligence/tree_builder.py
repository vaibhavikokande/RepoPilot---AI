"""Builds structured hierarchical codebase maps connecting files, classes, and functions."""

from pathlib import Path
from typing import Dict, List

from app.code_intelligence.models import CodeEntity, CodeFile, CodeStructureNode


class CodebaseTreeBuilder:
    """Constructs a structured hierarchy mapping directories to files and code entities."""

    @classmethod
    def build_codebase_tree(
        cls, code_files: List[CodeFile]
    ) -> List[CodeStructureNode]:
        """Convert a list of analyzed CodeFile objects into a hierarchical tree.

        Args:
            code_files: List of successfully parsed CodeFile instances.

        Returns:
            List of root-level CodeStructureNode objects.
        """
        # Directory path -> list of child nodes
        dir_children: Dict[str, List[CodeStructureNode]] = {}
        all_dirs: set[str] = set()

        # Build file-level nodes with their nested entities
        for cf in code_files:
            file_node = cls._build_file_node(cf)
            parent_dir = str(Path(cf.path).parent)
            if parent_dir == ".":
                parent_dir = ""

            dir_children.setdefault(parent_dir, []).append(file_node)

            # Record all ancestor directories
            curr = parent_dir
            while curr:
                all_dirs.add(curr)
                parent = str(Path(curr).parent)
                curr = "" if parent == "." else parent

        # Sort files in each directory alphabetically
        for d in dir_children:
            dir_children[d].sort(key=lambda n: n.name.lower())

        # Construct nested directory nodes from bottom to top
        sorted_dirs = sorted(all_dirs, key=lambda d: d.count("/"), reverse=True)
        for d in sorted_dirs:
            parent_d = str(Path(d).parent)
            if parent_d == ".":
                parent_d = ""

            dir_node = CodeStructureNode(
                name=Path(d).name,
                type="directory",
                path=d,
                children=dir_children.get(d, []),
            )
            dir_children.setdefault(parent_d, []).append(dir_node)

        # Root items are those under ""
        root_nodes = dir_children.get("", [])
        # Sort root items: directories first, then files
        root_nodes.sort(key=lambda n: (0 if n.type == "directory" else 1, n.name.lower()))
        return root_nodes

    @classmethod
    def _build_file_node(cls, code_file: CodeFile) -> CodeStructureNode:
        """Create a file node containing its classes, methods, and functions."""
        entity_children: List[CodeStructureNode] = []

        # Separate entities into classes, standalone functions, interfaces, types, etc.
        classes: Dict[str, CodeEntity] = {}
        class_methods: Dict[str, List[CodeEntity]] = {}
        standalone_functions: List[CodeEntity] = []
        interfaces: List[CodeEntity] = []
        types: List[CodeEntity] = []

        for entity in code_file.entities:
            if entity.type == "class":
                classes[entity.name] = entity
            elif entity.type == "method" and entity.parent:
                class_methods.setdefault(entity.parent, []).append(entity)
            elif entity.type == "function":
                standalone_functions.append(entity)
            elif entity.type == "interface":
                interfaces.append(entity)
            elif entity.type == "type_alias":
                types.append(entity)

        # 1. Add Class nodes with their nested methods
        for c_name, c_ent in sorted(classes.items(), key=lambda item: item[0].lower()):
            methods = class_methods.get(c_name, [])
            method_nodes = [
                CodeStructureNode(
                    name=m.name,
                    type="method",
                    path=f"{code_file.path}::{c_name}::{m.name}",
                    line_info=f"L{m.start_line}-L{m.end_line}",
                    docstring=(m.docstring[:100] + "...") if m.docstring and len(m.docstring) > 100 else m.docstring,
                )
                for m in sorted(methods, key=lambda m: m.start_line)
            ]

            entity_children.append(
                CodeStructureNode(
                    name=c_ent.name,
                    type="class",
                    path=f"{code_file.path}::{c_ent.name}",
                    line_info=f"L{c_ent.start_line}-L{c_ent.end_line}",
                    docstring=(c_ent.docstring[:100] + "...") if c_ent.docstring and len(c_ent.docstring) > 100 else c_ent.docstring,
                    children=method_nodes if method_nodes else None,
                )
            )

        # 2. Add Interfaces (TypeScript)
        for iface in interfaces:
            entity_children.append(
                CodeStructureNode(
                    name=iface.name,
                    type="interface",
                    path=f"{code_file.path}::{iface.name}",
                    line_info=f"L{iface.start_line}-L{iface.end_line}",
                )
            )

        # 3. Add Type Aliases (TypeScript)
        for t in types:
            entity_children.append(
                CodeStructureNode(
                    name=t.name,
                    type="type_alias",
                    path=f"{code_file.path}::{t.name}",
                    line_info=f"L{t.start_line}-L{t.end_line}",
                )
            )

        # 4. Add Top-level Functions
        for func in sorted(standalone_functions, key=lambda f: f.start_line):
            entity_children.append(
                CodeStructureNode(
                    name=func.name,
                    type="function",
                    path=f"{code_file.path}::{func.name}",
                    line_info=f"L{func.start_line}-L{func.end_line}",
                    docstring=(func.docstring[:100] + "...") if func.docstring and len(func.docstring) > 100 else func.docstring,
                )
            )

        return CodeStructureNode(
            name=Path(code_file.path).name,
            type="file",
            path=code_file.path,
            line_info=f"{code_file.lines} lines",
            children=entity_children if entity_children else None,
        )
