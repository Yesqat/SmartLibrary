"""Versioned, explainable baseline constants; not measured optimal weights."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationPolicy:
    version: str = "content-rrf-v1"
    window_days: int = 90
    view: int = 1
    click: int = 2
    favorite: int = 3
    reserve: int = 4
    borrow: int = 5
    profile_books: int = 200
    rrf_k: int = 60


POLICY = RecommendationPolicy()
