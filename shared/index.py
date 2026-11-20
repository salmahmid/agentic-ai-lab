"""Index Chroma réutilisable par les agents et les graphes."""

from __future__ import annotations

from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from shared.documents import load_knowledge_file
from shared.embeddings import build_embeddings
from shared.text import overlap_score


class KnowledgeIndex:
    """Petit index local. L'ingestion remplace la collection pour rester reproductible."""

    def __init__(self, persist_directory: Path, collection_name: str) -> None:
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.embeddings = build_embeddings()
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.store = self._ouvrir()
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)

    def _ouvrir(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            client=self.client,
        )

    def remplacer(self, documents: list[Document]) -> int:
        """Efface la collection puis indexe les documents fournis."""

        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.store = self._ouvrir()
        if not documents:
            return 0
        morceaux = self.splitter.split_documents(documents)
        morceaux = [morceau for morceau in morceaux if morceau.page_content.strip()]
        if morceaux:
            self.store.add_documents(morceaux)
        return len(morceaux)

    def ingerer_fichiers(self, fichiers: list[Path], titre: str | None = None) -> int:
        documents: list[Document] = []
        for fichier in fichiers:
            documents.extend(load_knowledge_file(fichier, title=titre))
        return self.remplacer(documents)

    def rechercher(self, requete: str, k: int = 4) -> list[Document]:
        """Recherche vectorielle puis réordonne par recouvrement lexical."""

        if self.store._collection.count() == 0:
            return []
        candidats = self.store.similarity_search(requete, k=max(k * 3, 8))
        candidats.sort(key=lambda document: overlap_score(requete, document.page_content), reverse=True)
        return candidats[:k]


def citation(document: Document) -> dict[str, object]:
    """Citation exploitable par l'interface : titre, page et extrait."""

    return {
        "titre": document.metadata.get("title"),
        "page": document.metadata.get("page"),
        "source": document.metadata.get("source"),
        "type": document.metadata.get("kind", "text"),
        "reference_image": document.metadata.get("image_ref"),
        "extrait": document.page_content[:400],
    }
