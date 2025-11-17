"""
Unit tests for ChromaManager.
Uses temporary directories for ChromaDB during tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.vectordb.chroma_manager import ChromaManager
from src.data.models import Book


@pytest.fixture
def temp_chroma_path():
    """Create a temporary directory for ChromaDB."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_embedding_manager():
    """Create a mocked EmbeddingManager."""
    mock_manager = MagicMock()
    # Mock embed_books to return dummy embeddings based on input length
    def embed_books_side_effect(books):
        return [[0.1 + i * 0.1] * 1536 for i in range(len(books))]

    mock_manager.embed_books.side_effect = embed_books_side_effect
    # Mock embed_query
    mock_manager.embed_query.return_value = [0.15] * 1536
    # Mock book_to_text
    mock_manager.book_to_text.side_effect = lambda book: f"{book.title} by {book.author}"
    return mock_manager


@pytest.fixture
def sample_books():
    """Create sample books for testing."""
    return [
        Book(
            title="Test Book 1",
            author="Author 1",
            rating=4.5,
            review="Great book!",
            trope="Enemies to Lovers",
            category="Romance",
            tags=["#swoony", "#fun"],
            description="A romantic comedy.",
            source="user_read"
        ),
        Book(
            title="Test Book 2",
            author="Author 2",
            rating=3.5,
            review="Good read.",
            trope="Dark Romance",
            category="Romance",
            tags=["#dark", "#angsty"],
            description="A dark romance.",
            source="discovered"
        ),
        Book(
            title="Test Book 3",
            author="Author 3",
            rating=4.0,
            review="Nice story.",
            trope="Fake Dating",
            category="Romance",
            tags=["#heartwarming"],
            description="A fake dating romance.",
            source="discovered"
        )
    ]


class TestChromaManagerInitialization:
    """Test ChromaManager initialization."""

    def test_init_creates_collection(self, temp_chroma_path):
        """Test that initialization creates a collection."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager'):

            manager = ChromaManager(collection_name="test_collection")

            assert manager.client is not None
            assert manager.collection is not None
            assert manager.collection.name == "test_collection"

    def test_init_uses_persistent_client(self, temp_chroma_path):
        """Test that persistent client is used."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager'):

            manager = ChromaManager()

            # Verify files were created in the persist directory
            assert Path(temp_chroma_path).exists()


class TestChromaManagerBookOperations:
    """Test book CRUD operations."""

    def test_add_books_success(self, temp_chroma_path, mock_embedding_manager, sample_books):
        """Test successfully adding books."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_add")
            manager.embedding_manager = mock_embedding_manager

            count = manager.add_books(sample_books[:2])

            assert count == 2
            assert manager.count() == 2

    def test_add_books_empty_list(self, temp_chroma_path, mock_embedding_manager):
        """Test adding empty book list."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_empty")
            manager.embedding_manager = mock_embedding_manager

            count = manager.add_books([])

            assert count == 0

    def test_add_books_with_start_id(self, temp_chroma_path, mock_embedding_manager, sample_books):
        """Test adding books with custom start_id."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_start_id")
            manager.embedding_manager = mock_embedding_manager

            # Add first batch starting at 0
            manager.add_books(sample_books[:1], start_id=0)

            # Add second batch starting at 100
            manager.add_books(sample_books[1:2], start_id=100)

            # Check IDs
            all_ids = manager.get_all_ids()
            assert "book_0" in all_ids
            assert "book_100" in all_ids

    def test_count_returns_correct_number(self, temp_chroma_path, mock_embedding_manager, sample_books):
        """Test that count returns correct number of books."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_count")
            manager.embedding_manager = mock_embedding_manager

            assert manager.count() == 0

            manager.add_books(sample_books)

            assert manager.count() == 3

    def test_get_book_by_id(self, temp_chroma_path, mock_embedding_manager, sample_books):
        """Test getting a book by ID."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_get")
            manager.embedding_manager = mock_embedding_manager

            manager.add_books(sample_books[:1])

            book = manager.get_book("book_0")

            assert book is not None
            assert book["title"] == "Test Book 1"
            assert book["author"] == "Author 1"

    def test_get_book_nonexistent(self, temp_chroma_path, mock_embedding_manager):
        """Test getting a nonexistent book returns None."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_get_none")

            book = manager.get_book("nonexistent_id")

            assert book is None

    def test_get_all_ids(self, temp_chroma_path, mock_embedding_manager, sample_books):
        """Test getting all book IDs."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_all_ids")
            manager.embedding_manager = mock_embedding_manager

            manager.add_books(sample_books)

            ids = manager.get_all_ids()

            assert len(ids) == 3
            assert "book_0" in ids
            assert "book_1" in ids
            assert "book_2" in ids

    def test_delete_book(self, temp_chroma_path, mock_embedding_manager, sample_books):
        """Test deleting a book."""
        with patch('src.config.settings.chroma_persist_dir', temp_chroma_path), \
             patch('src.vectordb.chroma_manager.EmbeddingManager', return_value=mock_embedding_manager):

            manager = ChromaManager(collection_name="test_delete")
            manager.embedding_manager = mock_embedding_manager

            manager.add_books(sample_books[:2])
            assert manager.count() == 2

            manager.delete_book("book_0")

            assert manager.count() == 1
            assert manager.get_book("book_0") is None


class TestChromaManagerUtilities:
    """Test utility functions."""

    def test_generate_book_id_numeric(self):
        """Test generating numeric book IDs."""
        book = Book(
            title="Test Book",
            author="Test Author",
            rating=4.0,
            review="Great book!",
            category="Romance"
        )

        book_id = ChromaManager.generate_book_id(book, use_numeric=True, numeric_id=42)

        assert book_id == "book_42"

    def test_generate_book_id_text(self):
        """Test generating text-based book IDs."""
        book = Book(
            title="The Love Hypothesis",
            author="Ali Hazelwood",
            rating=4.5,
            review="Amazing story!",
            category="Romance"
        )

        book_id = ChromaManager.generate_book_id(book, use_numeric=False)

        assert "love_hypothesis" in book_id.lower()
        assert "ali_hazelwood" in book_id.lower()

    def test_generate_book_id_text_cleans_special_chars(self):
        """Test that text IDs clean special characters."""
        book = Book(
            title="Book [Special] Title's",
            author="Author O'Brien",
            rating=4.0,
            review="Good read!",
            category="Romance"
        )

        book_id = ChromaManager.generate_book_id(book, use_numeric=False)

        assert "[" not in book_id
        assert "]" not in book_id
        assert "'" not in book_id
