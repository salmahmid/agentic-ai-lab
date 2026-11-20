"""Graphe linéaire : START, un nœud, END."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class EtatLineaire(TypedDict):
    """État minimal transporté d'un nœud à l'autre."""

    message: str


def saluer(etat: EtatLineaire) -> dict[str, str]:
    """Produit le message final à partir du prénom reçu."""

    prenom = etat["message"].strip() or "visiteur"
    return {"message": f"Bonjour {prenom}, bienvenue dans le graphe linéaire."}


def construire() -> object:
    graphe = StateGraph(EtatLineaire)
    graphe.add_node("saluer", saluer)
    graphe.add_edge(START, "saluer")
    graphe.add_edge("saluer", END)
    return graphe.compile()


graph = construire()


def main() -> None:
    print(graph.invoke({"message": "Salma"}))


if __name__ == "__main__":
    main()
