"""Offline item-neighbor boundary. Enable serving only after representative evaluation."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from math import sqrt
from typing import Protocol
from uuid import UUID


class CollaborativeRanker(Protocol):
    def rank(self, consumed: set[UUID], limit: int) -> list[UUID]: ...


class ItemNeighbors:
    """Binary item cosine with two-user support; no synthetic collaborative scores."""

    def __init__(self, histories: Iterable[set[UUID]]):
        self.counts: Counter[UUID] = Counter()
        self.pairs: Counter[tuple[UUID, UUID]] = Counter()
        for books in histories:
            self.counts.update(books)
            self.pairs.update((a, b) for a in books for b in books if a != b)

    def rank(self, consumed: set[UUID], limit: int) -> list[UUID]:
        scores: dict[UUID, float] = defaultdict(float)
        for (source, candidate), count in self.pairs.items():
            if source in consumed and candidate not in consumed and count >= 2:
                scores[candidate] += count / sqrt(self.counts[source] * self.counts[candidate])
        return sorted(scores, key=lambda item: (-scores[item], item))[:limit]
