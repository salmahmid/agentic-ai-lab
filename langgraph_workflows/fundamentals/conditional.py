"""Arête conditionnelle : un entier est orienté vers le nœud pair ou impair."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class EtatNombre(TypedDict, total=False):
    nombre: int
    resultat: str


def preparer(etat: EtatNombre) -> dict[str, int]:
    return {"nombre": int(etat["nombre"])}


def vers_branche(etat: EtatNombre) -> str:
    return "pair" if etat["nombre"] % 2 == 0 else "impair"


def pair(etat: EtatNombre) -> dict[str, str]:
    return {"resultat": f"{etat['nombre']} est pair."}


def impair(etat: EtatNombre) -> dict[str, str]:
    return {"resultat": f"{etat['nombre']} est impair."}


def construire() -> object:
    graphe = StateGraph(EtatNombre)
    graphe.add_node("preparer", preparer)
    graphe.add_node("pair", pair)
    graphe.add_node("impair", impair)
    graphe.add_edge(START, "preparer")
    graphe.add_conditional_edges("preparer", vers_branche, {"pair": "pair", "impair": "impair"})
    graphe.add_edge("pair", END)
    graphe.add_edge("impair", END)
    return graphe.compile()


graph = construire()


def main() -> None:
    print(graph.invoke({"nombre": 4}))
    print(graph.invoke({"nombre": 7}))


if __name__ == "__main__":
    main()
