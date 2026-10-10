"""Lexical and metadata-based intelligent code search engine."""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from app.code_intelligence.models import CodeChunk

logger = logging.getLogger(__name__)

# Stop words and conversational phrases commonly found in natural-language code queries
CONVERSATIONAL_STOPWORDS: Set[str] = {
    "a",
    "about",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "code",
    "deals",
    "defined",
    "definition",
    "do",
    "does",
    "find",
    "for",
    "from",
    "get",
    "handled",
    "handles",
    "handling",
    "how",
    "i",
    "implemented",
    "in",
    "into",
    "is",
    "it",
    "locate",
    "look",
    "me",
    "of",
    "on",
    "or",
    "out",
    "responsible",
    "search",
    "show",
    "some",
    "the",
    "this",
    "to",
    "up",
    "used",
    "we",
    "what",
    "where",
    "which",
    "who",
    "with",
    "you",
}

# Software engineering synonym / alias expansions to bridge colloquial terms with code names
KEYWORD_SYNONYMS: Dict[str, Set[str]] = {
    "auth": {"auth", "authentication", "authenticate", "authorize", "login", "credentials"},
    "authentication": {"auth", "authentication", "authenticate", "login"},
    "login": {"login", "signin", "auth", "authentication"},
    "user": {"user", "users", "account", "profile"},
    "users": {"user", "users", "account"},
    "db": {"db", "database", "sql", "repository", "store", "storage"},
    "database": {"db", "database", "repository", "storage"},
    "repo": {"repo", "repository", "github"},
    "repository": {"repo", "repository"},
    "config": {"config", "configuration", "settings", "setting", "env"},
    "configuration": {"config", "configuration", "settings"},
    "req": {"req", "request", "requests"},
    "request": {"req", "request", "requests"},
    "resp": {"resp", "response", "responses"},
    "response": {"resp", "response"},
    "err": {"err", "error", "exception"},
    "error": {"err", "error", "exception"},
    "util": {"util", "utils", "utility", "utilities", "helper"},
    "utils": {"util", "utils", "utility", "helper"},
    "dep": {"dep", "dependency", "dependencies"},
    "dependency": {"dep", "dependency"},
    "scan": {"scan", "scanner", "scanning"},
    "scanner": {"scan", "scanner"},
    "parse": {"parse", "parser", "parsing", "ast"},
    "parser": {"parse", "parser", "ast"},
    "test": {"test", "tests", "testing"},
    "doc": {"doc", "docs", "documentation"},
    "token": {"token", "jwt", "session", "key"},
    "client": {"client", "api", "http"},
    "server": {"server", "service", "backend"},
}


class CodeSearchEngine:
    """Indexes and scores CodeChunk objects using lexical, identifier, and AST metadata analysis."""

    def __init__(self, chunks: Optional[List[CodeChunk]] = None):
        self.chunks: List[CodeChunk] = chunks or []

    def set_chunks(self, chunks: List[CodeChunk]) -> None:
        """Update the chunk index."""
        self.chunks = chunks

    @classmethod
    def split_identifier(cls, name: str) -> List[str]:
        """Split camelCase, PascalCase, and snake_case identifiers into individual terms.

        Examples:
            'UserService' -> ['user', 'service']
            'auth_token_generator' -> ['auth', 'token', 'generator']
            'getHTTPResponse' -> ['get', 'http', 'response']
        """
        if not name:
            return []

        # Split on underscores, hyphens, and dots
        raw_parts = re.split(r"[_\-\.]+", name)
        tokens: List[str] = []

        for part in raw_parts:
            if not part:
                continue
            # Split camelCase / PascalCase
            camel_split = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+", part)
            if camel_split:
                tokens.extend([t.lower() for t in camel_split])
            else:
                tokens.append(part.lower())

        return tokens

    @classmethod
    def preprocess_query(cls, query: str) -> Tuple[List[str], Set[str]]:
        """Clean natural language queries into core search tokens and expanded synonyms.

        Returns:
            Tuple of:
            - core_tokens: Cleaned list of important search keywords
            - expanded_terms: Set of tokens plus software engineering synonyms
        """
        # Normalize punctuation and symbols to whitespace
        clean_query = re.sub(r"[^\w\s]", " ", query.lower())
        raw_words = clean_query.split()

        core_tokens: List[str] = []
        for word in raw_words:
            # Also break down any camelCase or snake_case inside the query
            sub_tokens = cls.split_identifier(word)
            for st in sub_tokens:
                if len(st) > 1 and st not in CONVERSATIONAL_STOPWORDS:
                    if st not in core_tokens:
                        core_tokens.append(st)

        # Fallback if query was entirely stop words
        if not core_tokens and raw_words:
            core_tokens = [w for w in raw_words if len(w) > 1]

        # Expand synonyms
        expanded_terms: Set[str] = set(core_tokens)
        for token in core_tokens:
            if token in KEYWORD_SYNONYMS:
                expanded_terms.update(KEYWORD_SYNONYMS[token])

        return core_tokens, expanded_terms

    def search(
        self,
        query: str,
        limit: int = 10,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Perform ranked lexical search across indexed chunks.

        Args:
            query: User's search query (e.g. "Where is user authentication handled?").
            limit: Maximum number of ranked results to return.
            entity_types: Optional list of entity types to restrict to (e.g. ['function', 'class']).

        Returns:
            List of result dictionaries containing chunk, score, match_reasons, and explanation.
        """
        if not query.strip() or not self.chunks:
            return []

        core_tokens, expanded_terms = self.preprocess_query(query)
        if not core_tokens and not expanded_terms:
            return []

        allowed_types = {t.lower() for t in entity_types} if entity_types else None
        scored_results: List[Dict] = []

        for chunk in self.chunks:
            if allowed_types and chunk.entity_type.lower() not in allowed_types:
                continue

            score, match_reasons = self._score_chunk(chunk, core_tokens, expanded_terms)
            if score > 0:
                explanation = self._build_explanation(chunk, match_reasons, core_tokens)
                scored_results.append({
                    "chunk": chunk,
                    "score": round(score, 2),
                    "match_reasons": match_reasons,
                    "explanation": explanation,
                })

        # Rank primarily by score descending, then by entity specificity (methods/functions before broad files)
        type_priority = {
            "function": 3,
            "method": 3,
            "class": 2,
            "interface": 2,
            "type_alias": 1,
            "file_module": 0,
        }

        scored_results.sort(
            key=lambda item: (
                item["score"],
                type_priority.get(item["chunk"].entity_type, 1),
                -item["chunk"].tokens_estimate,
            ),
            reverse=True,
        )

        return scored_results[:limit]

    def _score_chunk(
        self,
        chunk: CodeChunk,
        core_tokens: List[str],
        expanded_terms: Set[str],
    ) -> Tuple[float, List[str]]:
        """Calculate relevance score and collect human-readable match explanations."""
        score = 0.0
        reasons: List[str] = []

        entity_name_lower = chunk.entity_name.lower()
        entity_tokens = set(self.split_identifier(chunk.entity_name))
        file_path_lower = chunk.file_path.lower()
        file_path_tokens = set(re.split(r"[/\\_\-\.]+", file_path_lower))
        parent_tokens = (
            set(self.split_identifier(chunk.parent)) if chunk.parent else set()
        )
        docstring_lower = (chunk.docstring or "").lower()
        signature_lower = (chunk.signature or "").lower()
        code_lower = chunk.code_content.lower()

        # 1. Exact entity name match (Highest Weight: 10.0)
        for token in core_tokens:
            if entity_name_lower == token:
                score += 10.0
                reasons.append(f"Exact match on {chunk.entity_type} name '{chunk.entity_name}'")
                break
        else:
            # Check expanded synonyms exact name
            for exp in expanded_terms:
                if entity_name_lower == exp:
                    score += 8.0
                    reasons.append(f"Entity name '{chunk.entity_name}' matches concept '{exp}'")
                    break

        # 2. Tokenized entity name parts (Weight: 5.0 per term)
        matched_entity_tokens = entity_tokens.intersection(expanded_terms)
        if matched_entity_tokens and not any("Exact match" in r for r in reasons):
            score += 5.0 * len(matched_entity_tokens)
            reasons.append(f"Identifier parts matched: {', '.join(sorted(matched_entity_tokens))}")

        # 3. Parent / enclosing scope match (Weight: 4.0)
        matched_parent_tokens = parent_tokens.intersection(expanded_terms)
        if matched_parent_tokens:
            score += 4.0 * len(matched_parent_tokens)
            reasons.append(f"Enclosing class '{chunk.parent}' matches: {', '.join(sorted(matched_parent_tokens))}")

        # 4. File path & directory matches (Weight: 3.5)
        matched_path_tokens = file_path_tokens.intersection(expanded_terms)
        if matched_path_tokens:
            score += 3.5 * min(2, len(matched_path_tokens))
            reasons.append(f"File path '{chunk.file_path}' matches keywords: {', '.join(sorted(matched_path_tokens))}")

        # 5. Signature match (parameters or return types) (Weight: 3.0)
        matched_sig_terms = [t for t in expanded_terms if t in signature_lower and t not in entity_tokens]
        if matched_sig_terms:
            score += 3.0
            reasons.append(f"Signature matches terms: {', '.join(sorted(matched_sig_terms)[:3])}")

        # 6. Docstring match (Weight: 2.5)
        if docstring_lower:
            matched_doc_terms = [t for t in expanded_terms if t in docstring_lower]
            if matched_doc_terms:
                score += 2.5 * min(2, len(matched_doc_terms))
                reasons.append(f"Docstring mentions: {', '.join(sorted(matched_doc_terms)[:3])}")

        # 7. Decorators match (Weight: 2.0)
        for dec in chunk.decorators:
            dec_lower = dec.lower()
            if any(t in dec_lower for t in expanded_terms):
                score += 2.0
                reasons.append(f"Decorator '{dec}' matches query terms")
                break

        # 8. Body code content match (Weight: 1.0 per unique matched term, capped at 3.0)
        body_matches = [t for t in expanded_terms if t in code_lower and t not in entity_tokens]
        if body_matches:
            added = min(3.0, 1.0 * len(body_matches))
            score += added
            if not reasons:
                reasons.append(f"Code body contains: {', '.join(sorted(body_matches)[:3])}")

        # Query entity type hint (e.g. "where is function auth", "find class User")
        for t_hint in ["function", "class", "method", "interface"]:
            if t_hint in core_tokens and chunk.entity_type.lower() == t_hint:
                score += 2.0
                reasons.append(f"Matches requested entity type '{t_hint}'")

        return score, reasons

    @classmethod
    def _build_explanation(
        cls,
        chunk: CodeChunk,
        reasons: List[str],
        core_tokens: List[str],
    ) -> str:
        """Compose a concise, natural sentence explaining why this entity was returned."""
        type_title = chunk.entity_type.replace("_", " ").title()
        loc = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"

        if not reasons:
            return f"{type_title} '{chunk.entity_name}' at {loc} contains relevant code keywords."

        primary_reason = reasons[0]
        extra = f" ({reasons[1]})" if len(reasons) > 1 else ""

        scope_str = f" in '{chunk.parent}'" if chunk.parent else ""
        return f"{type_title} '{chunk.entity_name}'{scope_str} [{loc}] matches query: {primary_reason}{extra}."
