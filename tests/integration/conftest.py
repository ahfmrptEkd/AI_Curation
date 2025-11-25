"""
Shared fixtures for integration tests.
"""
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.data.models import Book


@pytest.fixture
def mock_embedding_function():
    """Mock OpenAI embedding function for ChromaDB."""
    mock_embed = MagicMock()
    # Return fixed embedding vectors
    mock_embed.return_value = [[0.1] * 1536]  # 1536-dimensional vector
    return mock_embed


@pytest.fixture
def integration_chroma_dir(tmp_path, monkeypatch) -> Generator[str, None, None]:
    """Temporary ChromaDB directory for integration tests."""
    chroma_dir = tmp_path / "integration_chroma"
    chroma_dir.mkdir()

    # Set environment variable for ChromaManager
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_dir))

    yield str(chroma_dir)
    # Cleanup handled by tmp_path


@pytest.fixture
def sample_discovered_books():
    """Sample discovered books for recommendation testing."""
    books = []
    book_data = [
        {
            "title": "Dark Romance Discovery 1",
            "author": "L.J. Shen",
            "category": "Romance",
            "trope": "Dark Romance",
            "rating": 4.5,
            "review": "Discovered from API",  # Add required review field
            "description": "A dark and intense romance with complex characters.",
            "source": "discovered",
            "tags": ["#긴장감넘치는", "#강렬한", "#몰입되는"]
        },
        {
            "title": "Sports Romance Discovery 1",
            "author": "Hannah Grace",
            "category": "Romance",
            "trope": "Sports Romance",
            "rating": 4.3,
            "review": "Discovered from API",
            "description": "A heartwarming college hockey romance.",
            "source": "discovered",
            "tags": ["#설레는", "#유쾌한", "#따뜻한"]
        },
        {
            "title": "Enemies to Lovers Discovery 1",
            "author": "Ali Hazelwood",
            "category": "Romance",
            "trope": "Enemies to Lovers",
            "rating": 4.6,
            "review": "Discovered from API",
            "description": "Two rivals find unexpected love in academia.",
            "source": "discovered",
            "tags": ["#설레는", "#유쾌한", "#지적인"]
        },
        {
            "title": "Second Chance Discovery 1",
            "author": "Colleen Hoover",
            "category": "Romance",
            "trope": "Second Chance",
            "rating": 4.4,
            "review": "Discovered from API",
            "description": "A second chance at love after years apart.",
            "source": "discovered",
            "tags": ["#감동적인", "#슬픈", "#희망찬"]
        },
        {
            "title": "Dark Romance Discovery 2",
            "author": "Penelope Douglas",
            "category": "Romance",
            "trope": "Dark Romance",
            "rating": 4.7,
            "review": "Discovered from API",
            "description": "A forbidden romance with dark themes.",
            "source": "discovered",
            "tags": ["#긴장감넘치는", "#금지된", "#강렬한"]
        }
    ]

    for data in book_data:
        books.append(Book(**data))

    return books


@pytest.fixture
def sample_user_read_books():
    """Sample user-read books (should NOT appear in recommendations)."""
    books = []
    book_data = [
        {
            "title": "User Read Book 1",
            "author": "Lucy Score",
            "category": "Romance",
            "trope": "Small Town Romance",
            "rating": 4.0,
            "review": "Great small town romance!",
            "description": "A charming small town romance.",
            "source": "user_read",
            "tags": ["#따뜻한", "#유쾌한", "#로맨틱한"]
        },
        {
            "title": "User Read Book 2",
            "author": "Tessa Bailey",
            "category": "Romance",
            "trope": "Workplace Romance",
            "rating": 4.2,
            "review": "Love the workplace dynamics!",
            "description": "A steamy workplace romance.",
            "source": "user_read",
            "tags": ["#설레는", "#섹시한", "#재미있는"]
        }
    ]

    for data in book_data:
        books.append(Book(**data))

    return books


@pytest.fixture
def mock_langgraph_recommendation():
    """Mock LangGraph recommendation response."""
    return {
        "recommendations": [
            {
                "title": "Dark Romance Discovery 1",
                "author": "L.J. Shen",
                "rating": 4.5,
                "trope": "Dark Romance",
                "explanation": "This book features intense emotional depth and complex characters, perfect for fans of dark romance."
            },
            {
                "title": "Dark Romance Discovery 2",
                "author": "Penelope Douglas",
                "rating": 4.7,
                "trope": "Dark Romance",
                "explanation": "A forbidden romance with captivating dark themes that will keep you on the edge of your seat."
            }
        ],
        "metadata": {
            "query": "dark romance with high rating",
            "filters": {"trope": "Dark Romance", "min_rating": 4.0},
            "total_found": 2
        }
    }


@pytest.fixture
def mock_google_books_api():
    """Mock Google Books API responses."""
    def mock_fetch_metadata(title: str, author: str = None):
        return {
            "title": title,
            "authors": [author] if author else ["Test Author"],
            "description": f"A captivating romance novel: {title}",
            "categories": ["Fiction", "Romance"],
            "published_date": "2024",
            "isbn": "1234567890",
            "page_count": 350,
            "cover_url": "https://example.com/cover.jpg"
        }

    return mock_fetch_metadata


@pytest.fixture
def mock_tag_generator():
    """Mock TagGenerator for integration tests."""
    def mock_generate_tags(text: str, use_description: bool = True):
        # Return different tags based on input text keywords
        if "dark" in text.lower():
            return ["#긴장감넘치는", "#강렬한", "#몰입되는"]
        elif "sport" in text.lower() or "hockey" in text.lower():
            return ["#설레는", "#유쾌한", "#따뜻한"]
        elif "enemies" in text.lower():
            return ["#설레는", "#유쾌한", "#지적인"]
        else:
            return ["#로맨틱한", "#감동적인", "#따뜻한"]

    return mock_generate_tags
