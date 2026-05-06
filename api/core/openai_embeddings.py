"""OpenAI embedding service implementation.

Uses text-embedding-3-large for POC. Benchmark against PubMedBERT later (see TODOS.md).
"""

from openai import AsyncOpenAI

from core.config import settings
from core.embeddings import EmbeddingService


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(self, client: AsyncOpenAI | None = None):
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            input=text,
            model=self.model,
            dimensions=self.dimensions,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        # OpenAI supports up to 2048 items per batch request
        batch_size = 2048
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self.client.embeddings.create(
                input=batch,
                model=self.model,
                dimensions=self.dimensions,
            )
            # Response items are in the same order as input
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings
