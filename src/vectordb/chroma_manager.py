"""
Chroma vector database manager for book storage and semantic search.
"""

from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.config import settings
from src.data.models import Book
from src.vectordb.embeddings import EmbeddingManager


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

    def add_books(self, books: List[Book], batch_size: int = 50) -> int:
        """
        Add multiple books to the vector database.

        Args:
            books: List of Book objects to add
            batch_size: Number of books to process at once

        Returns:
            Number of books successfully added
        """
        if not books:
            return 0

        added_count = 0

        # Process in batches
        for i in range(0, len(books), batch_size):
            batch = books[i:i + batch_size]

            # Generate embeddings
            embeddings = self.embedding_manager.embed_books(batch)

            # Prepare data for Chroma
            ids = [f"book_{i + j}" for j in range(len(batch))]
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
            print(f"✓ Added batch {i//batch_size + 1}: {len(batch)} books (Total: {added_count})")

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


if __name__ == "__main__":
    # Test ChromaManager
    print("=== Testing ChromaManager ===\n")

    # Initialize manager
    manager = ChromaManager(collection_name="test_books")

    # Clear test collection
    try:
        manager.client.delete_collection("test_books")
        manager = ChromaManager(collection_name="test_books")
        print("✓ Cleared test collection\n")
    except:
        pass

    # Create test books
    test_books = [
        Book(
            title="The Love Hypothesis",
            author="Ali Hazelwood",
            rating=4.5,
            review="Amazing fake dating story!",
            trope="Fake Dating",
            category="Romance",
            tags=["#swoony", "#fun", "#heartwarming"],
            description="A contemporary romantic comedy about a fake dating experiment."
        ),
        Book(
            title="Beach Read",
            author="Emily Henry",
            rating=4.3,
            review="Heartfelt and emotional.",
            trope="Enemies to Lovers",
            category="Romance",
            tags=["#heartwarming", "#emotional", "#hopeful"],
            description="Two writers challenge each other while spending summer as neighbors."
        ),
        Book(
            title="Twisted Love",
            author="Ana Huang",
            rating=4.0,
            review="Dark and intense.",
            trope="Dark Romance",
            category="Romance",
            tags=["#dark", "#angsty", "#steamy"],
            description="A grumpy bodyguard falls for his best friend's sister."
        )
    ]

    # Test adding books
    print("Adding test books...")
    count = manager.add_books(test_books)
    print(f"\n✅ Added {count} books")
    print(f"Total books in collection: {manager.count()}\n")

    # Test search
    print("="*60)
    print("\n🔍 Test 1: Basic semantic search")
    print("Query: 'romantic comedy with humor'\n")

    results = manager.search("romantic comedy with humor", n_results=2)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['metadata']['title']}")
        print(f"   Score: {result['score']:.3f}")
        print(f"   Tags: {result['metadata']['tags']}")
        print()

    # Test filtered search
    print("="*60)
    print("\n🔍 Test 2: Filtered search (Dark Romance only)")
    print("Query: 'intense romance'\n")

    results = manager.search(
        "intense romance",
        filters={"trope": "Dark Romance"},
        n_results=2
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['metadata']['title']}")
        print(f"   Trope: {result['metadata']['trope']}")
        print(f"   Score: {result['score']:.3f}")
        print()

    # Test rating filter
    print("="*60)
    print("\n🔍 Test 3: High-rated books (>= 4.3)")
    print("Query: 'heartwarming story'\n")

    results = manager.search(
        "heartwarming story",
        filters={"rating": {"$gte": 4.3}},
        n_results=2
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['metadata']['title']}")
        print(f"   Rating: {result['metadata']['rating']}⭐")
        print(f"   Score: {result['score']:.3f}")
        print()

    print("✅ ChromaManager test complete!")
