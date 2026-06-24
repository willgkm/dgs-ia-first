"""Camada de retrieval (serviços): Retriever (top-K + threshold) e ConflictDetector."""

from __future__ import annotations

from .conflict_detector import ConflictDetector, conflict_key
from .retriever import SimilarityRetriever

__all__ = ["SimilarityRetriever", "ConflictDetector", "conflict_key"]
