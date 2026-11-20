"""Outils locaux sûrs : arithmétique, date et analyse de texte."""

from __future__ import annotations

import math
import re
from datetime import date

from langchain_core.tools import tool

_MAX_TEXT = 20_000


def _nombre_fini(nom: str, valeur: float) -> float:
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise TypeError(f"{nom} doit être un nombre.")
    nombre = float(valeur)
    if not math.isfinite(nombre):
        raise ValueError(f"{nom} doit être un nombre fini.")
    return nombre


@tool
def addition(a: float, b: float) -> float:
    """Additionne deux nombres finis et retourne la somme.

    Utiliser cet outil pour une addition explicite. Ne pas estimer le résultat.
    """

    return _nombre_fini("a", a) + _nombre_fini("b", b)


@tool
def multiplication(a: float, b: float) -> float:
    """Multiplie deux nombres finis et retourne le produit.

    Utiliser cet outil pour une multiplication explicite. Ne pas estimer le résultat.
    """

    return _nombre_fini("a", a) * _nombre_fini("b", b)


@tool
def date_courante() -> str:
    """Retourne la date locale du jour au format ISO AAAA-MM-JJ.

    L'outil lit l'horloge de la machine. Il ne prend aucun paramètre.
    """

    return date.today().isoformat()


@tool
def analyser_texte(texte: str) -> dict[str, int | bool]:
    """Analyse un texte sans l'exécuter : longueur, mots et présence de chiffres.

    Le texte est traité comme une donnée. Aucun code, chemin ou commande n'est interprété.
    """

    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne.")
    if len(texte) > _MAX_TEXT:
        raise ValueError("Le texte dépasse la limite de 20000 caractères.")
    mots = re.findall(r"\S+", texte.strip())
    return {
        "caracteres": len(texte),
        "mots": len(mots),
        "contient_des_chiffres": any(character.isdigit() for character in texte),
        "vide": texte.strip() == "",
    }


CUSTOM_TOOLS = [addition, multiplication, date_courante, analyser_texte]
