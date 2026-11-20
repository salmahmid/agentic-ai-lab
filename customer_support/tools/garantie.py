"""Lecture seule du registre de garantie et calcul du statut à la date du jour."""

from __future__ import annotations

import calendar
import json
from datetime import date
from pathlib import Path

from customer_support.validation import valider_numero_serie
from shared.errors import UnsafeInputError

REGISTRE = Path(__file__).resolve().parent.parent / "data" / "registry" / "garanties.json"


def ajouter_mois(jour: date, mois: int) -> date:
    """Ajoute un nombre de mois civils sans dépasser le dernier jour du mois cible."""

    total = jour.month - 1 + mois
    annee = jour.year + total // 12
    mois_cible = total % 12 + 1
    jour_cible = min(jour.day, calendar.monthrange(annee, mois_cible)[1])
    return date(annee, mois_cible, jour_cible)


def _lire_registre() -> list[dict[str, object]]:
    with REGISTRE.open("r", encoding="utf-8") as fichier:
        contenu = json.load(fichier)
    return list(contenu.get("enregistrements", []))


def evaluer_garantie(numero_serie: str, aujourdhui: date | None = None) -> dict[str, str]:
    """Calcule le statut. ``aujourdhui`` est réservé aux tests ; l'outil public utilise la date du jour."""

    try:
        numero = valider_numero_serie(numero_serie)
    except UnsafeInputError as exc:
        return {
            "numero_serie": str(numero_serie),
            "produit": "",
            "date_achat": "",
            "date_expiration": "",
            "statut": "inconnu",
            "explication": str(exc),
        }
    if numero is None:
        return {
            "numero_serie": "",
            "produit": "",
            "date_achat": "",
            "date_expiration": "",
            "statut": "inconnu",
            "explication": "Aucun numéro de série n'a été fourni.",
        }
    jour = aujourdhui or date.today()
    for enregistrement in _lire_registre():
        if str(enregistrement.get("numero_serie", "")).upper() != numero:
            continue
        achat = date.fromisoformat(str(enregistrement["date_achat"]))
        expiration = ajouter_mois(achat, int(enregistrement["duree_mois"]))
        couvert = jour <= expiration
        statut = "couverte" if couvert else "expiree"
        explication = (
            f"Garantie {statut} au {jour.isoformat()} : "
            f"achetée le {achat.isoformat()}, expire le {expiration.isoformat()}."
        )
        return {
            "numero_serie": numero,
            "produit": str(enregistrement.get("modele", "")),
            "date_achat": achat.isoformat(),
            "date_expiration": expiration.isoformat(),
            "statut": statut,
            "explication": explication,
        }
    return {
        "numero_serie": numero,
        "produit": "",
        "date_achat": "",
        "date_expiration": "",
        "statut": "inconnu",
        "explication": f"Le numéro {numero} est absent du registre de garantie.",
    }


def consulter_garantie(numero_serie: str) -> dict[str, str]:
    """Outil local de l'agent garantie. Il ne consulte ni le RAG ni le réseau."""

    return evaluer_garantie(numero_serie)
