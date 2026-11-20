"""Pipeline RAG des manuels techniques, avec figures et mode visuel explicite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from customer_support.data.samples import DATA, ensure_sample_assets
from customer_support.rag.vision import decrire_image
from customer_support.validation import chemin_image_autorise, valider_reference_image
from shared.documents import load_knowledge_file
from shared.errors import LabError
from shared.index import KnowledgeIndex, citation
from shared.text import overlap_score

SEUIL = 0.2
MAX_REFORMULATIONS = 2
RACINES_IMAGES = [DATA / "images", DATA / "uploads"]


class IndexManuels:
    """Index texte et métadonnées visuelles des manuels fictifs."""

    def __init__(self, persistance: Path | None = None) -> None:
        ensure_sample_assets()
        self.catalogue = json.loads((DATA / "images" / "catalogue.json").read_text(encoding="utf-8"))
        self.index = KnowledgeIndex(persistance or (DATA / "chroma"), "manuels-px200")
        if self.index.store._collection.count() == 0:
            self.reconstruire()

    def reconstruire(self) -> int:
        documents = self._documents()
        return self.index.remplacer(documents)

    def _documents(self) -> list[Document]:
        documents: list[Document] = []
        manuel = DATA / "manuals"
        for fichier in sorted(manuel.iterdir()):
            if fichier.suffix.lower() not in {".md", ".pdf", ".txt"}:
                continue
            documents.extend(load_knowledge_file(fichier, title="Manuel technique fictif PX-200"))
        for reference, fiche in self.catalogue.items():
            documents.append(
                Document(
                    page_content=(
                        f"Figure {reference}. {fiche['titre']}. {fiche['description']} "
                        f"Modèle {fiche['modele']}."
                    ),
                    metadata={
                        "title": "Manuel technique fictif PX-200",
                        "source": fiche["fichier"],
                        "page": fiche["page"],
                        "kind": "figure",
                        "image_ref": reference,
                    },
                )
            )
        return documents

    def repondre(
        self,
        question: str,
        image_reference: str | None = None,
        device_model: str | None = None,
        image_path: str | None = None,
    ) -> dict[str, Any]:
        """Recherche les preuves puis rédige une réponse strictement appuyée sur elles."""

        if not question or not question.strip():
            return _erreur("La question documentaire est vide.")
        try:
            reference = valider_reference_image(image_reference)
            visuel = self._visuel(reference, image_path)
        except LabError as exc:
            return _erreur(str(exc))
        if reference and reference not in self.catalogue:
            visuel["erreur_reference"] = f"La référence d'image {reference} est inconnue du catalogue."
        question_active = question.strip()
        documents: list[Any] = []
        pertinent = False
        for essai in range(MAX_REFORMULATIONS + 1):
            documents = self.index.rechercher(question_active, k=4)
            scores = [overlap_score(question_active, document.page_content) for document in documents]
            pertinent = bool(scores) and max(scores) >= SEUIL
            if pertinent or essai == MAX_REFORMULATIONS:
                break
            question_active = _reformuler(question, device_model)
        retenus = [
            document
            for document in documents
            if overlap_score(question_active, document.page_content) >= SEUIL
        ]
        sources = [citation(document) for document in retenus]
        return {
            "ok": True,
            "pertinent": pertinent and bool(retenus),
            "reponse": _rediger(question, retenus, visuel),
            "sources": sources,
            "mode_visuel": visuel["mode_visuel"],
            "erreur": visuel.get("erreur_reference"),
        }

    def _visuel(self, reference: str | None, image_path: str | None) -> dict[str, Any]:
        fiche = self.catalogue.get(reference) if reference else None
        description_indexee = fiche["description"] if fiche else None
        if image_path:
            chemin = chemin_image_autorise(image_path, RACINES_IMAGES)
            vision = decrire_image(chemin)
            if vision["mode_visuel"] == "vision" and vision["description"]:
                return {
                    "mode_visuel": "vision",
                    "description": vision["description"],
                    "avertissement": None,
                    "reference": reference,
                }
            return {
                "mode_visuel": "texte_degrade",
                "description": description_indexee,
                "avertissement": vision["avertissement"],
                "reference": reference,
            }
        if reference:
            return {
                "mode_visuel": "texte_degrade",
                "description": description_indexee,
                "avertissement": (
                    "Aucune image binaire n'a été analysée par un modèle de vision. "
                    "La description provient de l'index textuel des figures."
                ),
                "reference": reference,
            }
        return {
            "mode_visuel": "sans_image",
            "description": None,
            "avertissement": "Aucune image n'a été fournie. L'interprétation visuelle n'a pas été faite.",
            "reference": None,
        }


def _reformuler(question: str, device_model: str | None) -> str:
    minuscules = question.lower()
    if not any(mot in minuscules for mot in ("px-200", "px200", "imprimante", "voyant")):
        return question
    modele = device_model or "PX-200"
    return f"{question} {modele} manuel technique pictogramme voyant papier"


def _rediger(question: str, documents: list[Any], visuel: dict[str, Any]) -> str:
    lignes = []
    if visuel.get("erreur_reference"):
        lignes.append(visuel["erreur_reference"])
    if visuel.get("avertissement"):
        lignes.append(str(visuel["avertissement"]))
    if visuel.get("mode_visuel") == "texte_degrade":
        lignes.append("Mode visuel : texte dégradé.")
    elif visuel.get("mode_visuel") == "vision":
        lignes.append("Mode visuel : interprétation par le modèle de vision configuré.")
    if visuel.get("description"):
        lignes.append(f"Description associée : {visuel['description']}")
    if not documents:
        lignes.append(
            "Les manuels techniques indexés sont insuffisants pour répondre. "
            "Aucune information externe n'est ajoutée."
        )
        return "\n".join(lignes)
    lignes.append("Éléments trouvés dans les manuels fictifs :")
    for document in documents:
        meta = document.metadata
        lignes.append(f"- {meta.get('title')}, page {meta.get('page')} : {document.page_content[:360]}")
    lignes.append("Cette réponse ne reprend que les passages ci-dessus.")
    return "\n".join(lignes)


def _erreur(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "pertinent": False,
        "reponse": message,
        "sources": [],
        "mode_visuel": None,
        "erreur": message,
    }


def repondre_documentation(
    question: str,
    image_reference: str | None = None,
    device_model: str | None = None,
    image_path: str | None = None,
    persistance: Path | None = None,
) -> dict[str, Any]:
    """Point d'entrée utilisé par l'outil MCP."""

    return IndexManuels(persistance).repondre(question, image_reference, device_model, image_path)
