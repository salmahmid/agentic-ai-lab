"""Orchestrateur LangGraph : une demande, un seul agent, puis l'arrêt."""

from __future__ import annotations

import asyncio
import operator
import re
import threading
from typing import Annotated, Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from customer_support.tools.garantie import evaluer_garantie
from customer_support.validation import valider_numero_serie
from shared.config import get_settings
from shared.errors import MCPUnavailableError, UnsafeInputError
from shared.mcp_decode import decoder_mcp
from shared.text import normalize

_DOC = (
    "voyant",
    "pictogramme",
    "manuel",
    "documentation",
    "photo",
    "image",
    "bourrage",
    "cartouche",
    "papier",
    "signifie",
    "signification",
)
_GARANTIE = ("garantie", "numero de serie", "numéro de série", "sous garantie", "warranty")
_SERIE = re.compile(r"\b[A-Z]{2,8}\d{2,6}-\d{3,8}\b")
AppelRAG = Callable[[dict[str, str]], dict[str, Any]]
EvaluationGarantie = Callable[[str], dict[str, str]]


class EtatSupport(TypedDict, total=False):
    """État explicite de l'orchestrateur."""

    question: str
    reference_image: str | None
    chemin_image: str | None
    numero_serie: str | None
    categorie: str
    agent: str | None
    reponse: str
    sources: list[dict[str, Any]]
    garantie: dict[str, str] | None
    erreur: str | None
    mode_visuel: str | None
    termine: bool
    etapes: Annotated[list[str], operator.add]


def classer_demande(question: str, numero_serie: str | None = None) -> str:
    """Choisit exactement une catégorie. Une demande mixte n'exécute aucun agent."""

    if not question or not question.strip():
        return "invalide"
    texte = normalize(question)
    documentaire = any(normalize(mot) in texte for mot in _DOC)
    garantie = any(normalize(mot) in texte for mot in _GARANTIE) or bool(_SERIE.search(question.upper()))
    if numero_serie and str(numero_serie).strip():
        garantie = True
    if documentaire and garantie:
        return "ambigu"
    if garantie:
        return "garantie"
    if documentaire:
        return "documentation"
    return "non_supportee"


def modele_appareil(question: str) -> str:
    if "px-200" in question.lower() or "px200" in question.lower():
        return "PX-200"
    return ""


def executer_coroutine(coroutine: Any) -> Any:
    """Exécute une coroutine même si une boucle asyncio est déjà ouverte."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    boite: dict[str, Any] = {}

    def cible() -> None:
        try:
            boite["valeur"] = asyncio.run(coroutine)
        except Exception as exc:  # propagée au fil appelant
            boite["erreur"] = exc

    fil = threading.Thread(target=cible)
    fil.start()
    fil.join()
    if "erreur" in boite:
        raise boite["erreur"]
    return boite["valeur"]


def appeler_rag_distant(payload: dict[str, str]) -> dict[str, Any]:
    """Appelle l'outil distant ``rag_multimodal``. Un échec réseau n'est pas masqué."""

    async def appel() -> Any:
        from langchain.mcp import MCPAdapter

        async with MCPAdapter(get_settings().mcp_rag_url) as adaptateur:
            outils = await adaptateur.list_tools()
            outil = next((candidat for candidat in outils if candidat.name == "rag_multimodal"), None)
            if outil is None:
                raise MCPUnavailableError("L'outil rag_multimodal est absent du serveur MCP.")
            return await outil.ainvoke(payload)

    try:
        brut = executer_coroutine(appel())
    except MCPUnavailableError:
        raise
    except Exception as exc:
        raise MCPUnavailableError(
            f"Serveur MCP documentaire injoignable ({type(exc).__name__})."
        ) from exc
    valeur = decoder_mcp(brut)
    if isinstance(valeur, dict):
        return valeur
    raise MCPUnavailableError("Réponse MCP documentaire illisible.")


def construire(appel_rag: AppelRAG | None = None, evaluer: EvaluationGarantie | None = None):
    """Compile l'orchestrateur. Les dépendances sont injectables dans les tests."""

    rag = appel_rag or appeler_rag_distant
    garantie = evaluer or evaluer_garantie

    def classer(etat: EtatSupport) -> dict[str, Any]:
        try:
            numero = valider_numero_serie(etat.get("numero_serie"))
        except UnsafeInputError as exc:
            return {
                "categorie": "invalide",
                "erreur": str(exc),
                "etapes": ["classification:invalide"],
            }
        categorie = classer_demande(etat.get("question", ""), numero)
        return {"categorie": categorie, "numero_serie": numero, "etapes": [f"classification:{categorie}"]}

    def choisir(etat: EtatSupport) -> str:
        categorie = etat.get("categorie")
        if categorie == "documentation":
            return "agent_documentaire"
        if categorie == "garantie":
            return "agent_garantie"
        return "reponse_controlee"

    def agent_documentaire(etat: EtatSupport) -> dict[str, Any]:
        payload = {
            "question": etat.get("question", ""),
            "image_reference": etat.get("reference_image") or "",
            "device_model": modele_appareil(etat.get("question", "")),
            "image_path": etat.get("chemin_image") or "",
        }
        try:
            resultat = rag(payload)
        except Exception as exc:
            return {
                "agent": "agent_documentaire",
                "reponse": "Le service documentaire MCP est indisponible. Aucune réponse n'a été inventée.",
                "sources": [],
                "erreur": str(exc),
                "termine": True,
                "etapes": ["agent_documentaire", "mcp:echec", "fin"],
            }
        if not resultat.get("ok", False):
            message = str(resultat.get("erreur") or resultat.get("reponse") or "Demande documentaire refusée.")
            return {
                "agent": "agent_documentaire",
                "reponse": message,
                "sources": [],
                "erreur": message,
                "mode_visuel": resultat.get("mode_visuel"),
                "termine": True,
                "etapes": ["agent_documentaire", "mcp:rag_multimodal", "fin"],
            }
        return {
            "agent": "agent_documentaire",
            "reponse": str(resultat.get("reponse", "")),
            "sources": list(resultat.get("sources", [])),
            "erreur": resultat.get("erreur"),
            "mode_visuel": resultat.get("mode_visuel"),
            "termine": True,
            "etapes": ["agent_documentaire", "mcp:rag_multimodal", "fin"],
        }

    def agent_garantie(etat: EtatSupport) -> dict[str, Any]:
        numero = etat.get("numero_serie") or ""
        if not numero:
            trouve = _SERIE.search(etat.get("question", "").upper())
            numero = trouve.group(0) if trouve else ""
        resultat = garantie(numero)
        return {
            "agent": "agent_garantie",
            "garantie": resultat,
            "reponse": resultat["explication"],
            "sources": [],
            "termine": True,
            "etapes": ["agent_garantie", "outil:consulter_garantie", "fin"],
        }

    def reponse_controlee(etat: EtatSupport) -> dict[str, Any]:
        messages = {
            "invalide": etat.get("erreur") or "La demande est vide.",
            "ambigu": (
                "La demande mélange documentation et garantie. "
                "Formulez une seule catégorie afin qu'un seul agent soit exécuté."
            ),
            "non_supportee": "Seules les demandes de documentation et de garantie sont prises en charge.",
        }
        categorie = etat.get("categorie", "non_supportee")
        return {
            "agent": None,
            "reponse": messages.get(categorie, messages["non_supportee"]),
            "erreur": messages.get(categorie, messages["non_supportee"]),
            "sources": [],
            "termine": True,
            "etapes": ["reponse_controlee", "fin"],
        }

    graphe = StateGraph(EtatSupport)
    graphe.add_node("classer", classer)
    graphe.add_node("agent_documentaire", agent_documentaire)
    graphe.add_node("agent_garantie", agent_garantie)
    graphe.add_node("reponse_controlee", reponse_controlee)
    graphe.add_edge(START, "classer")
    graphe.add_conditional_edges(
        "classer",
        choisir,
        {
            "agent_documentaire": "agent_documentaire",
            "agent_garantie": "agent_garantie",
            "reponse_controlee": "reponse_controlee",
        },
    )
    graphe.add_edge("agent_documentaire", END)
    graphe.add_edge("agent_garantie", END)
    graphe.add_edge("reponse_controlee", END)
    return graphe.compile()


graph = construire()


def traiter_demande(
    question: str,
    reference_image: str | None = None,
    chemin_image: str | None = None,
    numero_serie: str | None = None,
    appel_rag: AppelRAG | None = None,
    evaluer: EvaluationGarantie | None = None,
) -> dict[str, Any]:
    """Exécute l'orchestrateur jusqu'à la réponse finale."""

    compile = graph if appel_rag is None and evaluer is None else construire(appel_rag, evaluer)
    return compile.invoke(
        {
            "question": question,
            "reference_image": reference_image,
            "chemin_image": chemin_image,
            "numero_serie": numero_serie,
            "etapes": [],
            "sources": [],
            "termine": False,
        },
        config={"recursion_limit": 12},
    )
