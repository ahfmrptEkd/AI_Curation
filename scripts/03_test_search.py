"""
Test semantic search functionality with various queries and filters.
"""

from src.vectordb.chroma_manager import ChromaManager


def print_results(results, title):
    """Print search results in a formatted way."""
    print(f"\n{'='*70}")
    print(f"🔍 {title}")
    print(f"{'='*70}\n")

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, 1):
        meta = result['metadata']
        print(f"{i}. {meta['title']} by {meta['author']}")
        print(f"   Trope: {meta['trope']}")
        print(f"   Rating: {meta['rating']}⭐")
        print(f"   Tags: {meta['tags']}")
        print(f"   Similarity Score: {result['score']:.3f}")
        print()


def main():
    """Run comprehensive search tests."""
    print("\n" + "="*70)
    print("📚 Romance Book Search Testing")
    print("="*70)
    print()

    # Initialize ChromaDB
    print("🔌 Connecting to Vector Database...")
    chroma_manager = ChromaManager(collection_name="books")

    total_books = chroma_manager.count()
    print(f"✓ Connected! Total books in database: {total_books}")

    if total_books == 0:
        print("\n⚠️  Error: Vector database is empty!")
        print("Please run: python scripts/02_build_vectordb.py")
        return

    # Test 1: Basic Semantic Search
    print_results(
        chroma_manager.search("fun and exciting romance with humor", n_results=3),
        "Test 1: Fun and Exciting Romance"
    )

    # Test 2: Dark and Angsty
    print_results(
        chroma_manager.search("dark intense emotionally complex romance", n_results=3),
        "Test 2: Dark and Intense Romance"
    )

    # Test 3: Heartwarming and Emotional
    print_results(
        chroma_manager.search("heartwarming emotional love story", n_results=3),
        "Test 3: Heartwarming and Emotional"
    )

    # Test 4: Filtered by Trope
    print_results(
        chroma_manager.search(
            "romantic story",
            filters={"trope": "Dark Romance"},
            n_results=3
        ),
        "Test 4: Dark Romance Trope Only"
    )

    # Test 5: High-rated books
    print_results(
        chroma_manager.search(
            "best romance books",
            filters={"rating": {"$gte": 4.0}},
            n_results=3
        ),
        "Test 5: High-Rated Books (≥ 4.0⭐)"
    )

    # Test 6: Combined filters
    print_results(
        chroma_manager.search(
            "enemies to lovers",
            filters={
                "trope": "Enemies to Lovers",
                "rating": {"$gte": 3.5}
            },
            n_results=3
        ),
        "Test 6: Enemies to Lovers + High Rating"
    )

    # Test 7: Swoony Romance
    print_results(
        chroma_manager.search("swoony romantic sweet love story", n_results=3),
        "Test 7: Swoony Romance"
    )

    # Test 8: Sports Romance
    print_results(
        chroma_manager.search(
            "sports athletes",
            filters={"trope": "Sports Romance"},
            n_results=3
        ),
        "Test 8: Sports Romance"
    )

    print("="*70)
    print("✅ All tests complete!")
    print("="*70)
    print()


if __name__ == "__main__":
    main()
