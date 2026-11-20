"""Mise à jour d'état avec un réducteur de liste."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class EtatJournal(TypedDict):
    """``etapes`` accumule les valeurs au lieu de les remplacer."""

    etapes: Annotated[list[str], operator.add]
    valeur: int


def premiere(etat: EtatJournal) -> dict[str, object]:
    return {"etapes": ["premiere"], "valeur": etat["valeur"] + 1}


def seconde(etat: EtatJournal) -> dict[str, object]:
    return {"etapes": ["seconde"], "valeur": etat["valeur"] + 1}


def construire() -> object:
    graphe = StateGraph(EtatJournal)
    graphe.add_node("premiere", premiere)
    graphe.add_node("seconde", seconde)
    graphe.add_edge(START, "premiere")
    graphe.add_edge("premiere", "seconde")
    graphe.add_edge("seconde", END)
    return graphe.compile()


graph = construire()


def main() -> None:
    print(graph.invoke({"etapes": [], "valeur": 0}))


if __name__ == "__main__":
    main()
