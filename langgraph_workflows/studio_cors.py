"""Corrige la prérequête CORS de LangGraph Studio.

`langgraph-api` 0.18.3, la dernière version publiée au 20 novembre 2026,
active `ALLOW_PRIVATE_NETWORK` avec `langgraph dev` mais ne le transmet pas
à `CORSMiddleware`. Starlette répond alors `400 Disallowed CORS private-network`.
Chrome affiche `Failed to fetch`.

Aucune option de `langgraph.json`, aucune variable d'environnement et aucun
argument du CLI ne passent `allow_private_network=true` au middleware CORS.
Le champ `http.cors` est validé par un schéma qui ignore cette clé.

Ce module est le contournement pris en charge par la configuration officielle
`http.app` : https://docs.langchain.com/langsmith/custom-middleware
Il ne modifie pas les graphes. Il ne change une réponse que lorsque le refus
concerne exclusivement le réseau privé.
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REFUS_RESEAU_PRIVE = b"Disallowed CORS private-network"


class AutoriserReseauPrive(BaseHTTPMiddleware):
    """Transforme le seul refus de réseau privé en prérequête acceptée."""

    async def dispatch(self, request: Request, call_next):
        reponse = await call_next(request)
        if request.method != "OPTIONS":
            return reponse
        if request.headers.get("access-control-request-private-network") != "true":
            return reponse
        corps = b""
        async for morceau in reponse.body_iterator:
            corps += morceau
        if corps != _REFUS_RESEAU_PRIVE:
            return Response(
                content=corps,
                status_code=reponse.status_code,
                headers=_entetes(reponse),
                media_type=reponse.media_type,
            )
        entetes = _entetes(reponse)
        entetes["access-control-allow-private-network"] = "true"
        return Response(content=b"OK", status_code=200, headers=entetes, media_type="text/plain")


def _entetes(reponse: Response) -> dict[str, str]:
    return {cle: valeur for cle, valeur in reponse.headers.items() if cle.lower() != "content-length"}


app = Starlette()
app.add_middleware(AutoriserReseauPrive)
