"""Unit and integration tests for Day 6 RAG-based code understanding."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.rag import (
    CodeCitation,
    CodeRetriever,
    MockLLMGenerator,
    PromptBuilder,
    RAGPipeline,
    RAGRequest,
    RAGResponse,
    RetrievedSource,
    get_llm_generator,
)
from app.code_intelligence.models import CodeChunk
from app.schemas.repository import RepositoryInfo
from app.services.repository_service import RepositoryAccessError, RepositoryCloningError


client = TestClient(app)


def create_sample_retrieved_source(
    source_id: str = "S1",
    file_path: str = "app/auth.py",
    entity_name: str = "login_user",
    entity_type: str = "function",
    start_line: int = 10,
    end_line: int = 25,
    language: str = "Python",
    score: float = 0.92,
) -> RetrievedSource:
    """Helper to instantiate a sample RetrievedSource."""
    return RetrievedSource(
        source_id=source_id,
        chunk_id=f"chunk_{source_id}",
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        entity_name=entity_name,
        entity_type=entity_type,
        language=language,
        signature=f"def {entity_name}(username: str, password: str) -> bool:",
        docstring="Authenticates user credentials against the database.",
        code_content=f"def {entity_name}(username: str, password: str) -> bool:\n    return verify(username, password)",
        score=score,
    )


class TestPromptBuilder:
    """Tests for prompt builder and prompt injection defenses."""

    def test_system_prompt_grounding_and_injection_defenses(self):
        builder = PromptBuilder()
        sys_prompt = builder.build_system_prompt()

        assert "RepoPilot AI" in sys_prompt
        assert "STRICT GROUNDING RULES" in sys_prompt
        assert "[S1]" in sys_prompt
        assert "I couldn't find enough relevant code in the repository to answer this question confidently." in sys_prompt
        assert "UNTRUSTED DATA" in sys_prompt
        assert "Ignore previous instructions" in sys_prompt

    def test_build_user_prompt_with_sources(self):
        builder = PromptBuilder()
        s1 = create_sample_retrieved_source(source_id="S1")
        s2 = create_sample_retrieved_source(
            source_id="S2",
            file_path="app/db.py",
            entity_name="DatabasePool",
            entity_type="class",
            start_line=1,
            end_line=30,
        )

        user_prompt = builder.build_user_prompt("How does authentication work?", [s1, s2])

        assert "USER QUESTION:" in user_prompt
        assert "How does authentication work?" in user_prompt
        assert "--- BEGIN S1 ---" in user_prompt
        assert "SOURCE [S1]" in user_prompt
        assert "File: app/auth.py (Lines 10-25)" in user_prompt
        assert "--- BEGIN S2 ---" in user_prompt
        assert "SOURCE [S2]" in user_prompt
        assert "File: app/db.py (Lines 1-30)" in user_prompt
        assert "UNTRUSTED REPOSITORY DATA" in user_prompt

    def test_build_user_prompt_without_sources(self):
        builder = PromptBuilder()
        user_prompt = builder.build_user_prompt("Where is billing handled?", [])

        assert "Retrieved Code Sources: None found." in user_prompt
        assert "Where is billing handled?" in user_prompt

    def test_context_character_capping(self):
        builder = PromptBuilder(max_context_chars=100)
        s1 = create_sample_retrieved_source(source_id="S1")
        s2 = create_sample_retrieved_source(source_id="S2")

        user_prompt = builder.build_user_prompt("Question?", [s1, s2])
        # Only S1 should fit under 100 character budget limit
        assert "BEGIN S1" in user_prompt
        assert "BEGIN S2" not in user_prompt


class TestLLMGenerators:
    """Tests for LLM generator components."""

    @pytest.mark.anyio
    async def test_mock_llm_generator_empty_sources(self):
        gen = MockLLMGenerator()
        ans = await gen.generate(
            system_prompt="system",
            user_prompt="USER QUESTION:\nWhere is auth?\n\nRetrieved Code Sources: None found.",
        )
        assert "I couldn't find enough relevant code in the repository to answer this question confidently." in ans

    @pytest.mark.anyio
    async def test_mock_llm_generator_with_sources(self):
        builder = PromptBuilder()
        s1 = create_sample_retrieved_source(source_id="S1", entity_name="login_user")
        s2 = create_sample_retrieved_source(source_id="S2", file_path="app/session.py", entity_name="SessionManager")

        user_prompt = builder.build_user_prompt("How is authentication managed?", [s1, s2])
        gen = MockLLMGenerator()
        ans = await gen.generate(system_prompt="system", user_prompt=user_prompt)

        assert "[S1]" in ans
        assert "[S2]" in ans
        assert "app/auth.py" in ans
        assert "app/session.py" in ans

    def test_factory_get_llm_generator(self):
        gen = get_llm_generator()
        assert isinstance(gen, (MockLLMGenerator,))


class TestCitationValidation:
    """Tests for citation extraction and hallucination filtering."""

    def test_extract_valid_citations(self):
        pipeline = RAGPipeline(generator=MockLLMGenerator())
        s1 = create_sample_retrieved_source(source_id="S1")
        s2 = create_sample_retrieved_source(source_id="S2", file_path="app/db.py", entity_name="DB")

        answer_text = "Authentication is implemented in [S1], and connected to database in [S2]."
        citations = pipeline.extract_and_validate_citations(answer_text, [s1, s2])

        assert len(citations) == 2
        assert citations[0].source_id == "S1"
        assert citations[0].file_path == "app/auth.py"
        assert citations[1].source_id == "S2"
        assert citations[1].file_path == "app/db.py"

    def test_filters_out_hallucinated_citations(self):
        pipeline = RAGPipeline(generator=MockLLMGenerator())
        s1 = create_sample_retrieved_source(source_id="S1")

        # Answer text references [S1] and hallucinated [S99]
        answer_text = "Valid auth in [S1], and external service in [S99]."
        citations = pipeline.extract_and_validate_citations(answer_text, [s1])

        # S99 must be excluded because it was never in retrieved sources!
        assert len(citations) == 1
        assert citations[0].source_id == "S1"

    def test_fallback_citations_when_no_tags_in_answer(self):
        pipeline = RAGPipeline(generator=MockLLMGenerator())
        s1 = create_sample_retrieved_source(source_id="S1")
        s2 = create_sample_retrieved_source(source_id="S2")

        answer_text = "The repository contains authentication functions."
        citations = pipeline.extract_and_validate_citations(answer_text, [s1, s2])

        assert len(citations) == 2
        assert citations[0].source_id == "S1"
        assert citations[1].source_id == "S2"


class TestCodeRetriever:
    """Tests for CodeRetriever hit deduplication and formatting."""

    @pytest.mark.anyio
    async def test_retriever_deduplicates_overlapping_line_chunks(self):
        retriever = CodeRetriever()

        # Mock hybrid search returning duplicate hits
        mock_hits = [
            {
                "chunk_id": "c1",
                "file_path": "app/main.py",
                "start_line": 1,
                "end_line": 20,
                "entity_name": "app",
                "entity_type": "variable",
                "language": "python",
                "code_snippet": "app = FastAPI()",
                "score": 0.95,
            },
            {
                "chunk_id": "c2",
                "file_path": "app/main.py",
                "start_line": 1,
                "end_line": 20,
                "entity_name": "app",
                "entity_type": "variable",
                "language": "python",
                "code_snippet": "app = FastAPI()",
                "score": 0.91,
            },
            {
                "chunk_id": "c3",
                "file_path": "app/auth.py",
                "start_line": 10,
                "end_line": 30,
                "entity_name": "login",
                "entity_type": "function",
                "language": "python",
                "code_snippet": "def login(): pass",
                "score": 0.85,
            },
        ]

        with patch.object(retriever.vector_store, "collection_exists", return_value=True), \
             patch.object(retriever.hybrid_search, "search", return_value=mock_hits):
            sources = await retriever.retrieve("https://github.com/test/repo", "How does app start?", top_k=5)

            # c2 should have been deduplicated because same file, start_line, end_line as c1
            assert len(sources) == 2
            assert sources[0].source_id == "S1"
            assert sources[0].file_path == "app/main.py"
            assert sources[1].source_id == "S2"
            assert sources[1].file_path == "app/auth.py"


class TestRAGPipeline:
    """End-to-end tests for the RAGPipeline orchestrator."""

    @pytest.mark.anyio
    async def test_pipeline_ask_flow(self):
        retriever = CodeRetriever()
        s1 = create_sample_retrieved_source(source_id="S1", entity_name="authenticate")
        generator = MockLLMGenerator()

        pipeline = RAGPipeline(retriever=retriever, generator=generator)

        with patch.object(retriever, "retrieve", return_value=[s1]):
            repo_info = RepositoryInfo(
                name="Hello-World",
                owner="octocat",
                url="https://github.com/octocat/Hello-World",
                default_branch="main",
            )
            response = await pipeline.ask(
                repo_url="https://github.com/octocat/Hello-World",
                question="How does authentication work?",
                repo_info=repo_info,
                top_k=5,
            )

            assert isinstance(response, RAGResponse)
            assert response.status == "success"
            assert response.retrieved_chunks == 1
            assert len(response.citations) == 1
            assert response.citations[0].source_id == "S1"
            assert "[S1]" in response.answer


class TestRAGAPIEndpoint:
    """Tests for POST /api/v1/repositories/ask endpoint."""

    def test_ask_invalid_url_rejected(self):
        response = client.post(
            "/api/v1/repositories/ask",
            json={
                "repository_url": "invalid-url",
                "question": "How does auth work?",
            },
        )
        assert response.status_code == 400
        assert "Only secure HTTPS URLs are permitted" in response.json()["detail"]

    def test_ask_empty_question_rejected(self):
        response = client.post(
            "/api/v1/repositories/ask",
            json={
                "repository_url": "https://github.com/octocat/Hello-World",
                "question": "   ",
            },
        )
        assert response.status_code == 422

    @patch("app.api.v1.endpoints.repositories.RAGPipeline.ask")
    @patch("app.api.v1.endpoints.repositories.ChromaVectorStore.collection_exists", return_value=True)
    def test_ask_successful_flow(self, mock_col_exists, mock_ask):
        mock_ask.return_value = RAGResponse(
            repository=RepositoryInfo(
                name="Hello-World",
                owner="octocat",
                url="https://github.com/octocat/Hello-World",
                default_branch="master",
            ),
            question="Where is the greeting output?",
            answer="The greeting is output in [S1] via print statement.",
            citations=[
                CodeCitation(
                    source_id="S1",
                    file_path="main.py",
                    start_line=1,
                    end_line=5,
                    entity_name="main",
                    entity_type="function",
                    score=0.95,
                )
            ],
            sources=[
                create_sample_retrieved_source(
                    source_id="S1",
                    file_path="main.py",
                    entity_name="main",
                )
            ],
            retrieved_chunks=1,
            status="success",
        )

        response = client.post(
            "/api/v1/repositories/ask",
            json={
                "repository_url": "https://github.com/octocat/Hello-World",
                "question": "Where is the greeting output?",
                "top_k": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["question"] == "Where is the greeting output?"
        assert "[S1]" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source_id"] == "S1"
        assert len(data["sources"]) == 1

    @patch("app.api.v1.endpoints.repositories.ChromaVectorStore.collection_exists", return_value=False)
    @patch("app.services.repository_service.RepositoryService.cloned_repository")
    def test_ask_repository_not_found(self, mock_clone, mock_col_exists):
        mock_clone.side_effect = RepositoryAccessError("Repository does not exist or is private")

        response = client.post(
            "/api/v1/repositories/ask",
            json={
                "repository_url": "https://github.com/octocat/private-repo",
                "question": "How does auth work?",
            },
        )

        assert response.status_code == 404
        assert "Repository does not exist or is private" in response.json()["detail"]

    @patch("app.api.v1.endpoints.repositories.ChromaVectorStore.collection_exists", return_value=False)
    @patch("app.services.repository_service.RepositoryService.cloned_repository")
    def test_ask_cloning_error(self, mock_clone, mock_col_exists):
        mock_clone.side_effect = RepositoryCloningError("Failed to clone repository: network timeout")

        response = client.post(
            "/api/v1/repositories/ask",
            json={
                "repository_url": "https://github.com/octocat/Hello-World",
                "question": "How does auth work?",
            },
        )

        assert response.status_code == 502
        assert "Failed to clone repository" in response.json()["detail"]
