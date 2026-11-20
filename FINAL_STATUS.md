# État du laboratoire

Vérification du 20 novembre 2026. Aucun commit et aucun dépôt GitHub n'ont été créés.

## Terminé

- pytest : 44 passed, 3 warnings, en 3,29 s. Le test ajouté couvre la prérequête Studio. Les avertissements viennent de `langchain.mcp`, `langchain-experimental` et `langchain-community`.
- Cinq services déjà validés, laissés actifs : LangGraph `127.0.0.1:2024`, Streamlit RAG `8501`, Streamlit support `8502`, MCP démo `127.0.0.1:8000`, MCP documentation `127.0.0.1:8001`.
- Chrome a exécuté les trois parcours Streamlit. Les images sont dans `docs/screenshots/`.
- Studio : `docs/screenshots/langgraph-studio.png` montre `reducteur` (`__start__` → `premiere` → `seconde` → `__end__`). Le correctif CORS est `langgraph_workflows/studio_cors.py`, chargé par `langgraph.json`. Il survit à une réinstallation. Le correctif temporaire dans `.venv` a été retiré. La prérequête réseau privé répond `200` sans ce correctif de paquet.
- Docker 29.6.2 et Docker Compose v5.3.1 sont disponibles. n8n 2.48.7 écoute sur `http://127.0.0.1:5678`. Le workflow `mcp_integration/n8n/workflow.json` a été importé, inactif, sous le nom `Agentic AI Lab — client MCP`.
- Depuis le conteneur n8n, `http://host.docker.internal:18000/mcp` atteint le serveur MCP Python. Le port hôte 8000 est déjà publié par un autre conteneur, et le MCP Python n'écoute que sur `127.0.0.1`.
- `.gitignore` exclut `.env`, `.venv`, `.langgraph_api/`, les bases SQLite, les index Chroma, `IMG_7470.heic`, le PDF de cours et les deux notebooks. `.env.example` reste visible. Aucun fichier `.env` n'est présent. Les seules chaînes `sk-` du dépôt sont des exemples de test pour le masquage.

## Partiel

- Vision : `customer_support/data/images/img_px200_01.png` est résolu par `chemin_image_autorise` (5 227 octets, répertoire autorisé). Le modèle n'est appelé que si `image_path` est fourni et si une clé existe. La référence `img_px200_01` seule reste en `texte_degrade`. Aucune clé n'est présente, donc aucun pixel n'a été envoyé.
- n8n : l'import et le réseau MCP sont vérifiés. Le propriétaire n'est pas configuré (`userManagement.isInstanceOwnerSetUp=false`) et `credentials_entity` est vide. L'agent n'a pas appelé `add_numbers`.
- Studio : l'affichage dépend encore de l'autorisation Chrome pour le réseau local. Le bandeau `LANGSMITH_API_KEY` signale seulement l'absence de traçage. `langgraph-api` 0.18.3 reste la dernière version et contient toujours le refus CORS d'origine.

## Non testé

- Agent n8n sur `add_numbers(2, 3)` et la réponse `5`. Il manque le compte propriétaire n8n et une clé OpenAI.
- Recherche web live. `TAVILY_API_KEY` est absente.
- Interprétation réelle des pixels.
- Interface graphique de MCP Inspector.
- Publication GitHub.

## Publication

Après approbation explicite, depuis la racine du dépôt :

```bash
git status --short
git check-ignore -v .env .venv IMG_7470.heic "Support Résumé Agentic AI et MCP - Pr. YOUSSFI.pdf" agentic_ai_with_langchain_V3.ipynb demo-langgraph.ipynb
git add .
git status
git commit -m "Ajoute le laboratoire d'agents LangChain, LangGraph et MCP."
gh repo create agentic-ai-lab --source=. --remote=origin --private
git push -u origin HEAD
```

Ne pas forcer l'ajout des fichiers ignorés.
