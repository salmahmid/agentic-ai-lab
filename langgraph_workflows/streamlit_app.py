"""Interface Streamlit du graphe RAG.

Lancer avec : ``streamlit run langgraph_workflows/streamlit_app.py``
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# streamlit exécute le fichier depuis son dossier, pas depuis la racine du dépôt.
_RACINE = Path(__file__).resolve().parents[1]
if str(_RACINE) not in sys.path:
    sys.path.insert(0, str(_RACINE))

import streamlit as st

from langgraph_workflows.agentic_rag.graph import repondre
from shared.documents import safe_filename
from shared.errors import LabError, UnsupportedDocumentError
from shared.index import KnowledgeIndex

st.set_page_config(page_title="Agentic RAG Lab", page_icon=":books:", layout="centered")
st.markdown(
    """
    <style>
    .block-container {max-width: 860px; padding-top: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Agentic RAG Lab")
st.caption("Graphe LangGraph : routage, recherche Chroma, évaluation et réponse fondée sur les sources.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "index_televerse" not in st.session_state:
    st.session_state.index_televerse = None

with st.sidebar:
    st.header("Corpus")
    st.write("Le corpus pédagogique est chargé par défaut. Un fichier ajouté ici est indexé dans une collection de session.")
    fichier = st.file_uploader("Ajouter un PDF, Markdown ou TXT", type=["pdf", "md", "txt", "markdown"])
    if fichier is not None and st.button("Indexer le fichier"):
        try:
            nom = safe_filename(fichier.name)
            suffixe = Path(nom).suffix.lower()
            if suffixe not in {".pdf", ".md", ".txt", ".markdown"}:
                raise UnsupportedDocumentError("Format refusé.")
            dossier = Path(tempfile.mkdtemp(prefix="rag-lab-"))
            destination = dossier / nom
            destination.write_bytes(fichier.getvalue())
            index = KnowledgeIndex(dossier / "chroma", "session")
            nombre = index.ingerer_fichiers([destination])
            st.session_state.index_televerse = index
            st.success(f"{nombre} fragments indexés.")
        except LabError as exc:
            st.error(str(exc))
    if st.button("Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.write(f"{source.get('titre')} — page {source.get('page')}")

question = st.chat_input("Posez une question sur le corpus")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    try:
        with st.spinner("Recherche documentaire en cours..."):
            etat = repondre(question, index=st.session_state.index_televerse)
        reponse = etat.get("reponse", "")
        sources = etat.get("sources", [])
    except Exception as exc:  # affiche l'échec réel, sans réponse inventée
        reponse = f"Erreur : {exc}"
        sources = []
        st.error(reponse)
    st.session_state.messages.append({"role": "assistant", "content": reponse, "sources": sources})
    with st.chat_message("assistant"):
        st.markdown(reponse)
        if sources:
            with st.expander("Sources"):
                for source in sources:
                    st.write(f"{source.get('titre')} — page {source.get('page')}")
