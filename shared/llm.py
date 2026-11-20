"""Modèles de langage configurables et modèle scripté pour les tests."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, Field

from shared.config import get_settings
from shared.errors import ConfigurationError, MissingCredentialError


class ScriptedChatModel(BaseChatModel):
    """Modèle déterministe qui rejoue une liste de réponses.

    Chaque élément est un ``AIMessage`` ou une fonction ``messages -> AIMessage``.
    ``bind_tools`` retourne le même modèle : les appels d'outils sont ceux
    déjà présents dans les messages scriptés.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    script: list[Any] = Field(default_factory=list)
    cursor: int = 0
    name_label: str = "scripted"

    @property
    def _llm_type(self) -> str:
        return "scripted-chat"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"name_label": self.name_label, "script_length": len(self.script)}

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if not self.script:
            message = AIMessage(content=f"[{self.name_label}] Aucune réponse scriptée.")
        else:
            index = min(self.cursor, len(self.script) - 1)
            item = self.script[index]
            message = item(messages) if callable(item) else item
            if self.cursor < len(self.script):
                self.cursor += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def build_chat_model(model_name: str | None = None, temperature: float = 0.0) -> Any:
    """Construit le modèle de chat demandé par ``LLM_PROVIDER``.

    Lève ``MissingCredentialError`` si le fournisseur distant n'a pas de clé.
    Le fournisseur ``fake`` doit être injecté par l'appelant : cette fonction
    ne simule pas une réponse de modèle cloud.
    """

    settings = get_settings()
    provider = settings.llm_provider
    name = model_name or settings.llm_model

    if provider == "fake":
        raise ConfigurationError(
            "LLM_PROVIDER=fake exige un ScriptedChatModel fourni par le scénario de test."
        )
    if provider == "openai":
        if not settings.openai_api_key:
            raise MissingCredentialError(
                "OPENAI_API_KEY est absente. Définissez-la ou lancez l'exemple avec LLM_PROVIDER=fake."
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=name, temperature=temperature, api_key=settings.openai_api_key)
    if provider == "google":
        if not settings.google_api_key:
            raise MissingCredentialError(
                "GOOGLE_API_KEY est absente. Définissez-la ou lancez l'exemple avec LLM_PROVIDER=fake."
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=name,
            temperature=temperature,
            google_api_key=settings.google_api_key,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=name, temperature=temperature)
    raise ConfigurationError(
        f"LLM_PROVIDER='{provider}' n'est pas pris en charge. Valeurs : openai, google, ollama, fake."
    )


def build_vision_model() -> Any:
    """Construit le modèle de vision si une clé correspondante existe."""

    settings = get_settings()
    if not settings.vision_credentials_present:
        raise MissingCredentialError(
            "Aucun identifiant de vision n'est configuré. Le mode texte dégradé doit être utilisé."
        )
    provider = "google" if settings.vision_model.startswith("gemini") else settings.llm_provider
    if provider == "google" or settings.vision_model.startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.vision_model,
            temperature=0.0,
            google_api_key=settings.google_api_key,
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.vision_model,
        temperature=0.0,
        api_key=settings.openai_api_key,
    )
