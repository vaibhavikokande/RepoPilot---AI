"""Metric calculation utilities: line counts, cyclomatic complexity, nesting depth, and code duplication."""

import ast
import hashlib
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def count_file_lines(source_code: str, language: str) -> Dict[str, int]:
    """Classify lines of source code into total, code, comment, and blank lines.

    Args:
        source_code: Content of the source file.
        language: Detected programming language.

    Returns:
        Dict with keys: 'total', 'code', 'comment', 'blank'.
    """
    lines = source_code.splitlines()
    total = len(lines)
    blank = 0
    comment = 0
    code = 0

    lang = language.lower()
    in_block_comment = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue

        # Check multi-line block comments for JS/TS/C-style
        if lang in ("javascript", "typescript", "c", "cpp", "csharp", "java", "go"):
            if in_block_comment:
                comment += 1
                if "*/" in stripped:
                    in_block_comment = False
                continue
            elif stripped.startswith("/*"):
                comment += 1
                if "*/" not in stripped:
                    in_block_comment = True
                continue
            elif stripped.startswith("//"):
                comment += 1
                continue

        # Check Python comments and docstrings
        elif lang == "python":
            if stripped.startswith("#"):
                comment += 1
                continue
            elif stripped.startswith(('"""', "'''")):
                comment += 1
                # Check if it opens and closes on the same line
                if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                    in_block_comment = not in_block_comment
                continue
            elif in_block_comment:
                comment += 1
                if '"""' in stripped or "'''" in stripped:
                    in_block_comment = False
                continue

        # Default is code
        code += 1

    return {
        "total": total,
        "code": max(code, 0),
        "comment": comment,
        "blank": blank,
    }


def calculate_python_cyclomatic_complexity(node: ast.AST) -> int:
    """Calculate McCabe cyclomatic complexity for a Python AST node (function or method).

    Base complexity is 1. Each decision point (branch) adds 1.
    """
    complexity = 1

    for child in ast.walk(node):
        # Control flow branches
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, (ast.With, ast.AsyncWith)):
            complexity += 1
        elif isinstance(child, ast.Assert):
            complexity += 1
        # Comprehension filters: [x for x in list if condition]
        elif isinstance(child, ast.comprehension):
            complexity += len(child.ifs)
        # Logical operators: a and b, x or y (each additional operand is a decision point)
        elif isinstance(child, ast.BoolOp):
            complexity += max(0, len(child.values) - 1)
        # Python 3.10+ pattern matching case guards
        elif hasattr(ast, "Match") and isinstance(child, ast.Match):
            pass
        elif hasattr(ast, "match_case") and isinstance(child, ast.match_case):
            if child.guard is not None:
                complexity += 1

    return complexity


def calculate_js_ts_cyclomatic_complexity(code_snippet: str) -> int:
    """Heuristically calculate McCabe cyclomatic complexity for JavaScript / TypeScript snippet."""
    complexity = 1

    # Match branching constructs: if, else if, while, for, case, catch, &&, ||, ??, ternary ?
    patterns = [
        r"\bif\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bcase\b",
        r"\bcatch\b",
        r"\&\&",
        r"\|\|",
        r"\?\?",
        r"\?[^.]",  # Ternary operator (? not followed by . which is optional chaining)
    ]

    for pat in patterns:
        matches = re.findall(pat, code_snippet)
        complexity += len(matches)

    return complexity


def calculate_python_nesting_depth(node: ast.AST) -> int:
    """Calculate maximum control flow nesting depth within a Python function/method AST."""
    compound_types = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncWith,
    )

    def _get_depth(current_node: ast.AST, current_depth: int) -> int:
        max_depth = current_depth
        for child in ast.iter_child_nodes(current_node):
            if isinstance(child, compound_types):
                max_depth = max(max_depth, _get_depth(child, current_depth + 1))
            else:
                max_depth = max(max_depth, _get_depth(child, current_depth))
        return max_depth

    # Start recursion from child nodes of the function so the function itself is depth 0
    max_nesting = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, compound_types):
            max_nesting = max(max_nesting, _get_depth(child, 1))
        else:
            max_nesting = max(max_nesting, _get_depth(child, 0))

    return max_nesting


def calculate_generic_nesting_depth(code_snippet: str) -> int:
    """Calculate maximum nesting depth based on brace or indentation levels."""
    max_depth = 0
    current_depth = 0

    for char in code_snippet:
        if char == "{":
            current_depth += 1
            if current_depth > max_depth:
                max_depth = current_depth
        elif char == "}":
            current_depth = max(0, current_depth - 1)

    return max_depth


def find_duplicate_blocks(
    files: List[Tuple[str, str]],
    min_lines: int = 6,
) -> List[Dict[str, any]]:
    """Detect duplicate or near-duplicate code blocks across files using rolling hash windows.

    Args:
        files: List of (file_path, file_content) tuples.
        min_lines: Minimum consecutive lines to consider a duplicate block.

    Returns:
        List of duplicate block occurrences with file paths and line ranges.
    """
    # Map from normalized block hash to list of occurrences: [(file_path, start_line, end_line, snippet)]
    hash_to_occurrences: Dict[str, List[Tuple[str, int, int, str]]] = {}

    for file_path, content in files:
        raw_lines = content.splitlines()
        normalized_lines: List[str] = []
        line_indices: List[int] = []

        for idx, line in enumerate(raw_lines):
            stripped = line.strip()
            # Ignore blank lines, single braces/brackets, and comments for hash matching
            if (
                not stripped
                or stripped in ("{", "}", "(", ")", "[", "]", ";", ":")
                or stripped.startswith(("#", "//", "/*", "*"))
            ):
                continue
            normalized_lines.append(stripped)
            line_indices.append(idx + 1)

        if len(normalized_lines) < min_lines:
            continue

        # Slide a window of size min_lines
        for i in range(len(normalized_lines) - min_lines + 1):
            block_lines = normalized_lines[i : i + min_lines]
            block_str = "\n".join(block_lines)
            block_hash = hashlib.sha256(block_str.encode("utf-8")).hexdigest()[:16]

            start_line = line_indices[i]
            end_line = line_indices[i + min_lines - 1]

            if block_hash not in hash_to_occurrences:
                hash_to_occurrences[block_hash] = []
            
            # Avoid self-overlapping adjacent hits in the same file
            existing = hash_to_occurrences[block_hash]
            if not any(e[0] == file_path and abs(e[1] - start_line) < min_lines for e in existing):
                existing.append((file_path, start_line, end_line, block_lines[0]))

    # Filter to hashes that appear in 2 or more distinct places
    duplicates: List[Dict[str, any]] = []
    seen_locations: Set[Tuple[str, int]] = set()

    for block_hash, occs in hash_to_occurrences.items():
        if len(occs) >= 2:
            first_file, first_start, first_end, sample_line = occs[0]
            for other_file, other_start, other_end, _ in occs[1:]:
                key = (other_file, other_start)
                if key not in seen_locations:
                    seen_locations.add(key)
                    duplicates.append({
                        "file_path": other_file,
                        "start_line": other_start,
                        "end_line": other_end,
                        "original_file": first_file,
                        "original_start": first_start,
                        "original_end": first_end,
                        "lines_count": min_lines,
                        "sample": sample_line[:60],
                    })

    return duplicates
