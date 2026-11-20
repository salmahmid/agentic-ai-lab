"""Utilitaires de texte partagés par les graphes RAG."""

from __future__ import annotations

import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9àâäéèêëïîôùûüç-]{3,}", re.IGNORECASE)
_STOPWORDS = {
    "les", "des", "une", "dans", "pour", "avec", "sans", "que", "qui", "quoi",
    "est", "son", "ses", "sur", "par", "pas", "plus", "cette", "comme", "vous",
    "votre", "nous", "mais", "donc", "alors", "être", "fait", "faire", "the",
    "and", "mon", "mes", "aux", "du", "au", "en", "de", "la", "le", "un",
}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.lower()


def tokens(text: str) -> set[str]:
    return {token for token in _TOKEN.findall(normalize(text)) if token not in _STOPWORDS}


def overlap_score(query: str, document: str) -> float:
    """Proportion des mots significatifs de la requête présents dans le document."""

    query_tokens = tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & tokens(document)) / len(query_tokens)
