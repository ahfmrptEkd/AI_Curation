"""
Discover new Romance books from Google Books API and add to Vector DB.

This script:
1. Searches for 150-200 recent Romance books (2020-2025) using hybrid strategy
2. Excludes books the user has already read
3. Adds discovered books to ChromaDB with 'source=discovered' metadata
4. Shows progress and statistics

Usage:
    python scripts/05_discover_new_books.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.external_api import BookMetadataFetcher
from src.data.sheets_client import SheetsClient
from src.vectordb.chroma_manager import ChromaManager
from src.vectordb.embeddings import EmbeddingManager


def main():
    print("=" * 80)
    print("          ROMANCE BOOK DISCOVERY & VECTOR DB UPDATE")
    print("=" * 80)
    print()

    # Step 1: Load user's reading list (to exclude)
    print("📖 STEP 1: Loading user's reading list...")
    print("-" * 80)

    sheets = SheetsClient()
    user_books = sheets.get_all_books()
    user_titles = {book.title.lower().strip() for book in user_books}

    print(f"  User has read: {len(user_books)} books")
    print(f"  Titles to exclude: {len(user_titles)}")
    print()

    # Step 2: Search for new Romance books
    print("🔍 STEP 2: Searching for new Romance books from Google Books API...")
    print("-" * 80)

    fetcher = BookMetadataFetcher()
    discovered_books = fetcher.search_romance_books(
        min_year=2020,
        max_books=200
    )

    print()
    print(f"  Total discovered: {len(discovered_books)} books")
    print()

    # Step 3: Filter out already-read books
    print("🔄 STEP 3: Filtering out already-read books...")
    print("-" * 80)

    new_books = []
    already_read = []

    for book in discovered_books:
        title_normalized = book['title'].lower().strip()
        if title_normalized in user_titles:
            already_read.append(book['title'])
        else:
            new_books.append(book)

    print(f"  Already read (excluded): {len(already_read)} books")
    print(f"  New books to add: {len(new_books)} books")

    if already_read:
        print(f"\n  Sample already-read books:")
        for title in already_read[:5]:
            print(f"    - {title}")
    print()

    # Step 4: Add to Vector DB
    print("💾 STEP 4: Adding new books to Vector DB...")
    print("-" * 80)

    if not new_books:
        print("  ⚠️  No new books to add!")
        return

    chroma = ChromaManager()
    embedding_manager = EmbeddingManager()

    # Get current count
    current_count = chroma.collection.count()
    print(f"  Current Vector DB size: {current_count} books")

    # Add books in batches (directly, no Book model needed)
    batch_size = 20
    added_count = 0

    for i in range(0, len(new_books), batch_size):
        batch = new_books[i:i + batch_size]

        # Prepare documents, metadatas, embeddings, and IDs
        documents = []
        metadatas = []
        ids = []

        for idx, book_dict in enumerate(batch):
            # Document text for embedding (use description)
            author_str = ', '.join(book_dict['authors']) if book_dict['authors'] else 'Unknown'
            doc_text = f"Title: {book_dict['title']}\nAuthor: {author_str}\nDescription: {book_dict['description']}"
            documents.append(doc_text)

            # Metadata (only essential fields, no None values)
            metadata = {
                'title': book_dict['title'],
                'author': author_str,
                'category': 'Romance',
                'source': 'discovered',  # KEY: Distinguish from user-read books
                'published': book_dict.get('published', '')[:4],  # Just the year
                'search_method': book_dict['search_method'],
            }
            metadatas.append(metadata)

            # ID
            book_id = f"discovered_{added_count + idx}"
            ids.append(book_id)

        # Generate embeddings (one by one using embed_query)
        embeddings = [embedding_manager.embed_query(doc) for doc in documents]

        # Add batch to ChromaDB
        chroma.collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )

        added_count += len(batch)
        print(f"  Added batch {i//batch_size + 1}: {len(batch)} books (total: {added_count}/{len(new_books)})")

    # Verify
    new_count = chroma.collection.count()
    print(f"\n  New Vector DB size: {new_count} books")
    print(f"  Increase: +{new_count - current_count} books")
    print()

    # Step 5: Statistics
    print("📊 STEP 5: Summary Statistics")
    print("-" * 80)

    # Year distribution
    from collections import Counter
    years = Counter([book['published'][:4] for book in new_books if book.get('published')])

    print("  Year distribution of new books:")
    for year in sorted(years.keys(), reverse=True):
        print(f"    {year}: {years[year]} books")

    # Search method distribution
    methods = Counter([book['search_method'] for book in new_books])
    print(f"\n  Search method breakdown:")
    for method, count in methods.items():
        percentage = count / len(new_books) * 100
        print(f"    {method}: {count} books ({percentage:.1f}%)")

    # Top search queries
    queries = Counter([book['search_query'] for book in new_books])
    print(f"\n  Top 5 most productive queries:")
    for query, count in queries.most_common(5):
        print(f"    '{query}': {count} books")

    print()
    print("=" * 80)
    print("✅ DISCOVERY COMPLETE!")
    print("=" * 80)
    print(f"  Total new books added to Vector DB: {len(new_books)}")
    print(f"  Vector DB now contains: {new_count} total books")
    print(f"    - User read: {len(user_books)} books")
    print(f"    - Discovered: ~{new_count - len(user_books)} books")
    print()
    print("  Next steps:")
    print("    - Run recommendation tests with new books")
    print("    - Books are marked with source='discovered' in metadata")
    print("    - Recommendation system will exclude user_read books")
    print("=" * 80)


if __name__ == "__main__":
    main()
