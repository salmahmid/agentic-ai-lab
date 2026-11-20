"""Fonctions d'embedding, dont un embedding local déterministe."""

from __future__ import annotations

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

from shared.config import get_settings
from shared.errors import ConfigurationError, MissingCredentialError

_TOKEN = re.compile(r"[a-z0-9àâäéèêëïîôùûüç-]{2,}", re.IGNORECASE)


class HashEmbeddings(Embeddings):
    """Embedding sac-de-jetons stable, sans réseau ni clé API.

    Deux textes qui partagent des mots produisent des vecteurs proches.
    Ce n'est pas un modèle sémantique : il sert aux tests et aux démonstrations hors ligne.
    """

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = _TOKEN.findall(text.lower())
        if not tokens:
            tokens = ["vide"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def build_embeddings() -> Embeddings:
    """Construit l'embedding indiqué par ``EMBEDDING_PROVIDER``."""

    settings = get_settings()
    provider = settings.embedding_provider
    if provider == "hash":
        return HashEmbeddings()
    if provider == "openai":
        if not settings.openai_api_key:
            raise MissingCredentialError("EMBEDDING_PROVIDER=openai exige OPENAI_API_KEY.")
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
    if provider == "google":
        if not settings.google_api_key:
            raise MissingCredentialError("EMBEDDING_PROVIDER=google exige GOOGLE_API_KEY.")
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.google_api_key,
        )
    raise ConfigurationError(
        f"EMBEDDING_PROVIDER='{provider}' n'est pas pris en charge. Valeurs : hash, openai, google."
    )
