"""
Unit tests for SheetsClient.
Tests all methods with mocked Google Sheets API.
"""
import pytest
from unittest.mock import MagicMock, Mock, patch, call
from datetime import datetime

from src.data.sheets_client import SheetsClient
from src.data.models import Book


class TestSheetsClientInitialization:
    """Test SheetsClient initialization."""

    @patch('src.data.sheets_client.gspread.authorize')
    @patch('src.data.sheets_client.ServiceAccountCredentials.from_service_account_file')
    def test_init_with_service_account(self, mock_sa_creds, mock_authorize):
        """Test initialization with Service Account."""
        mock_creds = MagicMock()
        mock_sa_creds.return_value = mock_creds

        mock_client = MagicMock()
        mock_authorize.return_value = mock_client

        mock_spreadsheet = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet

        # Create mock worksheet for current year
        mock_worksheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet

        client = SheetsClient(use_service_account=True)

        assert client.use_service_account is True
        assert client.worksheet_names == ["2023", "2024", "2025"]
        mock_sa_creds.assert_called_once()
        mock_authorize.assert_called_once_with(mock_creds)

    @patch('src.data.sheets_client.gspread.authorize')
    @patch('src.data.sheets_client.ServiceAccountCredentials.from_service_account_file')
    def test_init_with_custom_worksheets(self, mock_sa_creds, mock_authorize):
        """Test initialization with custom worksheet list."""
        mock_creds = MagicMock()
        mock_sa_creds.return_value = mock_creds

        mock_client = MagicMock()
        mock_authorize.return_value = mock_client

        mock_spreadsheet = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet

        mock_worksheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet

        custom_worksheets = ["2024", "2025"]
        client = SheetsClient(use_service_account=True, worksheets=custom_worksheets)

        assert client.worksheet_names == custom_worksheets


class TestSheetsClientReadOperations:
    """Test SheetsClient read operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked SheetsClient."""
        with patch('src.data.sheets_client.gspread.authorize'), \
             patch('src.data.sheets_client.ServiceAccountCredentials.from_service_account_file'):

            client = SheetsClient(use_service_account=True)

            # Mock spreadsheet and worksheets
            client.spreadsheet = MagicMock()
            client.sheet = MagicMock()

            return client

    def test_get_all_books_single_worksheet(self, mock_client):
        """Test loading books from a single worksheet."""
        mock_worksheet = MagicMock()
        mock_client.spreadsheet.worksheet.return_value = mock_worksheet

        # Mock sheet data
        mock_records = [
            {
                "Book Title": "Test Book 1",
                "Author": "Author 1",
                "Rating": "⭐⭐⭐⭐",
                "Summary/Notes": "Great book!",
                "Trope": "Enemies to Lovers",
                "Tags": ""
            },
            {
                "Book Title": "Test Book 2",
                "Author": "Author 2",
                "Rating": "⭐⭐⭐",
                "Summary/Notes": "Good read.",
                "Trope": "Dark Romance",
                "Tags": ""
            }
        ]
        mock_worksheet.get_all_records.return_value = mock_records

        mock_client.worksheet_names = ["2024"]
        books = mock_client.get_all_books()

        assert len(books) == 2
        assert books[0].title == "Test Book 1"
        assert books[0].rating == 4.0
        assert books[1].title == "Test Book 2"
        assert books[1].rating == 3.0

    def test_get_all_books_multiple_worksheets(self, mock_client):
        """Test loading books from multiple worksheets."""
        def mock_worksheet_side_effect(name):
            mock_ws = MagicMock()
            if name == "2023":
                mock_ws.get_all_records.return_value = [
                    {
                        "Book Title": "Book 2023",
                        "Author": "Author A",
                        "Rating": "⭐⭐⭐⭐",
                        "Summary/Notes": "Great!",
                        "Trope": "Romance",
                        "Tags": ""
                    }
                ]
            elif name == "2024":
                mock_ws.get_all_records.return_value = [
                    {
                        "Book Title": "Book 2024",
                        "Author": "Author B",
                        "Rating": "⭐⭐⭐⭐⭐",
                        "Summary/Notes": "Amazing!",
                        "Trope": "Dark Romance",
                        "Tags": ""
                    }
                ]
            return mock_ws

        mock_client.spreadsheet.worksheet.side_effect = mock_worksheet_side_effect
        mock_client.worksheet_names = ["2023", "2024"]

        books = mock_client.get_all_books()

        assert len(books) == 2
        assert books[0].title == "Book 2023"
        assert books[1].title == "Book 2024"

    def test_parse_books_from_records_emoji_rating(self, mock_client):
        """Test parsing books with emoji star ratings."""
        records = [
            {
                "Book Title": "Test Book",
                "Author": "Test Author",
                "Rating": "⭐⭐⭐⭐⭐",
                "Summary/Notes": "Perfect!",
                "Trope": "Romance",
                "Tags": ""
            }
        ]

        books = mock_client._parse_books_from_records(records)

        assert len(books) == 1
        assert books[0].rating == 5.0

    def test_parse_books_from_records_numeric_rating(self, mock_client):
        """Test parsing books with numeric ratings."""
        records = [
            {
                "Book Title": "Test Book",
                "Author": "Test Author",
                "Rating": "4.5",
                "Summary/Notes": "Great!",
                "Trope": "Romance",
                "Tags": ""
            }
        ]

        books = mock_client._parse_books_from_records(records)

        assert len(books) == 1
        assert books[0].rating == 4.5

    def test_parse_books_from_records_skips_invalid(self, mock_client):
        """Test parsing skips invalid records."""
        records = [
            {
                "Book Title": "",  # Empty title
                "Author": "Author 1",
                "Rating": "⭐⭐⭐",
                "Summary/Notes": "",
                "Trope": "",
                "Tags": ""
            },
            {
                "Book Title": "Valid Book",
                "Author": "",  # Empty author
                "Rating": "⭐⭐⭐",
                "Summary/Notes": "",
                "Trope": "",
                "Tags": ""
            },
            {
                "Book Title": "Good Book",
                "Author": "Good Author",
                "Rating": "⭐⭐⭐⭐",
                "Summary/Notes": "Nice!",
                "Trope": "Romance",
                "Tags": ""
            }
        ]

        books = mock_client._parse_books_from_records(records)

        # Should only have 1 valid book
        assert len(books) == 1
        assert books[0].title == "Good Book"

    def test_get_book_by_title_found(self, mock_client):
        """Test getting a book by title when it exists."""
        mock_worksheet = MagicMock()
        mock_client.spreadsheet.worksheet.return_value = mock_worksheet

        mock_records = [
            {
                "Book Title": "Target Book",
                "Author": "Target Author",
                "Rating": "⭐⭐⭐⭐",
                "Summary/Notes": "Great!",
                "Trope": "Romance",
                "Tags": ""
            }
        ]
        mock_worksheet.get_all_records.return_value = mock_records
        mock_client.worksheet_names = ["2024"]

        book = mock_client.get_book_by_title("Target Book")

        assert book is not None
        assert book.title == "Target Book"
        assert book.author == "Target Author"

    def test_get_book_by_title_case_insensitive(self, mock_client):
        """Test getting a book by title is case-insensitive."""
        mock_worksheet = MagicMock()
        mock_client.spreadsheet.worksheet.return_value = mock_worksheet

        mock_records = [
            {
                "Book Title": "Target Book",
                "Author": "Author",
                "Rating": "⭐⭐⭐",
                "Summary/Notes": "",
                "Trope": "",
                "Tags": ""
            }
        ]
        mock_worksheet.get_all_records.return_value = mock_records
        mock_client.worksheet_names = ["2024"]

        book = mock_client.get_book_by_title("target book")

        assert book is not None
        assert book.title == "Target Book"

    def test_get_book_by_title_not_found(self, mock_client):
        """Test getting a book that doesn't exist returns None."""
        mock_worksheet = MagicMock()
        mock_client.spreadsheet.worksheet.return_value = mock_worksheet

        mock_records = []
        mock_worksheet.get_all_records.return_value = mock_records
        mock_client.worksheet_names = ["2024"]

        book = mock_client.get_book_by_title("Nonexistent Book")

        assert book is None

    def test_get_books_without_tags(self, mock_client):
        """Test getting books that don't have tags."""
        mock_worksheet = MagicMock()
        mock_client.spreadsheet.worksheet.return_value = mock_worksheet

        mock_records = [
            {
                "Book Title": "Book With Tags",
                "Author": "Author 1",
                "Rating": "⭐⭐⭐",
                "Summary/Notes": "",
                "Trope": "",
                "Tags": "#tag1,#tag2"
            },
            {
                "Book Title": "Book Without Tags",
                "Author": "Author 2",
                "Rating": "⭐⭐⭐",
                "Summary/Notes": "",
                "Trope": "",
                "Tags": ""
            }
        ]
        mock_worksheet.get_all_records.return_value = mock_records
        mock_client.worksheet_names = ["2024"]

        books = mock_client.get_books_without_tags()

        assert len(books) == 1
        assert books[0].title == "Book Without Tags"


class TestSheetsClientWriteOperations:
    """Test SheetsClient write operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked SheetsClient."""
        with patch('src.data.sheets_client.gspread.authorize'), \
             patch('src.data.sheets_client.ServiceAccountCredentials.from_service_account_file'):

            client = SheetsClient(use_service_account=True)
            client.spreadsheet = MagicMock()
            client.sheet = MagicMock()

            return client

    def test_add_book_success(self, mock_client):
        """Test successfully adding a book."""
        # Mock get_all_values to return existing data
        mock_client.sheet.get_all_values.return_value = [
            ["Month", "#", "Book Title", "Author", "Pages", "Type", "Trope", "Rating", "Spice", "Summary"],
            ["January", "1", "Existing Book", "Author", "", "Romance", "", "⭐⭐⭐", "", "Review"]
        ]

        test_book = Book(
            title="New Book",
            author="New Author",
            rating=4.0,
            review="Great book!",
            trope="Dark Romance",
            category="Romance"
        )

        result = mock_client.add_book(test_book)

        assert result is True
        mock_client.sheet.append_row.assert_called_once()

        # Check the row that was added
        call_args = mock_client.sheet.append_row.call_args[0][0]
        assert call_args[2] == "New Book"  # Title
        assert call_args[3] == "New Author"  # Author
        assert call_args[6] == "Dark Romance"  # Trope
        assert call_args[7] == "⭐⭐⭐⭐"  # Rating (4 stars)
        assert call_args[9] == "Great book!"  # Review

    def test_add_book_reading_order_calculation(self, mock_client):
        """Test that reading order is calculated correctly."""
        mock_client.sheet.get_all_values.return_value = [
            ["Month", "#", "Book Title", "Author", "Pages", "Type", "Trope", "Rating", "Spice", "Summary"],
            ["January", "1", "Book 1", "Author", "", "Romance", "", "⭐⭐⭐", "", "Review"],
            ["February", "2", "Book 2", "Author", "", "Romance", "", "⭐⭐⭐", "", "Review"],
            ["March", "3", "Book 3", "Author", "", "Romance", "", "⭐⭐⭐", "", "Review"]
        ]

        test_book = Book(
            title="New Book",
            author="Author",
            rating=3.0,
            review="",
            category="Romance"
        )

        mock_client.add_book(test_book)

        call_args = mock_client.sheet.append_row.call_args[0][0]
        assert call_args[1] == 4  # Next order should be 4

    def test_add_book_handles_empty_rows(self, mock_client):
        """Test that add_book correctly handles empty rows in order calculation."""
        mock_client.sheet.get_all_values.return_value = [
            ["Month", "#", "Book Title", "Author", "Pages", "Type", "Trope", "Rating", "Spice", "Summary"],
            ["January", "1", "Book 1", "Author", "", "Romance", "", "⭐⭐⭐", "", "Review"],
            ["", "", "", "", "", "", "", "", "", ""],  # Empty row
            ["February", "2", "Book 2", "Author", "", "Romance", "", "⭐⭐⭐", "", "Review"]
        ]

        test_book = Book(
            title="New Book",
            author="Author",
            rating=3.0,
            review="",
            category="Romance"
        )

        mock_client.add_book(test_book)

        call_args = mock_client.sheet.append_row.call_args[0][0]
        assert call_args[1] == 3  # Next order should be 3 (skipping empty row)

    def test_update_tags_success(self, mock_client):
        """Test successfully updating tags for a book."""
        # Mock finding the book
        mock_cell = MagicMock()
        mock_cell.row = 2
        mock_client.sheet.find.return_value = mock_cell

        # Mock headers
        mock_client.sheet.row_values.return_value = [
            "Month", "#", "Book Title", "Author", "Pages", "Type", "Trope", "Rating", "Spice", "Summary", "Tags"
        ]

        result = mock_client.update_tags("Test Book", ["#tag1", "#tag2", "#tag3"])

        assert result is True
        mock_client.sheet.update_cell.assert_called_once_with(2, 11, "#tag1,#tag2,#tag3")

    def test_update_tags_creates_column_if_missing(self, mock_client):
        """Test that update_tags creates Tags column if it doesn't exist."""
        mock_cell = MagicMock()
        mock_cell.row = 2
        mock_client.sheet.find.return_value = mock_cell

        # Mock headers without Tags column
        mock_client.sheet.row_values.return_value = [
            "Month", "#", "Book Title", "Author", "Pages", "Type", "Trope", "Rating", "Spice", "Summary"
        ]

        result = mock_client.update_tags("Test Book", ["#tag1"])

        assert result is True
        # Should call update_cell twice: once for header, once for tags
        assert mock_client.sheet.update_cell.call_count == 2

    def test_update_tags_book_not_found(self, mock_client):
        """Test updating tags when book is not found."""
        mock_client.sheet.find.return_value = None

        result = mock_client.update_tags("Nonexistent Book", ["#tag1"])

        assert result is False


class TestSheetsClientWorksheetSetup:
    """Test worksheet setup functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked SheetsClient."""
        with patch('src.data.sheets_client.gspread.authorize'), \
             patch('src.data.sheets_client.ServiceAccountCredentials.from_service_account_file'):

            client = SheetsClient(use_service_account=True)
            client.spreadsheet = MagicMock()
            client.sheet = MagicMock()

            return client

    def test_setup_worksheet_creates_new(self, mock_client):
        """Test creating a new worksheet with proper setup."""
        import gspread

        # Mock worksheet doesn't exist
        mock_client.spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound("Not found")

        mock_new_worksheet = MagicMock()
        mock_new_worksheet.id = 123
        mock_client.spreadsheet.add_worksheet.return_value = mock_new_worksheet

        result = mock_client.setup_worksheet("NEW_2026", include_sample_data=False)

        assert result is True
        mock_client.spreadsheet.add_worksheet.assert_called_once()
        mock_new_worksheet.update.assert_called_once()  # Headers
        mock_new_worksheet.format.assert_called_once()  # Header formatting
        mock_new_worksheet.freeze.assert_called_once()  # Freeze first row
        mock_client.spreadsheet.batch_update.assert_called()  # Data validation & colors

    def test_setup_worksheet_with_sample_data(self, mock_client):
        """Test creating worksheet with sample data."""
        import gspread

        mock_client.spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound("Not found")

        mock_new_worksheet = MagicMock()
        mock_new_worksheet.id = 123
        mock_client.spreadsheet.add_worksheet.return_value = mock_new_worksheet

        result = mock_client.setup_worksheet("NEW_2026", include_sample_data=True)

        assert result is True
        # Should update twice: once for headers, once for sample data
        assert mock_new_worksheet.update.call_count == 2

    def test_setup_worksheet_already_exists(self, mock_client):
        """Test setup when worksheet already exists."""
        mock_existing_worksheet = MagicMock()
        mock_existing_worksheet.row_values.return_value = ["Month", "#", "Book Title"]
        mock_client.spreadsheet.worksheet.return_value = mock_existing_worksheet

        result = mock_client.setup_worksheet("2024", include_sample_data=False)

        assert result is False


class TestSheetsClientInfo:
    """Test spreadsheet information retrieval."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked SheetsClient."""
        with patch('src.data.sheets_client.gspread.authorize'), \
             patch('src.data.sheets_client.ServiceAccountCredentials.from_service_account_file'):

            client = SheetsClient(use_service_account=True)
            client.spreadsheet = MagicMock()
            client.sheet = MagicMock()

            return client

    def test_get_spreadsheet_info(self, mock_client):
        """Test getting spreadsheet information."""
        mock_client.spreadsheet.id = "test-sheet-id"
        mock_client.spreadsheet.title = "Test Spreadsheet"
        mock_client.spreadsheet.url = "https://docs.google.com/spreadsheets/d/test-sheet-id"

        mock_ws1 = MagicMock()
        mock_ws1.title = "2024"
        mock_ws1.row_count = 100
        mock_ws1.col_count = 10
        mock_ws1.id = 1

        mock_ws2 = MagicMock()
        mock_ws2.title = "2025"
        mock_ws2.row_count = 50
        mock_ws2.col_count = 10
        mock_ws2.id = 2

        mock_client.spreadsheet.worksheets.return_value = [mock_ws1, mock_ws2]

        info = mock_client.get_spreadsheet_info()

        assert info["spreadsheet_id"] == "test-sheet-id"
        assert info["title"] == "Test Spreadsheet"
        assert info["total_worksheets"] == 2
        assert len(info["worksheets"]) == 2
        assert info["worksheets"][0]["title"] == "2024"
