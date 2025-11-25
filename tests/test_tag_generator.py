"""
Unit tests for TagGenerator.
Tests tag generation with mocked OpenAI API.
"""
import pytest
from unittest.mock import MagicMock, Mock, patch

from src.agents.tag_generator import TagGenerator
from src.data.models import Book


class TestTagGeneratorInitialization:
    """Test TagGenerator initialization."""

    @patch('src.agents.tag_generator.ChatOpenAI')
    def test_init_creates_llm(self, mock_openai):
        """Test that TagGenerator initializes with correct LLM."""
        generator = TagGenerator()

        mock_openai.assert_called_once()
        assert generator.llm is not None
        assert generator.AVAILABLE_TAGS is not None
        assert len(generator.AVAILABLE_TAGS) == 20

    def test_available_tags_list(self):
        """Test that available tags list contains expected tags."""
        expected_tags = [
            "#healing", "#suspenseful", "#thought-provoking", "#heartwarming",
            "#sad", "#fun", "#heavy", "#light", "#touching", "#realistic",
            "#fantastical", "#inspiring", "#comforting", "#exciting", "#dark",
            "#hopeful", "#emotional", "#steamy", "#angsty", "#swoony"
        ]

        assert TagGenerator.AVAILABLE_TAGS == expected_tags


class TestTagGeneratorSingleTag:
    """Test single tag generation."""

    @pytest.fixture
    def generator(self):
        """Create a TagGenerator with mocked LLM."""
        with patch('src.agents.tag_generator.ChatOpenAI'):
            generator = TagGenerator()
            generator.llm = MagicMock()
            return generator

    def test_generate_tags_with_review(self, generator):
        """Test generating tags from user review."""
        mock_response = MagicMock()
        mock_response.content = "#fun,#exciting,#light"
        generator.llm.invoke.return_value = mock_response

        tags = generator.generate_tags(
            title="Test Book",
            rating=4.5,
            review="This was so fun and exciting! Loved every moment."
        )

        assert len(tags) == 3
        assert tags == ["#fun", "#exciting", "#light"]
        generator.llm.invoke.assert_called_once()

    def test_generate_tags_with_description(self, generator):
        """Test generating tags from book description."""
        mock_response = MagicMock()
        mock_response.content = "#heartwarming,#swoony"
        generator.llm.invoke.return_value = mock_response

        tags = generator.generate_tags(
            title="Romance Novel",
            description="A heartwarming tale of two people finding love."
        )

        assert len(tags) == 2
        assert tags == ["#heartwarming", "#swoony"]

    def test_generate_tags_prioritizes_review_over_description(self, generator):
        """Test that review takes priority over description."""
        mock_response = MagicMock()
        mock_response.content = "#dark,#angsty"
        generator.llm.invoke.return_value = mock_response

        tags = generator.generate_tags(
            title="Dark Romance",
            rating=3.5,
            review="This was dark and angsty.",
            description="A light and fluffy romance."
        )

        # Should use review, not description
        assert tags == ["#dark", "#angsty"]

        # Check that the prompt included the review
        call_args = generator.llm.invoke.call_args[0][0]
        prompt_text = str(call_args)
        assert "dark and angsty" in prompt_text.lower()

    def test_generate_tags_no_content_returns_default(self, generator):
        """Test that missing content returns default tag."""
        tags = generator.generate_tags(
            title="Book Without Content",
            rating=3.0
        )

        assert tags == ["#thought-provoking"]

    def test_generate_tags_handles_llm_error(self, generator):
        """Test graceful handling of LLM errors."""
        generator.llm.invoke.side_effect = Exception("API Error")

        tags = generator.generate_tags(
            title="Test Book",
            review="Great book!"
        )

        assert tags == []


class TestTagGeneratorParsing:
    """Test tag parsing logic."""

    @pytest.fixture
    def generator(self):
        """Create a TagGenerator."""
        with patch('src.agents.tag_generator.ChatOpenAI'):
            return TagGenerator()

    def test_parse_tags_with_hashtags(self, generator):
        """Test parsing tags that already have hashtags."""
        tags = generator._parse_tags("#fun,#exciting,#light")
        assert tags == ["#fun", "#exciting", "#light"]

    def test_parse_tags_without_hashtags(self, generator):
        """Test parsing tags without hashtags."""
        tags = generator._parse_tags("fun,exciting,light")
        assert tags == ["#fun", "#exciting", "#light"]

    def test_parse_tags_with_spaces(self, generator):
        """Test parsing tags with extra spaces."""
        tags = generator._parse_tags(" #fun , #exciting , #light ")
        assert tags == ["#fun", "#exciting", "#light"]

    def test_parse_tags_mixed_format(self, generator):
        """Test parsing tags with mixed formats."""
        tags = generator._parse_tags("#fun, exciting, #light")
        assert tags == ["#fun", "#exciting", "#light"]


class TestTagGeneratorValidation:
    """Test tag validation logic."""

    @pytest.fixture
    def generator(self):
        """Create a TagGenerator."""
        with patch('src.agents.tag_generator.ChatOpenAI'):
            return TagGenerator()

    def test_validate_tags_all_valid(self, generator):
        """Test validation with all valid tags."""
        tags = ["#fun", "#exciting", "#light"]
        valid_tags = generator._validate_tags(tags)
        assert valid_tags == ["#fun", "#exciting", "#light"]

    def test_validate_tags_removes_invalid(self, generator):
        """Test that invalid tags are filtered out."""
        tags = ["#fun", "#invalid_tag", "#exciting"]
        valid_tags = generator._validate_tags(tags)
        assert valid_tags == ["#fun", "#exciting"]

    def test_validate_tags_limits_to_three(self, generator):
        """Test that only first 3 tags are kept."""
        tags = ["#fun", "#exciting", "#light", "#dark", "#heavy"]
        valid_tags = generator._validate_tags(tags)
        assert len(valid_tags) == 3
        assert valid_tags == ["#fun", "#exciting", "#light"]

    def test_validate_tags_all_invalid_returns_default(self, generator):
        """Test that all invalid tags returns default."""
        tags = ["#invalid1", "#invalid2", "#invalid3"]
        valid_tags = generator._validate_tags(tags)
        assert valid_tags == ["#thought-provoking"]

    def test_validate_tags_empty_returns_default(self, generator):
        """Test that empty tag list returns default."""
        tags = []
        valid_tags = generator._validate_tags(tags)
        assert valid_tags == ["#thought-provoking"]


class TestTagGeneratorBatch:
    """Test batch tag generation."""

    @pytest.fixture
    def generator(self):
        """Create a TagGenerator with mocked LLM."""
        with patch('src.agents.tag_generator.ChatOpenAI'):
            generator = TagGenerator()
            generator.llm = MagicMock()
            return generator

    def test_generate_tags_batch_success(self, generator):
        """Test successful batch tag generation."""
        books = [
            Book(
                title="Book 1",
                author="Author 1",
                rating=4.0,
                review="Fun and exciting!",
                category="Romance"
            ),
            Book(
                title="Book 2",
                author="Author 2",
                rating=3.5,
                review="Dark and angsty.",
                category="Romance"
            )
        ]

        # Mock batch responses
        mock_response_1 = MagicMock()
        mock_response_1.content = "#fun,#exciting"

        mock_response_2 = MagicMock()
        mock_response_2.content = "#dark,#angsty"

        generator.llm.batch.return_value = [mock_response_1, mock_response_2]

        results = generator.generate_tags_batch(books)

        assert len(results) == 2
        assert results["Book 1"] == ["#fun", "#exciting"]
        assert results["Book 2"] == ["#dark", "#angsty"]

    def test_generate_tags_batch_with_description(self, generator):
        """Test batch generation uses description when review is empty."""
        books = [
            Book(
                title="Book 1",
                author="Author 1",
                rating=4.0,
                review="",
                description="A heartwarming romance.",
                category="Romance"
            )
        ]

        mock_response = MagicMock()
        mock_response.content = "#heartwarming,#swoony"
        generator.llm.batch.return_value = [mock_response]

        results = generator.generate_tags_batch(books)

        assert results["Book 1"] == ["#heartwarming", "#swoony"]

    def test_generate_tags_batch_empty_list(self, generator):
        """Test batch generation with empty book list."""
        results = generator.generate_tags_batch([])
        assert results == {}

    def test_generate_tags_batch_fallback_on_error(self, generator):
        """Test batch generation falls back to sequential on error."""
        books = [
            Book(
                title="Book 1",
                author="Author 1",
                rating=4.0,
                review="Great book!",
                category="Romance"
            )
        ]

        # Mock batch failure
        generator.llm.batch.side_effect = Exception("Batch API Error")

        # Mock sequential success
        mock_response = MagicMock()
        mock_response.content = "#fun,#exciting"
        generator.llm.invoke.return_value = mock_response

        results = generator.generate_tags_batch(books)

        assert "Book 1" in results
        assert results["Book 1"] == ["#fun", "#exciting"]

    def test_generate_tags_batch_handles_individual_errors(self, generator):
        """Test batch generation handles individual book errors."""
        books = [
            Book(
                title="Good Book",
                author="Author 1",
                rating=4.0,
                review="Great!",
                category="Romance"
            ),
            Book(
                title="Bad Book",
                author="Author 2",
                rating=3.0,
                review="Meh.",
                category="Romance"
            )
        ]

        # First response is good, second raises error
        mock_response = MagicMock()
        mock_response.content = "#fun,#exciting"

        bad_response = MagicMock()
        bad_response.content = None  # This will cause an error

        generator.llm.batch.return_value = [mock_response, bad_response]

        results = generator.generate_tags_batch(books)

        assert results["Good Book"] == ["#fun", "#exciting"]
        assert results["Bad Book"] == ["#thought-provoking"]  # Fallback


class TestTagGeneratorRealWorld:
    """Test real-world scenarios."""

    @pytest.fixture
    def generator(self):
        """Create a TagGenerator with mocked LLM."""
        with patch('src.agents.tag_generator.ChatOpenAI'):
            generator = TagGenerator()
            generator.llm = MagicMock()
            return generator

    def test_romance_specific_tags(self, generator):
        """Test that romance-specific tags are recognized."""
        romance_tags = ["#swoony", "#steamy", "#angsty"]

        for tag in romance_tags:
            assert tag in TagGenerator.AVAILABLE_TAGS

    def test_rating_influences_prompt(self, generator):
        """Test that rating is included in the prompt."""
        mock_response = MagicMock()
        mock_response.content = "#sad,#heavy"
        generator.llm.invoke.return_value = mock_response

        generator.generate_tags(
            title="Sad Book",
            rating=2.0,
            review="This made me cry."
        )

        # Check that rating was passed to prompt
        call_args = generator.llm.invoke.call_args[0][0]
        prompt_text = str(call_args)
        assert "2.0" in prompt_text

    def test_multiple_books_different_genres(self, generator):
        """Test batch generation with diverse romance subgenres."""
        books = [
            Book(
                title="Dark Romance",
                author="Author 1",
                rating=4.5,
                review="Intense and dark, but captivating.",
                category="Romance"
            ),
            Book(
                title="Contemporary Romance",
                author="Author 2",
                rating=4.0,
                review="Light, fun, and heartwarming.",
                category="Romance"
            ),
            Book(
                title="Fantasy Romance",
                author="Author 3",
                rating=4.5,
                review="Epic world-building with swoony romance.",
                category="Romance"
            )
        ]

        mock_responses = [
            MagicMock(content="#dark,#angsty,#exciting"),
            MagicMock(content="#fun,#heartwarming,#light"),
            MagicMock(content="#fantastical,#swoony,#exciting")
        ]
        generator.llm.batch.return_value = mock_responses

        results = generator.generate_tags_batch(books)

        assert results["Dark Romance"] == ["#dark", "#angsty", "#exciting"]
        assert results["Contemporary Romance"] == ["#fun", "#heartwarming", "#light"]
        assert results["Fantasy Romance"] == ["#fantastical", "#swoony", "#exciting"]
