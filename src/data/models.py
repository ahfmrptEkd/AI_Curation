"""
Data models for the book recommendation system.
Uses Pydantic for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any


class Book(BaseModel):
    """Book model with review and metadata."""

    title: str = Field(..., description="Book title")
    author: str = Field(..., description="Book author")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1 to 5")
    review: str = Field(..., description="User review text")
    trope: str = Field(default="", description="Romance subgenre/trope (e.g., Friends to Lovers)")

    # Default category (all books are Romance for first user)
    category: str = Field(default="Romance", description="Book category/genre")

    # Source tracking for recommendation filtering
    source: str = Field(
        default="user_read",
        description="Book source: 'user_read' (from reading history) or 'discovered' (from API discovery)"
    )

    # AI-generated and API fields
    tags: Optional[List[str]] = Field(default=None, description="Emotion tags (AI-generated)")
    description: Optional[str] = Field(default=None, description="Book description from Google Books API")
    cover_url: Optional[str] = Field(default=None, description="Cover image URL from Google Books API")
    isbn: Optional[str] = Field(default=None, description="ISBN number")

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        """Parse tags from string or list."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            # Handle comma-separated tags
            tags = [tag.strip() for tag in v.split(',') if tag.strip()]
            return tags if tags else None
        return v

    @field_validator('rating', mode='before')
    @classmethod
    def parse_rating(cls, v):
        """Convert string rating to float."""
        if isinstance(v, str):
            return float(v)
        return v

    def get_tags_string(self) -> str:
        """Get tags as comma-separated string."""
        if self.tags:
            return ",".join(self.tags)
        return ""

    def has_tags(self) -> bool:
        """Check if book has tags."""
        return self.tags is not None and len(self.tags) > 0

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Too Much",
                "author": "I.A. Dice",
                "rating": 3.0,
                "review": "Unhinged. Oh my freaking god unhinged. Literally, things just kept happening...",
                "trope": "Friends to Lovers",
                "category": "Romance",
                "tags": ["#suspense", "#comedy"],
                "description": "A fresh start in Newport Beach leads to an unexpected romance..."
            }
        }


class RecommendationRequest(BaseModel):
    """Request model for book recommendations."""

    query: str = Field(..., description="User's recommendation query")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters (category, min_rating, tags)"
    )
    count: int = Field(default=3, ge=1, le=10, description="Number of recommendations")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "힐링되는 소설 추천해줘",
                "filters": {
                    "category": "소설",
                    "min_rating": 4.0
                },
                "count": 3
            }
        }


class RecommendationResponse(BaseModel):
    """Response model for book recommendations."""

    books: List[Dict] = Field(..., description="List of recommended books with metadata")
    explanation: str = Field(..., description="Explanation for recommendations")
    query: str = Field(..., description="Original query")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "힐링되는 소설 추천해줘",
                "books": [
                    {
                        "title": "달러구트 꿈 백화점",
                        "author": "이미예",
                        "rating": 4.5,
                        "tags": ["#힐링되는", "#따뜻한"],
                        "score": 0.89
                    }
                ],
                "explanation": "이 책은 따뜻하고 힐링되는 내용으로..."
            }
        }


if __name__ == "__main__":
    # Test data models
    print("=== Testing Book Model ===")

    # Test 1: Create book from dict
    book_data = {
        "title": "달러구트 꿈 백화점",
        "author": "이미예",
        "rating": "4.5",  # String rating
        "review": "따뜻하고 힐링되는 내용이었다.",
        "category": "소설",
        "tags": "#힐링되는,#따뜻한"  # Comma-separated string
    }
    book = Book(**book_data)
    print(f"Title: {book.title}")
    print(f"Rating: {book.rating} (type: {type(book.rating)})")
    print(f"Tags: {book.tags}")
    print(f"Has tags: {book.has_tags()}")
    print(f"Tags string: {book.get_tags_string()}")

    # Test 2: Create book without tags
    book_no_tags = Book(
        title="Test Book",
        author="Test Author",
        rating=4.0,
        review="Good book",
        category="Fiction",
        tags=None
    )
    print(f"\nBook without tags - Has tags: {book_no_tags.has_tags()}")

    # Test 3: Recommendation request
    print("\n=== Testing RecommendationRequest Model ===")
    req = RecommendationRequest(
        query="힐링되는 소설 추천해줘",
        filters={"category": "소설", "min_rating": 4.0},
        count=3
    )
    print(f"Query: {req.query}")
    print(f"Filters: {req.filters}")
    print(f"Count: {req.count}")

    print("\n✅ All models working correctly!")
