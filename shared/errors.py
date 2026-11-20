"""Exceptions explicites du laboratoire."""

from __future__ import annotations


class LabError(Exception):
    """Erreur de base, destinée à être affichée à l'utilisateur."""


class ConfigurationError(LabError):
    """Configuration absente ou incohérente."""


class MissingCredentialError(ConfigurationError):
    """Une clé API requise pour l'opération demandée n'est pas définie."""


class UnsafeInputError(LabError):
    """Entrée refusée par une validation de sécurité."""


class UnsupportedDocumentError(LabError):
    """Format de document refusé."""


class MCPUnavailableError(LabError):
    """Le serveur MCP distant n'a pas pu être contacté. Aucun résultat n'est inventé."""
