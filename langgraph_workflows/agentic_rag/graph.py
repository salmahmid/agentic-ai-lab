"""Graphe RAG : routage, recherche, évaluation, reformulation bornée, réponse."""

from __future__ import annotations

import argparse
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from langchain_agents.rag.ingest import construire_index, ingerer_corpus, repertoire_index
from shared.index import KnowledgeIndex, citation
from shared.text import overlap_score

SEUIL = 0.2
MAX_REFORMULATIONS = 2
_SALUTATIONS = ("bonjour", "salut", "bonsoir", "merci")


class EtatRAG(TypedDict, total=False):
    """État du graphe documentaire. ``etapes`` sert à vérifier le chemin parcouru."""

    question: str
    question_initiale: str
    essais: int
    documents: list[dict[str, Any]]
    pertinent: bool
    reponse: str
    sources: list[dict[str, Any]]
    incertitude: bool
    etapes: Annotated[list[str], operator.add]


def _index_par_defaut() -> KnowledgeIndex:
    index = construire_index()
    if not repertoire_index().exists() or index.store._collection.count() == 0:
        ingerer_corpus()
        index = construire_index()
    return index


def construire(index: KnowledgeIndex | None = None):
    """Compile le graphe. L'index peut être injecté dans les tests."""

    base = index or _index_par_defaut()

    def preparer(etat: EtatRAG) -> dict[str, Any]:
        question = etat.get("question", "").strip()
        return {
            "question": question,
            "question_initiale": etat.get("question_initiale", question),
            "essais": etat.get("essais", 0),
            "pertinent": False,
            "incertitude": False,
            "sources": [],
            "documents": [],
            "etapes": ["preparer"],
        }

    def orienter(etat: EtatRAG) -> str:
        question = etat.get("question", "")
        if not question:
            return "repondre"
        mots = question.lower().split()
        if len(mots) <= 3 and any(mot.strip("!?.") in _SALUTATIONS for mot in mots):
            return "repondre"
        return "retrouver"

    def retrouver(etat: EtatRAG) -> dict[str, Any]:
        documents = base.rechercher(etat["question"], k=4)
        return {"documents": [citation(document) for document in documents], "etapes": ["retrouver"]}

    def evaluer(etat: EtatRAG) -> dict[str, Any]:
        meilleur = 0.0
        for document in etat.get("documents", []):
            meilleur = max(meilleur, overlap_score(etat["question"], str(document.get("extrait", ""))))
        return {"pertinent": meilleur >= SEUIL, "etapes": ["evaluer"]}

    def apres_evaluation(etat: EtatRAG) -> str:
        if etat.get("pertinent"):
            return "repondre"
        if etat.get("essais", 0) >= MAX_REFORMULATIONS:
            return "repondre"
        return "reformuler"

    def reformuler(etat: EtatRAG) -> dict[str, Any]:
        """Élargit uniquement les termes déjà présents. N'injecte pas le vocabulaire du corpus."""

        essais = etat.get("essais", 0) + 1
        initiale = etat.get("question_initiale", etat.get("question", ""))
        minuscules = initiale.lower()
        supplements: list[str] = []
        if "mémoire" in minuscules or "memoire" in minuscules:
            supplements.append("checkpointer thread")
        if "outil" in minuscules:
            supplements.append("addition multiplication date")
        if "corpus" in minuscules or "document" in minuscules:
            supplements.append("recherche documentaire")
        question = initiale if not supplements else f"{initiale} {' '.join(supplements)}"
        return {"question": question, "essais": essais, "etapes": ["reformuler"]}

    def repondre(etat: EtatRAG) -> dict[str, Any]:
        question = etat.get("question_initiale") or etat.get("question", "")
        if not question:
            return {
                "reponse": "La question est vide. Aucune recherche n'a été lancée.",
                "incertitude": True,
                "sources": [],
                "etapes": ["repondre"],
            }
        if question.lower().split()[0].strip("!?.") in _SALUTATIONS and not etat.get("documents"):
            return {
                "reponse": "Bonjour. Posez une question sur le corpus du laboratoire pour lancer la recherche.",
                "incertitude": False,
                "sources": [],
                "etapes": ["repondre"],
            }
        if not etat.get("pertinent"):
            return {
                "reponse": (
                    "Les documents indexés sont insuffisants pour répondre de façon fiable. "
                    "Je ne complète pas avec une information absente du corpus."
                ),
                "incertitude": True,
                "sources": [],
                "etapes": ["repondre"],
            }
        lignes = [
            f"- {source['titre']}, page {source['page']} : {source['extrait']}"
            for source in etat.get("documents", [])
            if overlap_score(question, str(source.get("extrait", ""))) >= SEUIL
        ]
        sources = [
            source
            for source in etat.get("documents", [])
            if overlap_score(question, str(source.get("extrait", ""))) >= SEUIL
        ]
        return {
            "reponse": "Réponse fondée sur le corpus :\n" + "\n".join(lignes),
            "incertitude": False,
            "sources": sources,
            "etapes": ["repondre"],
        }

    graphe = StateGraph(EtatRAG)
    graphe.add_node("preparer", preparer)
    graphe.add_node("retrouver", retrouver)
    graphe.add_node("evaluer", evaluer)
    graphe.add_node("reformuler", reformuler)
    graphe.add_node("repondre", repondre)
    graphe.add_edge(START, "preparer")
    graphe.add_conditional_edges("preparer", orienter, {"repondre": "repondre", "retrouver": "retrouver"})
    graphe.add_edge("retrouver", "evaluer")
    graphe.add_conditional_edges(
        "evaluer",
        apres_evaluation,
        {"repondre": "repondre", "reformuler": "reformuler"},
    )
    graphe.add_edge("reformuler", "retrouver")
    graphe.add_edge("repondre", END)
    return graphe.compile()


def repondre(question: str, index: KnowledgeIndex | None = None) -> dict[str, Any]:
    """Exécute le graphe et retourne l'état final."""

    compile = construire(index)
    return compile.invoke(
        {"question": question},
        config={"recursion_limit": 20},
    )


graph = construire()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Exécute le graphe RAG LangGraph.")
    parser.add_argument("--question", required=True)
    args = parser.parse_args(argv)
    etat = repondre(args.question)
    print(etat["reponse"])
    for source in etat.get("sources", []):
        print(f"Source : {source['titre']}, page {source['page']}")


if __name__ == "__main__":
    main()
