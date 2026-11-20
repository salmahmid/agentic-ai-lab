"""Outils locaux et recherches prédéfinies."""

from __future__ import annotations

import json
from datetime import date

import pytest

from langchain_agents.tools.custom import addition, analyser_texte, date_courante, multiplication
from langchain_agents.tools.predefined import (
    avertissement_repl,
    executer_python_fiable,
    recherche_duckduckgo,
    recherche_tavily,
)


def test_arithmetique_et_date() -> None:
    assert addition.invoke({"a": 2, "b": 3.5}) == 5.5
    assert multiplication.invoke({"a": 4, "b": 5}) == 20
    assert date_courante.invoke({}) == date.today().isoformat()


def test_analyse_texte_ne_execute_rien() -> None:
    resultat = analyser_texte.invoke({"texte": "Deux mots 12"})
    assert resultat["mots"] == 3
    assert resultat["contient_des_chiffres"] is True
    with pytest.raises(ValueError):
        analyser_texte.invoke({"texte": "x" * 20001})


def test_addition_refuse_infini() -> None:
    with pytest.raises(ValueError):
        addition.invoke({"a": float("inf"), "b": 1})


def test_tavily_sans_cle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    resultat = recherche_tavily("langgraph")
    assert resultat["ok"] is False
    assert "TAVILY_API_KEY" in resultat["error"]
    assert resultat["results"] == []


def test_tavily_erreur_reseau_masque_la_cle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "secret-tavily")

    class Client:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def search(self, query: str, max_results: int) -> dict:
            raise RuntimeError(f"panne avec {self.api_key}")

    monkeypatch.setattr("tavily.TavilyClient", Client)
    resultat = recherche_tavily("langgraph")
    assert resultat["ok"] is False
    assert "secret-tavily" not in resultat["error"]


def test_duckduckgo_panne(monkeypatch: pytest.MonkeyPatch) -> None:
    class DDGS:
        def __enter__(self) -> DDGS:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def text(self, query: str, max_results: int) -> list[dict[str, str]]:
            raise ConnectionError("réseau indisponible")

    monkeypatch.setattr("ddgs.DDGS", DDGS)
    resultat = recherche_duckduckgo("langgraph")
    assert resultat["ok"] is False
    assert resultat["results"] == []


def test_duckduckgo_resultat(monkeypatch: pytest.MonkeyPatch) -> None:
    class DDGS:
        def __enter__(self) -> DDGS:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def text(self, query: str, max_results: int) -> list[dict[str, str]]:
            return [{"title": "Doc", "href": "https://example.test", "body": query}]

    monkeypatch.setattr("ddgs.DDGS", DDGS)
    resultat = recherche_duckduckgo("langgraph")
    assert resultat["ok"] is True
    assert resultat["results"][0]["url"] == "https://example.test"


def test_repl_bloque_par_defaut() -> None:
    assert "jamais branché" in avertissement_repl()
    with pytest.raises(PermissionError):
        executer_python_fiable("2 + 2")


def test_repl_expression_autorisee(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTIC_ALLOW_PYTHON_REPL", "true")
    assert executer_python_fiable("2 + 2").strip() == "4"
    with pytest.raises(PermissionError):
        executer_python_fiable("import os")


def test_outils_langchain_predefinis() -> None:
    from langchain_agents.tools.predefined import outil_duckduckgo_langchain, outil_tavily_langchain

    outil = outil_duckduckgo_langchain()
    assert outil.name
    with pytest.raises(RuntimeError):
        outil_tavily_langchain()


def test_sortie_json_outil_tavily() -> None:
    from langchain_agents.tools.predefined import recherche_tavily_outil

    charge = json.loads(recherche_tavily_outil.invoke({"requete": "test"}))
    assert charge["ok"] is False
