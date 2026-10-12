"""Main RAG Pipeline orchestrating retrieval, prompt construction, LLM generation, and citation validation."""

import logging
import re
from typing import Dict, List, Optional, Set

from app.code_intelligence.models import CodeChunk
from app.core.config import get_settings
from app.rag.generator import BaseLLMGenerator, get_llm_generator
from app.rag.models import CodeCitation, RAGResponse, RetrievedSource
from app.rag.prompt_builder import PromptBuilder
from app.rag.retriever import CodeRetriever
from app.schemas.repository import RepositoryInfo

logger = logging.getLogger(__name__)

CITATION_REGEX = re.compile(r"\[(S\d+)\]")


class RAGPipeline:
    """End-to-end RAG pipeline for repository code understanding."""

    def __init__(
        self,
        retriever: Optional[CodeRetriever] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        generator: Optional[BaseLLMGenerator] = None,
    ):
        settings = get_settings()
        self.retriever = retriever or CodeRetriever()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.generator = generator or get_llm_generator(settings)

    def extract_and_validate_citations(
        self,
        answer_text: str,
        sources: List[RetrievedSource],
    ) -> List[CodeCitation]:
        """Extract [S1], [S2] citation tags from answer text and validate them against actual retrieved sources.

        Hallucinated citations (referencing source IDs that do not exist in retrieved sources)
        are strictly excluded.
        """
        source_map: Dict[str, RetrievedSource] = {s.source_id: s for s in sources}
        mentioned_tags: List[str] = CITATION_REGEX.findall(answer_text)

        seen_sources: Set[str] = set()
        citations: List[CodeCitation] = []

        for tag in mentioned_tags:
            if tag in source_map and tag not in seen_sources:
                seen_sources.add(tag)
                src = source_map[tag]
                citations.append(
                    CodeCitation(
                        source_id=src.source_id,
                        file_path=src.file_path,
                        start_line=src.start_line,
                        end_line=src.end_line,
                        entity_name=src.entity_name,
                        entity_type=src.entity_type,
                        score=src.score,
                    )
                )

        # If no citations were explicitly tagged in the text but sources were retrieved,
        # fallback to including citations for all retrieved sources so the user has references.
        if not citations and sources:
            for src in sources:
                citations.append(
                    CodeCitation(
                        source_id=src.source_id,
                        file_path=src.file_path,
                        start_line=src.start_line,
                        end_line=src.end_line,
                        entity_name=src.entity_name,
                        entity_type=src.entity_type,
                        score=src.score,
                    )
                )

        return citations

    async def ask(
        self,
        repo_url: str,
        question: str,
        repo_info: RepositoryInfo,
        top_k: int = 5,
        chunks: Optional[List[CodeChunk]] = None,
        clone_url: Optional[str] = None,
        owner: Optional[str] = None,
        name: Optional[str] = None,
    ) -> RAGResponse:
        """Execute the full RAG workflow for a given question and repository.

        Args:
            repo_url: Target repository URL.
            question: User question.
            repo_info: RepositoryInfo model for the target repo.
            top_k: Number of code chunks to retrieve.
            chunks: Optional pre-parsed code chunks.
            clone_url: Optional clone URL for auto-indexing if needed.
            owner: Optional repository owner.
            name: Optional repository name.

        Returns:
            RAGResponse with grounded answer, verified citations, and source evidence.
        """
        clean_question = question.strip()
        logger.info("Executing RAG question for %s: '%s'", repo_url, clean_question)

        # 1. Retrieve relevant code chunks
        sources = await self.retriever.retrieve(
            repo_url=repo_url,
            question=clean_question,
            top_k=top_k,
            chunks=chunks,
            clone_url=clone_url,
            owner=owner,
            name=name,
        )

        logger.info("Retrieved %d source chunks for question.", len(sources))

        # 2. Build system and user prompts with bounded context and injection defenses
        system_prompt = self.prompt_builder.build_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(
            question=clean_question,
            sources=sources,
        )

        # 3. Generate grounded answer via LLM
        answer = await self.generator.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # 4. Extract and validate source citations
        citations = self.extract_and_validate_citations(
            answer_text=answer,
            sources=sources,
        )

        logger.info(
            "Answer generated successfully (%d characters, %d verified citations).",
            len(answer),
            len(citations),
        )

        return RAGResponse(
            repository=repo_info,
            question=clean_question,
            answer=answer,
            citations=citations,
            sources=sources,
            retrieved_chunks=len(sources),
            status="success",
        )
