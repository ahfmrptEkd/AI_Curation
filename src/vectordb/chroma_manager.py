"""
Chroma vector database manager for book storage and semantic search.
"""

from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.config import settings
from src.data.models import Book
import re
from src.vectordb.embeddings import EmbeddingManager
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ChromaManager:
    """Manages ChromaDB operations for book recommendations."""

    def __init__(self, collection_name: str = "books"):
        """
        Initialize ChromaDB client and collection.

        Args:
            collection_name: Name of the collection to use
        """
        # Initialize persistent client
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

        # Initialize embedding manager
        self.embedding_manager = EmbeddingManager()

    @staticmethod
    def generate_book_id(book: Book, use_numeric: bool = False, numeric_id: int = 0) -> str:
        """
        Generate a consistent book ID.

        Args:
            book: Book object
            use_numeric: If True, use numeric format (book_N)
            numeric_id: Numeric ID to use if use_numeric=True

        Returns:
            Consistent book ID string
        """
        if use_numeric:
            return f"book_{numeric_id}"
        else:
            # Normalize whitespace: strip and collapse multiple spaces
            title_normalized = re.sub(r'\s+', ' ', book.title.strip())
            author_normalized = re.sub(r'\s+', ' ', book.author.strip())
            
            # Text-based ID from title and author
            title_clean = title_normalized.lower().replace(" ", "_").replace("'", "").replace("[", "").replace("]", "")
            author_clean = author_normalized.lower().replace(" ", "_").replace("'", "")
            
            # Combine and clean up underscores
            book_id = f"{title_clean}_{author_clean}"
            book_id = re.sub(r'_+', '_', book_id)  # __ -> _
            book_id = book_id.strip('_')  # Remove leading/trailing underscores
            
            return book_id[:100]  # Limit length

    def add_books(self, books: List[Book], batch_size: int = 50, start_id: int = 0) -> int:
        """
        Add multiple books to the vector database.

        Args:
            books: List of Book objects to add
            batch_size: Number of books to process at once
            start_id: Starting ID number for books (default: 0)

        Returns:
            Number of books successfully added
        """
        if not books:
            return 0

        added_count = 0
        current_id = start_id

        # Process in batches
        for i in range(0, len(books), batch_size):
            batch = books[i:i + batch_size]

            # Generate embeddings
            embeddings = self.embedding_manager.embed_books(batch)

            # Prepare data for Chroma - use global counter for unique IDs
            ids = [f"book_{current_id + j}" for j in range(len(batch))]
            documents = [self.embedding_manager.book_to_text(book) for book in batch]
            metadatas = [self._book_to_metadata(book) for book in batch]

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            added_count += len(batch)
            current_id += len(batch)
            logger.info(f"✓ Added batch {i//batch_size + 1}: {len(batch)} books (Total: {added_count})")

        return added_count

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search with optional metadata filtering.

        Args:
            query: Natural language search query
            filters: Optional filters (trope, rating, tags, category)
            n_results: Number of results to return

        Returns:
            List of search results with metadata and scores

        Example filters:
            {"trope": "Dark Romance"}
            {"rating": {"$gte": 4.0}}
            {"tags": {"$contains": "swoony"}}
        """
        # Generate query embedding
        query_embedding = self.embedding_manager.embed_query(query)

        # Build where clause from filters
        where = self._build_where_clause(filters) if filters else None

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["metadatas", "documents", "distances"]
        )

        # Format results
        formatted_results = self._format_results(results)

        return formatted_results

    def upsert_book(self, book: Book, book_id: str):
        """
        Update existing book or insert new one.

        Args:
            book: Book object
            book_id: Unique identifier for the book
        """
        embedding = self.embedding_manager.embed_books([book])[0]
        document = self.embedding_manager.book_to_text(book)
        metadata = self._book_to_metadata(book)

        self.collection.upsert(
            ids=[book_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata]
        )

    def delete_book(self, book_id: str):
        """Delete a book from the collection."""
        self.collection.delete(ids=[book_id])

    def count(self) -> int:
        """Get total number of books in the collection."""
        return self.collection.count()

    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single book by ID.

        Args:
            book_id: Unique identifier for the book

        Returns:
            Book metadata dict if found, None otherwise
        """
        try:
            result = self.collection.get(ids=[book_id], include=["metadatas"])
            if result and result["ids"]:
                return result["metadatas"][0]
            return None
        except Exception:
            return None

    def get_all_ids(self) -> List[str]:
        """
        Get all book IDs in the collection.

        Returns:
            List of book IDs
        """
        result = self.collection.get(include=[])
        return result["ids"] if result else []

    def update_books(self, books: List[Book], book_ids: List[str], batch_size: int = 50) -> int:
        """
        Update multiple existing books in the vector database.

        Args:
            books: List of Book objects to update
            book_ids: Corresponding list of book IDs
            batch_size: Number of books to process at once

        Returns:
            Number of books successfully updated
        """
        if not books or len(books) != len(book_ids):
            return 0

        updated_count = 0

        # Process in batches
        for i in range(0, len(books), batch_size):
            batch_books = books[i:i + batch_size]
            batch_ids = book_ids[i:i + batch_size]

            # Generate embeddings
            embeddings = self.embedding_manager.embed_books(batch_books)

            # Prepare data for Chroma
            documents = [self.embedding_manager.book_to_text(book) for book in batch_books]
            metadatas = [self._book_to_metadata(book) for book in batch_books]

            # Update collection
            self.collection.upsert(
                ids=batch_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            updated_count += len(batch_books)
            logger.info(f"✓ Updated batch {i//batch_size + 1}: {len(batch_books)} books (Total: {updated_count})")

        return updated_count

    def _book_to_metadata(self, book: Book) -> Dict[str, Any]:
        """
        Convert Book object to Chroma metadata.

        Args:
            book: Book object

        Returns:
            Dictionary of metadata fields
        """
        return {
            "title": book.title,
            "author": book.author,
            "rating": book.rating,
            "category": book.category,
            "trope": book.trope if book.trope else "",
            "tags": ",".join(book.tags) if book.tags else "",
            "source": book.source,
        }

    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Chroma where clause from filter dictionary.

        Args:
            filters: Filter dictionary

        Returns:
            Chroma-compatible where clause

        Supported filters:
            - trope: exact match
            - rating: $gte, $lte, $eq
            - tags: $contains
            - category: exact match
            - source: exact match (user_read or discovered)
        """
        where = {}
        where_conditions = []

        for key, value in filters.items():
            if key == "trope" and value:
                where_conditions.append({"trope": {"$eq": value}})

            elif key == "category" and value:
                where_conditions.append({"category": {"$eq": value}})

            elif key == "source" and value:
                where_conditions.append({"source": {"$eq": value}})

            elif key == "rating" and isinstance(value, dict):
                # Handle rating comparisons
                for op, rating_value in value.items():
                    where_conditions.append({"rating": {op: rating_value}})

            elif key == "rating" and isinstance(value, (int, float)):
                # Exact rating match
                where_conditions.append({"rating": {"$eq": value}})

            elif key == "tags" and isinstance(value, dict):
                # Handle tags contains
                if "$contains" in value:
                    where_conditions.append({"tags": {"$contains": value["$contains"]}})

        # Combine conditions with AND
        if len(where_conditions) == 1:
            where = where_conditions[0]
        elif len(where_conditions) > 1:
            where = {"$and": where_conditions}

        return where

    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format Chroma query results into a clean list.

        Args:
            results: Raw results from Chroma query

        Returns:
            List of formatted result dictionaries
        """
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i],
                "document": results["documents"][0][i],
                "distance": results["distances"][0][i],
                "score": 1 - results["distances"][0][i]  # Convert distance to similarity score
            })

        return formatted


