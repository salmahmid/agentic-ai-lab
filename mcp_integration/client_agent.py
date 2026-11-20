"""Client LangChain branché sur le serveur MCP de démonstration en Streamable HTTP."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from langchain.agents import create_agent
from langchain.mcp import MCPAdapter

from langchain_agents.runtime import dernier_texte
from shared.config import get_settings
from shared.errors import MCPUnavailableError
from shared.llm import ScriptedChatModel, build_chat_model
from shared.mcp_decode import decoder_mcp


async def lister_et_additionner(url: str, a: float = 2, b: float = 3) -> dict[str, Any]:
    """Découvre les outils du serveur distant et invoque ``add_numbers``."""

    try:
        async with MCPAdapter(url) as adaptateur:
            outils = await adaptateur.list_tools()
            noms = sorted(outil.name for outil in outils)
            addition = next((outil for outil in outils if outil.name == "add_numbers"), None)
            if addition is None:
                raise MCPUnavailableError("L'outil add_numbers est introuvable sur le serveur MCP.")
            brut = await addition.ainvoke({"a": a, "b": b})
    except MCPUnavailableError:
        raise
    except Exception as exc:
        raise MCPUnavailableError(
            f"Serveur MCP injoignable à {url} ({type(exc).__name__}). Aucun résultat n'a été inventé."
        ) from exc
    return {"outils": noms, "resultat": decoder_mcp(brut)}


def modele_client() -> Any:
    """Modèle cloud si les clés existent, sinon modèle scripté qui appelle ``add_numbers``."""

    if get_settings().llm_provider != "fake":
        return build_chat_model()

    def decider(messages: list[Any]) -> Any:
        from langchain_core.messages import AIMessage

        dernier = messages[-1]
        if getattr(dernier, "type", None) == "tool":
            return AIMessage(content=f"Résultat MCP : {getattr(dernier, 'content', '')}")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "add_numbers",
                    "args": {"a": 20, "b": 22},
                    "id": "mcp-add",
                    "type": "tool_call",
                }
            ],
        )

    return ScriptedChatModel(script=[decider], name_label="client-mcp")


async def interroger(url: str, message: str) -> str:
    """Construit un agent ``create_agent`` dont les outils viennent du serveur MCP."""

    try:
        async with MCPAdapter(url) as adaptateur:
            outils = await adaptateur.list_tools()
            agent = create_agent(
                model=modele_client(),
                tools=outils,
                system_prompt=(
                    "Tu es un agent connecté à un serveur MCP en Streamable HTTP. "
                    "Utilise add_numbers pour une addition. "
                    "Si web_search retourne une erreur de clé, explique-la sans inventer de pages."
                ),
            )
            resultat = await agent.ainvoke({"messages": [{"role": "user", "content": message}]})
            return dernier_texte(resultat)
    except Exception as exc:
        raise MCPUnavailableError(
            f"Échec du client MCP sur {url} ({type(exc).__name__})."
        ) from exc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Client MCP LangChain en Streamable HTTP.")
    parser.add_argument("--url", default=None)
    parser.add_argument("--message", default="Additionne 20 et 22 avec l'outil MCP.")
    args = parser.parse_args(argv)
    url = args.url or get_settings().mcp_demo_url
    try:
        print(asyncio.run(interroger(url, args.message)))
    except MCPUnavailableError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
