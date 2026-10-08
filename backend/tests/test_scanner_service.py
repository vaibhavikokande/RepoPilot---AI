"""Tests for repository scanner, language detection, and file tree generation."""

from pathlib import Path

from app.services.scanner_service import ScannerService


class TestScannerService:
    """Test suite for ScannerService operations."""

    def test_language_detection(self) -> None:
        """Known extensions and filenames should map to expected languages."""
        cases = [
            (Path("main.py"), "Python"),
            (Path("app.pyw"), "Python"),
            (Path("index.ts"), "TypeScript"),
            (Path("Component.tsx"), "TypeScript"),
            (Path("server.js"), "JavaScript"),
            (Path("App.jsx"), "JavaScript"),
            (Path("styles.css"), "CSS"),
            (Path("index.html"), "HTML"),
            (Path("query.sql"), "SQL"),
            (Path("script.sh"), "Shell"),
            (Path("Cargo.toml"), "TOML"),
            (Path("config.yaml"), "YAML"),
            (Path("README.md"), "Markdown"),
            (Path("Dockerfile"), "Dockerfile"),
            (Path("Dockerfile.dev"), "Dockerfile"),
            (Path("Makefile"), "Makefile"),
            (Path("unknown.xyz"), None),
        ]

        for path, expected_lang in cases:
            assert ScannerService.detect_language(path) == expected_lang

    def test_ignored_directory_detection(self) -> None:
        """Common dependency and metadata directories must be ignored."""
        assert ScannerService.is_ignored_directory(".git") is True
        assert ScannerService.is_ignored_directory("node_modules") is True
        assert ScannerService.is_ignored_directory("__pycache__") is True
        assert ScannerService.is_ignored_directory(".venv") is True
        assert ScannerService.is_ignored_directory(".next") is True
        assert ScannerService.is_ignored_directory("dist") is True

        assert ScannerService.is_ignored_directory("app") is False
        assert ScannerService.is_ignored_directory("src") is False
        assert ScannerService.is_ignored_directory("tests") is False

    def test_ignored_file_detection(self) -> None:
        """Binary, archive, and minified files must be ignored."""
        assert ScannerService.is_ignored_file("image.png") is True
        assert ScannerService.is_ignored_file("photo.JPG") is True
        assert ScannerService.is_ignored_file("bundle.zip") is True
        assert ScannerService.is_ignored_file("doc.pdf") is True
        assert ScannerService.is_ignored_file("bundle.min.js") is True
        assert ScannerService.is_ignored_file("app.exe") is True

        assert ScannerService.is_ignored_file("app.py") is False
        assert ScannerService.is_ignored_file("index.ts") is False
        assert ScannerService.is_ignored_file("README.md") is False

    def test_scan_repository_statistics_and_languages(
        self, sample_repo_path: Path
    ) -> None:
        """Scanning the sample repo should return accurate statistics and languages."""
        stats, languages = ScannerService.scan_repository(sample_repo_path)

        # 7 valid files: app/main.py, app/services.py, frontend/index.ts,
        # frontend/style.css, tests/test_main.py, README.md, Dockerfile
        assert stats.total_files == 7
        assert stats.total_size_bytes > 0

        # Ignored files should not be counted:
        # .git/config, node_modules/pkg.js, app/__pycache__/main.cpython-313.pyc, logo.png, archive.zip
        assert ".png" not in stats.file_extensions
        assert ".zip" not in stats.file_extensions

        # Check languages detected
        assert languages.get("Python") == 3
        assert languages.get("TypeScript") == 1
        assert languages.get("CSS") == 1
        assert languages.get("Markdown") == 1
        assert languages.get("Dockerfile") == 1

        # Check largest files list
        assert len(stats.largest_files) > 0
        assert stats.largest_files[0].size_bytes >= stats.largest_files[-1].size_bytes

    def test_generate_file_tree(self, sample_repo_path: Path) -> None:
        """File tree should be correctly structured and exclude ignored items."""
        tree = ScannerService.generate_file_tree(sample_repo_path, max_depth=3)

        root_names = {node.name for node in tree}
        assert "app" in root_names
        assert "frontend" in root_names
        assert "tests" in root_names
        assert "README.md" in root_names
        assert "Dockerfile" in root_names

        # Excluded directories must not appear
        assert ".git" not in root_names
        assert "node_modules" not in root_names
        assert "logo.png" not in root_names

        # Find app directory node
        app_node = next(node for node in tree if node.name == "app")
        assert app_node.type == "directory"
        assert app_node.children is not None

        app_children_names = {child.name for child in app_node.children}
        assert "main.py" in app_children_names
        assert "services.py" in app_children_names
        assert "__pycache__" not in app_children_names
