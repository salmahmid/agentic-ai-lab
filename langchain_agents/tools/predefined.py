"""Outils prédéfinis, avec échecs explicites et un REPL strictement limité."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.tools import tool

from shared.config import get_settings

# Expression arithmétique seulement : pas d'appel, pas d'import, pas d'attribut.
_EXPRESSION_ARITHMETIQUE = re.compile(r"^[0-9+\-*/().\s]{1,80}$")
_AVERTISSEMENT_REPL = (
    "PythonREPLTool exécute du code Python. Dans ce laboratoire il est limité "
    "à une expression arithmétique locale, désactivé par défaut, et il n'est "
    "jamais branché sur les applications Streamlit."
)


def avertissement_repl() -> str:
    """Retourne l'avertissement de sécurité affiché par la démonstration."""

    return _AVERTISSEMENT_REPL


def recherche_duckduckgo(requete: str, max_results: int = 3) -> dict[str, Any]:
    """Interroge DuckDuckGo. Une panne réseau devient un résultat ``ok=False``."""

    texte = requete.strip()
    if not texte:
        return {"ok": False, "provider": "duckduckgo", "error": "La requête est vide.", "results": []}
    if max_results < 1 or max_results > 5:
        return {"ok": False, "provider": "duckduckgo", "error": "max_results doit être entre 1 et 5.", "results": []}
    try:
        from ddgs import DDGS

        with DDGS() as client:
            rows = list(client.text(texte, max_results=max_results))
    except Exception as exc:  # réseau, paquet ou blocage du moteur
        return {
            "ok": False,
            "provider": "duckduckgo",
            "error": f"Recherche DuckDuckGo indisponible ({type(exc).__name__}).",
            "results": [],
        }
    results = [
        {
            "title": row.get("title", ""),
            "url": row.get("href") or row.get("url", ""),
            "content": row.get("body") or row.get("snippet", ""),
        }
        for row in rows
    ]
    return {"ok": True, "provider": "duckduckgo", "results": results}


def recherche_tavily(requete: str, max_results: int = 3) -> dict[str, Any]:
    """Interroge Tavily si ``TAVILY_API_KEY`` existe. Sinon, erreur explicite."""

    texte = requete.strip()
    if not texte:
        return {"ok": False, "provider": "tavily", "error": "La requête est vide.", "results": []}
    cle = get_settings().tavily_api_key
    if not cle:
        return {
            "ok": False,
            "provider": "tavily",
            "error": "TAVILY_API_KEY est absente. Aucune recherche n'a été envoyée.",
            "results": [],
        }
    try:
        from tavily import TavilyClient

        brut = TavilyClient(api_key=cle).search(query=texte, max_results=max_results)
    except Exception as exc:
        message = str(exc).replace(cle, "[SECRET REDACTE]")
        return {
            "ok": False,
            "provider": "tavily",
            "error": f"Recherche Tavily échouée ({type(exc).__name__} : {message}).",
            "results": [],
        }
    results = [
        {
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "content": row.get("content", ""),
        }
        for row in brut.get("results", [])
    ]
    return {"ok": True, "provider": "tavily", "results": results}


def executer_python_fiable(code: str) -> str:
    """Exécute une expression arithmétique via ``PythonREPLTool``.

    Refus si le drapeau n'est pas activé ou si le texte n'est pas une expression
    arithmétique. Cette fonction ne doit pas être exposée à une saisie publique.
    """

    if not get_settings().allow_python_repl:
        raise PermissionError(
            "PythonREPLTool est désactivé. "
            "Définissez AGENTIC_ALLOW_PYTHON_REPL=true seulement pour une démonstration locale de confiance."
        )
    expression = code.strip()
    if not _EXPRESSION_ARITHMETIQUE.fullmatch(expression):
        raise PermissionError(
            "Snippet refusé. Seule une expression arithmétique de démonstration est autorisée."
        )
    from langchain_experimental.tools import PythonREPLTool

    # print est ajouté ici : l'utilisateur ne peut pas l'écrire lui-même.
    return str(PythonREPLTool().invoke(f"print({expression})")).strip()


@tool
def recherche_duckduckgo_outil(requete: str) -> str:
    """Recherche des pages web avec DuckDuckGo et retourne un JSON contrôlé."""

    return json.dumps(recherche_duckduckgo(requete), ensure_ascii=False)


@tool
def recherche_tavily_outil(requete: str) -> str:
    """Recherche des pages web avec Tavily. Signale clairement l'absence de clé ou une panne."""

    return json.dumps(recherche_tavily(requete), ensure_ascii=False)


@tool
def python_repl_fiable(expression: str) -> str:
    """Évalue une expression arithmétique de démonstration. Refusée dans les autres cas."""

    return executer_python_fiable(expression)


def outil_duckduckgo_langchain() -> Any:
    """Retourne l'outil LangChain ``DuckDuckGoSearchRun`` si le paquet est importable."""

    try:
        from langchain_community.tools import DuckDuckGoSearchRun
    except Exception as exc:
        raise RuntimeError(
            "DuckDuckGoSearchRun n'est pas importable. Installez langchain-community et ddgs."
        ) from exc
    return DuckDuckGoSearchRun()


def outil_tavily_langchain() -> Any:
    """Retourne ``TavilySearch`` ou lève une erreur si la clé est absente."""

    if not get_settings().tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY est absente. TavilySearch n'est pas instancié.")
    from langchain_tavily import TavilySearch

    return TavilySearch(max_results=3)
