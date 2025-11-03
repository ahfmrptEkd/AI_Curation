"""
Test recommendation system with various queries.
Validates semantic search, filtering, explanations, and guardrails.
"""

from src.agents.recommender import BookRecommender


def print_separator(title: str):
    """Print a formatted separator."""
    print("\n" + "="*70)
    print(f"🔍 {title}")
    print("="*70)


def print_recommendations(result: dict):
    """Print recommendations in a formatted way."""
    recommendations = result.get("recommendations", [])
    explanation = result.get("explanation", "")

    if not recommendations:
        print(f"\n{explanation}")
        return

    print(f"\nFound {len(recommendations)} recommendations:\n")

    for i, rec in enumerate(recommendations, 1):
        meta = rec["metadata"]
        print(f"{i}. {meta['title']} by {meta['author']}")
        print(f"   Trope: {meta.get('trope', 'N/A')}")
        print(f"   Rating: {meta.get('rating', 'N/A')}⭐")
        print(f"   Tags: {meta.get('tags', 'N/A')}")
        print(f"   Similarity Score: {rec['score']:.3f}")
        print()

    print(f"Explanation:\n{explanation}\n")


def main():
    """Run comprehensive recommendation tests."""
    print("="*70)
    print("📚 Book Recommendation System Testing")
    print("="*70)

    recommender = BookRecommender()

    # Test 1: Dark Romance (clear query)
    print_separator("Test 1: Dark Romance")
    result = recommender.recommend(
        query="dark and intense romance with complex characters",
        n_results=3
    )
    print_recommendations(result)

    # Test 2: Sports Romance with filter
    print_separator("Test 2: Sports Romance with Trope Filter")
    result = recommender.recommend(
        query="athletic romance with competitive tension",
        filters={"trope": "Sports Romance"},
        n_results=3
    )
    print_recommendations(result)

    # Test 3: High-rated only
    print_separator("Test 3: High-Rated Books (≥ 4.0⭐)")
    result = recommender.recommend(
        query="heartwarming and emotional love story",
        filters={"rating": {"$gte": 4.0}},
        n_results=3
    )
    print_recommendations(result)

    # Test 4: Enemies to Lovers
    print_separator("Test 4: Enemies to Lovers Trope")
    result = recommender.recommend(
        query="enemies to lovers with witty banter",
        filters={"trope": "Enemies to Lovers"},
        n_results=3
    )
    print_recommendations(result)

    # Test 5: Swoony Romance (vague query)
    print_separator("Test 5: Swoony Romance (Vague Query)")
    result = recommender.recommend(
        query="swoony and romantic book",
        n_results=3
    )
    print_recommendations(result)

    # Test 6: Invalid query (non-Romance) - should be redirected
    print_separator("Test 6: Non-Romance Query (Guardrail Test)")
    result = recommender.recommend(
        query="science fiction space opera with aliens",
        n_results=3
    )
    print_recommendations(result)

    # Test 7: Fantasy Romance
    print_separator("Test 7: Fantasy Romance (Romantasy)")
    result = recommender.recommend(
        query="fantasy romance with magic and adventure",
        n_results=3
    )
    print_recommendations(result)

    # Test 8: Specific author style
    print_separator("Test 8: Similar to Rina Kent Style")
    result = recommender.recommend(
        query="dark romance similar to Rina Kent with morally gray characters",
        n_results=3
    )
    print_recommendations(result)

    print("="*70)
    print("✅ All recommendation tests complete!")
    print("="*70)


if __name__ == "__main__":
    main()
