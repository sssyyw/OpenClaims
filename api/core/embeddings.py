from abc import ABC, abstractmethod

from pydantic import BaseModel


class EmbeddingResult(BaseModel):
    text: str
    vector: list[float]


class EmbeddingService(ABC):
    """Abstract interface for text embedding.

    POC: OpenAI text-embedding-3-large.
    Future: benchmark against PubMedBERT (see TODOS.md).
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        ...
