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
    """Generate emotion tags for Korean book reviews using LLM."""

    # Available emotion tags
    AVAILABLE_TAGS = [
        "#힐링되는", "#긴장감넘치는", "#생각이많아지는", "#따뜻한", "#슬픈",
        "#유쾌한", "#무거운", "#가벼운", "#감동적인", "#현실적인", "#판타지적인",
        "#교훈적인", "#위로받는", "#설레는", "#우울한", "#희망적인"
    ]

    def __init__(self):
        """Initialize the tag generator with GPT-4o-mini."""
        self.llm = ChatOpenAI(
            model=settings.tag_generation_model,
            temperature=0.3,  # Low temperature for consistency
            api_key=settings.openai_api_key
        )

        # System prompt with Korean cultural context
        self.system_prompt = """You are a Korean book review emotion analyzer.

Analyze reviews and extract 1-3 core emotion hashtags.

Cultural context:
- Korean reviews use indirect expressions: '괜찮았어요' = very good
- Physical reactions indicate deep emotions: '눈물이 났어요' = deeply moved
- '소름돋았어요' = intense impression
- '마음이 따뜻해졌어요' = heartwarming

Available tags (choose from these only):
#힐링되는 #긴장감넘치는 #생각이많아지는 #따뜻한 #슬픈
#유쾌한 #무거운 #가벼운 #감동적인 #현실적인 #판타지적인
#교훈적인 #위로받는 #설레는 #우울한 #희망적인

Rules:
1. Extract 1-3 tags that best capture the emotional tone
2. Prioritize explicit emotional words in the review
3. Consider the rating (5.0 = very positive emotions, 1.0 = negative emotions)
4. Output format: #tag1,#tag2,#tag3 (comma-separated, no spaces)
5. ONLY use tags from the available list above

Examples:
- "따뜻하고 힐링되는 내용이었다. 읽는 내내 미소가 지어졌다." → #힐링되는,#따뜻한
- "긴장감 넘치고 소름돋는 전개였다." → #긴장감넘치는,#무거운
- "눈물이 났다. 감동적인 스토리." → #감동적인,#슬픈
- "가볍게 읽기 좋았다. 재미있었다." → #가벼운,#유쾌한"""

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", """Book: {title}
Rating: {rating}/5
Review: {review}

Extract emotion tags:""")
        ])

    def generate_tags(self, title: str, rating: float, review: str) -> List[str]:
        """
        Generate emotion tags for a book review.

        Args:
            title: Book title
            rating: Rating from 1 to 5
            review: Korean review text

        Returns:
            List of emotion hashtags (1-3 tags)
        """
        try:
            # Create the prompt
            prompt = self.prompt_template.format_messages(
                title=title,
                rating=rating,
                review=review
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
            valid_tags = ["#생각이많아지는"]  # Default fallback

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
                    results[book.title] = ["#생각이많아지는"]  # Fallback

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

    # Test cases
    test_cases = [
        {
            "title": "달러구트 꿈 백화점",
            "rating": 4.5,
            "review": "따뜻하고 힐링되는 내용이었다. 읽는 내내 미소가 지어졌다."
        },
        {
            "title": "1984",
            "rating": 4.6,
            "review": "소름돋는 디스토피아. 현실과 겹쳐보이는 부분이 무섭다."
        },
        {
            "title": "나미야 잡화점의 기적",
            "rating": 5.0,
            "review": "눈물이 났다. 시간을 넘나드는 편지가 주는 감동이 대단했다."
        },
        {
            "title": "미드나잇 라이브러리",
            "rating": 4.8,
            "review": "삶의 선택에 대해 깊이 생각하게 되었다. 우울했던 마음이 위로받았다."
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['title']}")
        print(f"Rating: {test['rating']}/5")
        print(f"Review: {test['review']}")

        tags = generator.generate_tags(
            title=test['title'],
            rating=test['rating'],
            review=test['review']
        )

        print(f"Generated tags: {', '.join(tags)}")
        print("-" * 60)
        print()

    print("✅ Tag generation test complete!")
