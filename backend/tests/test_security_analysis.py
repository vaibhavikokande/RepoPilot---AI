"""Unit and integration tests for Day 8 Security Analysis and Risk Detection."""

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.repository import RepositoryInfo
from app.schemas.security import (
    SecurityCategory,
    SecurityConfidence,
    SecurityFinding,
    SecuritySeverity,
)
from app.security_analysis import (
    SecurityAnalysisRequest,
    SecurityAnalysisResponse,
    SecurityAnalyzer,
    SecurityRulesEngine,
    calculate_category_summary,
    calculate_security_summary,
    deduplicate_and_sort_findings,
    redact_secret_string,
)
from app.services.repository_service import (
    RepositoryAccessError,
    RepositoryCloningError,
)

client = TestClient(app)


class TestSecretRedaction:
    """Tests for secret redaction helper functions."""

    def test_redact_live_token_prefixes(self):
        openai_key = "sk-proj-1234567890abcdefghijklmnop"
        redacted = redact_secret_string(openai_key)
        assert "sk-***" in redacted
        assert openai_key not in redacted
        assert "length 34" in redacted

        github_pat = "ghp_abcdefghijklmnopqrstuvwxyz012345"
        redacted_gh = redact_secret_string(github_pat)
        assert "ghp_***" in redacted_gh
        assert github_pat not in redacted_gh

        aws_key = "AKIAIOSFODNN7EXAMPLE"
        redacted_aws = redact_secret_string(aws_key)
        assert "AKIA***" in redacted_aws
        assert aws_key not in redacted_aws

    def test_redact_generic_secret(self):
        generic = "super_secret_password_123"
        redacted = redact_secret_string(generic)
        assert generic not in redacted
        assert "[REDACTED" in redacted


class TestSecurityRulesPythonAST:
    """Tests for AST-based detection rules in Python files."""

    @pytest.fixture
    def engine(self):
        return SecurityRulesEngine()

    # Rule A: Hardcoded credentials
    def test_hardcoded_credentials_positive(self, engine):
        code = 'api_key = "sk-live-99998888777766665555444433332222"\npassword = "production_super_secret_password"\n'
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "config.py", code)

        assert len(findings) == 2
        rule_ids = [f.rule_id for f in findings]
        assert rule_ids == ["PYTHON_HARDCODED_CREDENTIAL", "PYTHON_HARDCODED_CREDENTIAL"]

        # Ensure secrets are NOT leaked in evidence
        for f in findings:
            assert "sk-live" not in f.evidence_summary
            assert "production_super_secret" not in f.evidence_summary
            assert f.cwe_id == "CWE-798"
            assert f.category == SecurityCategory.CREDENTIALS

    def test_hardcoded_credentials_placeholders_ignored(self, engine):
        code = (
            'api_key = "your_api_key_here"\n'
            'password = "CHANGE_ME"\n'
            'token = "TODO"\n'
            'empty = ""\n'
            'short = "abc"\n'
            'dummy = "dummy"\n'
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "config.py", code)
        assert len(findings) == 0

    # Rule B: Dangerous dynamic execution
    def test_dangerous_eval_and_exec_detected(self, engine):
        code = (
            "def run_user_input(expr, code_block):\n"
            "    res = eval(expr)\n"
            "    exec(code_block)\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "executor.py", code)

        rule_ids = [f.rule_id for f in findings]
        assert "PYTHON_DANGEROUS_EVAL" in rule_ids
        assert "PYTHON_DANGEROUS_EXEC" in rule_ids
        assert all(f.cwe_id == "CWE-95" for f in findings)
        assert all(f.severity == SecuritySeverity.HIGH for f in findings)

    def test_safe_literal_eval_not_flagged(self, engine):
        code = (
            "import ast\n"
            "def parse_data(val):\n"
            "    return ast.literal_eval(val)\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "parser.py", code)
        assert len(findings) == 0

    # Rule C: Insecure subprocess usage
    def test_subprocess_shell_true_dynamic_detected(self, engine):
        code = (
            "import subprocess\n"
            "def run_cmd(user_target):\n"
            '    subprocess.run(f"ping {user_target}", shell=True)\n'
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "network.py", code)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "PYTHON_INSECURE_SUBPROCESS"
        assert f.severity == SecuritySeverity.HIGH
        assert f.cwe_id == "CWE-78"

    def test_os_system_detected(self, engine):
        code = (
            "import os\n"
            "def cleanup(filename):\n"
            '    os.system("rm -f " + filename)\n'
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "cleaner.py", code)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "PYTHON_INSECURE_SUBPROCESS"
        assert f.severity == SecuritySeverity.HIGH

    def test_subprocess_argument_list_not_flagged(self, engine):
        code = (
            "import subprocess\n"
            "def safe_clone(url, path):\n"
            '    subprocess.run(["git", "clone", url, path], check=True)\n'
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "git.py", code)
        assert len(findings) == 0

    # Rule D: SQL Injection
    def test_sql_injection_concatenation_detected(self, engine):
        code = (
            "def get_user(cursor, username):\n"
            '    cursor.execute(f"SELECT * FROM users WHERE name = \'{username}\'")\n'
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "db.py", code)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "PYTHON_SQL_INJECTION"
        assert f.cwe_id == "CWE-89"
        assert f.severity == SecuritySeverity.HIGH

    def test_sql_parameterized_query_not_flagged(self, engine):
        code = (
            "def get_user(cursor, username):\n"
            '    cursor.execute("SELECT * FROM users WHERE name = %s", (username,))\n'
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "db.py", code)
        assert len(findings) == 0

    # Rule E: Unsafe deserialization
    def test_unsafe_pickle_detected(self, engine):
        code = (
            "import pickle\n"
            "def load_payload(raw_bytes):\n"
            "    return pickle.loads(raw_bytes)\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "serializer.py", code)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "PYTHON_UNSAFE_DESERIALIZATION"
        assert f.cwe_id == "CWE-502"
        assert f.severity == SecuritySeverity.HIGH

    def test_safe_json_loads_not_flagged(self, engine):
        code = (
            "import json\n"
            "def load_payload(raw_str):\n"
            "    return json.loads(raw_str)\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "serializer.py", code)
        assert len(findings) == 0

    # Rule F: Weak cryptography
    def test_weak_crypto_md5_detected(self, engine):
        code = (
            "import hashlib\n"
            "def hash_password(pwd):\n"
            "    return hashlib.md5(pwd.encode()).hexdigest()\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "auth.py", code)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "PYTHON_WEAK_CRYPTO"
        assert f.cwe_id == "CWE-328"
        assert f.severity == SecuritySeverity.MEDIUM

    def test_weak_crypto_usedforsecurity_false_not_flagged(self, engine):
        code = (
            "import hashlib\n"
            "def cache_key(data):\n"
            "    return hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "cache.py", code)
        assert len(findings) == 0

    # Rule G: Insecure TLS verification
    def test_insecure_tls_verify_false_detected(self, engine):
        code = (
            "import requests\n"
            "def fetch_api(url):\n"
            "    return requests.get(url, verify=False)\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "client.py", code)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "PYTHON_INSECURE_TLS"
        assert f.cwe_id == "CWE-295"
        assert f.severity == SecuritySeverity.HIGH

    def test_secure_tls_default_not_flagged(self, engine):
        code = (
            "import requests\n"
            "def fetch_api(url):\n"
            "    return requests.get(url)\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "client.py", code)
        assert len(findings) == 0

    # Rule H: Broad exception in security context
    def test_broad_exception_in_auth_function_detected(self, engine):
        code = (
            "def authenticate_user(token):\n"
            "    try:\n"
            "        check_token(token)\n"
            "    except Exception:\n"
            "        pass\n"
        )
        tree = ast.parse(code)
        findings = engine.analyze_python_ast(tree, "auth_service.py", code)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "PYTHON_BROAD_EXCEPTION_SECURITY"
        assert f.severity == SecuritySeverity.LOW
        assert f.cwe_id == "CWE-391"


class TestSecurityRulesJSTS:
    """Tests for JavaScript/TypeScript detection rules."""

    @pytest.fixture
    def engine(self):
        return SecurityRulesEngine()

    def test_js_eval_detected(self, engine):
        code = "const result = eval(userExpression);\n"
        findings = engine.analyze_js_ts_source("script.js", code)
        assert len(findings) == 1
        assert findings[0].rule_id == "JS_DANGEROUS_EVAL"
        assert findings[0].cwe_id == "CWE-95"

    def test_js_hardcoded_credential_detected(self, engine):
        code = "const apiKey = 'sk-proj-999988887777666655554444';\n"
        findings = engine.analyze_js_ts_source("auth.ts", code)
        assert len(findings) == 1
        assert findings[0].rule_id == "JS_HARDCODED_CREDENTIAL"
        assert "sk-proj" not in findings[0].evidence_summary

    def test_js_insecure_tls_detected(self, engine):
        code = "const agent = new https.Agent({ rejectUnauthorized: false });\n"
        findings = engine.analyze_js_ts_source("agent.ts", code)
        assert len(findings) == 1
        assert findings[0].rule_id == "JS_INSECURE_TLS"
        assert findings[0].cwe_id == "CWE-295"

    def test_js_weak_crypto_detected(self, engine):
        code = "const hash = crypto.createHash('md5').update(pwd).digest('hex');\n"
        findings = engine.analyze_js_ts_source("crypto.js", code)
        assert len(findings) == 1
        assert findings[0].rule_id == "JS_WEAK_CRYPTO"
        assert findings[0].cwe_id == "CWE-328"

    def test_js_comments_not_flagged(self, engine):
        code = "// const apiKey = 'sk-proj-1234567890abcdefghijklmnop';\n/* eval(expr); */\n"
        findings = engine.analyze_js_ts_source("test.js", code)
        assert len(findings) == 0


class TestSecurityAnalyzerOrchestrator:
    """Tests for SecurityAnalyzer repository traversal, deduplication, and summaries."""

    @pytest.mark.anyio
    async def test_analyzer_on_fixture_directory(self, tmp_path):
        # Create a sample repository directory with positive and negative files
        repo_dir = tmp_path / "sample_repo"
        repo_dir.mkdir()

        # Vulnerable Python file
        vuln_file = repo_dir / "vuln.py"
        vuln_file.write_text(
            'api_key = "sk-live-111122223333444455556666"\n'
            'def run(x):\n'
            '    return eval(x)\n',
            encoding="utf-8",
        )

        # Safe Python file
        safe_file = repo_dir / "safe.py"
        safe_file.write_text(
            'import json\n'
            'def parse(s):\n'
            '    return json.loads(s)\n',
            encoding="utf-8",
        )

        # File with invalid syntax (should be skipped gracefully)
        bad_syntax_file = repo_dir / "bad.py"
        bad_syntax_file.write_text("def broken(:\n", encoding="utf-8")

        analyzer = SecurityAnalyzer()
        repo_info = RepositoryInfo(
            name="sample_repo",
            owner="testowner",
            url="https://github.com/testowner/sample_repo",
            default_branch="main",
        )

        response = await analyzer.analyze_repository(repo_dir, repo_info, explain_with_llm=False)

        assert response.status == "completed"
        assert response.analysis.files_discovered == 3
        assert response.analysis.files_analyzed == 2
        assert response.analysis.files_skipped == 1  # bad.py skipped
        assert len(response.findings) >= 2
        assert response.summary.critical >= 1
        assert response.summary.high >= 1
        assert response.llm_summary is not None


class TestSecurityAPIEndpoint:
    """Integration tests for POST /api/v1/repositories/analyze-security."""

    def test_security_analysis_invalid_url(self):
        response = client.post(
            "/api/v1/repositories/analyze-security",
            json={"repository_url": "invalid-url"},
        )
        assert response.status_code == 400
        assert "HTTPS URLs are permitted" in response.json()["detail"]

    def test_security_analysis_non_github_url(self):
        response = client.post(
            "/api/v1/repositories/analyze-security",
            json={"repository_url": "https://gitlab.com/owner/repo"},
        )
        assert response.status_code == 400

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_security_analysis_successful_flow(self, mock_cloned_repo, tmp_path):
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()
        test_py = repo_dir / "app.py"
        test_py.write_text('api_key = "sk-live-12345123451234512345"\n', encoding="utf-8")

        mock_context = MagicMock()
        mock_context.__enter__.return_value = (repo_dir, "main")
        mock_context.__exit__.return_value = None
        mock_cloned_repo.return_value = mock_context

        response = client.post(
            "/api/v1/repositories/analyze-security",
            json={"repository_url": "https://github.com/owner/mock_repo"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["repository"]["name"] == "mock_repo"
        assert data["analysis"]["files_analyzed"] >= 1
        assert len(data["findings"]) >= 1
        # Confirm secret is redacted
        assert "sk-live-1234512345" not in str(data)

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_security_analysis_repository_not_found(self, mock_cloned_repo):
        mock_cloned_repo.side_effect = RepositoryAccessError("Repository does not exist")
        response = client.post(
            "/api/v1/repositories/analyze-security",
            json={"repository_url": "https://github.com/owner/nonexistent"},
        )
        assert response.status_code == 404

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_security_analysis_cloning_error(self, mock_cloned_repo):
        mock_cloned_repo.side_effect = RepositoryCloningError("Git clone network error")
        response = client.post(
            "/api/v1/repositories/analyze-security",
            json={"repository_url": "https://github.com/owner/network-fail"},
        )
        assert response.status_code == 502
