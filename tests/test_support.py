"""Orchestrateur de support : routage exclusif, RAG et garantie."""

from __future__ import annotations

from pathlib import Path

import pytest

from customer_support.graph import classer_demande, traiter_demande
from customer_support.rag.pipeline import IndexManuels
from shared.errors import MCPUnavailableError

QUESTION_DOC = (
    "Mon imprimante PX-200 affiche un voyant clignotant. "
    "Que signifie le pictogramme sur la photo jointe ?"
)
QUESTION_GARANTIE = "Est-ce que mon imprimante est encore sous garantie ? Son numéro de série est PX200-0042."


def _rag_ok(payload: dict[str, str]) -> dict[str, object]:
    assert payload["question"]
    return {
        "ok": True,
        "reponse": "Le voyant papier clignotant indique un bac vide ou un bourrage.",
        "sources": [{"titre": "Manuel technique fictif PX-200", "page": 2, "reference_image": "img_px200_01"}],
        "mode_visuel": "texte_degrade",
        "erreur": None,
    }


def test_routage_documentation_n_appelle_pas_la_garantie() -> None:
    appels = {"garantie": 0}

    def garantie(numero: str) -> dict[str, str]:
        appels["garantie"] += 1
        raise AssertionError(numero)

    etat = traiter_demande(
        QUESTION_DOC,
        reference_image="img_px200_01",
        appel_rag=_rag_ok,
        evaluer=garantie,
    )
    assert etat["categorie"] == "documentation"
    assert etat["agent"] == "agent_documentaire"
    assert "mcp:rag_multimodal" in etat["etapes"]
    assert "outil:consulter_garantie" not in etat["etapes"]
    assert appels["garantie"] == 0
    assert etat["sources"][0]["page"] == 2
    assert etat["termine"] is True
    assert etat["etapes"][-1] == "fin"


def test_routage_garantie_n_appelle_pas_le_rag() -> None:
    def rag(payload: dict[str, str]) -> dict[str, object]:
        raise AssertionError(payload)

    etat = traiter_demande(QUESTION_GARANTIE, appel_rag=rag)
    assert etat["categorie"] == "garantie"
    assert etat["agent"] == "agent_garantie"
    assert etat["garantie"]["numero_serie"] == "PX200-0042"
    assert etat["garantie"]["statut"] in {"couverte", "expiree"}
    assert etat["garantie"]["date_expiration"]
    assert "outil:consulter_garantie" in etat["etapes"]
    assert "mcp:rag_multimodal" not in etat["etapes"]
    assert etat["termine"] is True


def test_cas_limites_du_graphe() -> None:
    vide = traiter_demande("   ")
    assert vide["categorie"] == "invalide"
    assert vide["agent"] is None
    assert "agent_documentaire" not in vide["etapes"]
    assert "agent_garantie" not in vide["etapes"]

    ambigu = traiter_demande("Le voyant est allumé et je veux connaître la garantie.")
    assert ambigu["categorie"] == "ambigu"
    assert "agent_documentaire" not in ambigu["etapes"]
    assert "agent_garantie" not in ambigu["etapes"]

    autre = traiter_demande("Quelle est la météo demain ?")
    assert autre["categorie"] == "non_supportee"

    inconnu = traiter_demande("La garantie couvre-t-elle le numéro PX200-9999 ?")
    assert inconnu["garantie"]["statut"] == "inconnu"

    def panne(payload: dict[str, str]) -> dict[str, object]:
        raise MCPUnavailableError("connexion refusée")

    echec = traiter_demande(QUESTION_DOC, appel_rag=panne)
    assert "indisponible" in echec["reponse"]
    assert echec["sources"] == []
    assert "mcp:echec" in echec["etapes"]
    assert echec["termine"] is True


def test_pipeline_documentaire(tmp_path: Path) -> None:
    index = IndexManuels(tmp_path / "manuels")
    reponse = index.repondre(QUESTION_DOC, image_reference="img_px200_01")
    assert reponse["ok"] is True
    assert reponse["pertinent"] is True
    assert reponse["mode_visuel"] == "texte_degrade"
    assert "texte dégradé" in reponse["reponse"]
    assert reponse["sources"]
    assert any(source["page"] == 2 for source in reponse["sources"])

    sans_image = index.repondre("Que signifie le voyant papier clignotant de l'imprimante PX-200 ?")
    assert sans_image["mode_visuel"] == "sans_image"
    assert "Aucune image" in sans_image["reponse"]

    inconnue = index.repondre(QUESTION_DOC, image_reference="img_absente_01")
    assert "inconnue" in inconnue["reponse"]

    malveillante = index.repondre(QUESTION_DOC, image_reference="../../etc/passwd")
    assert malveillante["ok"] is False

    hors_sujet = index.repondre("Quelle est la capitale du Japon ?")
    assert hors_sujet["pertinent"] is False
    assert "insuffisants" in hors_sujet["reponse"]
    assert "Tokyo" not in hors_sujet["reponse"]


def test_classification_exclusive() -> None:
    assert classer_demande(QUESTION_DOC) == "documentation"
    assert classer_demande(QUESTION_GARANTIE) == "garantie"
    assert classer_demande("") == "invalide"


def test_vision_absente(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    from customer_support.data.samples import ensure_sample_assets

    ensure_sample_assets()
    image = Path("customer_support/data/images/img_px200_01.png")
    index = IndexManuels(tmp_path / "vision")
    resultat = index.repondre(QUESTION_DOC, image_reference="img_px200_01", image_path=str(image))
    assert resultat["mode_visuel"] == "texte_degrade"
    assert "pixels" in resultat["reponse"].lower()
