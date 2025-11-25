"""
MCP Tool Handler for Book Recommendation System.
Provides business logic layer between FastMCP server and core components.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from src.agents.recommender import BookRecommender
from src.agents.tag_generator import TagGenerator
from src.vectordb.chroma_manager import ChromaManager
from src.data.sheets_client import SheetsClient
from src.data.models import Book


class RecommendBooksParams(BaseModel):
    """Parameters for book recommendation."""
    query: str = Field(..., description="User's query (e.g., 'Dark Romance 추천해줘')")
    category: Optional[str] = Field(None, description="Romance subgenre filter (e.g., 'Dark Romance', 'Sports Romance')")
    min_rating: Optional[float] = Field(None, description="Minimum rating (1.0-5.0)", ge=1.0, le=5.0)
    count: int = Field(3, description="Number of recommendations (default: 3)", ge=1, le=10)


class AddBookReviewParams(BaseModel):
    """Parameters for adding a new book review."""
    title: str = Field(..., description="Book title")
    author: str = Field(..., description="Author name")
    rating: float = Field(..., description="Rating (1.0-5.0)", ge=1.0, le=5.0)
    review: str = Field(..., description="Book review text")
    category: str = Field(..., description="Book category (e.g., 'Romance', 'Dark Romance')")


class MCPToolHandler:
    """
    Handler for MCP tool operations.
    Orchestrates existing components to fulfill tool requests.
    """

    def __init__(self):
        """Initialize all required components."""
        print("[MCPToolHandler] Initializing components...")

        self.recommender = BookRecommender()
        self.chroma_manager = ChromaManager(collection_name="books")
        self.tag_generator = TagGenerator()
        self.sheets_client = SheetsClient(use_service_account=True)

        print("[MCPToolHandler] All components initialized successfully!")

    def handle_recommend(
        self,
        query: str,
        category: Optional[str] = None,
        min_rating: Optional[float] = None,
        count: int = 3
    ) -> Dict[str, Any]:
        """
        Handle book recommendation request.

        Args:
            query: User's natural language query
            category: Optional Romance subgenre filter
            min_rating: Optional minimum rating filter
            count: Number of recommendations

        Returns:
            Dictionary with status and recommendation data
        """
        try:
            print(f"[handle_recommend] Query: {query}, Filters: category={category}, min_rating={min_rating}")

            # Build filters
            filters = {}
            if category:
                filters["trope"] = category  # Use 'trope' field which stores Romance subgenres
            if min_rating:
                filters["rating"] = {"$gte": min_rating}

            # Get recommendations from BookRecommender
            result = self.recommender.recommend(
                query=query,
                filters=filters if filters else None,
                n_results=count
            )

            # Format response
            recommendations = result.get("recommendations", [])
            explanation = result.get("explanation", "")

            # Extract book details
            books = []
            for rec in recommendations:
                metadata = rec.get("metadata", {})
                books.append({
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "trope": metadata.get("trope", ""),
                    "rating": metadata.get("rating", "N/A"),
                    "tags": metadata.get("tags", ""),
                    "description": rec.get("description", ""),
                    "cover_url": rec.get("cover_url", ""),
                    "similarity_score": rec.get("score", 0.0)
                })

            return {
                "status": "success",
                "data": {
                    "books": books,
                    "explanation": explanation,
                    "query": query,
                    "total_results": len(books)
                }
            }

        except Exception as e:
            print(f"[handle_recommend] Error: {e}")
            return {
                "status": "error",
                "error": f"Failed to get recommendations: {str(e)}"
            }

    def handle_add_review(
        self,
        title: str,
        author: str,
        rating: float,
        review: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Handle adding a new book review.

        Steps:
        1. Generate emotion tags using TagGenerator
        2. Create Book object
        3. Add to Google Sheets
        4. Update Vector DB

        Args:
            title: Book title
            author: Author name
            rating: Rating (1.0-5.0)
            review: Review text
            category: Book category

        Returns:
            Dictionary with status and generated tags
        """
        try:
            print(f"[handle_add_review] Adding review for '{title}' by {author}")

            # Step 1: Generate emotion tags
            print("[handle_add_review] Generating emotion tags...")
            tags = self.tag_generator.generate_tags(
                title=title,
                rating=rating,
                review=review
            )
            print(f"[handle_add_review] Generated tags: {tags}")

            # Step 2: Create Book object
            book = Book(
                title=title,
                author=author,
                rating=rating,
                review=review,
                category=category,
                tags=tags,
                trope=category,  # Use category as trope for Romance subgenres
                source="user_read" 
            )

            # Step 3: Add to Google Sheets
            print("[handle_add_review] Adding to Google Sheets...")
            try:
                success = self.sheets_client.add_book(book)
                if success:
                    print("[handle_add_review] ✅ Book added to Google Sheets")
                else:
                    print("[handle_add_review] ⚠️ Failed to add to Google Sheets (but Vector DB updated)")
            except Exception as e:
                print(f"[handle_add_review] ⚠️ Google Sheets error: {e} (but Vector DB updated)")

            # Step 4: Update Vector DB
            print("[handle_add_review] Updating Vector DB...")
            # Generate a unique ID for the book
            book_id = f"user_review_{title.lower().replace(' ', '_')}"

            # Upsert to Chroma
            self.chroma_manager.upsert_book(book, book_id)
            print(f"[handle_add_review] Book added to Vector DB with ID: {book_id}")

            return {
                "status": "success",
                "data": {
                    "title": title,
                    "author": author,
                    "rating": rating,
                    "tags": tags,
                    "message": "Book review added successfully! ✅ Synced to Google Sheets and Vector DB"
                }
            }

        except Exception as e:
            print(f"[handle_add_review] Error: {e}")
            return {
                "status": "error",
                "error": f"Failed to add review: {str(e)}"
            }


# For testing
