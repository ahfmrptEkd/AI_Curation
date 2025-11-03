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

import sys
import os
import time
from fastmcp import FastMCP
from typing import Optional
from src.data.external_api import BookMetadataFetcher
from src.data.sheets_client import SheetsClient
from src.vectordb.chroma_manager import ChromaManager
from src.data.models import Book
from pathlib import Path
from datetime import datetime

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
def setup_google_sheets(
    worksheet_name: str = "2025",
    include_sample_data: bool = True
) -> dict:
    """
    Setup Google Sheets with proper structure for book tracking.

    Creates a new worksheet with all required headers and optional sample data.
    Use this for NEW users who have a blank Google Sheets or need to add a new year.

    Args:
        worksheet_name: Name for the worksheet (default: "2025")
        include_sample_data: Add 2 sample book entries to show format (default: True)

    Returns:
        Dictionary containing:
        - success: Whether setup was successful
        - worksheet_name: Name of created/updated worksheet
        - spreadsheet_url: Link to the Google Sheets
        - message: Status message

    Headers created:
        - Title, Author, Rating, Date, Review, Category, Tags, Trope, ISBN, Notes

    Note:
        - Requires Google Sheets to be shared with service account
        - Creates worksheet if it doesn't exist
        - Won't overwrite existing data if worksheet has headers
        - Sample data helps understand the expected format

    Examples:
        >>> setup_google_sheets()  # Create 2025 worksheet with samples
        >>> setup_google_sheets("2024", include_sample_data=False)  # Just headers
    """
    try:
        print(f"[setup_google_sheets] Setting up worksheet '{worksheet_name}'...")

        sheets_client = SheetsClient()

        # Get spreadsheet info
        info = sheets_client.get_spreadsheet_info()

        # Setup worksheet
        success = sheets_client.setup_worksheet(
            worksheet_name=worksheet_name,
            include_sample_data=include_sample_data
        )

        if success:
            sample_msg = " with 2 sample entries" if include_sample_data else ""
            return {
                "success": True,
                "worksheet_name": worksheet_name,
                "spreadsheet_title": info.get("title", ""),
                "spreadsheet_url": info.get("url", ""),
                "message": f"✅ Worksheet '{worksheet_name}' setup complete{sample_msg}!",
                "next_steps": [
                    "Add your books manually to the worksheet, or",
                    "Use add_book_review() tool to add books via Claude Desktop",
                    "Once you have 10+ books, run scripts/01_enrich_and_build.py to build Vector DB"
                ]
            }
        else:
            return {
                "success": False,
                "worksheet_name": worksheet_name,
                "message": f"⚠️  Worksheet '{worksheet_name}' already exists with data",
                "suggestion": "Use a different worksheet name or check existing data"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to setup Google Sheets",
            "troubleshooting": [
                "Ensure Google Sheets is shared with service account email",
                "Check GOOGLE_SHEETS_ID in environment variables",
                "Verify credentials.json is valid"
            ]
        }


@mcp.tool()
def check_system_status() -> dict:
    """
    Check the current status of the book recommendation system.

    Returns comprehensive system information including:
    - Vector DB status (exists, total books, by source)
    - Last update time
    - Recommendation readiness
    - Suggested actions

    Returns:
        Dictionary containing:
        - initialized: Whether system is set up
        - total_books: Total count in Vector DB
        - user_read_books: Books from reading history
        - discovered_books: Books available for recommendations
        - ready_for_recommendations: Boolean indicating readiness
        - last_discovery_run: Time of last discovery (if available)
        - suggestions: List of recommended next steps

    Use this to:
    - Check if system needs initialization
    - See when to run book discovery again
    - Verify recommendation pool is fresh
    """
    status = {
        "initialized": False,
        "vector_db_exists": False,
        "total_books": 0,
        "user_read_books": 0,
        "discovered_books": 0,
        "ready_for_recommendations": False,
        "suggestions": []
    }

    try:
        # Check if Vector DB exists
        db_path = Path("data/chroma_db")
        status["vector_db_exists"] = db_path.exists()

        if not status["vector_db_exists"]:
            status["suggestions"] = [
                "System not initialized",
                "Run initial setup: python scripts/01_enrich_and_build.py",
                "Then discover books: python scripts/04_discover_new_books.py"
            ]
            return status

        # Get Vector DB stats
        chroma = ChromaManager(collection_name="books")
        status["total_books"] = chroma.count()

        if status["total_books"] == 0:
            status["suggestions"] = [
                "Vector DB is empty",
                "Run: python scripts/01_enrich_and_build.py"
            ]
            return status

        # Count by source
        all_books = chroma.collection.get(include=['metadatas'])
        sources = {}
        for meta in all_books['metadatas']:
            source = meta.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1

        status["user_read_books"] = sources.get('user_read', 0) + sources.get('unknown', 0)
        status["discovered_books"] = sources.get('discovered', 0)
        status["initialized"] = True

        # Check readiness
        if status["discovered_books"] == 0:
            status["ready_for_recommendations"] = False
            status["suggestions"] = [
                f"System has {status['user_read_books']} books from reading history",
                "But no discovered books for recommendations yet",
                "Run: discover_new_books() tool to add ~100 new books",
                "Or run: python scripts/04_discover_new_books.py"
            ]
        elif status["discovered_books"] < 50:
            status["ready_for_recommendations"] = True
            status["suggestions"] = [
                f"System ready with {status['discovered_books']} discovered books",
                "Recommendation pool is small - consider running discover_new_books() for more variety"
            ]
        else:
            status["ready_for_recommendations"] = True
            status["suggestions"] = [
                f"System ready! {status['total_books']} total books ({status['discovered_books']} for recommendations)",
                "Run discover_new_books() monthly to keep recommendations fresh"
            ]

        # Check DB modification time for last update estimate
        if db_path.exists():
            db_file = db_path / "chroma.sqlite3"
            if db_file.exists():
                mtime = os.path.getmtime(db_file)
                last_modified = datetime.fromtimestamp(mtime)
                status["last_db_update"] = last_modified.strftime("%Y-%m-%d %H:%M:%S")

        return status

    except Exception as e:
        status["error"] = str(e)
        status["suggestions"] = ["Error checking system status", "System may need reinitialization"]
        return status


@mcp.tool()
def discover_new_books(
    max_books: int = 100,
    include_authors: bool = True,
    include_keywords: bool = False
) -> dict:
    """
    Discover new Romance books and add them to the recommendation pool.

    This tool searches for newly published Romance books from Google Books API
    and adds them to the Vector Database. Run this periodically (monthly) to
    keep recommendations fresh with the latest releases.

    Args:
        max_books: Maximum number of new books to discover (default: 100, max: 200)
        include_authors: Search by popular Romance authors (recommended: True)
        include_keywords: Search by Romance keywords/tropes (optional: False)

    Returns:
        Dictionary containing:
        - books_discovered: Number of new books found
        - books_added: Number of books added to Vector DB
        - books_skipped: Number of duplicates skipped
        - sample_books: List of 5 sample titles added
        - execution_time: Time taken in seconds

    Note:
        - Only adds books not in your reading history
        - Books are marked with source='discovered'
        - Typically takes 3-7 minutes to complete
        - API rate limited (safe to run)

    Examples:
        >>> discover_new_books(max_books=50)  # Quick refresh
        >>> discover_new_books(max_books=200, include_keywords=True)  # Full update
    """

    start_time = time.time()

    results = {
        "status": "in_progress",
        "books_discovered": 0,
        "books_added": 0,
        "books_skipped": 0,
        "sample_books": [],
        "execution_time": 0
    }

    try:
        print(f"[discover_new_books] Starting discovery (max: {max_books})...")

        # Step 1: Get existing books to avoid duplicates
        print("[1/4] Loading existing books from Google Sheets...")
        sheets_client = SheetsClient()
        existing_books = sheets_client.get_all_books()
        existing_titles = {
            (b.title.lower().strip(), b.author.lower().strip())
            for b in existing_books
        }
        print(f"  Found {len(existing_books)} existing books to exclude")

        # Step 2: Get already discovered books from Vector DB
        print("[2/4] Checking Vector DB for discovered books...")
        chroma_manager = ChromaManager(collection_name="books")
        all_db_books = chroma_manager.collection.get(include=['metadatas'])
        for meta in all_db_books['metadatas']:
            if meta.get('source') == 'discovered':
                title = meta.get('title', '').lower().strip()
                author = meta.get('author', '').lower().strip()
                if title and author:
                    existing_titles.add((title, author))
        print(f"  Total books to exclude: {len(existing_titles)}")

        # Step 3: Discover new books from Google Books API
        print("[3/4] Discovering new books from Google Books API...")
        api_client = BookMetadataFetcher()
        discovered_books = []

        # Author-based search (most reliable)
        if include_authors:
            popular_authors = [
                "Emily Henry", "Colleen Hoover", "Ali Hazelwood",
                "Lucy Score", "Tessa Bailey", "L.J. Shen",
                "Hannah Grace", "Elle Kennedy", "Penelope Douglas"
            ]

            for author in popular_authors[:5]:  # Limit to 5 authors for speed
                books = api_client.search_romance_books(
                    query=f'inauthor:"{author}"',
                    max_results=min(max_books // 5, 20)
                )
                for book_data in books:
                    title = book_data.get('title', '').strip()
                    author_name = book_data.get('author', '').strip()

                    # Check duplicate
                    key = (title.lower(), author_name.lower())
                    if key in existing_titles:
                        results["books_skipped"] += 1
                        continue

                    # Create Book object
                    book = Book(
                        title=title,
                        author=author_name,
                        rating=0.0,  # No rating yet
                        review="",  # No review yet
                        category=book_data.get('category', 'Romance'),
                        trope="",
                        source="discovered",
                        description=book_data.get('description', '')
                    )
                    discovered_books.append(book)
                    existing_titles.add(key)

                    if len(discovered_books) >= max_books:
                        break

                if len(discovered_books) >= max_books:
                    break

                time.sleep(0.5)  # Rate limiting

        results["books_discovered"] = len(discovered_books)
        print(f"  Discovered {len(discovered_books)} new books")

        # Step 4: Add to Vector DB
        if discovered_books:
            print(f"[4/4] Adding {len(discovered_books)} books to Vector DB...")

            # Get current count for proper ID generation
            current_count = chroma_manager.count()

            added = chroma_manager.add_books(
                discovered_books,
                batch_size=20,
                start_id=current_count
            )
            results["books_added"] = added

            # Sample books for display
            results["sample_books"] = [
                f"{b.title} by {b.author}"
                for b in discovered_books[:5]
            ]
        else:
            print("[4/4] No new books to add")

        results["status"] = "success"
        results["execution_time"] = round(time.time() - start_time, 2)

        return results

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        results["execution_time"] = round(time.time() - start_time, 2)
        return results


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
