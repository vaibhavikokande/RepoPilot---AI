"""LLM Generator abstractions and implementations for RAG answer synthesis."""

import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMGenerationError(Exception):
    """Raised when an error occurs during LLM answer generation."""
    pass


class BaseLLMGenerator(ABC):
    """Abstract base class for LLM response generation."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Generate a response text given system and user prompts."""
        pass


class OpenAILLMGenerator(BaseLLMGenerator):
    """Generates answers via OpenAI Chat Completions API using async httpx."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 45.0,
    ):
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAILLMGenerator")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Invoke OpenAI Chat Completions API."""
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,  # Low temperature for factual, grounded answers
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 401:
                    raise LLMGenerationError(
                        "OpenAI authentication failed: Invalid API key."
                    )
                elif response.status_code == 429:
                    raise LLMGenerationError(
                        "OpenAI rate limit or quota exceeded."
                    )
                elif response.status_code != 200:
                    raise LLMGenerationError(
                        f"OpenAI API returned error HTTP {response.status_code}: {response.text}"
                    )

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMGenerationError("OpenAI API returned an empty choices list.")

                content = choices[0].get("message", {}).get("content", "")
                return content.strip()

        except httpx.TimeoutException as exc:
            logger.error("OpenAI API request timed out after %.1fs", self.timeout_seconds)
            raise LLMGenerationError(f"OpenAI request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            logger.error("OpenAI API network error: %s", exc)
            raise LLMGenerationError(f"OpenAI network connection failed: {exc}") from exc


class MockLLMGenerator(BaseLLMGenerator):
    """Deterministic, grounded mock LLM generator for tests and environments without API keys."""

    def __init__(self, model_name: str = "mock-gpt-4o"):
        self.model_name = model_name

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Synthesize a grounded answer citing the sources present in user_prompt."""
        # 1. Check if no sources were provided
        if "Retrieved Code Sources: None found" in user_prompt:
            return (
                "I couldn't find enough relevant code in the repository to answer this question confidently.\n\n"
                "No matching code entities or files were identified for this query."
            )

        # 2. Extract question from prompt
        q_match = re.search(r"USER QUESTION:\s*(.*?)\s*RETRIEVED CODE SOURCES", user_prompt, re.DOTALL)
        question = q_match.group(1).strip() if q_match else "the requested query"

        # 3. Extract source blocks: find all --- BEGIN S(\d+) --- ... --- END S(\d+) ---
        source_pattern = re.compile(
            r"--- BEGIN (S\d+) ---\s*SOURCE \[\1\]\s*File: (.*?)(?:\n|$)Entity: (.*?)(?:\n|$)Language: (.*?)(?:\n|Signature: (.*?)\n)?\s*```\w*\n(.*?)\n```\s*--- END \1 ---",
            re.DOTALL,
        )

        matches = source_pattern.findall(user_prompt)

        if not matches:
            # Fallback if pattern matching doesn't match custom format
            # Check for source labels like [S1], [S2]
            source_labels = re.findall(r"SOURCE \[(S\d+)\]", user_prompt)
            if not source_labels:
                return (
                    "I couldn't find enough relevant code in the repository to answer this question confidently.\n\n"
                    "The retrieved context did not contain parseable code references."
                )
            citations_str = ", ".join([f"[{s}]" for s in source_labels])
            return (
                f"Based on the retrieved code sources ({citations_str}), the repository implements components "
                f"relevant to \"{question}\". Please review the referenced sources for implementation specifics."
            )

        # 4. Generate structured synthesis based on extracted sources
        answer_parts = [
            f"Based on the codebase analysis for **\"{question}\"**, here is how the relevant components work:\n"
        ]

        for match in matches:
            source_id, file_path, entity_info, lang, sig, code = match
            source_id = source_id.strip()
            file_path = file_path.strip()
            entity_info = entity_info.strip()
            clean_code = code.strip()

            first_line = clean_code.split("\n")[0] if clean_code else ""

            answer_parts.append(
                f"- **{entity_info}** in [{source_id}] (`{file_path}`):\n"
                f"  This component is responsible for handling logic in `{file_path}`. "
                f"It is defined as `{first_line[:80]}` and directly addresses aspects of the query.\n"
            )

        citations_list = ", ".join([f"[{m[0]}]" for m in matches])
        answer_parts.append(
            f"In summary, the repository addresses this functionality across {len(matches)} identified code units "
            f"({citations_list})."
        )

        return "\n".join(answer_parts)


def get_llm_generator(settings: Optional[Settings] = None) -> BaseLLMGenerator:
    """Factory creating configured LLM generator based on application settings."""
    app_settings = settings or get_settings()
    provider = app_settings.llm_provider.lower().strip()
    api_key = app_settings.llm_api_key or app_settings.openai_api_key

    if provider == "mock":
        logger.info("Using MockLLMGenerator (configured via provider='mock').")
        return MockLLMGenerator()

    if provider == "openai":
        if api_key:
            logger.info("Using OpenAILLMGenerator with model '%s'.", app_settings.llm_model)
            return OpenAILLMGenerator(
                api_key=api_key,
                model=app_settings.llm_model,
            )
        else:
            logger.warning(
                "OpenAI LLM provider requested but no API key configured (OPENAI_API_KEY/LLM_API_KEY). "
                "Falling back to MockLLMGenerator for reliable offline operation."
            )
            return MockLLMGenerator()

    # Default fallback
    logger.info("Defaulting to MockLLMGenerator for provider '%s'.", provider)
    return MockLLMGenerator()
