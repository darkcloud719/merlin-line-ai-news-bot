import json
import unittest

from pydantic import ValidationError

from merlin_bot.models import DailyNewsDigest, DailyWorkplaceEnglishLesson


class ModelTests(unittest.TestCase):
    def test_openai_schema_has_no_unsupported_format_keywords(self) -> None:
        schema = json.dumps(DailyNewsDigest.model_json_schema())
        self.assertNotIn('"format": "uri"', schema)
        self.assertNotIn('"format": "date"', schema)

    def test_news_source_is_preserved(self) -> None:
        digest = DailyNewsDigest.model_validate(
            {
                "date": "2026-10-09",
                "news_items": [
                    {
                        "title": "A title",
                        "summary": "A summary",
                        "source": "TechCrunch",
                        "url": "https://example.com/news",
                        "published_date": "2026-10-09",
                        "why_important": ["Useful"],
                    }
                ],
            }
        )
        self.assertEqual(digest.news_items[0].source, "TechCrunch")

    def test_news_url_must_be_https(self) -> None:
        with self.assertRaises(ValidationError):
            DailyNewsDigest.model_validate(
                {
                    "date": "2026-10-09",
                    "news_items": [
                        {
                            "title": "A title",
                            "summary": "A summary",
                            "source": "Example",
                            "url": "http://example.com/news",
                            "published_date": "2026-10-09",
                            "why_important": ["Useful"],
                        }
                    ],
                }
            )

    def test_news_dates_must_use_iso_format(self) -> None:
        with self.assertRaises(ValidationError):
            DailyNewsDigest.model_validate(
                {
                    "date": "October 9, 2026",
                    "news_items": [
                        {
                            "title": "A title",
                            "summary": "A summary",
                            "source": "Example",
                            "url": "https://example.com/news",
                            "published_date": "2026-10-09",
                            "why_important": ["Useful"],
                        }
                    ],
                }
            )

    def test_workplace_lesson_requires_exactly_ten_expressions(self) -> None:
        with self.assertRaises(ValidationError):
            DailyWorkplaceEnglishLesson.model_validate(
                {
                    "date": "2026-10-09",
                    "topic": "Meetings",
                    "level": "B1-B2",
                    "expressions": [],
                    "dialogue": [{"speaker": "A", "english": "Hi", "chinese": "嗨"}],
                    "practice_question": "Question",
                    "practice_answer": "Answer",
                }
            )


if __name__ == "__main__":
    unittest.main()

