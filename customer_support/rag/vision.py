"""Interprétation d'image. Sans modèle de vision, le mode texte dégradé est explicite."""

from __future__ import annotations

import base64
from pathlib import Path

from langchain_core.messages import HumanMessage

from shared.config import get_settings
from shared.llm import build_vision_model


def decrire_image(chemin: Path) -> dict[str, str | None]:
    """Appelle le modèle de vision configuré. N'invente pas de description s'il est absent."""

    reglages = get_settings()
    if not reglages.vision_credentials_present:
        return {
            "mode_visuel": "texte_degrade",
            "description": None,
            "avertissement": (
                "Aucun modèle de vision n'est configuré. Les pixels de l'image ne sont pas interprétés. "
                "Seule la description textuelle indexée peut être utilisée."
            ),
        }
    try:
        modele = build_vision_model()
        contenu = base64.b64encode(chemin.read_bytes()).decode("ascii")
        mime = "image/png" if chemin.suffix.lower() == ".png" else "image/jpeg"
        reponse = modele.invoke(
            [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                "Décris ce schéma technique fictif en français, en une ou deux phrases. "
                                "N'invente pas de marque réelle."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{contenu}"}},
                    ]
                )
            ]
        )
        texte = reponse.content if isinstance(reponse.content, str) else str(reponse.content)
    except Exception as exc:
        return {
            "mode_visuel": "texte_degrade",
            "description": None,
            "avertissement": (
                f"Le modèle de vision a échoué ({type(exc).__name__}). "
                "Les pixels ne sont pas présentés comme interprétés."
            ),
        }
    return {"mode_visuel": "vision", "description": texte.strip(), "avertissement": None}
