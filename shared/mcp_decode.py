"""Décodage des réponses MCP, qui peuvent être du JSON, un bloc ou une liste."""

from __future__ import annotations

import json
from typing import Any


def decoder_mcp(brut: Any) -> Any:
    """Réduit une réponse d'outil MCP à un dict, un nombre ou un texte."""

    if isinstance(brut, list):
        valeurs = [decoder_mcp(element) for element in brut]
        return valeurs[0] if len(valeurs) == 1 else valeurs
    if isinstance(brut, dict):
        if brut.get("type") == "text" and "text" in brut:
            return decoder_mcp(brut["text"])
        if "structuredContent" in brut and isinstance(brut["structuredContent"], dict):
            return brut["structuredContent"]
        return brut
    if isinstance(brut, str):
        texte = brut.strip()
        if texte[:1] in "[{":
            try:
                return decoder_mcp(json.loads(texte))
            except json.JSONDecodeError:
                return brut
        return brut
    contenu = getattr(brut, "content", None)
    if contenu is not None and contenu is not brut:
        return decoder_mcp(contenu)
    return brut
