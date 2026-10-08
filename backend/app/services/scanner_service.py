"""Repository scanning, file statistics, language detection, and file tree generation."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.repository import FileInfo, FileTreeNode, RepositoryStatistics

# Directories to unconditionally ignore
IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".next",
    "dist",
    "build",
    "coverage",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    ".svn",
    ".hg",
    "target",
    "bin",
    "obj",
    ".gradle",
    ".cargo",
    ".cache",
    ".yarn",
}

# Binary, media, archive, and compiled extensions to ignore
IGNORED_EXTENSIONS: Set[str] = {
    # Images & Media
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".svg",
    ".ico",
    ".webp",
    ".tiff",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    # Archives
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    # Documents & Binaries
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".pyc",
    ".pyo",
    ".pyd",
    ".wasm",
    ".bin",
    ".iso",
    ".dmg",
    # Fonts
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    # Minified / Source maps
    ".map",
}

# Extension to language mapping
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".pyw": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hxx": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".sql": "SQL",
    ".r": "R",
    ".dart": "Dart",
    ".lua": "Lua",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".markdown": "Markdown",
}

# Filename-specific mappings
SPECIAL_FILENAME_LANGUAGE_MAP: Dict[str, str] = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "gemfile": "Ruby",
    "rakefile": "Ruby",
    "cmakelists.txt": "CMake",
}


class ScannerService:
    """Service for scanning repositories, collecting metrics, and detecting languages."""

    @staticmethod
    def is_ignored_directory(dir_name: str) -> bool:
        """Check if directory name matches ignored directories list."""
        return dir_name.lower() in IGNORED_DIRECTORIES

    @staticmethod
    def is_ignored_file(file_name: str) -> bool:
        """Check if file has an ignored extension or should be skipped."""
        lower_name = file_name.lower()
        if lower_name.endswith(".min.js") or lower_name.endswith(".min.css"):
            return True
        ext = os.path.splitext(lower_name)[1]
        return ext in IGNORED_EXTENSIONS

    @classmethod
    def detect_language(cls, file_path: Path) -> Optional[str]:
        """Detect the programming/markup language of a file."""
        lower_name = file_path.name.lower()

        # Check special filenames first
        if lower_name in SPECIAL_FILENAME_LANGUAGE_MAP:
            return SPECIAL_FILENAME_LANGUAGE_MAP[lower_name]

        if lower_name.startswith("dockerfile."):
            return "Dockerfile"

        # Check extension
        ext = file_path.suffix.lower()
        return EXTENSION_LANGUAGE_MAP.get(ext)

    @classmethod
    def scan_repository(
        cls, repo_path: Path, top_n_largest: int = 5
    ) -> Tuple[RepositoryStatistics, Dict[str, int]]:
        """Walk the repository, calculate statistics, and detect languages.

        Args:
            repo_path: Root Path to the cloned repository.
            top_n_largest: Number of largest files to track.

        Returns:
            Tuple of (RepositoryStatistics, languages_dict).
        """
        repo_path = repo_path.resolve()
        total_files = 0
        total_directories = 0
        total_size_bytes = 0
        file_extensions: Dict[str, int] = {}
        languages: Dict[str, int] = {}
        all_files_info: List[FileInfo] = []

        for root, dirs, files in os.walk(repo_path, topdown=True):
            # Mutate dirs in-place to skip ignored directories from traversal
            dirs[:] = [d for d in dirs if not cls.is_ignored_directory(d)]
            total_directories += len(dirs)

            root_path = Path(root)

            for file_name in files:
                if cls.is_ignored_file(file_name):
                    continue

                full_path = root_path / file_name

                # Prevent following external symlinks or broken files
                if not full_path.is_file() or full_path.is_symlink():
                    continue

                try:
                    size = full_path.stat().st_size
                except OSError:
                    continue

                total_files += 1
                total_size_bytes += size

                # Extension tracking
                ext = full_path.suffix.lower() or "(no extension)"
                file_extensions[ext] = file_extensions.get(ext, 0) + 1

                # Language detection
                lang = cls.detect_language(full_path)
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1

                # Track relative path for largest files list
                rel_path = str(full_path.relative_to(repo_path))
                all_files_info.append(FileInfo(path=rel_path, size_bytes=size))

        # Sort largest files by size descending
        all_files_info.sort(key=lambda f: f.size_bytes, reverse=True)
        largest_files = all_files_info[:top_n_largest]

        # Sort languages by frequency descending
        sorted_languages = dict(
            sorted(languages.items(), key=lambda item: item[1], reverse=True)
        )

        # Sort extensions by frequency descending
        sorted_extensions = dict(
            sorted(file_extensions.items(), key=lambda item: item[1], reverse=True)
        )

        stats = RepositoryStatistics(
            total_files=total_files,
            total_directories=total_directories,
            total_size_bytes=total_size_bytes,
            file_extensions=sorted_extensions,
            largest_files=largest_files,
        )

        return stats, sorted_languages

    @classmethod
    def generate_file_tree(
        cls,
        repo_path: Path,
        max_depth: int = 4,
        max_children_per_dir: int = 50,
    ) -> List[FileTreeNode]:
        """Generate a structured, simplified file tree for the repository.

        Args:
            repo_path: Root Path to the cloned repository.
            max_depth: Maximum recursion depth.
            max_children_per_dir: Maximum items per directory to include.

        Returns:
            List of FileTreeNode representing top-level nodes in the tree.
        """
        repo_path = repo_path.resolve()

        def _build_nodes(current_path: Path, current_depth: int) -> List[FileTreeNode]:
            if current_depth > max_depth:
                return []

            nodes: List[FileTreeNode] = []

            try:
                entries = list(current_path.iterdir())
            except OSError:
                return []

            # Separate directories and files
            dirs: List[Path] = []
            files: List[Path] = []

            for entry in entries:
                if entry.is_dir() and not cls.is_ignored_directory(entry.name):
                    dirs.append(entry)
                elif entry.is_file() and not cls.is_ignored_file(entry.name):
                    files.append(entry)

            # Sort alphabetically (dirs first, then files)
            dirs.sort(key=lambda d: d.name.lower())
            files.sort(key=lambda f: f.name.lower())

            # Append directories
            for d in dirs[:max_children_per_dir]:
                rel_path = str(d.relative_to(repo_path))
                children = (
                    _build_nodes(d, current_depth + 1)
                    if current_depth < max_depth
                    else None
                )
                nodes.append(
                    FileTreeNode(
                        name=d.name,
                        type="directory",
                        path=rel_path,
                        children=children,
                    )
                )

            # Append files
            for f in files[:max_children_per_dir]:
                rel_path = str(f.relative_to(repo_path))
                try:
                    size = f.stat().st_size
                except OSError:
                    size = 0

                nodes.append(
                    FileTreeNode(
                        name=f.name,
                        type="file",
                        path=rel_path,
                        size_bytes=size,
                    )
                )

            return nodes

        return _build_nodes(repo_path, current_depth=1)
