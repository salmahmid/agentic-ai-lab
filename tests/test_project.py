"""Contrats statiques : configuration Studio, workflow n8n et interfaces."""

from __future__ import annotations

import ast
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def test_langgraph_json_expose_les_graphes() -> None:
    config = json.loads((RACINE / "langgraph.json").read_text(encoding="utf-8"))
    assert "support_client" in config["graphs"]
    assert "rag_agentique" in config["graphs"]
    for valeur in config["graphs"].values():
        chemin, symbole = valeur.split(":")
        fichier = RACINE / chemin
        assert fichier.is_file()
        source = fichier.read_text(encoding="utf-8")
        assert f"{symbole} =" in source or f"def {symbole}" in source


def test_preflight_studio_reseau_prive() -> None:
    """Le refus CORS de langgraph-api 0.18.3 est corrigé par le module du projet."""

    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.testclient import TestClient

    from langgraph_workflows.studio_cors import AutoriserReseauPrive

    application = AutoriserReseauPrive(
        CORSMiddleware(
            Starlette(),
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    )
    client = TestClient(application)
    reponse = client.options(
        "/ok",
        headers={
            "Origin": "https://smith.langchain.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    assert reponse.status_code == 200
    assert reponse.headers["access-control-allow-private-network"] == "true"
    assert reponse.text == "OK"


def test_workflow_n8n() -> None:
    workflow = json.loads((RACINE / "mcp_integration/n8n/workflow.json").read_text(encoding="utf-8"))
    types = {noeud["type"] for noeud in workflow["nodes"]}
    assert "@n8n/n8n-nodes-langchain.agent" in types
    assert "@n8n/n8n-nodes-langchain.lmChatOpenAi" in types
    assert "@n8n/n8n-nodes-langchain.mcpClientTool" in types
    mcp = next(noeud for noeud in workflow["nodes"] if noeud["type"].endswith("mcpClientTool"))
    assert mcp["parameters"]["serverTransport"] == "httpStreamable"
    assert "MCP_DEMO_URL" in mcp["parameters"]["endpointUrl"]
    assert "Agent MCP" in workflow["connections"]["Outils MCP"]["ai_tool"][0][0]["node"]


def test_interfaces_streamlit_sont_analysables() -> None:
    for relatif in ("langgraph_workflows/streamlit_app.py", "customer_support/app.py"):
        source = (RACINE / relatif).read_text(encoding="utf-8")
        ast.parse(source)
        assert "st.chat_input" in source or "st.form" in source
        assert "Effacer" in source
        assert "st.spinner" in source
        assert "st.error" in source or "st.warning" in source
