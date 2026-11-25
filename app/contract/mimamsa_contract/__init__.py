"""Mimamsa data interchange contract v1: schemas, semantic rules and a bundle validator.

Shared by Track A (producers) and Track B (the offline application, which only imports).
The validator is read-only: it never modifies a record, a bundle or a frozen artefact.
"""
from __future__ import annotations

CONTRACT_VERSION = "1.0.0"
CONTRACT_MAJOR = 1

from .issues import Issue, ValidationReport  # noqa: E402
from .restricted import RestrictedRegister, RestrictedConfigError, load_register  # noqa: E402

__all__ = [
    "CONTRACT_VERSION",
    "CONTRACT_MAJOR",
    "Issue",
    "ValidationReport",
    "RestrictedRegister",
    "RestrictedConfigError",
    "load_register",
]
