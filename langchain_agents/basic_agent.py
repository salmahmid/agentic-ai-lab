"""Agent conversationnel minimal et point d'entrée en ligne de commande."""

from __future__ import annotations

import argparse

from langchain_agents.offline import modele_hors_ligne
from langchain_agents.runtime import build_basic_agent, dernier_texte
from shared.config import get_settings
from shared.errors import LabError
from shared.llm import build_chat_model


def agent_par_defaut():
    """Utilise le fournisseur configuré, ou le modèle scripté si ``LLM_PROVIDER=fake``."""

    if get_settings().llm_provider == "fake":
        return build_basic_agent(modele_hors_ligne())
    return build_basic_agent(build_chat_model())


def repondre(message: str, thread_id: str = "demo") -> str:
    agent = agent_par_defaut()
    resultat = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return dernier_texte(resultat)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Agent LangChain minimal du laboratoire.")
    parser.add_argument("--message", required=True, help="Message utilisateur.")
    parser.add_argument("--thread-id", default="demo")
    args = parser.parse_args(argv)
    try:
        if get_settings().llm_provider == "fake":
            print("Mode hors ligne : modèle scripté local, aucun fournisseur cloud n'est appelé.")
        print(repondre(args.message, args.thread_id))
    except LabError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
