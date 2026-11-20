"""Serveur MCP de démonstration : addition et recherche web.

Transport : Streamable HTTP. Point d'accès par défaut : http://127.0.0.1:8000/mcp
"""

from __future__ import annotations

import argparse
import math
from typing import Any

from fastmcp import FastMCP

from langchain_agents.tools.predefined import recherche_tavily
from shared.config import get_settings

mcp = FastMCP(
    "agentic-ai-lab-demo",
    instructions=(
        "Serveur de démonstration. add_numbers additionne deux nombres. "
        "web_search interroge Tavily uniquement si TAVILY_API_KEY est définie."
    ),
)


@mcp.tool
def add_numbers(a: float, b: float) -> float:
    """Additionne deux nombres finis et retourne la somme."""

    if isinstance(a, bool) or isinstance(b, bool):
        raise ValueError("Les booléens ne sont pas acceptés.")
    if not math.isfinite(float(a)) or not math.isfinite(float(b)):
        raise ValueError("Les opérandes doivent être des nombres finis.")
    return float(a) + float(b)


@mcp.tool
def web_search(query: str) -> dict[str, Any]:
    """Recherche le web via Tavily. Retourne une erreur explicite si la clé est absente."""

    return recherche_tavily(query)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Démarre le serveur MCP de démonstration.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)
    reglages = get_settings()
    hote = args.host or reglages.mcp_demo_host
    port = args.port or reglages.mcp_demo_port
    mcp.run(transport="streamable-http", host=hote, port=port)


if __name__ == "__main__":
    main()
