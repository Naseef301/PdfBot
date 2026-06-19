import logging
import re
import os
import sys



import ollama

from config import MULTI_QUERY_COUNT, OLLAMA_MODEL
from memory import ConversationState

logger = logging.getLogger(__name__)

# Spell checker — catches typos BEFORE LLM sees the query
try:
    from spellchecker import SpellChecker
    _spell = SpellChecker()
    _SPELL_AVAILABLE = True
except ImportError:
    logger.warning("pyspellchecker not installed. Run: pip install pyspellchecker")
    _SPELL_AVAILABLE = False

_LIST_PREFIX = re.compile(r"^\s*(?:\d+[\.\)]|[-*•]+)\s*")
# Words to never "correct" — domain terms, numbers, article numbers
_PROTECTED = {"mqtt", "http", "iot", "api", "rag", "llm", "pdf", "21", "32", "19", "14", "22", "20"}


def _deduplicate_preserve_order(items: list[str]) -> list[str]:
    """Return a case-insensitive deduplicated list while preserving order."""
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def generate_multi_queries(question: str) -> list[str]:
    """
    Generate multiple concise alternative search queries for a question.

    The original question is always returned as the first element.
    If Ollama fails for any reason, only the original question is returned.
    """
    question = question.strip()
    if not question:
        return [""]

    prompt = (
        f"Generate exactly {MULTI_QUERY_COUNT} alternative search queries for "
        "retrieval in a RAG system.\n"
        "Rules:\n"
        "- one query per line\n"
        "- no numbering or bullets\n"
        "- no explanations\n"
        "- no quotation marks\n"
        "- each query must be under 12 words\n"
        "- use different words or synonyms from the original question\n\n"
        f"Question: {question}\n"
        "Alternative queries:"
    )

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )
        response_text = response["message"]["content"]
    except Exception as exc:
        logger.error("Failed to generate multi-queries with Ollama: %s", exc)
        return [question]

    cleaned_queries: list[str] = [question]

    for line in response_text.splitlines():
        candidate = _LIST_PREFIX.sub("", line).strip()
        if not candidate or len(candidate) < 4:
            continue
        cleaned_queries.append(candidate)

    deduplicated = _deduplicate_preserve_order(cleaned_queries)
    final_queries = deduplicated[: MULTI_QUERY_COUNT + 1]

    logger.debug(
        "Generated multi-queries for question=%r; returning %d queries: %s",
        question,
        len(final_queries),
        final_queries,
    )

    return final_queries


def _fix_spelling(text: str) -> str:
    """
    Fix obvious spelling mistakes using pyspellchecker.
    Skips protected domain terms and numbers.
    """
    if not _SPELL_AVAILABLE:
        return text

    words = text.split()
    corrected = []
    for word in words:
        clean = word.lower().strip(".,?!")
        if clean in _PROTECTED or clean.isdigit() or len(clean) <= 2:
            corrected.append(word)
        else:
            fixed = _spell.correction(clean)
            corrected.append(fixed if fixed else word)

    result = " ".join(corrected)
    if result != text:
        logger.debug(f"Spell fix: '{text}' → '{result}'")
    return result


def rewrite_query(question: str, state: ConversationState) -> str:
    """
    Rewrite a user question into a self-contained, retrieval-optimised query.

    Pipeline:
    1. Fix spelling with pyspellchecker (fast, no LLM needed)
    2. If standalone + no references → return spell-fixed query directly
    3. Otherwise → LLM rewrite for continuation/pronoun resolution
    """
    question = question.strip()

    # Step 1: Fix spelling ALWAYS — before anything else
    question = _fix_spelling(question)

    # Step 2: Fast-path — no LLM needed if conversation is empty and question is clear
    if state.is_empty() and not _has_reference_words(question):
        return _normalize(question)

    # Step 3: Fast-path for long self-contained questions with no references
    word_count = len(question.split())
    if word_count >= 6 and not _has_reference_words(question):
        return _normalize(question)

    # Step 4: Full LLM rewrite for continuation/reference resolution
    history_str = state.get_formatted_history(n=3)
    last_topic = state.get_last_topic() or ""

    prompt = f"""You are a search query optimizer for a document QA system.

Your job: Rewrite the user's latest question into a clear, self-contained search query.

Rules:
1. Fix any remaining spelling mistakes silently
2. If the question refers to previous context ("explain more", "what about that", "compare them"),
   incorporate the topic from conversation history into the query
3. Expand pronouns and references ("it", "that", "them") using history
4. Output ONLY the rewritten query — no explanation, no preamble, no quotes
5. If the question is already clear and self-contained, return it as-is
6. Never invent topics not mentioned by the user

Conversation history:
{history_str}

Last resolved topic: {last_topic}

User's latest question: {question}

Rewritten query:"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        rewritten = response["message"]["content"].strip()

        if not rewritten or len(rewritten) > 300:
            logger.warning(f"Query rewrite invalid, using spell-fixed: '{question}'")
            return question

        logger.debug(f"Query rewrite: '{question}' → '{rewritten}'")
        return rewritten

    except Exception as e:
        logger.error(f"Query rewriting failed: {e}. Using spell-fixed question.")
        return question


def _normalize(question: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", question).strip()


def _has_reference_words(question: str) -> bool:
    """Detect vague references that need LLM context resolution."""
    q = question.lower()
    signals = [
        "explain more", "tell me more", "more details", "elaborate",
        "go on", "continue", "expand",
        " it ", " its ", " they ", " them ", " their ",
        " that ", " those ", " this ", " these ",
        "the first", "the second", "the other", "both of",
        "what about", "and this", "and that", "what else",
        "what is it", "why is that", "how does it",
    ]
    return any(s in f" {q} " for s in signals)