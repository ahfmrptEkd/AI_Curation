"""
Build vector database from Google Sheets books.
Embeds all books and stores them in ChromaDB for semantic search.
"""

from src.data.sheets_client import SheetsClient
from src.vectordb.chroma_manager import ChromaManager


def main():
    """Build vector database from Google Sheets books."""
    print("="*70)
    print("📚 Building Vector Database from Google Sheets")
    print("="*70)
    print()

    # Initialize clients
    print("🔌 Connecting to Google Sheets...")
    sheets_client = SheetsClient()

    print("🔌 Initializing ChromaDB...")
    chroma_manager = ChromaManager(collection_name="books")

    # Check if collection already exists and has data
    existing_count = chroma_manager.count()
    if existing_count > 0:
        print(f"\n⚠️  Warning: Collection already has {existing_count} books")
        response = input("Do you want to rebuild? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

        # Clear collection
        print("🗑️  Clearing existing collection...")
        chroma_manager.client.delete_collection("books")
        chroma_manager = ChromaManager(collection_name="books")
        print("✓ Collection cleared")

    print()

    # Load books from Google Sheets
    print("📖 Loading books from Google Sheets...")
    books = sheets_client.get_all_books()
    print(f"✓ Loaded {len(books)} books")
    print()

    # Filter books with reviews (we need some content to embed)
    books_with_content = [
        book for book in books
        if book.review or book.description
    ]

    print(f"📊 Books with content (review or description): {len(books_with_content)}")

    if len(books_with_content) < len(books):
        skipped = len(books) - len(books_with_content)
        print(f"⚠️  Skipping {skipped} books without review or description")

    print()

    # Add books to vector database
    print("🔄 Adding books to vector database...")
    print("(This may take a few minutes...)")
    print()

    added_count = chroma_manager.add_books(books_with_content, batch_size=20)

    print()
    print("="*70)
    print("✅ Vector Database Build Complete!")
    print("="*70)
    print()
    print(f"📊 Statistics:")
    print(f"   Total books loaded from Sheets: {len(books)}")
    print(f"   Books added to vector DB: {added_count}")
    print(f"   Books in collection: {chroma_manager.count()}")
    print()
    print(f"💾 Database location: {chroma_manager.client.get_settings().persist_directory}")
    print()

    # Show sample search
    print("="*70)
    print("🔍 Testing Semantic Search...")
    print("="*70)
    print()

    test_query = "dark and intense romance"
    print(f"Query: '{test_query}'")
    print()

    results = chroma_manager.search(test_query, n_results=3)

    for i, result in enumerate(results, 1):
        meta = result['metadata']
        print(f"{i}. {meta['title']} by {meta['author']}")
        print(f"   Trope: {meta['trope']}")
        print(f"   Rating: {meta['rating']}⭐")
        print(f"   Tags: {meta['tags']}")
        print(f"   Similarity Score: {result['score']:.3f}")
        print()

    print("✅ Build complete! You can now run:")
    print("   python scripts/03_test_search.py")
    print()


if __name__ == "__main__":
    main()
