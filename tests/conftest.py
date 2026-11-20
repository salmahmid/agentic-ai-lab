"""Environnement de test isolé des clés éventuellement présentes sur la machine."""

from __future__ import annotations

import os

os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["TAVILY_API_KEY"] = ""
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGSMITH_API_KEY"] = ""
os.environ["AGENTIC_ALLOW_PYTHON_REPL"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
