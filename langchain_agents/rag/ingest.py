"""Ingestion du corpus pédagogique de la partie LangChain."""

from __future__ import annotations

import argparse
from pathlib import Path

from shared.config import get_settings
from shared.index import KnowledgeIndex

CORPUS = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def repertoire_index() -> Path:
    return get_settings().root / "data" / "chroma_laboratoire"


def construire_index(persistance: Path | None = None) -> KnowledgeIndex:
    return KnowledgeIndex(persistance or repertoire_index(), "laboratoire")


def ingerer_corpus(persistance: Path | None = None) -> int:
    """Indexe les fichiers Markdown, texte et PDF du corpus pédagogique."""

    fichiers = sorted(
        chemin
        for chemin in CORPUS.iterdir()
        if chemin.is_file() and chemin.suffix.lower() in {".md", ".txt", ".pdf", ".markdown"}
    )
    if not fichiers:
        raise FileNotFoundError(f"Aucun document dans {CORPUS}")
    return construire_index(persistance).ingerer_fichiers(fichiers, titre="Guide du laboratoire")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingère le corpus pédagogique dans Chroma.")
    parser.parse_args(argv)
    nombre = ingerer_corpus()
    print(f"Corpus indexé : {nombre} fragments dans {repertoire_index()}")


if __name__ == "__main__":
    main()
