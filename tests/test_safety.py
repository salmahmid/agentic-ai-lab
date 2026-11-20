"""Sécurité des chemins, des documents et du registre de garantie."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from customer_support.tools.garantie import ajouter_mois, evaluer_garantie
from customer_support.validation import valider_numero_serie, valider_reference_image
from shared.documents import assert_within, load_knowledge_file, safe_filename
from shared.embeddings import build_embeddings
from shared.errors import MissingCredentialError, UnsafeInputError, UnsupportedDocumentError


def test_chemin_et_nom() -> None:
    racine = Path("customer_support/data/manuals").resolve()
    assert assert_within(racine, racine / "manuel_px200.md").is_file()
    with pytest.raises(UnsafeInputError):
        assert_within(racine, racine / ".." / ".." / "etc" / "passwd")
    with pytest.raises(UnsafeInputError):
        safe_filename("../secret.txt")


def test_document_non_supporte(tmp_path: Path) -> None:
    fichier = tmp_path / "charge.exe"
    fichier.write_text("non", encoding="utf-8")
    with pytest.raises(UnsupportedDocumentError):
        load_knowledge_file(fichier)


def test_reference_image_malveillante() -> None:
    assert valider_reference_image("img_px200_01") == "img_px200_01"
    with pytest.raises(UnsafeInputError):
        valider_reference_image("../../etc/passwd")
    with pytest.raises(UnsafeInputError):
        valider_reference_image("img_../secret")
    with pytest.raises(UnsafeInputError):
        valider_numero_serie("../PX200-0042")


def test_garantie_calculee_selon_la_date() -> None:
    couverte = evaluer_garantie("PX200-0042", aujourdhui=date(2026, 11, 20))
    expiree = evaluer_garantie("PX200-0042", aujourdhui=date(2028, 1, 1))
    inconnue = evaluer_garantie("PX200-9999", aujourdhui=date(2026, 11, 20))
    assert couverte["statut"] == "couverte"
    assert couverte["date_expiration"] == "2027-11-01"
    assert expiree["statut"] == "expiree"
    assert inconnue["statut"] == "inconnu"
    assert ajouter_mois(date(2023, 1, 31), 1) == date(2023, 2, 28)


def test_embedding_openai_sans_cle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(MissingCredentialError):
        build_embeddings()
