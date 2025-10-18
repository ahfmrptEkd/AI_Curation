"""
Generate emotion tags for all books in Google Sheets.
Uses batch processing for efficiency.
"""

from src.data.sheets_client import SheetsClient
from src.agents.tag_generator import TagGenerator
from tqdm import tqdm
import time


def main():
    """Main function to generate tags for all books."""
    print("=" * 60)
    print("Book Tag Generation Script")
    print("=" * 60)
    print()

    # Initialize clients
    print("📚 Initializing...")
    try:
        sheets_client = SheetsClient()
        tag_generator = TagGenerator()
        print("✅ Clients initialized successfully\n")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        print("\nPlease check:")
        print("1. credentials.json exists")
        print("2. .env file is configured")
        print("3. OpenAI API key is valid")
        return

    # Load all books
    print("📖 Loading books from Google Sheets...")
    try:
        all_books = sheets_client.get_all_books()
        print(f"✅ Loaded {len(all_books)} books\n")
    except Exception as e:
        print(f"❌ Failed to load books: {e}")
        return

    if not all_books:
        print("⚠️  No books found in Google Sheets")
        return

    # Filter books without tags
    books_without_tags = [book for book in all_books if not book.has_tags()]
    books_with_tags = [book for book in all_books if book.has_tags()]

    print(f"📊 Summary:")
    print(f"   Total books: {len(all_books)}")
    print(f"   Already tagged: {len(books_with_tags)}")
    print(f"   Need tagging: {len(books_without_tags)}")
    print()

    if not books_without_tags:
        print("✅ All books already have tags!")
        return

    # Confirm before processing
    print(f"⚡ About to generate tags for {len(books_without_tags)} books")
    print(f"   Estimated time: ~{len(books_without_tags) * 0.5:.1f} seconds (batch processing)")
    print(f"   Estimated cost: ~${len(books_without_tags) * 0.01:.2f}")
    print()

    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    print()
    print("🤖 Generating tags using batch processing...")
    print("-" * 60)

    # Process in batches of 10 for better error handling
    batch_size = 10
    all_results = {}
    failed_books = []

    for i in range(0, len(books_without_tags), batch_size):
        batch = books_without_tags[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(books_without_tags) + batch_size - 1) // batch_size

        print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} books)")

        try:
            # Generate tags for batch
            results = tag_generator.generate_tags_batch(batch)
            all_results.update(results)

            # Update Google Sheets
            print("\n💾 Updating Google Sheets...")
            for book in batch:
                if book.title in results:
                    tags = results[book.title]
                    success = sheets_client.update_tags(book.title, tags)
                    if not success:
                        failed_books.append(book.title)

            # Brief pause between batches
            if i + batch_size < len(books_without_tags):
                time.sleep(1)

        except Exception as e:
            print(f"❌ Error processing batch {batch_num}: {e}")
            failed_books.extend([book.title for book in batch])

    # Final summary
    print()
    print("=" * 60)
    print("✅ Tag Generation Complete!")
    print("=" * 60)
    print(f"📊 Results:")
    print(f"   Successfully tagged: {len(all_results) - len(failed_books)}/{len(books_without_tags)}")

    if failed_books:
        print(f"   Failed: {len(failed_books)}")
        print("\n⚠️  Failed books:")
        for title in failed_books[:5]:  # Show first 5
            print(f"   - {title}")
        if len(failed_books) > 5:
            print(f"   ... and {len(failed_books) - 5} more")

    print()
    print("💡 Next steps:")
    print("   1. Check Google Sheets to verify tags")
    print("   2. Run: python scripts/02_build_vectordb.py")
    print()


if __name__ == "__main__":
    main()
