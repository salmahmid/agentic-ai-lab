"""Agent RAG : le modèle décide d'appeler l'outil de recherche."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from langchain_agents.rag.ingest import construire_index, ingerer_corpus
from langchain_agents.runtime import dernier_texte
from shared.config import get_settings
from shared.index import KnowledgeIndex, citation
from shared.llm import build_chat_model
from shared.text import overlap_score

SEUIL = 0.2


def passages_pertinents(index: KnowledgeIndex, question: str) -> list[Document]:
    trouves = index.rechercher(question, k=4)
    return [document for document in trouves if overlap_score(question, document.page_content) >= SEUIL]


def formuler_recherche(index: KnowledgeIndex, question: str) -> dict[str, Any]:
    """Retourne des citations ou explique que le corpus est insuffisant."""

    if not question.strip():
        return {"ok": False, "erreur": "Question vide.", "sources": [], "contexte": ""}
    documents = passages_pertinents(index, question)
    if not documents:
        return {
            "ok": True,
            "suffisant": False,
            "sources": [],
            "contexte": (
                "Aucun passage du corpus ne couvre cette question. "
                "Il faut répondre que l'information est insuffisante et ne pas inventer."
            ),
        }
    sources = [citation(document) for document in documents]
    contexte = "\n\n".join(
        f"[{source['titre']}, page {source['page']}] {source['extrait']}" for source in sources
    )
    return {"ok": True, "suffisant": True, "sources": sources, "contexte": contexte}


def outil_recherche(index: KnowledgeIndex):
    """Fabrique l'outil de retrieval lié à un index précis."""

    @tool
    def rechercher_connaissances(question: str) -> str:
        """Recherche le corpus pédagogique. À utiliser pour une question de cours, pas pour une salutation."""

        return json.dumps(formuler_recherche(index, question), ensure_ascii=False)

    return rechercher_connaissances


def build_rag_agent(model: Any, index: KnowledgeIndex | None = None) -> Any:
    base = index or construire_index()
    return create_agent(
        model=model,
        tools=[outil_recherche(base)],
        system_prompt=(
            "Tu es un assistant RAG. Appelle rechercher_connaissances si la question porte "
            "sur le laboratoire ou son corpus. Pour une salutation, réponds directement. "
            "Si l'outil indique que le corpus est insuffisant, dis-le clairement et n'invente pas. "
            "Cite le titre et la page des sources utilisées. Réponds en français."
        ),
    )


def agent_par_defaut(index: KnowledgeIndex | None = None) -> Any:
    if get_settings().llm_provider == "fake":
        from shared.llm import ScriptedChatModel

        def decider(messages: list[Any]) -> AIMessage:
            dernier = messages[-1]
            if getattr(dernier, "type", None) == "tool":
                donnees = json.loads(str(dernier.content))
                if not donnees.get("suffisant", False):
                    return AIMessage(
                        content="Les documents du laboratoire sont insuffisants pour répondre à cette question."
                    )
                pages = ", ".join(
                    f"{source.get('titre')} p.{source.get('page')}" for source in donnees.get("sources", [])
                )
                return AIMessage(content=f"D'après le corpus ({pages}) : {donnees.get('contexte', '')[:500]}")
            texte = str(getattr(dernier, "content", ""))
            if "bonjour" in texte.lower() and "objectif" not in texte.lower():
                return AIMessage(content="Bonjour. Posez une question sur le corpus du laboratoire.")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "rechercher_connaissances",
                        "args": {"question": texte},
                        "id": "appel-rag",
                        "type": "tool_call",
                    }
                ],
            )

        modele = ScriptedChatModel(script=[decider], name_label="rag-hors-ligne")
    else:
        modele = build_chat_model()
    return build_rag_agent(modele, index)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Interroge l'agent RAG pédagogique.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--ingerer", action="store_true", help="Reconstruit l'index avant la question.")
    args = parser.parse_args(argv)
    if args.ingerer or not repertoire_pret():
        ingerer_corpus()
    if get_settings().llm_provider == "fake":
        print("Mode hors ligne : la recherche documentaire est réelle, la rédaction est scriptée.")
    resultat = agent_par_defaut().invoke({"messages": [{"role": "user", "content": args.question}]})
    print(dernier_texte(resultat))


def repertoire_pret() -> bool:
    from langchain_agents.rag.ingest import repertoire_index

    return repertoire_index().exists()


if __name__ == "__main__":
    main()
