"""
External API clients for fetching book metadata.
Supports Google Books API and Open Library.
"""

import requests
from typing import Optional, Dict, Any
from urllib.parse import quote


class BookMetadataFetcher:
    """Fetches book metadata from external APIs."""

    def __init__(self, timeout: int = 5):
        """
        Initialize the metadata fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.google_books_base = "https://www.googleapis.com/books/v1/volumes"
        self.open_library_base = "https://covers.openlibrary.org/b"

    def fetch_google_books(self, title: str, author: str) -> Optional[Dict[str, Any]]:
        """
        Fetch book metadata from Google Books API.

        Args:
            title: Book title
            author: Book author

        Returns:
            Dictionary with book metadata or None if not found

        Example return:
            {
                'title': 'The Love Hypothesis',
                'authors': ['Ali Hazelwood'],
                'description': 'A contemporary romantic comedy...',
                'categories': ['Fiction', 'Romance'],
                'thumbnail': 'https://...',
                'isbn_13': '9780593336823',
                'isbn_10': '0593336828',
                'published_date': '2021-09-14',
                'page_count': 384
            }
        """
        try:
            # Build search query
            query = f'intitle:{quote(title)}+inauthor:{quote(author)}'
            url = f"{self.google_books_base}?q={query}&maxResults=1"

            # Make request
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Check if we got results
            if data.get('totalItems', 0) == 0:
                print(f"No results found for: {title} by {author}")
                return None

            # Extract first result
            item = data['items'][0]
            volume_info = item.get('volumeInfo', {})

            # Extract ISBNs
            isbn_13 = None
            isbn_10 = None
            for identifier in volume_info.get('industryIdentifiers', []):
                if identifier['type'] == 'ISBN_13':
                    isbn_13 = identifier['identifier']
                elif identifier['type'] == 'ISBN_10':
                    isbn_10 = identifier['identifier']

            # Build result
            result = {
                'title': volume_info.get('title'),
                'authors': volume_info.get('authors', []),
                'description': volume_info.get('description'),
                'categories': volume_info.get('categories', []),
                'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail'),
                'isbn_13': isbn_13,
                'isbn_10': isbn_10,
                'published_date': volume_info.get('publishedDate'),
                'page_count': volume_info.get('pageCount')
            }

            return result

        except requests.RequestException as e:
            print(f"Error fetching from Google Books: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def fetch_open_library_cover(self, isbn: str) -> Optional[str]:
        """
        Fetch high-resolution book cover from Open Library.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Cover URL or None if not found

        Example return:
            'https://covers.openlibrary.org/b/isbn/9780593336823-L.jpg'
        """
        try:
            # Try large size cover
            url = f"{self.open_library_base}/isbn/{isbn}-L.jpg"

            # Check if URL exists
            response = requests.head(url, timeout=self.timeout)

            if response.status_code == 200:
                return url
            else:
                print(f"Cover not found for ISBN: {isbn}")
                return None

        except requests.RequestException as e:
            print(f"Error fetching cover from Open Library: {e}")
            return None

    def enrich_book_metadata(self, title: str, author: str) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive book metadata from multiple sources.

        Args:
            title: Book title
            author: Book author

        Returns:
            Combined metadata from Google Books and Open Library

        Example return:
            {
                'title': 'The Love Hypothesis',
                'authors': ['Ali Hazelwood'],
                'description': 'A contemporary romantic comedy...',
                'categories': ['Fiction', 'Romance'],
                'thumbnail': 'https://covers.openlibrary.org/...',  # High-res from Open Library
                'isbn_13': '9780593336823',
                'isbn_10': '0593336828',
                'published_date': '2021-09-14',
                'page_count': 384
            }
        """
        # Fetch from Google Books
        metadata = self.fetch_google_books(title, author)

        if not metadata:
            return None

        # Try to get better cover from Open Library
        if metadata.get('isbn_13'):
            cover_url = self.fetch_open_library_cover(metadata['isbn_13'])
            if cover_url:
                metadata['thumbnail'] = cover_url
        elif metadata.get('isbn_10'):
            cover_url = self.fetch_open_library_cover(metadata['isbn_10'])
            if cover_url:
                metadata['thumbnail'] = cover_url

        return metadata


if __name__ == "__main__":
    # Test the metadata fetcher
    print("=== Testing BookMetadataFetcher ===\n")

    fetcher = BookMetadataFetcher()

    # Test 1: Popular Romance book
    print("Test 1: The Love Hypothesis by Ali Hazelwood")
    print("-" * 60)

    result = fetcher.fetch_google_books("The Love Hypothesis", "Ali Hazelwood")

    if result:
        print(f"✅ Found!")
        print(f"Title: {result['title']}")
        print(f"Authors: {', '.join(result['authors'])}")
        print(f"Description: {result['description'][:100]}...")
        print(f"Categories: {result['categories']}")
        print(f"ISBN-13: {result['isbn_13']}")
        print(f"Published: {result['published_date']}")
        print(f"Pages: {result['page_count']}")
        print(f"Thumbnail: {result['thumbnail']}")
    else:
        print("❌ Not found")

    print("\n" + "="*60 + "\n")

    # Test 2: Enrich with Open Library cover
    print("Test 2: Enriched metadata with Open Library cover")
    print("-" * 60)

    enriched = fetcher.enrich_book_metadata("Beach Read", "Emily Henry")

    if enriched:
        print(f"✅ Enriched!")
        print(f"Title: {enriched['title']}")
        print(f"Description: {enriched['description'][:100]}...")
        print(f"Cover URL: {enriched['thumbnail']}")
    else:
        print("❌ Not found")

    print("\n" + "="*60 + "\n")

    # Test 3: Another Romance book
    print("Test 3: Icebreaker by Hannah Grace")
    print("-" * 60)

    result = fetcher.fetch_google_books("Icebreaker", "Hannah Grace")

    if result:
        print(f"✅ Found!")
        print(f"Title: {result['title']}")
        print(f"Authors: {', '.join(result['authors'])}")
        print(f"Description: {result['description'][:150] if result['description'] else 'N/A'}...")
    else:
        print("❌ Not found")

    print("\n✅ Metadata fetcher test complete!")
