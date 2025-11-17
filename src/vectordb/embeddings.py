"""
Embedding manager for converting books to vector embeddings.
Uses OpenAI text-embedding-3-small for efficient semantic search.
"""

from typing import List
from langchain_openai import OpenAIEmbeddings
from src.config import settings
from src.data.models import Book


class EmbeddingManager:
    """Manages book-to-text conversion and embedding generation."""

    def __init__(self):
        """Initialize OpenAI embeddings with configured model."""
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key
        )

    def book_to_text(self, book: Book) -> str:
        """
        Convert a Book object to searchable text for embedding.

        Priority: Description > Review
        - Description is objective and represents book's actual content
        - Review is subjective and represents individual emotional response

        Args:
            book: Book object to convert

        Returns:
            Formatted text string for embedding

        Example output:
            Title: The Love Hypothesis
            Author: Ali Hazelwood
            Trope: Fake Dating
            Emotion Tags: #swoony, #fun, #heartwarming
            Description: A contemporary romantic comedy about a fake dating experiment...
        """
        # Use description if available, otherwise use review
        content = book.description if book.description else book.review

        # Build searchable text
        text_parts = [
            f"Title: {book.title}",
            f"Author: {book.author}",
            f"Trope: {book.trope}" if book.trope else None,
            f"Emotion Tags: {', '.join(book.tags)}" if book.tags else None,
            f"Description: {content}" if content else None
        ]

        # Filter out None values and join
        text = "\n".join(part for part in text_parts if part)

        return text

    def embed_books(self, books: List[Book]) -> List[List[float]]:
        """
        Generate embeddings for multiple books in batch.

        Args:
            books: List of Book objects

        Returns:
            List of embedding vectors (one per book)

        Note:
            Uses batch processing for efficiency.
            OpenAI allows up to 2048 texts per batch.
        """
        if not books:
            return []

        # Convert all books to text
        texts = [self.book_to_text(book) for book in books]

        # Generate embeddings in batch
        embeddings = self.embeddings.embed_documents(texts)

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Query embedding vector
        """
        return self.embeddings.embed_query(query)


