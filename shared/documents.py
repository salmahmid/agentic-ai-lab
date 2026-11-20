"""Chargement de documents et validations de chemins."""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader

from shared.errors import UnsafeInputError, UnsupportedDocumentError

ALLOWED_DOCUMENT_SUFFIXES = {".pdf", ".md", ".txt", ".markdown"}
_PAGE_MARKER = re.compile(r"<!--\s*page:\s*(\d+)\s*-->", re.IGNORECASE)


def assert_within(root: Path, candidate: Path) -> Path:
    """Résout ``candidate`` et refuse tout chemin qui sort de ``root``."""

    root_resolved = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise UnsafeInputError("Chemin refusé : il sort du répertoire autorisé.") from exc
    return resolved


def safe_filename(name: str) -> str:
    """Conserve uniquement le nom de fichier et rejette les séparateurs."""

    if not name or "\x00" in name:
        raise UnsafeInputError("Nom de fichier invalide.")
    cleaned = Path(name).name
    if cleaned in {"", ".", ".."} or cleaned != name.replace("\\", "/").split("/")[-1]:
        raise UnsafeInputError("Nom de fichier invalide.")
    if "/" in name or "\\" in name or ".." in Path(name).parts:
        raise UnsafeInputError("Le nom de fichier ne doit pas contenir de chemin.")
    return cleaned


def load_text_document(path: Path, title: str | None = None) -> list[Document]:
    """Charge un fichier texte ou Markdown en conservant les marqueurs de page."""

    raw = path.read_text(encoding="utf-8")
    parts = _PAGE_MARKER.split(raw)
    documents: list[Document] = []
    if len(parts) == 1:
        documents.append(
            Document(
                page_content=raw.strip(),
                metadata={"title": title or path.stem, "source": path.name, "page": 1, "kind": "text"},
            )
        )
        return documents

    # split() avec un groupe place le numéro de page entre les segments.
    preamble, rest = parts[0], parts[1:]
    page = 1
    if preamble.strip():
        documents.append(
            Document(
                page_content=preamble.strip(),
                metadata={"title": title or path.stem, "source": path.name, "page": 1, "kind": "text"},
            )
        )
    index = 0
    while index < len(rest):
        page = int(rest[index])
        content = rest[index + 1] if index + 1 < len(rest) else ""
        if content.strip():
            documents.append(
                Document(
                    page_content=content.strip(),
                    metadata={
                        "title": title or path.stem,
                        "source": path.name,
                        "page": page,
                        "kind": "text",
                    },
                )
            )
        index += 2
    return documents


def load_pdf_document(path: Path, title: str | None = None) -> list[Document]:
    """Extrait le texte de chaque page PDF. Les pages vides sont ignorées."""

    reader = PdfReader(str(path))
    documents: list[Document] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        documents.append(
            Document(
                page_content=text.strip(),
                metadata={
                    "title": title or path.stem,
                    "source": path.name,
                    "page": index,
                    "kind": "text",
                },
            )
        )
    return documents


def load_knowledge_file(path: Path, title: str | None = None) -> list[Document]:
    """Charge un PDF, un Markdown ou un texte. Tout autre suffixe est refusé."""

    suffix = path.suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_SUFFIXES:
        raise UnsupportedDocumentError(
            f"Format '{suffix or 'sans extension'}' refusé. Formats acceptés : pdf, md, txt."
        )
    if not path.is_file():
        raise FileNotFoundError(f"Document introuvable : {path.name}")
    if suffix == ".pdf":
        return load_pdf_document(path, title=title)
    return load_text_document(path, title=title)
