<!-- page: 1 -->
# Guide du laboratoire Agentic AI Lab

Ce document est une ressource pédagogique originale. Il ne décrit pas un service commercial.

L'objectif du laboratoire Agentic AI Lab est d'apprendre LangChain, LangGraph et le protocole MCP
sur des exemples exécutables. Les étudiants construisent un agent outillé, une mémoire de
conversation, un graphe de retrieval augmenté et un serveur MCP.

<!-- page: 2 -->
# Outils et mémoire

L'agent de base dispose d'une addition, d'une multiplication, de la date courante et d'une
analyse de texte. La mémoire courte est portée par un checkpointer LangGraph et isolée par
thread_id. Une base SQLite peut conserver cette mémoire après l'arrêt du processus.

Le retrieval n'est utile que lorsqu'une question porte sur le corpus. Une simple salutation
ne doit pas déclencher de recherche documentaire.

<!-- page: 3 -->
# Limites

Si les passages retrouvés ne couvrent pas la question, l'assistant doit expliquer son
incertitude. Il ne complète pas avec une connaissance externe présentée comme un fait du corpus.
