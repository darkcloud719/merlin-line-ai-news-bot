import unittest

from news_views import build_ai_news_carousel, normalize_url


class NewsViewTests(unittest.TestCase):
    def test_normalize_url_allows_https_only(self) -> None:
        self.assertEqual(normalize_url("http://example.com"), "")
        self.assertEqual(normalize_url("https://example.com"), "https://example.com")

    def test_empty_news_raises_domain_error_instead_of_key_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "No news items"):
            build_ai_news_carousel({})


if __name__ == "__main__":
    unittest.main()

