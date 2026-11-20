# Installation et exécution

Python 3.12 est la version utilisée pour la vérification locale. Le projet accepte aussi Python 3.11. Python 3.13 n'a pas été testé ici.

## Environnement

Depuis la racine du dépôt :

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Sous Windows PowerShell :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Renseigner dans `.env` uniquement les clés réellement disponibles. `EMBEDDING_PROVIDER=hash` permet d'indexer sans clé. `LLM_PROVIDER=fake` exécute les exemples d'agents avec un modèle scripté local : les outils réels sont appelés, mais aucun fournisseur cloud ne l'est.

## Commandes de démonstration

Les commandes ci-dessous ont été exécutées avec `LLM_PROVIDER=fake` et `EMBEDDING_PROVIDER=hash`, sauf les serveurs de longue durée et les interfaces graphiques.

```bash
python -m langchain_agents.basic_agent --message "Combien font 2 + 3 ?"
python -m langchain_agents.memory_agent --thread-id fil-demo --message "Je m'appelle Salma" --message "Quel est mon historique ?"
python -m langchain_agents.middleware_examples --scenario all
python -m langchain_agents.rag.ingest
python -m langchain_agents.rag.agent --question "Quel est l'objectif du laboratoire ?"
python -m langgraph_workflows.fundamentals.linear
python -m langgraph_workflows.fundamentals.conditional
python -m langgraph_workflows.fundamentals.reducer_example
python -m langgraph_workflows.fundamentals.cycle
python -m langgraph_workflows.fundamentals.checkpoint
python -m langgraph_workflows.agentic_rag.graph --question "Quel est l'objectif du laboratoire Agentic AI Lab ?"
python -m customer_support.rag.ingest
```

## Serveurs MCP

Deux terminaux :

```bash
python -m mcp_integration.server
python -m customer_support.mcp_server.server
```

Les URL par défaut sont `http://127.0.0.1:8000/mcp` et `http://127.0.0.1:8001/mcp`. Un troisième terminal peut ensuite lancer :

```bash
python -m mcp_integration.client_agent
```

Sans serveur, le client s'arrête avec une erreur. Il n'affiche pas de somme inventée.

## Streamlit

```bash
streamlit run langgraph_workflows/streamlit_app.py
streamlit run customer_support/app.py
```

L'application de support n'affiche une réponse documentaire qu'après le démarrage du second serveur MCP. Le 20 novembre 2026, Chrome a soumis la question du voyant `img_px200_01` et la question de garantie `PX200-0042`. Les captures sont `docs/screenshots/streamlit-support-documentation.png` et `docs/screenshots/streamlit-support-garantie.png`. La question RAG est dans `docs/screenshots/streamlit-rag.png`.

## Tests

```bash
pytest
```

La suite utilise des modèles scriptés, des embeddings de hachage et, pour deux tests, de vrais serveurs MCP locaux. Elle ne dépend pas d'une clé API.

## LangGraph Studio et n8n

Ces deux environnements sont documentés dans le README. Leur installation n'est pas exigée pour `pytest`.

Le 20 novembre 2026, Studio a affiché le graphe `reducteur`. La capture est `docs/screenshots/langgraph-studio.png`. Sans l'autorisation Chrome d'accès au réseau local, la page HTTPS affiche `Failed to fetch`. `langgraph-api` 0.18.3 refuse aussi la prérequête réseau privé. Le module `langgraph_workflows/studio_cors.py`, déclaré dans `langgraph.json`, corrige ce refus sans modifier `.venv`. Après réinstallation, relancer `langgraph dev` : le correctif est dans le projet.

n8n 2.48.7 tourne dans Docker sur `http://127.0.0.1:5678`. Le workflow est importé. `userManagement.isInstanceOwnerSetUp` vaut `false` et aucune credential n'est enregistrée. L'agent n'a donc pas appelé `add_numbers`. Depuis le conteneur, l'URL MCP reste `http://host.docker.internal:18000/mcp`. Ne pas utiliser le port hôte 8000 : un autre conteneur l'occupe.
