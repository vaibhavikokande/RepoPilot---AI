"""Error and stack trace parser for the AI debugging assistant.

Extracts structured information from error messages and stack traces,
supporting Python tracebacks and basic JavaScript/TypeScript error formats.
Treats all user-supplied input as untrusted data.
"""

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Safety limits
MAX_ERROR_INPUT_LENGTH = 15_000
MAX_FRAMES = 50

# Python traceback patterns
PYTHON_TRACEBACK_HEADER = re.compile(r"^Traceback \(most recent call last\):", re.MULTILINE)
PYTHON_FRAME_RE = re.compile(
    r'^\s*File "([^"]+)", line (\d+)(?:, in (.+))?$', re.MULTILINE
)
PYTHON_ERROR_LINE_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning|Fault|Interrupt))\s*:\s*(.+)$",
    re.MULTILINE,
)
PYTHON_ERROR_TYPE_ONLY = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning|Fault|Interrupt))\s*$",
    re.MULTILINE,
)

# JavaScript / Node.js patterns
JS_ERROR_LINE_RE = re.compile(
    r"^(?:Uncaught\s+)?([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|TypeError|RangeError|ReferenceError|SyntaxError))\s*:\s*(.+)$",
    re.MULTILINE,
)
JS_FRAME_RE = re.compile(
    r"^\s*at\s+(?:(.+?)\s+)?\(?([^:\s()]+):(\d+)(?::(\d+))?\)?$", re.MULTILINE
)

# Generic file:line patterns (fallback)
GENERIC_FILE_LINE_RE = re.compile(
    r"(?:^|\s)([a-zA-Z0-9_/\\.-]+\.(?:py|js|ts|tsx|jsx|java|go|rs|rb|cpp|c|h)):(\d+)",
    re.MULTILINE,
)


from app.schemas.debug import ParsedError, StackFrame


def _classify_application_frame(file_path: str) -> bool:
    """Determine whether a file path appears to be application code vs stdlib/vendor."""
    if not file_path:
        return True
    lower = file_path.lower().replace("\\", "/")
    stdlib_indicators = (
        "/lib/python",
        "/site-packages/",
        "/node_modules/",
        "/dist-packages/",
        "<frozen ",
        "<string>",
        "<module>",
        "internal/",
        "/usr/lib/",
    )
    return not any(ind in lower for ind in stdlib_indicators)


def _sanitize_path(raw_path: str) -> str:
    """Strip enclosing quotes, whitespace, and normalize separators."""
    cleaned = raw_path.strip().strip("'\"")
    # Normalize Windows backslashes for display
    return cleaned.replace("\\", "/")


def parse_python_traceback(text: str) -> ParsedError:
    """Parse a Python traceback into structured components."""
    result = ParsedError()
    result.language = "python"

    # Extract frames
    for match in PYTHON_FRAME_RE.finditer(text):
        fp = _sanitize_path(match.group(1))
        line_num = int(match.group(2)) if match.group(2) else None
        func = match.group(3).strip() if match.group(3) else None
        frame = StackFrame(
            file_path=fp,
            line_number=line_num,
            function_name=func,
            is_application_code=_classify_application_frame(fp),
        )
        result.frames.append(frame)

    # Try to extract code context lines that follow each File line
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if PYTHON_FRAME_RE.match(line) and i + 1 < len(lines):
            context_line = lines[i + 1].strip()
            if context_line and not PYTHON_FRAME_RE.match(lines[i + 1]):
                # Attach to the most recently added frame
                frame_idx = len(result.frames) - 1
                # Find which frame this corresponds to
                count = 0
                for j, fl in enumerate(lines[:i + 1]):
                    if PYTHON_FRAME_RE.match(fl):
                        count += 1
                if 0 < count <= len(result.frames):
                    result.frames[count - 1].code_context = context_line

    # Extract error type and message
    err_match = PYTHON_ERROR_LINE_RE.search(text)
    if err_match:
        result.error_type = err_match.group(1).strip()
        result.error_message = err_match.group(2).strip()
    else:
        type_only = PYTHON_ERROR_TYPE_ONLY.search(text)
        if type_only:
            result.error_type = type_only.group(1).strip()
            result.error_message = result.error_type

    # Fallback to generic file:line pattern if no standard traceback frames were found
    if not result.frames:
        for match in GENERIC_FILE_LINE_RE.finditer(text):
            fp = _sanitize_path(match.group(1))
            line_num = int(match.group(2))
            frame = StackFrame(
                file_path=fp,
                line_number=line_num,
                is_application_code=_classify_application_frame(fp),
            )
            result.frames.append(frame)

    # Collect unique file paths
    seen = set()
    for frame in result.frames:
        if frame.file_path and frame.file_path not in seen:
            seen.add(frame.file_path)
            result.file_paths.append(frame.file_path)

    return result


def parse_js_traceback(text: str) -> ParsedError:
    """Parse a JavaScript/TypeScript error and stack trace."""
    result = ParsedError()
    result.language = "javascript"

    # Extract error type and message
    err_match = JS_ERROR_LINE_RE.search(text)
    if err_match:
        result.error_type = err_match.group(1).strip()
        result.error_message = err_match.group(2).strip()

    # Extract frames
    for match in JS_FRAME_RE.finditer(text):
        func_name = match.group(1).strip() if match.group(1) else None
        fp = _sanitize_path(match.group(2))
        line_num = int(match.group(3)) if match.group(3) else None
        frame = StackFrame(
            file_path=fp,
            line_number=line_num,
            function_name=func_name,
            is_application_code=_classify_application_frame(fp),
        )
        result.frames.append(frame)

    # Fallback to generic file:line pattern if no standard traceback frames were found
    if not result.frames:
        for match in GENERIC_FILE_LINE_RE.finditer(text):
            fp = _sanitize_path(match.group(1))
            line_num = int(match.group(2))
            frame = StackFrame(
                file_path=fp,
                line_number=line_num,
                is_application_code=_classify_application_frame(fp),
            )
            result.frames.append(frame)

    # Collect unique file paths
    seen = set()
    for frame in result.frames:
        if frame.file_path and frame.file_path not in seen:
            seen.add(frame.file_path)
            result.file_paths.append(frame.file_path)

    return result


def parse_generic_error(text: str) -> ParsedError:
    """Fallback parser for unrecognized error formats."""
    result = ParsedError()
    result.language = None

    # Try to find file:line patterns
    for match in GENERIC_FILE_LINE_RE.finditer(text):
        fp = _sanitize_path(match.group(1))
        line_num = int(match.group(2))
        frame = StackFrame(
            file_path=fp,
            line_number=line_num,
            is_application_code=_classify_application_frame(fp),
        )
        result.frames.append(frame)

    # Collect file paths
    seen = set()
    for frame in result.frames:
        if frame.file_path and frame.file_path not in seen:
            seen.add(frame.file_path)
            result.file_paths.append(frame.file_path)

    # Use the first non-blank line as a general error message
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            result.error_message = stripped[:500]
            break

    return result


def parse_error(
    error_text: str,
    language_hint: Optional[str] = None,
) -> ParsedError:
    """Parse an error message or stack trace into structured components.

    Detects the error format automatically and delegates to the appropriate parser.
    Treats all input as untrusted data.

    Args:
        error_text: Raw error message or stack trace.
        language_hint: Optional language hint ('python', 'javascript', 'typescript').

    Returns:
        ParsedError with extracted structured information.
    """
    if not error_text or not error_text.strip():
        result = ParsedError()
        result.error_message = ""
        return result

    # Enforce safety limit
    truncated = error_text[:MAX_ERROR_INPUT_LENGTH]
    was_truncated = len(error_text) > MAX_ERROR_INPUT_LENGTH

    result: Optional[ParsedError] = None

    # Determine parser based on language hint or auto-detection
    lang = (language_hint or "").lower().strip()

    if lang in ("python", "py"):
        result = parse_python_traceback(truncated)
    elif lang in ("javascript", "typescript", "js", "ts", "node"):
        result = parse_js_traceback(truncated)
    elif PYTHON_TRACEBACK_HEADER.search(truncated):
        result = parse_python_traceback(truncated)
    elif JS_FRAME_RE.search(truncated) or JS_ERROR_LINE_RE.search(truncated):
        result = parse_js_traceback(truncated)
    else:
        # Try Python first (most common), then JS, then generic
        py_result = parse_python_traceback(truncated)
        if py_result.frames or py_result.error_type:
            result = py_result
        else:
            js_result = parse_js_traceback(truncated)
            if js_result.frames or js_result.error_type:
                result = js_result
            else:
                result = parse_generic_error(truncated)

    # Apply safety limit on frames
    if len(result.frames) > MAX_FRAMES:
        result.frames = result.frames[:MAX_FRAMES]

    # Store sanitized raw trace
    result.raw_trace = truncated

    # If no error message was found, use a summary
    if not result.error_message:
        first_line = truncated.strip().splitlines()[0] if truncated.strip() else ""
        result.error_message = first_line[:500] or "Unable to extract a clear error message from the input."

    # Override language from hint if provided
    if language_hint and not result.language:
        result.language = language_hint.lower().strip()

    return result
