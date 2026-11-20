"""Crée les images et le PDF fictifs à partir du manuel Markdown."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent
MANUEL = DATA / "manuals" / "manuel_px200.md"
PDF = DATA / "manuals" / "manuel_px200.pdf"
IMAGES = DATA / "images"
CATALOGUE = IMAGES / "catalogue.json"

_POLICES = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def ecrire_images() -> None:
    """Dessine deux schémas originaux. Ce ne sont pas des visuels de fabricant."""

    from PIL import Image, ImageDraw

    IMAGES.mkdir(parents=True, exist_ok=True)
    voyant = Image.new("RGB", (640, 360), "white")
    dessin = ImageDraw.Draw(voyant)
    dessin.rounded_rectangle((40, 40, 600, 320), radius=16, outline="black", width=3)
    dessin.rectangle((250, 130, 300, 190), outline="black", width=3)
    dessin.polygon([(275, 120), (255, 145), (295, 145)], fill="black")
    dessin.ellipse((330, 145, 390, 205), fill="orange", outline="black")
    dessin.text((70, 70), "PX-200 - schema fictif", fill="black")
    dessin.text((70, 250), "img_px200_01 voyant papier clignotant", fill="black")
    voyant.save(IMAGES / "img_px200_01.png")

    cartouche = Image.new("RGB", (640, 360), "white")
    dessin = ImageDraw.Draw(cartouche)
    dessin.rounded_rectangle((40, 40, 600, 320), radius=16, outline="black", width=3)
    dessin.rounded_rectangle((180, 110, 460, 240), radius=12, outline="black", width=4)
    dessin.rectangle((210, 140, 430, 210), fill="#d9e8ff", outline="black")
    dessin.text((70, 70), "PX-200 - schema fictif", fill="black")
    dessin.text((70, 260), "img_px200_02 logement de cartouche", fill="black")
    cartouche.save(IMAGES / "img_px200_02.png")


def ecrire_pdf() -> None:
    """Produit un PDF texte à partir des pages marquées dans le Markdown."""

    from fpdf import FPDF

    pages = _pages_markdown()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    police = next((chemin for chemin in _POLICES if Path(chemin).is_file()), None)
    if police:
        pdf.add_font("Manuel", "", police)
        pdf.set_font("Manuel", size=12)
    else:
        pdf.set_font("Helvetica", size=12)
        pages = [_sans_accents(page) for page in pages]
    for page in pages:
        pdf.add_page()
        pdf.multi_cell(0, 7, page)
    PDF.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(PDF))


def ensure_sample_assets() -> None:
    """Crée les fichiers binaires de démonstration s'ils sont absents ou vides."""

    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    manquantes = [IMAGES / item["fichier"] for item in catalogue.values()]
    if any(not chemin.is_file() or chemin.stat().st_size == 0 for chemin in manquantes):
        ecrire_images()
    if not PDF.is_file() or PDF.stat().st_size == 0:
        ecrire_pdf()


def _pages_markdown() -> list[str]:
    brut = MANUEL.read_text(encoding="utf-8")
    morceaux = [morceau.strip() for morceau in brut.split("<!-- page:")]
    pages: list[str] = []
    for morceau in morceaux:
        if not morceau:
            continue
        _, _, contenu = morceau.partition("-->")
        texte = contenu.strip() if contenu else morceau
        if texte:
            pages.append(texte)
    if not pages:
        raise RuntimeError("Le manuel Markdown ne contient aucune page.")
    return pages


def _sans_accents(texte: str) -> str:
    correspondances = str.maketrans("àâäéèêëïîôùûüçÀÂÄÉÈÊËÏÎÔÙÛÜÇ", "aaaeeeeiioouuucAAAEEEEIIOOUUUC")
    return texte.translate(correspondances)
