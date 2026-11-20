"""Cycle avec condition d'arrêt explicite."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class EtatCompteur(TypedDict):
    valeur: int
    limite: int


def incrementer(etat: EtatCompteur) -> dict[str, int]:
    return {"valeur": etat["valeur"] + 1}


def continuer_ou_terminer(etat: EtatCompteur) -> str:
    """Retourne le nœud suivant. La boucle s'arrête quand la limite est atteinte."""

    if etat["valeur"] >= etat["limite"]:
        return END
    return "incrementer"


def construire() -> object:
    graphe = StateGraph(EtatCompteur)
    graphe.add_node("incrementer", incrementer)
    graphe.add_edge(START, "incrementer")
    graphe.add_conditional_edges("incrementer", continuer_ou_terminer)
    return graphe.compile()


graph = construire()


def main() -> None:
    print(graph.invoke({"valeur": 0, "limite": 3}))


if __name__ == "__main__":
    main()
