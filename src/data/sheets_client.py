"""
Google Sheets client for reading and updating book data.
Supports both OAuth2 (for local development) and Service Account (for production).
"""

import gspread
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from typing import List, Optional
import os
import pickle

from src.config import settings
from src.data.models import Book


# Scopes required for Google Sheets and Drive access
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]


class SheetsClient:
    """Client for interacting with Google Sheets."""

    def __init__(self, use_service_account: bool = True, worksheets: Optional[List[str]] = None):
        """
        Initialize gspread client with credentials.

        Args:
            use_service_account: If True, use Service Account authentication (recommended for production).
                                If False, use OAuth2 flow (requires browser).
            worksheets: List of worksheet names to read from. If None, reads from ["2023", "2024", "2025"].
        """
        self.use_service_account = use_service_account
        self.creds = self._get_credentials()
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(settings.google_sheets_id)

        # Default to reading from all year worksheets
        # Note: "2025 " has a trailing space in the actual sheet
        self.worksheet_names = worksheets or ["2023", "2024", "2025"]

        # For backward compatibility
        self.sheet = self.spreadsheet.sheet1

    def _get_credentials(self):
        """
        Get credentials based on authentication method.
        Service Account is preferred for web/production environments.
        """
        if self.use_service_account:
            return self._get_service_account_credentials()
        else:
            return self._get_oauth_credentials()

    def _get_service_account_credentials(self) -> ServiceAccountCredentials:
        """
        Get Service Account credentials.
        This method doesn't require browser authentication.

        To use this:
        1. Create a Service Account in Google Cloud Console
        2. Download the JSON key file
        3. Share your Google Sheet with the service account email
        """
        try:
            creds = ServiceAccountCredentials.from_service_account_file(
                settings.google_credentials_path,
                scopes=SCOPES
            )
            return creds
        except Exception as e:
            print(f"Service Account authentication failed: {e}")
            print("Make sure:")
            print("1. credentials.json is a Service Account key file")
            print("2. The Service Account email has access to your Google Sheet")
            raise

    def _get_oauth_credentials(self) -> Credentials:
        """
        Get valid user credentials from storage or initiate OAuth2 flow.
        The token is stored in token.pickle for reuse.
        """
        creds = None
        token_path = 'token.pickle'

        # Load existing token if available
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                creds.refresh(Request())
            else:
                # Start OAuth2 flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.google_credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        return creds

    def get_all_books(self) -> List[Book]:
        """
        Load all books from multiple Google Sheets worksheets.
        Reads from worksheets specified in __init__ (default: 2023, 2024, 2025).

        Returns:
            List of Book objects from all worksheets combined
        """
        all_books = []

        for worksheet_name in self.worksheet_names:
            try:
                print(f"Loading from worksheet: {worksheet_name}")
                worksheet = self.spreadsheet.worksheet(worksheet_name)
                records = worksheet.get_all_records()

                books_from_sheet = self._parse_books_from_records(records, worksheet_name)
                all_books.extend(books_from_sheet)

                print(f"✓ Loaded {len(books_from_sheet)} books from {worksheet_name}")

            except gspread.WorksheetNotFound:
                print(f"⚠️  Worksheet '{worksheet_name}' not found, skipping...")
                continue
            except Exception as e:
                print(f"Error loading from worksheet '{worksheet_name}': {e}")
                continue

        print(f"\nTotal books loaded: {len(all_books)}")
        return all_books

    def _parse_books_from_records(self, records: List[dict], source_sheet: str = "") -> List[Book]:
        """
        Parse Book objects from sheet records.

        Args:
            records: List of dictionaries from get_all_records()
            source_sheet: Name of the source worksheet (for debugging)

        Returns:
            List of Book objects
        """
        books = []
        for record in records:
            try:
                author = record.get('Author', '')
                if not author or not isinstance(author, str):
                    continue

                title = record.get('Book Title', '').strip()
                if not title:
                    continue

                # Parse rating (handle emoji stars: ⭐⭐⭐ -> 3.0)
                rating_str = str(record.get('Rating', ''))
                if '⭐' in rating_str:
                    rating = float(rating_str.count('⭐'))
                else:
                    rating = float(rating_str) if rating_str and rating_str != '' else 3.0

                book = Book(
                    title=title,
                    author=author.strip(),
                    rating=rating,
                    review=record.get('Summary/Notes', ''),
                    trope=record.get('Trope', '').strip(),
                    category="Romance",  # Default for first user
                    tags=record.get('Tags', '')  # Tags might be empty or not exist yet
                )
                books.append(book)
            except Exception as e:
                print(f"Error parsing book from {source_sheet}: {record.get('Book Title', 'Unknown')}: {e}")
                continue

        return books

    def get_book_by_title(self, title: str) -> Optional[Book]:
        """
        Fetch a single book by title.

        Args:
            title: Book title to search for

        Returns:
            Book object or None if not found
        """
        books = self.get_all_books()
        for book in books:
            if book.title.strip().lower() == title.strip().lower():
                return book
        return None

    def update_tags(self, title: str, tags: List[str]) -> bool:
        """
        Update tags column for a specific book.

        Args:
            title: Book title to update
            tags: List of tags to set

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the row with matching title (search in "Book Title" column)
            cell = self.sheet.find(title)
            if not cell:
                print(f"Book not found: {title}")
                return False

            # Find Tags column index dynamically
            headers = self.sheet.row_values(1)
            if 'Tags' in headers:
                tags_col = headers.index('Tags') + 1  # 1-indexed
            else:
                # If Tags column doesn't exist, add it
                tags_col = len(headers) + 1
                self.sheet.update_cell(1, tags_col, 'Tags')
                print(f"Added 'Tags' column at position {tags_col}")

            tags_string = ",".join(tags)

            # Update the tags cell
            self.sheet.update_cell(cell.row, tags_col, tags_string)
            print(f"✓ Updated tags for '{title}': {tags_string}")
            return True

        except Exception as e:
            print(f"Error updating tags for '{title}': {e}")
            return False

    def add_book(self, book: Book) -> bool:
        """
        Add a new book to the sheet.

        Args:
            book: Book object to add

        Returns:
            True if successful, False otherwise
        """
        try:
            row = [
                book.title,
                book.author,
                book.rating,
                book.review,
                book.category,
                book.get_tags_string()
            ]
            self.sheet.append_row(row)
            print(f"✓ Added new book: '{book.title}'")
            return True
        except Exception as e:
            print(f"Error adding book '{book.title}': {e}")
            return False

    def get_books_without_tags(self) -> List[Book]:
        """
        Get all books that don't have tags yet.

        Returns:
            List of Book objects without tags
        """
        all_books = self.get_all_books()
        return [book for book in all_books if not book.has_tags()]

    def setup_worksheet(self, worksheet_name: str, include_sample_data: bool = False) -> bool:
        """
        Setup a new worksheet with proper headers and optional sample data.

        Args:
            worksheet_name: Name of the worksheet to create (e.g., "2025")
            include_sample_data: Whether to include sample book entries

        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to get existing worksheet
            try:
                worksheet = self.spreadsheet.worksheet(worksheet_name)
                print(f"⚠️  Worksheet '{worksheet_name}' already exists")

                # Check if it has headers
                first_row = worksheet.row_values(1)
                if first_row:
                    print(f"   Current headers: {first_row}")
                    return False

            except:
                # Worksheet doesn't exist, create it
                worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=100,
                    cols=10
                )
                print(f"✓ Created new worksheet: '{worksheet_name}'")

            # Setup headers
            headers = [
                "Title",
                "Author",
                "Rating",
                "Date",
                "Review",
                "Category",
                "Tags",
                "Trope",
                "ISBN",
                "Notes"
            ]

            worksheet.update('A1:J1', [headers])

            # Format header row (bold, frozen)
            worksheet.format('A1:J1', {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            })
            worksheet.freeze(rows=1)

            print(f"✓ Added headers to '{worksheet_name}'")

            # Add sample data if requested
            if include_sample_data:
                sample_data = [
                    [
                        "Book Lovers",
                        "Emily Henry",
                        "4.5",
                        "2024-01-15",
                        "A charming romance about two workaholics finding love. Great characters!",
                        "Romance",
                        "#heartwarming,#swoony",
                        "Contemporary Romance",
                        "",
                        "Loved the New York setting"
                    ],
                    [
                        "The Love Hypothesis",
                        "Ali Hazelwood",
                        "4.0",
                        "2024-01-20",
                        "Fake dating with a grumpy professor. STEM representation!",
                        "Romance",
                        "#swoony,#fun",
                        "Contemporary Romance",
                        "",
                        "Perfect for STEM nerds"
                    ]
                ]

                worksheet.update('A2:J3', sample_data)
                print(f"✓ Added 2 sample book entries")

            return True

        except Exception as e:
            print(f"Error setting up worksheet '{worksheet_name}': {e}")
            return False

    def get_spreadsheet_info(self) -> dict:
        """
        Get information about the current spreadsheet.

        Returns:
            Dictionary with spreadsheet details
        """
        try:
            worksheets = self.spreadsheet.worksheets()

            return {
                "spreadsheet_id": self.spreadsheet.id,
                "title": self.spreadsheet.title,
                "url": self.spreadsheet.url,
                "worksheets": [
                    {
                        "title": ws.title,
                        "rows": ws.row_count,
                        "cols": ws.col_count,
                        "id": ws.id
                    }
                    for ws in worksheets
                ],
                "total_worksheets": len(worksheets)
            }
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    # Test Google Sheets connection
    print("=== Testing Google Sheets Client ===\n")

    try:
        client = SheetsClient()
        print("✅ Successfully connected to Google Sheets!\n")

        # Test 1: Load all books
        books = client.get_all_books()
        print(f"📚 Loaded {len(books)} books from sheet\n")

        if books:
            # Show first book
            print("First book:")
            first_book = books[0]
            print(f"  Title: {first_book.title}")
            print(f"  Author: {first_book.author}")
            print(f"  Rating: {first_book.rating}")
            print(f"  Category: {first_book.category}")
            print(f"  Tags: {first_book.tags}")
            print(f"  Has tags: {first_book.has_tags()}\n")

        # Test 2: Books without tags
        no_tags = client.get_books_without_tags()
        print(f"📝 Books without tags: {len(no_tags)}")

        if no_tags and len(no_tags) <= 5:
            print("\nBooks needing tags:")
            for book in no_tags[:5]:
                print(f"  - {book.title} by {book.author}")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure:")
        print("1. credentials.json is in the project root")
        print("2. Google Sheets ID is correct in .env")
        print("3. You have authorized the OAuth app")
