"""Mémoire courte de conversation via les checkpointers LangGraph.

La mémoire courte est la liste des messages du fil, conservée par le checkpointer.
Deux ``thread_id`` distincts ne partagent pas cette liste.

La mémoire persistante optionnelle utilise SQLite (``CHECKPOINT_PATH``).
Elle survit au redémarrage du processus, contrairement à ``InMemorySaver``.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from langchain_agents.runtime import build_basic_agent, texte_message
from shared.config import get_settings
from shared.llm import ScriptedChatModel, build_chat_model


def _modele_echo() -> ScriptedChatModel:
    def repondre(messages: list[Any]) -> AIMessage:
        dernier = messages[-1]
        return AIMessage(content=f"Message reçu : {texte_message(dernier)}")

    return ScriptedChatModel(script=[repondre], name_label="echo")


def modele_memoire() -> Any:
    if get_settings().llm_provider == "fake":
        return _modele_echo()
    return build_chat_model()


def agent_memoire(checkpointer: Any | None = None) -> Any:
    """Agent dont l'état de conversation est associé à un ``thread_id``."""

    return build_basic_agent(modele_memoire(), checkpointer=checkpointer or InMemorySaver())


def configuration(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def envoyer(agent: Any, message: str, thread_id: str) -> str:
    resultat = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=configuration(thread_id),
    )
    return texte_message(resultat["messages"][-1])


def historique(agent: Any, thread_id: str) -> list[str]:
    """Retourne les textes humains et d'assistant conservés pour ce fil."""

    etat = agent.get_state(configuration(thread_id))
    messages = etat.values.get("messages", [])
    return [texte_message(message) for message in messages]


def agent_memoire_sqlite(chemin: Path) -> tuple[Any, sqlite3.Connection]:
    """Ouvre une mémoire SQLite. L'appelant doit fermer la connexion."""

    from langgraph.checkpoint.sqlite import SqliteSaver

    chemin.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(str(chemin), check_same_thread=False)
    saver = SqliteSaver(connexion)
    return agent_memoire(checkpointer=saver), connexion


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Démonstration de mémoire par thread_id.")
    parser.add_argument("--thread-id", default="fil-demo")
    parser.add_argument("--message", action="append", required=True, help="Message, répétable.")
    args = parser.parse_args(argv)
    if get_settings().llm_provider == "fake":
        print("Mode hors ligne : la mémoire est réelle, le modèle est scripté.")
    agent = agent_memoire()
    for message in args.message:
        print(f"[{args.thread_id}] {envoyer(agent, message, args.thread_id)}")
    print("Historique :")
    for ligne in historique(agent, args.thread_id):
        print(f"- {ligne}")


if __name__ == "__main__":
    main()
