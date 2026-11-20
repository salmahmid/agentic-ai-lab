"""Serveurs MCP et client Streamable HTTP."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mcp_integration.client_agent import interroger, lister_et_additionner
from mcp_integration.server import add_numbers, web_search


def test_outils_locaux_du_serveur_demo() -> None:
    assert add_numbers(2, 3) == 5
    resultat = web_search("langgraph")
    assert resultat["ok"] is False
    assert resultat["results"] == []


def _port_libre() -> int:
    with socket.socket() as prise:
        prise.bind(("127.0.0.1", 0))
        return int(prise.getsockname()[1])


def _attendre(port: int) -> None:
    delai = time.time() + 25
    while time.time() < delai:
        with socket.socket() as prise:
            prise.settimeout(0.2)
            if prise.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"Le port {port} n'a pas été ouvert.")


def _serveur(module: str, port: int, journal: Path) -> subprocess.Popen[bytes]:
    environnement = os.environ.copy()
    environnement["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    journal_fichier = journal.open("w", encoding="utf-8")
    processus = subprocess.Popen(
        [sys.executable, "-m", module, "--port", str(port)],
        cwd=Path(__file__).resolve().parents[1],
        env=environnement,
        stdout=journal_fichier,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    processus.journal = journal_fichier  # type: ignore[attr-defined]
    return processus


def _arreter(processus: subprocess.Popen[bytes], journal: Path) -> str:
    try:
        os.killpg(processus.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        processus.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(processus.pid, signal.SIGKILL)
        processus.wait(timeout=5)
    fichier = getattr(processus, "journal", None)
    if fichier is not None:
        fichier.close()
    return journal.read_text(encoding="utf-8", errors="replace") if journal.is_file() else ""


def test_client_streamable_http_add_numbers(tmp_path: Path) -> None:
    port = _port_libre()
    journal = tmp_path / "demo.log"
    processus = _serveur("mcp_integration.server", port, journal)
    try:
        _attendre(port)
        url = f"http://127.0.0.1:{port}/mcp"
        decouverte = __import__("asyncio").run(lister_et_additionner(url, 20, 22))
        assert decouverte["outils"] == ["add_numbers", "web_search"]
        assert float(decouverte["resultat"]) == 42
        texte = __import__("asyncio").run(interroger(url, "Additionne 20 et 22."))
        assert "42" in texte
    except Exception:
        print(_arreter(processus, journal))
        raise
    else:
        _arreter(processus, journal)


def test_rag_multimodal_streamable_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    port = _port_libre()
    journal = tmp_path / "rag.log"
    processus = _serveur("customer_support.mcp_server.server", port, journal)
    try:
        _attendre(port)
        from customer_support.graph import appeler_rag_distant

        monkeypatch.setenv("MCP_RAG_URL", f"http://127.0.0.1:{port}/mcp")
        resultat = appeler_rag_distant(
            {
                "question": "Que signifie le voyant papier clignotant de l'imprimante PX-200 ?",
                "image_reference": "img_px200_01",
                "device_model": "PX-200",
                "image_path": "",
            }
        )
        assert resultat["ok"] is True
        assert resultat["sources"]
        assert "Tokyo" not in resultat["reponse"]
    except Exception:
        print(_arreter(processus, journal))
        raise
    else:
        _arreter(processus, journal)
