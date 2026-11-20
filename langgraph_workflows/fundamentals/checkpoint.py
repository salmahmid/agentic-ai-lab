"""Mémoire de graphe : le checkpointer isole les fils de conversation."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class EtatMemoire(TypedDict):
    nom: str
    historique: Annotated[list[str], operator.add]


def memoriser(etat: EtatMemoire) -> dict[str, list[str]]:
    return {"historique": [etat["nom"]]}


def construire(avec_memoire: bool = False) -> object:
    """Compile le graphe.

    LangGraph Studio fournit déjà la persistance. Le checkpointer explicite
    est réservé à l'exécution locale, sinon le serveur de développement refuse
    de charger le graphe.
    """

    graphe = StateGraph(EtatMemoire)
    graphe.add_node("memoriser", memoriser)
    graphe.add_edge(START, "memoriser")
    graphe.add_edge("memoriser", END)
    if avec_memoire:
        return graphe.compile(checkpointer=InMemorySaver())
    return graphe.compile()


graph = construire()
graph_avec_memoire = construire(avec_memoire=True)


def main() -> None:
    config_a = {"configurable": {"thread_id": "fil-a"}}
    config_b = {"configurable": {"thread_id": "fil-b"}}
    print(graph_avec_memoire.invoke({"nom": "Salma", "historique": []}, config=config_a))
    print(graph_avec_memoire.invoke({"nom": "Lina", "historique": []}, config=config_a))
    print(graph_avec_memoire.invoke({"nom": "Lina", "historique": []}, config=config_b))


if __name__ == "__main__":
    main()
