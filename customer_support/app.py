"""Application Streamlit du support après-vente.

Lancer avec : ``streamlit run customer_support/app.py``
Le serveur MCP documentaire doit être démarré pour les questions de documentation.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# streamlit exécute le fichier depuis son dossier, pas depuis la racine du dépôt.
_RACINE = Path(__file__).resolve().parents[1]
if str(_RACINE) not in sys.path:
    sys.path.insert(0, str(_RACINE))

import streamlit as st

from customer_support.data.samples import DATA
from customer_support.graph import traiter_demande
from shared.config import get_settings
from shared.documents import safe_filename
from shared.errors import LabError

st.set_page_config(page_title="Support PX-200", page_icon=":wrench:", layout="centered")
st.markdown(
    """
    <style>
    .block-container {max-width: 920px; padding-top: 1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Support après-vente PX-200")
st.caption("Assistant fictif : une demande est orientée soit vers la documentation, soit vers la garantie.")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Connexion")
    st.write(f"Documentation MCP : `{get_settings().mcp_rag_url}`")
    st.write("La garantie est lue dans le registre local, sans MCP.")
    if st.button("Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("details"):
            st.json(message["details"])

with st.form("demande"):
    question = st.text_area("Question", placeholder="Décrivez le voyant ou demandez l'état de la garantie.")
    colonne_image, colonne_serie = st.columns(2)
    reference = colonne_image.text_input("Référence image", placeholder="img_px200_01")
    serie = colonne_serie.text_input("Numéro de série", placeholder="PX200-0042")
    image = st.file_uploader("Image optionnelle", type=["png", "jpg", "jpeg", "webp", "gif"])
    envoyer = st.form_submit_button("Envoyer")

if envoyer:
    if not question.strip():
        st.warning("La question est vide.")
    else:
        chemin = None
        try:
            if image is not None:
                nom = safe_filename(image.name)
                uploads = DATA / "uploads"
                uploads.mkdir(parents=True, exist_ok=True)
                destination = uploads / f"{uuid.uuid4().hex}{Path(nom).suffix.lower()}"
                destination.write_bytes(image.getvalue())
                chemin = str(destination)
            with st.spinner("Analyse de la demande..."):
                etat = traiter_demande(
                    question=question,
                    reference_image=reference or None,
                    chemin_image=chemin,
                    numero_serie=serie or None,
                )
            details = {
                "categorie": etat.get("categorie"),
                "agent": etat.get("agent"),
                "sources": etat.get("sources", []),
                "garantie": etat.get("garantie"),
                "mode_visuel": etat.get("mode_visuel"),
                "erreur": etat.get("erreur"),
            }
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state.messages.append(
                {"role": "assistant", "content": etat.get("reponse", ""), "details": details}
            )
            st.rerun()
        except LabError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Échec du traitement : {exc}")
