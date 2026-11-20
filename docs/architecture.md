# Architecture

Ce document décrit les flux réellement implémentés dans le dépôt. Les serveurs MCP sont des processus séparés. Le 20 novembre 2026, l'API `langgraph dev` et le CLI MCP Inspector ont été exécutés. n8n n'était pas installé. Aucun navigateur n'a ouvert Studio, Streamlit ou l'inspecteur. La vision réelle des pixels n'a pas été exécutée : sans clé, le pipeline reste en `texte_degrade`.

## Vue d'ensemble

```mermaid
flowchart LR
    utilisateur[Utilisateur]
    agents[Agents LangChain]
    graphes[Graphes LangGraph]
    demo[MCP demo :8000]
    docs[MCP documentation :8001]
    chroma[Chroma local]
    registre[Registre JSON]
    utilisateur --> agents
    utilisateur --> graphes
    agents --> chroma
    graphes --> chroma
    graphes --> demo
    graphes --> docs
    docs --> chroma
    graphes --> registre
```

## Partie A — agent LangChain

`create_agent` assemble un modèle, des outils et des middlewares. Le checkpointer LangGraph conserve les messages d'un `thread_id`. L'outil de recherche lit Chroma et retourne des citations. Si le score de recouvrement est trop faible, l'outil demande explicitement de ne pas inventer.

## Partie B — graphe RAG

```mermaid
flowchart TD
    debut[START] --> preparer
    preparer -->|salutation ou question vide| repondre
    preparer -->|question documentaire| retrouver
    retrouver --> evaluer
    evaluer -->|pertinent| repondre
    evaluer -->|essais restants| reformuler
    evaluer -->|limite atteinte| repondre
    reformuler --> retrouver
    repondre --> fin[END]
```

La reformulation n'ajoute pas le vocabulaire du corpus à une question hors sujet. Après deux reformulations, le graphe s'arrête et signale que les documents sont insuffisants.

## Partie C — MCP

Les deux serveurs utilisent FastMCP et le transport `streamable-http`. Le point d'accès est `/mcp`.

- `mcp_integration/server.py` expose `add_numbers` et `web_search`.
- `customer_support/mcp_server/server.py` expose `rag_multimodal`.
- Le client LangChain utilise `langchain.mcp.MCPAdapter` avec une URL HTTP. Une chaîne qui n'est pas une URL n'est pas acceptée par cet adaptateur, ce qui évite de lancer un fichier local par erreur.

## Partie D — support client

```mermaid
flowchart TD
    debut[START] --> classer
    classer -->|documentation| agent_documentaire
    classer -->|garantie| agent_garantie
    classer -->|vide, ambigu ou non supportee| reponse_controlee
    agent_documentaire --> fin[END]
    agent_garantie --> fin
    reponse_controlee --> fin
```

Une demande mixte ne lance aucun des deux agents. L'agent documentaire appelle uniquement l'outil MCP `rag_multimodal`. L'agent garantie lit uniquement `consulter_garantie`. Si le serveur documentaire ne répond pas, l'état contient une erreur et aucune réponse métier n'est fabriquée.

Le pipeline documentaire indexe le texte des manuels et les descriptions de figures. Un modèle de vision n'est appelé que si une clé correspondante est présente. Sinon le champ `mode_visuel` vaut `texte_degrade`.
