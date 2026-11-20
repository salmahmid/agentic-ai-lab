"""Validations d'entrées du support client."""

from __future__ import annotations

import re
from pathlib import Path

from shared.documents import assert_within
from shared.errors import UnsafeInputError, UnsupportedDocumentError

_IMAGE_REF = re.compile(r"^img_[a-z0-9_]{1,40}$")
_SERIE = re.compile(r"^[A-Z]{2,8}\d{2,6}-\d{3,8}$")
_SUFFIXES_IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_TAILLE_MAX = 5 * 1024 * 1024


def valider_reference_image(valeur: str | None) -> str | None:
    """Accepte uniquement un identifiant de catalogue, jamais un chemin."""

    if valeur is None or not str(valeur).strip():
        return None
    reference = str(valeur).strip()
    if not _IMAGE_REF.fullmatch(reference):
        raise UnsafeInputError("Référence d'image refusée.")
    return reference


def valider_numero_serie(valeur: str | None) -> str | None:
    """Valide un numéro de série sans l'utiliser comme chemin de fichier."""

    if valeur is None or not str(valeur).strip():
        return None
    numero = str(valeur).strip().upper()
    if not _SERIE.fullmatch(numero):
        raise UnsafeInputError("Numéro de série refusé.")
    return numero


def chemin_image_autorise(chemin: str | Path, racines: list[Path]) -> Path:
    """Résout une image uniquement si elle reste dans un répertoire autorisé."""

    candidat = Path(chemin)
    if candidat.suffix.lower() not in _SUFFIXES_IMAGE:
        raise UnsupportedDocumentError("Format d'image refusé.")
    for racine in racines:
        try:
            resolu = assert_within(racine, candidat)
        except UnsafeInputError:
            continue
        if not resolu.is_file():
            raise UnsafeInputError("Image introuvable dans la zone autorisée.")
        if resolu.stat().st_size > _TAILLE_MAX:
            raise UnsafeInputError("Image trop volumineuse (maximum 5 Mo).")
        return resolu
    raise UnsafeInputError("Chemin d'image refusé.")
