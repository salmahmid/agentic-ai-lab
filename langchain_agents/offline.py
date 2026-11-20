"""Modèle scripté capable d'enchaîner les outils locaux pendant une démonstration."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage

from langchain_agents.runtime import reponse_outil, texte_message
from shared.llm import ScriptedChatModel

_ADDITION = re.compile(r"(-?\d+(?:\.\d+)?)\s*\+\s*(-?\d+(?:\.\d+)?)")
_PRODUIT = re.compile(r"(-?\d+(?:\.\d+)?)\s*\*\s*(-?\d+(?:\.\d+)?)")


def reponse_hors_ligne(messages: list[Any]) -> AIMessage:
    """Choisit un outil local ou une réponse finale, sans appeler de modèle distant."""

    outil = reponse_outil(messages)
    if outil is not None:
        return outil
    texte = ""
    for message in reversed(messages):
        if getattr(message, "type", None) in {"human", "user"}:
            texte = texte_message(message)
            break
    produit = _PRODUIT.search(texte)
    if produit:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "multiplication",
                    "args": {"a": float(produit.group(1)), "b": float(produit.group(2))},
                    "id": "appel-multiplication",
                    "type": "tool_call",
                }
            ],
        )
    somme = _ADDITION.search(texte)
    if somme:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "addition",
                    "args": {"a": float(somme.group(1)), "b": float(somme.group(2))},
                    "id": "appel-addition",
                    "type": "tool_call",
                }
            ],
        )
    if "date" in texte.lower():
        return AIMessage(
            content="",
            tool_calls=[{"name": "date_courante", "args": {}, "id": "appel-date", "type": "tool_call"}],
        )
    if "analyse" in texte.lower():
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "analyser_texte",
                    "args": {"texte": texte},
                    "id": "appel-analyse",
                    "type": "tool_call",
                }
            ],
        )
    return AIMessage(content="Bonjour, je suis l'agent de démonstration hors ligne du laboratoire.")


def modele_hors_ligne() -> ScriptedChatModel:
    return ScriptedChatModel(script=[reponse_hors_ligne], name_label="hors-ligne")
