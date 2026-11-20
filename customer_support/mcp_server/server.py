"""Serveur MCP du RAG multimodal. Transport Streamable HTTP, port 8001 par défaut."""

from __future__ import annotations

import argparse
from typing import Any

from fastmcp import FastMCP

from customer_support.rag.pipeline import repondre_documentation
from shared.config import get_settings
from shared.errors import LabError

mcp = FastMCP(
    "agentic-ai-lab-documentation",
    instructions=(
        "Outil rag_multimodal : répond à une question sur les manuels techniques fictifs. "
        "Le mode texte dégradé est signalé lorsqu'aucun modèle de vision n'est disponible."
    ),
)


@mcp.tool
def rag_multimodal(
    question: str,
    image_reference: str = "",
    device_model: str = "",
    image_path: str = "",
) -> dict[str, Any]:
    """Recherche les manuels et, si un modèle de vision est configuré, interprète l'image fournie."""

    try:
        return repondre_documentation(
            question=question,
            image_reference=image_reference or None,
            device_model=device_model or None,
            image_path=image_path or None,
        )
    except LabError as exc:
        return {
            "ok": False,
            "pertinent": False,
            "reponse": str(exc),
            "sources": [],
            "mode_visuel": None,
            "erreur": str(exc),
        }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Démarre le serveur MCP documentaire.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)
    reglages = get_settings()
    mcp.run(
        transport="streamable-http",
        host=args.host or reglages.mcp_rag_host,
        port=args.port or reglages.mcp_rag_port,
    )


if __name__ == "__main__":
    main()
