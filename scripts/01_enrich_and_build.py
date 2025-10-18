"""
Enrich books with descriptions and tags, then rebuild vector database.

Workflow:
1. Load books from Google Sheets (user's read books with reviews)
2. Fetch descriptions from Google Books API for ALL books
3. Generate emotion tags (using description if available, fallback to review)
4. Rebuild vector database with enriched data

Note:
- Descriptions and Tags are NOT saved to Google Sheets (memory only)
- They are only stored in Vector DB for recommendation purposes
- Google Sheets remains as user's personal reading log (reviews & ratings)
"""

from src.data.sheets_client import SheetsClient
from src.data.external_api import BookMetadataFetcher
from src.agents.tag_generator import TagGenerator
from src.vectordb.chroma_manager import ChromaManager
from tqdm import tqdm
import time


def main():
    """Main enrichment and rebuild pipeline."""
    print("="*70)
    print("📚 Book Enrichment & Vector DB Rebuild Pipeline")
    print("="*70)
    print()

    # Initialize clients
    print("🔌 Initializing clients...")
    sheets_client = SheetsClient()
    api_client = BookMetadataFetcher()
    tag_generator = TagGenerator()
    chroma_manager = ChromaManager(collection_name="books")
    print("✅ All clients initialized\n")

    # Load books
    print("📖 Loading books from Google Sheets...")
    books = sheets_client.get_all_books()
    print(f"✓ Loaded {len(books)} books\n")

    print("📊 Current Status:")
    print(f"   Total books: {len(books)}")
    print(f"   Books with review: {len([b for b in books if b.review])}")
    print(f"   Books with description: {len([b for b in books if b.description])}")
    print()

    # Step 1: Fetch descriptions for ALL books from Google Books API
    print("="*70)
    print("STEP 1: Fetching Descriptions from Google Books API")
    print("="*70)
    print(f"\nFetching descriptions for ALL {len(books)} books")
    print(f"This enriches the Vector DB for better recommendations")
    print(f"Estimated time: ~{len(books) * 0.5:.0f} seconds (~{len(books) * 0.5 / 60:.1f} minutes)\n")

    response = input("Fetch descriptions? (y/n): ")
    if response.lower() == 'y':
        success = 0
        failed = 0

        print("\n🔄 Fetching from Google Books API...")
        for book in tqdm(books, desc="API calls"):
            try:
                metadata = api_client.fetch_google_books(book.title, book.author)
                if metadata and metadata.get('description'):
                    book.description = metadata['description']
                    success += 1
                else:
                    failed += 1
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                failed += 1
                time.sleep(1)

        print(f"\n✓ Fetched: {success}, Failed: {failed}")
        print("📝 Note: Descriptions stored in memory only (not in Google Sheets)")
        print("   They will be saved to Vector DB in Step 3\n")
    else:
        print("Skipped - will use reviews only for tags\n")

    # Step 2: Generate tags
    print("="*70)
    print("STEP 2: Generating Emotion Tags")
    print("="*70)

    books_with_tags = [b for b in books if b.has_tags()]
    books_need_tags = [b for b in books if not b.has_tags()]

    print(f"\n   Already tagged: {len(books_with_tags)}")
    print(f"   Need tagging: {len(books_need_tags)}")

    if books_need_tags:
        print(f"\n   Strategy:")
        books_use_desc = [b for b in books_need_tags if b.description]
        books_use_review = [b for b in books_need_tags if not b.description and b.review]
        print(f"   - {len(books_use_desc)} will use description")
        print(f"   - {len(books_use_review)} will use review")
        print(f"\n   Estimated cost: ~${len(books_need_tags) * 0.01:.2f}")
        print()

        response = input("Generate tags? (y/n): ")
        if response.lower() != 'y':
            print("Skipped - using existing tags only")
        else:
            print("\n🤖 Generating tags (batch processing)...")
            batch_size = 10
            all_tags = {}

            for i in range(0, len(books_need_tags), batch_size):
                batch = books_need_tags[i:i+batch_size]
                try:
                    results = tag_generator.generate_tags_batch(batch)
                    all_tags.update(results)

                    # Apply tags to book objects
                    for book in batch:
                        if book.title in results:
                            book.tags = results[book.title]

                    time.sleep(1)
                except Exception as e:
                    print(f"\n⚠️  Error in batch: {e}")

            print(f"\n✓ Generated tags for {len(all_tags)} books")
            print("📝 Note: Tags stored in memory only (not in Google Sheets)")
            print("   They will be saved to Vector DB in Step 3\n")

    else:
        print("✅ All books already have tags\n")

    # Step 3: Rebuild Vector DB
    print("="*70)
    print("STEP 3: Rebuilding Vector Database")
    print("="*70)

    # Count books with content
    books_with_content = [b for b in books if (b.review and b.review.strip()) or (b.description and b.description.strip())]
    print(f"\n{len(books_with_content)} books have content (review or description)")
    print(f"All {len(books_with_content)} will be added to Vector DB\n")

    response = input("Rebuild Vector DB? (y/n): ")
    if response.lower() != 'y':
        print("Skipped")
        return

    # Clear and rebuild
    print("\n🗑️  Clearing existing collection...")
    try:
        chroma_manager.collection.delete()
        chroma_manager = ChromaManager(collection_name="books")
    except:
        pass

    print(f"🔄 Adding {len(books_with_content)} books to Vector DB...")
    print("   (This will take a few minutes...)\n")

    # Add in batches
    batch_size = 20
    for i in range(0, len(books_with_content), batch_size):
        batch = books_with_content[i:i+batch_size]
        try:
            chroma_manager.add_books(batch)
            print(f"✓ Added batch {i//batch_size + 1}: {len(batch)} books (Total: {i+len(batch)})")
        except Exception as e:
            print(f"⚠️  Error in batch {i//batch_size + 1}: {e}")

    # Final summary
    final_count = chroma_manager.count()
    print("\n" + "="*70)
    print("✅ Pipeline Complete!")
    print("="*70)
    print(f"\n📊 Final Status:")
    print(f"   Books in Vector DB: {final_count}")
    print(f"   Books with descriptions: {len([b for b in books if b.description])}")
    print(f"   Books with tags: {len([b for b in books if b.has_tags()])}")
    print()


if __name__ == "__main__":
    main()
