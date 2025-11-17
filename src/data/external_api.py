"""
External API clients for fetching book metadata.
Supports Google Books API and Open Library.
"""

import requests
import time
from typing import Optional, Dict, Any, List
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

    def search_romance_books(
        self,
        min_year: int = 2020,
        max_books: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Search for Romance books using hybrid strategy (Author + Keyword).

        Based on comprehensive EDA, this uses:
        - PRIMARY (70%): Author-based search (most reliable)
        - SECONDARY (30%): Keyword-based search (diversity)

        Args:
            min_year: Minimum publication year (default: 2020)
            max_books: Maximum number of books to return (default: 200)

        Returns:
            List of book dictionaries with metadata
        """
        print(f"🔍 Searching for Romance books (published {min_year}+)...")
        all_books = []

        # STEP 1: Author-based search (70%)
        print("\n📚 STEP 1: Author-based search")
        print("-" * 60)

        authors = [
            # Contemporary Romance
            'Emily Henry', 'Colleen Hoover', 'Ali Hazelwood',
            'Lucy Score', 'Tessa Bailey', 'Beth O Leary',
            'Christina Lauren', 'Abby Jimenez',

            # Dark Romance
            'Penelope Douglas', 'L.J. Shen', 'H.D. Carlton',

            # Sports Romance
            'Hannah Grace', 'Elle Kennedy', 'Kennedy Ryan',
            'Ilsa Madden-Mills',

            # Fantasy Romance
            'Sarah J. Maas', 'Rebecca Yarros',
            'Jennifer L. Armentrout', 'Carissa Broadbent',

            # Historical Romance
            'Lisa Kleypas', 'Tessa Dare',
        ]

        for author in authors:
            author_books = self._search_by_author(author, min_year)
            all_books.extend(author_books)
            print(f"  {author:25s}: {len(author_books):2d} books")

        print(f"\n  Subtotal from authors: {len(all_books)} books")

        # STEP 2: Keyword-based search (30%)
        print("\n🔑 STEP 2: Keyword-based search")
        print("-" * 60)

        keywords = [
            # Tropes
            'enemies to lovers romance',
            'second chance romance',
            'fake relationship romance',
            'forced proximity romance',
            'grumpy sunshine romance',

            # Subgenres
            'sports romance',
            'office romance',
            'small town romance',
            'billionaire romance',
            'royal romance',
        ]

        for keyword in keywords:
            keyword_books = self._search_by_keyword(keyword, min_year)
            all_books.extend(keyword_books)
            print(f"  {keyword:30s}: {len(keyword_books):2d} books")

        print(f"\n  Subtotal from keywords: {len(all_books) - sum(len(self._search_by_author(a, min_year)) for a in authors)} books")

        # STEP 3: Deduplication
        print("\n🔄 STEP 3: Deduplication")
        print("-" * 60)
        unique_books = self._deduplicate_books(all_books)
        print(f"  Before: {len(all_books)} books")
        print(f"  After:  {len(unique_books)} unique books")

        # STEP 4: Limit to max_books
        final_books = unique_books[:max_books]

        print(f"\n✅ Final result: {len(final_books)} books")
        print("=" * 60)

        return final_books

    def _search_by_author(
        self,
        author_name: str,
        min_year: int = 2020
    ) -> List[Dict[str, Any]]:
        """
        Search books by author name (most reliable method).

        Args:
            author_name: Author name to search
            min_year: Minimum publication year

        Returns:
            List of books by this author
        """
        books = []

        # Pagination (up to 5 pages = 200 results max)
        for page in range(5):
            params = {
                'q': f'inauthor:"{author_name}"',
                'maxResults': 40,
                'startIndex': page * 40,
                'printType': 'books',
                'langRestrict': 'en'
                # NOTE: NO orderBy=newest (it's broken!)
            }

            try:
                response = requests.get(
                    self.google_books_base,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()

                if not data.get('items'):
                    break  # No more results

                for item in data['items']:
                    volume = item.get('volumeInfo', {})
                    pub_date = volume.get('publishedDate', '')

                    # Client-side filtering (CRITICAL!)
                    if pub_date:
                        try:
                            pub_year = int(pub_date.split('-')[0])
                            if pub_year >= min_year:
                                # Description is MANDATORY for embeddings
                                if volume.get('description'):
                                    book = self._extract_book_info(volume, 'author', author_name)
                                    books.append(book)
                        except (ValueError, IndexError):
                            continue

                time.sleep(0.3)  # Rate limiting

            except Exception as e:
                print(f"    Error searching {author_name}: {e}")
                break

        return books

    def _search_by_keyword(
        self,
        keyword: str,
        min_year: int = 2020
    ) -> List[Dict[str, Any]]:
        """
        Search books by keyword (for diversity).

        Args:
            keyword: Keyword to search (trope or subgenre)
            min_year: Minimum publication year

        Returns:
            List of Romance books matching keyword
        """
        books = []

        # Pagination (up to 3 pages = 120 results max)
        for page in range(3):
            params = {
                'q': f'"{keyword}"',  # Exact phrase search
                'maxResults': 40,
                'startIndex': page * 40,
                'printType': 'books',
                'langRestrict': 'en'
            }

            try:
                response = requests.get(
                    self.google_books_base,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()

                if not data.get('items'):
                    break

                for item in data['items']:
                    volume = item.get('volumeInfo', {})
                    pub_date = volume.get('publishedDate', '')

                    # Client-side filtering
                    if pub_date:
                        try:
                            pub_year = int(pub_date.split('-')[0])
                            if pub_year >= min_year:
                                if volume.get('description'):
                                    # IMPORTANT: Verify it's actually Romance
                                    if self._is_romance_book(volume):
                                        book = self._extract_book_info(volume, 'keyword', keyword)
                                        books.append(book)
                        except (ValueError, IndexError):
                            continue

                time.sleep(0.3)

            except Exception as e:
                print(f"    Error searching '{keyword}': {e}")
                break

        return books

    def _is_romance_book(self, volume_info: Dict[str, Any]) -> bool:
        """
        Verify if a book is actually Romance (client-side filtering).

        Args:
            volume_info: Volume info from Google Books API

        Returns:
            True if Romance, False otherwise
        """
        categories = volume_info.get('categories', [])
        description = volume_info.get('description', '').lower()
        title = volume_info.get('title', '').lower()

        # Check categories
        if any('romance' in str(cat).lower() for cat in categories):
            return True

        # Check description
        romance_keywords = ['romance', 'love story', 'relationship', 'lovers']
        if any(keyword in description for keyword in romance_keywords):
            # Exclude academic books
            exclude_keywords = ['academic', 'scholarly', 'critical analysis', 'literary criticism']
            if not any(keyword in description or keyword in title for keyword in exclude_keywords):
                return True

        # Check title
        if 'romance' in title:
            return True

        return False

    def _extract_book_info(
        self,
        volume_info: Dict[str, Any],
        search_method: str,
        search_query: str
    ) -> Dict[str, Any]:
        """
        Extract book information from Google Books volume info.

        Args:
            volume_info: Volume info dict from API
            search_method: 'author' or 'keyword'
            search_query: The actual search query used

        Returns:
            Standardized book dictionary
        """
        # Extract ISBNs
        isbn_13 = None
        isbn_10 = None
        for identifier in volume_info.get('industryIdentifiers', []):
            if identifier['type'] == 'ISBN_13':
                isbn_13 = identifier['identifier']
            elif identifier['type'] == 'ISBN_10':
                isbn_10 = identifier['identifier']

        return {
            'title': volume_info.get('title'),
            'authors': volume_info.get('authors', []),
            'published': volume_info.get('publishedDate'),
            'description': volume_info.get('description'),
            'isbn_13': isbn_13,
            'isbn_10': isbn_10,
            'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail'),
            'categories': volume_info.get('categories', []),
            'page_count': volume_info.get('pageCount'),
            'search_method': search_method,
            'search_query': search_query
        }

    def _deduplicate_books(self, books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate books based on ISBN or Title+Author.

        Args:
            books: List of book dictionaries

        Returns:
            Deduplicated list
        """
        seen = set()
        unique_books = []

        for book in books:
            # ISBN-based deduplication (preferred)
            isbn = book.get('isbn_13') or book.get('isbn_10')
            if isbn:
                if isbn in seen:
                    continue
                seen.add(isbn)
            else:
                # Title + Author based deduplication
                key = (
                    book['title'].lower().strip(),
                    ','.join(sorted([a.lower() for a in book['authors']]))
                )
                if key in seen:
                    continue
                seen.add(key)

            unique_books.append(book)

        return unique_books


