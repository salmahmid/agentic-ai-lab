"""RAG pédagogique et graphes LangGraph déterministes."""

from __future__ import annotations

from pathlib import Path

from langchain_agents.rag.agent import agent_par_defaut, formuler_recherche
from langchain_agents.rag.ingest import ingerer_corpus
from langchain_agents.runtime import dernier_texte
from langgraph_workflows.agentic_rag.graph import repondre
from langgraph_workflows.fundamentals.checkpoint import graph_avec_memoire as graphe_memoire
from langgraph_workflows.fundamentals.conditional import graph as graphe_conditionnel
from langgraph_workflows.fundamentals.cycle import graph as graphe_cycle
from langgraph_workflows.fundamentals.linear import graph as graphe_lineaire
from langgraph_workflows.fundamentals.reducer_example import graph as graphe_reducteur
from shared.index import KnowledgeIndex


def test_graphes_fondamentaux() -> None:
    assert "Salma" in graphe_lineaire.invoke({"message": "Salma"})["message"]
    assert "pair" in graphe_conditionnel.invoke({"nombre": 4})["resultat"]
    assert "impair" in graphe_conditionnel.invoke({"nombre": 7})["resultat"]
    journal = graphe_reducteur.invoke({"etapes": [], "valeur": 0})
    assert journal["etapes"] == ["premiere", "seconde"]
    assert journal["valeur"] == 2
    assert graphe_cycle.invoke({"valeur": 0, "limite": 3})["valeur"] == 3


def test_memoire_de_graphe() -> None:
    fil_a = {"configurable": {"thread_id": "a"}}
    fil_b = {"configurable": {"thread_id": "b"}}
    graphe_memoire.invoke({"nom": "Salma", "historique": []}, config=fil_a)
    etat = graphe_memoire.invoke({"nom": "Lina", "historique": []}, config=fil_a)
    autre = graphe_memoire.invoke({"nom": "Lina", "historique": []}, config=fil_b)
    assert etat["historique"] == ["Salma", "Lina"]
    assert autre["historique"] == ["Lina"]


def test_index_et_agent_rag(tmp_path: Path) -> None:
    index = KnowledgeIndex(tmp_path / "chroma", "test-labo")
    index.ingerer_fichiers(
        [Path("langchain_agents/data/knowledge/guide_laboratoire.md")],
        titre="Guide du laboratoire",
    )
    trouve = formuler_recherche(index, "Quel est l'objectif du laboratoire Agentic AI Lab ?")
    assert trouve["suffisant"] is True
    assert trouve["sources"][0]["page"]
    assert "Guide du laboratoire" in str(trouve["sources"][0]["titre"])
    absent = formuler_recherche(index, "Quelle est la capitale du Japon ?")
    assert absent["suffisant"] is False
    agent = agent_par_defaut(index)
    reponse = dernier_texte(
        agent.invoke(
            {"messages": [{"role": "user", "content": "Quel est l'objectif du laboratoire ?"}]}
        )
    )
    assert "page" in reponse.lower() or "corpus" in reponse.lower()
    salutation = dernier_texte(agent.invoke({"messages": [{"role": "user", "content": "Bonjour"}]}))
    assert "Bonjour" in salutation or "bonjour" in salutation.lower()


def test_ingestion_commandee(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("langchain_agents.rag.ingest.repertoire_index", lambda: tmp_path / "index")
    nombre = ingerer_corpus(tmp_path / "index")
    assert nombre > 0


def test_graphe_rag_source_et_incertitude(tmp_path: Path) -> None:
    index = KnowledgeIndex(tmp_path / "graphe", "rag")
    index.ingerer_fichiers(
        [Path("langchain_agents/data/knowledge/guide_laboratoire.md")],
        titre="Guide du laboratoire",
    )
    utile = repondre("Quel est l'objectif du laboratoire Agentic AI Lab ?", index=index)
    assert utile["incertitude"] is False
    assert utile["sources"]
    assert "reformuler" not in utile["etapes"]
    inutile = repondre("Quelle est la capitale du Japon ?", index=index)
    assert inutile["incertitude"] is True
    assert "insuffisants" in inutile["reponse"]
    assert "Tokyo" not in inutile["reponse"]
    assert inutile["etapes"][-1] == "repondre"
    assert inutile["essais"] == 2
    salut = repondre("Bonjour", index=index)
    assert salut["sources"] == []
    assert "retrouver" not in salut["etapes"]
