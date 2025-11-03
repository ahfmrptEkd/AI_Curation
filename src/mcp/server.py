#!/usr/bin/env python3
"""
FastMCP Server for Book Recommendation System.

This server exposes two tools to Claude Desktop:
1. recommend_books - Get personalized Romance book recommendations
2. add_book_review - Add a new book review to the system

Usage:
    python src/mcp/server.py

Configuration in Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "book-curator": {
          "command": "python",
          "args": ["/absolute/path/to/AI_Curation/src/mcp/server.py"],
          "env": {
            "PYTHONPATH": "/absolute/path/to/AI_Curation"
          }
        }
      }
    }
"""

from fastmcp import FastMCP
from typing import Optional
import sys
import os

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.mcp.tools import MCPToolHandler

# Initialize FastMCP server
mcp = FastMCP("book-curator")

# Initialize tool handler (lazy initialization to avoid startup overhead)
_handler: Optional[MCPToolHandler] = None


def get_handler() -> MCPToolHandler:
    """Get or create MCPToolHandler instance (lazy initialization)."""
    global _handler
    if _handler is None:
        print("[MCP Server] Initializing MCPToolHandler...")
        _handler = MCPToolHandler()
        print("[MCP Server] MCPToolHandler ready!")
    return _handler


@mcp.tool()
def recommend_books(
    query: str,
    category: str | None = None,
    min_rating: float | None = None,
    count: int = 3
) -> dict:
    """
    Get personalized Romance book recommendations.

    Searches from 'discovered' books only (not your reading history).
    Uses AI to find books matching your query with semantic understanding.

    Args:
        query: Your query in natural language (e.g., "dark and intense romance", "enemies to lovers")
        category: Optional Romance subgenre filter. Examples:
            - "Dark Romance"
            - "Sports Romance"
            - "Contemporary Romance"
            - "Fantasy Romance" (Romantasy)
            - "Enemies to Lovers"
        min_rating: Optional minimum rating filter (1.0-5.0)
        count: Number of recommendations to return (default: 3, max: 10)

    Returns:
        Dictionary containing:
        - books: List of recommended books with details
        - explanation: AI-generated explanation for recommendations
        - total_results: Number of books found

    Examples:
        >>> recommend_books("dark romance with alpha male")
        >>> recommend_books("enemies to lovers", min_rating=4.0, count=5)
        >>> recommend_books("sports romance", category="Sports Romance")
    """
    handler = get_handler()
    return handler.handle_recommend(
        query=query,
        category=category,
        min_rating=min_rating,
        count=count
    )


@mcp.tool()
def add_book_review(
    title: str,
    author: str,
    rating: float,
    review: str,
    category: str
) -> dict:
    """
    Add a new book review to the system.

    Automatically generates emotion tags using AI and updates both
    Google Sheets (planned) and Vector Database.

    Args:
        title: Book title (e.g., "Icebreaker")
        author: Author name (e.g., "Hannah Grace")
        rating: Your rating from 1.0 to 5.0 (e.g., 4.5)
        review: Your review text in English or Korean
        category: Book category/trope. Examples:
            - "Contemporary Romance"
            - "Dark Romance"
            - "Sports Romance"
            - "Fantasy Romance"

    Returns:
        Dictionary containing:
        - title, author, rating: Confirmed book details
        - tags: AI-generated emotion tags
        - message: Success confirmation

    Examples:
        >>> add_book_review(
        ...     title="Icebreaker",
        ...     author="Hannah Grace",
        ...     rating=4.5,
        ...     review="Amazing sports romance with great chemistry!",
        ...     category="Sports Romance"
        ... )
    """
    handler = get_handler()
    return handler.handle_add_review(
        title=title,
        author=author,
        rating=rating,
        review=review,
        category=category
    )


if __name__ == "__main__":
    # Run the MCP server
    print("="*60)
    print("📚 Book Curator MCP Server")
    print("="*60)
    print("\nStarting server...")
    print("This server provides Romance book recommendations via MCP.\n")
    print("Available tools:")
    print("  1. recommend_books - Get personalized recommendations")
    print("  2. add_book_review - Add a new book review")
    print("\nServer is ready for connections from Claude Desktop.")
    print("="*60 + "\n")

    # Start the FastMCP server (stdio mode for Claude Desktop)
    mcp.run()
