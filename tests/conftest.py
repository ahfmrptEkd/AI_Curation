"""
Pytest configuration and shared fixtures for AI_Curation tests.
"""
import os
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load environment variables for tests
load_dotenv()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for tag generation and recommendation tests."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "#설레는 #몰입되는 #로맨틱한"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_sheets_service():
    """Mock Google Sheets service for SheetsClient tests."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def sample_book_data():
    """Sample book data for testing."""
    return {
        "title": "Test Romance Book",
        "author": "Test Author",
        "rating": 4.5,
        "review": "Amazing romance story with great character development.",
        "trope": "Enemies to Lovers",
        "category": "Romance",
        "tags": ["#설레는", "#몰입되는", "#로맨틱한"],
        "description": "A heartwarming romance about two people who start as enemies.",
        "source": "user_read"
    }


@pytest.fixture
def sample_books_list(sample_book_data):
    """List of sample books for testing."""
    from src.data.models import Book

    books = []
    for i in range(5):
        book_dict = sample_book_data.copy()
        book_dict["title"] = f"Test Book {i+1}"
        book_dict["rating"] = 3.0 + i * 0.5
        books.append(Book(**book_dict))

    return books


@pytest.fixture
def temp_chroma_dir(tmp_path):
    """Temporary directory for ChromaDB during tests."""
    chroma_dir = tmp_path / "chroma_test"
    chroma_dir.mkdir()
    return str(chroma_dir)


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set up test environment variables."""
    test_env = {
        "OPENAI_API_KEY": "test-api-key-12345",
        "GOOGLE_SHEETS_ID": "test-sheet-id-12345",
        "CHROMA_PERSIST_DIR": "./test_chroma_db"
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
