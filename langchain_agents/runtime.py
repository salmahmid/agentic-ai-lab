"""Construction des agents ``create_agent`` et lecture de leur dernier message."""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage

from langchain_agents.tools.custom import CUSTOM_TOOLS


SYSTEM_PROMPT = (
    "Tu es l'assistant pédagogique du laboratoire Agentic AI Lab. "
    "Réponds en français. Utilise les outils pour les calculs, la date et l'analyse de texte. "
    "N'invente pas le résultat d'un outil."
)


def build_basic_agent(model: Any, checkpointer: Any = None) -> Any:
    """Agent conversationnel minimal, avec les quatre outils locaux."""

    return create_agent(
        model=model,
        tools=CUSTOM_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def texte_message(message: Any) -> str:
    contenu = getattr(message, "content", "")
    if isinstance(contenu, str):
        return contenu
    if isinstance(contenu, list):
        morceaux: list[str] = []
        for bloc in contenu:
            if isinstance(bloc, str):
                morceaux.append(bloc)
            elif isinstance(bloc, dict):
                morceaux.append(str(bloc.get("text", "")))
        return "\n".join(morceau for morceau in morceaux if morceau)
    return str(contenu)


def dernier_texte(resultat: dict[str, Any]) -> str:
    return texte_message(resultat["messages"][-1])


def reponse_outil(messages: list[Any]) -> AIMessage | None:
    """Si le dernier message est un résultat d'outil, le reformule."""

    dernier = messages[-1]
    if getattr(dernier, "type", None) == "tool":
        return AIMessage(content=f"Résultat de l'outil : {texte_message(dernier)}")
    return None
