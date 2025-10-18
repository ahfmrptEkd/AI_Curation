"""
Emotion tag generator for Korean book reviews.
Uses GPT-4o-mini to analyze reviews and extract emotion hashtags.
"""

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict
from src.config import settings
from src.data.models import Book


class TagGenerator:
    """Generate emotion tags for book reviews using LLM."""

    # Available emotion tags (English for Romance books)
    AVAILABLE_TAGS = [
        "#healing", "#suspenseful", "#thought-provoking", "#heartwarming", "#sad",
        "#fun", "#heavy", "#light", "#touching", "#realistic", "#fantastical",
        "#inspiring", "#comforting", "#exciting", "#dark", "#hopeful",
        "#emotional", "#steamy", "#angsty", "#swoony"
    ]

    def __init__(self):
        """Initialize the tag generator with GPT-4o-mini."""
        self.llm = ChatOpenAI(
            model=settings.tag_generation_model,
            temperature=0.3,  # Low temperature for consistency
            api_key=settings.openai_api_key
        )

        # System prompt for English romance book reviews
        self.system_prompt = """You are a book review emotion analyzer specializing in Romance novels.

Analyze reviews and extract 1-3 core emotion hashtags that capture the reader's emotional experience.

Available tags (choose from these only):
#healing #suspenseful #thought-provoking #heartwarming #sad
#fun #heavy #light #touching #realistic #fantastical
#inspiring #comforting #exciting #dark #hopeful
#emotional #steamy #angsty #swoony

Rules:
1. Extract 1-3 tags that best capture the emotional tone
2. Prioritize explicit emotional words and reactions in the review
3. Consider the rating (5.0 = very positive emotions, 1.0 = negative emotions)
4. Pay attention to romance-specific emotions (swoony, angsty, steamy)
5. Output format: #tag1,#tag2,#tag3 (comma-separated, no spaces)
6. ONLY use tags from the available list above

Examples:
- "Unhinged. So fun. Things just kept happening." → #fun,#exciting
- "Honestly, I dislike Logan. He keeps treating her like shit." → #angsty,#dark
- "Sweet, spicy and just the right amount of slowburn." → #swoony,#steamy,#heartwarming
- "Loved it. This book was great." → #touching,#hopeful"""

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", """Book: {title}
Rating: {rating}/5
Review: {review}

Extract emotion tags:""")
        ])

    def generate_tags(
        self,
        title: str,
        rating: float = None,
        review: str = None,
        description: str = None
    ) -> List[str]:
        """
        Generate emotion tags for a book based on review or description.

        Args:
            title: Book title
            rating: Rating from 1 to 5 (optional for new books)
            review: User review text (for books already read)
            description: Book description from Google Books API (for new books)

        Returns:
            List of emotion hashtags (1-3 tags)

        Note:
            Priority: review > description
            - Use review for books the user has read (captures actual emotional response)
            - Use description for new/recommended books (captures book's tone/mood)
        """
        try:
            # Determine which text to use (priority: description > review)
            if description:
                text = description
                source = "description"
            elif review:
                text = review
                source = "review"
            else:
                print(f"Warning: No review or description provided for '{title}'")
                return ["#thought-provoking"]  # Default fallback

            # Use rating if provided, otherwise default to neutral
            rating_value = rating if rating else 0.0

            # Create the prompt
            prompt = self.prompt_template.format_messages(
                title=title,
                rating=rating_value,
                review=text
            )

            # Get LLM response
            response = self.llm.invoke(prompt)
            tags_string = response.content.strip()

            # Parse tags
            tags = self._parse_tags(tags_string)

            # Validate tags
            valid_tags = self._validate_tags(tags)

            return valid_tags

        except Exception as e:
            print(f"Error generating tags for '{title}': {e}")
            return []

    def _parse_tags(self, tags_string: str) -> List[str]:
        """
        Parse tags from LLM output.

        Args:
            tags_string: Raw output from LLM (e.g., "#힐링되는,#따뜻한")

        Returns:
            List of hashtags
        """
        # Remove any extra whitespace
        tags_string = tags_string.strip()

        # Split by comma
        tags = [tag.strip() for tag in tags_string.split(',')]

        # Ensure tags start with #
        tags = [tag if tag.startswith('#') else f'#{tag}' for tag in tags]

        return tags

    def _validate_tags(self, tags: List[str]) -> List[str]:
        """
        Validate that tags are in the available list.

        Args:
            tags: List of tags to validate

        Returns:
            List of valid tags
        """
        valid_tags = []
        for tag in tags:
            if tag in self.AVAILABLE_TAGS:
                valid_tags.append(tag)
            else:
                print(f"Warning: Invalid tag '{tag}' - not in available list")

        # Ensure we have at least 1 tag
        if not valid_tags:
            print("Warning: No valid tags generated, using default")
            valid_tags = ["#thought-provoking"]  # Default fallback

        # Limit to 3 tags
        return valid_tags[:3]

    def generate_tags_batch(self, books: List[Book]) -> Dict[str, List[str]]:
        """
        Generate emotion tags for multiple books in batch.
        Uses LLM batch processing for better performance and cost efficiency.

        Args:
            books: List of Book objects

        Returns:
            Dictionary mapping book titles to their tags
        """
        if not books:
            return {}

        print(f"Processing {len(books)} books in batch...")

        # Prepare all prompts
        prompts = []
        for book in books:
            prompt = self.prompt_template.format_messages(
                title=book.title,
                rating=book.rating,
                review=book.review
            )
            prompts.append(prompt)

        # Batch invoke (parallel processing)
        try:
            responses = self.llm.batch(prompts)

            # Process results
            results = {}
            for book, response in zip(books, responses):
                try:
                    tags_string = response.content.strip()
                    tags = self._parse_tags(tags_string)
                    valid_tags = self._validate_tags(tags)
                    results[book.title] = valid_tags
                    print(f"✓ {book.title}: {', '.join(valid_tags)}")
                except Exception as e:
                    print(f"✗ Error processing '{book.title}': {e}")
                    results[book.title] = ["#thought-provoking"]  # Fallback

            return results

        except Exception as e:
            print(f"Batch processing error: {e}")
            print("Falling back to sequential processing...")

            # Fallback: sequential processing
            results = {}
            for book in books:
                tags = self.generate_tags(book.title, book.rating, book.review)
                results[book.title] = tags

            return results


if __name__ == "__main__":
    # Test the tag generator
    print("=== Testing Tag Generator ===\n")

    generator = TagGenerator()

    print("📚 Test 1: User Review-based Tags (Books already read)\n")

    # Test cases with user reviews
    review_tests = [
        {
            "title": "Too Much",
            "rating": 3.0,
            "review": "Unhinged. Oh my freaking god unhinged. Literally, things just kept happening and I was like wtf the whole time. so fun."
        },
        {
            "title": "Too Sweet",
            "rating": 3.0,
            "review": "This fic is sweet, spicy and just the right amount of slowburn. There is no third act break up (Hallelujah!)."
        }
    ]

    for i, test in enumerate(review_tests, 1):
        print(f"Test {i}: {test['title']}")
        print(f"Rating: {test['rating']}/5")
        print(f"Review: {test['review'][:60]}...")

        tags = generator.generate_tags(
            title=test['title'],
            rating=test['rating'],
            review=test['review']
        )

        print(f"Generated tags: {', '.join(tags)}")
        print("-" * 60)
        print()

    print("\n📖 Test 2: Description-based Tags (New/Recommended books)\n")

    # Test cases with book descriptions (simulating Google Books API)
    description_tests = [
        {
            "title": "The Love Hypothesis",
            "description": "A contemporary romantic comedy about a fake dating experiment between a PhD student and a grumpy professor. Witty banter, slow-burn chemistry, and STEM representation make this a delightful enemies-to-lovers romance."
        },
        {
            "title": "Beach Read",
            "description": "Two writers with opposing worldviews challenge each other to write in the other's genre while spending a summer as neighbors. A heartfelt exploration of grief, hope, and second chances wrapped in humor and romance."
        }
    ]

    for i, test in enumerate(description_tests, 1):
        print(f"Test {i}: {test['title']}")
        print(f"Description: {test['description'][:80]}...")

        tags = generator.generate_tags(
            title=test['title'],
            description=test['description']
        )

        print(f"Generated tags: {', '.join(tags)}")
        print("-" * 60)
        print()

    print("✅ Tag generation test complete!")
