from __future__ import annotations

import logging
from collections.abc import Mapping

from merlin_bot.constants import (
    AI_NEWS_EN_DIGEST_FILE_NAME,
    AI_NEWS_ZH_DIGEST_FILE_NAME,
    CYBERSECURITY_NEWS_EN_DIGEST_FILE_NAME,
    CYBERSECURITY_NEWS_ZH_DIGEST_FILE_NAME,
    RSS_AI_FEEDS,
    RSS_CYBERSECURITY_FEEDS,
    WORKPLACE_ENGLISH_LESSON_FILE_NAME,
)
from merlin_bot.feeds import fetch_news_candidates
from merlin_bot.generation import ContentGenerator
from merlin_bot.prompts import EN_DIGEST_PROMPT, WORKPLACE_ENGLISH_PROMPT, ZH_DIGEST_PROMPT
from merlin_bot.storage import BlobJsonRepository

logger = logging.getLogger(__name__)


class DailyContentJob:
    def __init__(self, generator: ContentGenerator, repository: BlobJsonRepository) -> None:
        self._generator = generator
        self._repository = repository

    def run(self) -> None:
        failures: list[str] = []
        categories: tuple[tuple[str, Mapping[str, str], tuple[tuple[str, Mapping[str, str]], ...]], ...] = (
            (
                "ai",
                RSS_AI_FEEDS,
                (
                    (AI_NEWS_ZH_DIGEST_FILE_NAME, ZH_DIGEST_PROMPT),
                    (AI_NEWS_EN_DIGEST_FILE_NAME, EN_DIGEST_PROMPT),
                ),
            ),
            (
                "cybersecurity",
                RSS_CYBERSECURITY_FEEDS,
                (
                    (CYBERSECURITY_NEWS_ZH_DIGEST_FILE_NAME, ZH_DIGEST_PROMPT),
                    (CYBERSECURITY_NEWS_EN_DIGEST_FILE_NAME, EN_DIGEST_PROMPT),
                ),
            ),
        )

        for category, feeds, outputs in categories:
            try:
                candidates = fetch_news_candidates(feeds, days_back=3)
                logger.info("Fetched %d %s news candidates", len(candidates), category)
            except Exception:
                logger.exception("Failed to fetch candidates for %s", category)
                failures.append(f"{category}:fetch")
                continue

            for blob_name, prompt in outputs:
                try:
                    digest = self._generator.generate_news_digest(candidates, prompt)
                    self._repository.save_model(blob_name, digest)
                    logger.info("Generated and saved %s", blob_name)
                except Exception:
                    logger.exception("Failed to generate or save %s", blob_name)
                    failures.append(blob_name)

        try:
            lesson = self._generator.generate_workplace_lesson(WORKPLACE_ENGLISH_PROMPT)
            self._repository.save_model(WORKPLACE_ENGLISH_LESSON_FILE_NAME, lesson)
            logger.info("Generated and saved %s", WORKPLACE_ENGLISH_LESSON_FILE_NAME)
        except Exception:
            logger.exception("Failed to generate or save workplace English lesson")
            failures.append(WORKPLACE_ENGLISH_LESSON_FILE_NAME)

        if failures:
            raise RuntimeError(f"Daily content job failed for: {', '.join(failures)}")

