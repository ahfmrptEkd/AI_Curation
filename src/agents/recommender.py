"""
Book Recommender Agent using LangGraph.
Provides personalized Romance book recommendations with content-based explanations.
"""

from typing import List, Dict, Optional, Any, TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from src.config import settings
from src.vectordb.chroma_manager import ChromaManager
from src.data.external_api import BookMetadataFetcher
from src.data.models import Book


class RecommenderState(TypedDict):
    """State for the recommendation agent."""
    messages: Annotated[list, add_messages]
    query: str
    filters: Optional[Dict[str, Any]]
    n_results: int
    candidates: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    explanation: str


class BookRecommender:
    """
    LangGraph-based book recommendation agent.

    Features:
    - Similarity-based search (no rating re-ranking to avoid recommending read books)
    - Content-based explanations using book descriptions
    - Romance-only guardrails via system prompts
    - External metadata enrichment (Google Books API)
    """

    def __init__(self):
        """Initialize the recommendation agent."""
        self.llm = ChatOpenAI(
            model=settings.recommendation_model,
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        self.chroma_manager = ChromaManager(collection_name="books")
        self.metadata_fetcher = BookMetadataFetcher()

        # Build the LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for recommendations."""
        workflow = StateGraph(RecommenderState)

        # Add nodes
        workflow.add_node("validate_query", self._validate_query)
        workflow.add_node("search_candidates", self._search_candidates)
        workflow.add_node("enrich_metadata", self._enrich_metadata)
        workflow.add_node("generate_explanation", self._generate_explanation)

        # Define edges
        workflow.set_entry_point("validate_query")
        workflow.add_edge("validate_query", "search_candidates")
        workflow.add_edge("search_candidates", "enrich_metadata")
        workflow.add_edge("enrich_metadata", "generate_explanation")
        workflow.add_edge("generate_explanation", END)

        return workflow.compile()

    def _validate_query(self, state: RecommenderState) -> RecommenderState:
        """
        Validate and enhance user query with Romance-only guardrails.
        Uses LLM to ensure query is appropriate for Romance genre.
        """
        query = state["query"]

        # System prompt with Romance-only guardrail
        system_prompt = """You are a Romance book recommendation assistant.

IMPORTANT GUARDRAILS:
- You ONLY recommend Romance books (all subgenres: Contemporary, Dark, Sports, Fantasy Romance, etc.)
- If user asks for non-Romance books, politely redirect them to Romance genre
- If query is unclear, assume they want Romance books

Your task: Validate if the query is appropriate for Romance recommendations.
If yes, enhance the query for better semantic search.
If no, explain you only handle Romance books.

Output format:
VALID|<enhanced query for search>
OR
INVALID|<polite explanation about Romance-only focus>

Examples:
Input: "dark and intense love story"
Output: VALID|dark intense romance with complex relationships and emotional depth

Input: "science fiction books"
Output: INVALID|I specialize in Romance book recommendations. Would you like me to suggest Science Fiction Romance or Romantasy books instead?

Input: "swoony sports romance"
Output: VALID|swoony sports romance with athletic heroes and romantic tension
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User query: {query}")
        ]

        response = self.llm.invoke(messages)
        result = response.content.strip()

        if result.startswith("INVALID"):
            # Store explanation in state
            explanation = result.split("|", 1)[1] if "|" in result else result
            state["explanation"] = explanation
            state["recommendations"] = []
            # Skip other nodes by setting empty candidates
            state["candidates"] = []
        else:
            # Extract enhanced query
            enhanced_query = result.split("|", 1)[1] if "|" in result else query
            state["query"] = enhanced_query

        return state

    def _search_candidates(self, state: RecommenderState) -> RecommenderState:
        """
        Search for candidate books using semantic similarity.
        IMPORTANT: Uses similarity-only (no rating re-ranking) to avoid recommending already-read books.
        And Only searches 'discovered' books (not user's reading history).
        """
        # Skip if query was marked invalid (candidates would be explicitly set to None or have explanation)
        if state.get("explanation") and not state.get("recommendations"):
            return state

        query = state["query"]
        filters = state.get("filters") or {}
        n_results = state.get("n_results", 5)
        filters["source"] = "discovered"

        # Search with more candidates than needed for better filtering
        search_results = self.chroma_manager.search(
            query=query,
            filters=filters,
            n_results=n_results * 2  # Get 2x candidates
        )

        # Re-rank by similarity score only (NOT by rating)
        # This prevents recommending only already-read high-rated books
        ranked_results = sorted(
            search_results,
            key=lambda x: x['score'],
            reverse=True
        )[:n_results]

        state["candidates"] = ranked_results
        return state

    def _enrich_metadata(self, state: RecommenderState) -> RecommenderState:
        """
        Enrich candidate books with external metadata (descriptions, covers).
        This provides content for explanations since we can't use user reviews for unread books.
        """
        candidates = state["candidates"]

        if not candidates:  # Skip if no candidates
            return state

        enriched = []
        for candidate in candidates:
            metadata = candidate["metadata"]
            title = metadata.get("title", "")
            author = metadata.get("author", "")

            # Try to fetch external metadata
            external_data = self.metadata_fetcher.fetch_google_books(title, author)

            if external_data:
                # Add description and other metadata
                candidate["description"] = external_data.get("description", "")
                candidate["cover_url"] = external_data.get("thumbnail", "")
                candidate["categories"] = external_data.get("categories", [])
            else:
                # Use existing description if available
                candidate["description"] = metadata.get("description", "")
                candidate["cover_url"] = ""
                candidate["categories"] = []

            enriched.append(candidate)

        state["recommendations"] = enriched
        return state

    def _generate_explanation(self, state: RecommenderState) -> RecommenderState:
        """
        Generate content-based explanations for recommendations.
        IMPORTANT: Uses book descriptions/content, NOT user reviews (since books are unread).
        """
        if not state["recommendations"]:  # Skip if no recommendations
            return state

        query = state["query"]
        recommendations = state["recommendations"]

        # Format candidate books for LLM
        formatted_books = []
        for i, rec in enumerate(recommendations, 1):
            metadata = rec["metadata"]
            description = rec.get("description") or "No description available"

            # Safely truncate description
            desc_preview = description[:300] if len(description) > 300 else description

            book_info = f"""
Book {i}: {metadata.get('title')} by {metadata.get('author')}
Trope: {metadata.get('trope', 'N/A')}
Rating: {metadata.get('rating', 'N/A')}⭐
Tags: {metadata.get('tags', 'N/A')}
Similarity Score: {rec['score']:.3f}
Description: {desc_preview}
"""
            formatted_books.append(book_info.strip())

        # System prompt for content-based explanations
        system_prompt = """You are a Romance book curator providing personalized recommendations.

IMPORTANT GUIDELINES:
- Base explanations on book CONTENT and DESCRIPTIONS (not user reviews - these are unread books!)
- Explain why each book matches the user's request
- Highlight the trope, emotional appeal, and unique aspects
- Use warm, enthusiastic tone
- Be specific about what makes each book special

Format:
Brief intro explaining why these books match the request, then list each book with:
- Title and Author
- Why it's recommended (based on content/trope/description)
- What emotional experience to expect
"""

        books_text = "\n\n".join(formatted_books)

        user_prompt = f"""User is looking for: "{query}"

Here are the top matching Romance books:

{books_text}

Provide a warm, personalized explanation for why these books are great matches. Focus on the content and what the reader will experience."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages)
        state["explanation"] = response.content.strip()

        return state

    def recommend(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        n_results: int = 3
    ) -> Dict[str, Any]:
        """
        Get book recommendations for a query.

        Args:
            query: Natural language query (e.g., "dark and intense romance")
            filters: Optional filters (trope, rating, tags)
            n_results: Number of recommendations to return (default: 3)

        Returns:
            Dictionary with 'recommendations' and 'explanation'
        """
        # Initialize state
        initial_state = RecommenderState(
            messages=[],
            query=query,
            filters=filters,
            n_results=n_results,
            candidates=[],
            recommendations=[],
            explanation=""
        )

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        return {
            "recommendations": final_state["recommendations"],
            "explanation": final_state["explanation"]
        }


