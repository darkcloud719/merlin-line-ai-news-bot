from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping, Sequence
from typing import Any

from openai import AzureOpenAI

from merlin_bot.constants import TAIPEI
from merlin_bot.models import DailyNewsDigest, DailyWorkplaceEnglishLesson


class ContentGenerationError(RuntimeError):
    """Raised when Azure OpenAI returns no structured content."""


class ContentGenerator:
    def __init__(self, client: AzureOpenAI, deployment_name: str) -> None:
        self._client = client
        self._deployment_name = deployment_name

    def generate_news_digest(
        self,
        candidates: Sequence[Mapping[str, Any]],
        prompt: Mapping[str, str],
    ) -> DailyNewsDigest:
        if not candidates:
            raise ContentGenerationError("Cannot generate a digest without news candidates")

        today = dt.datetime.now(TAIPEI).date().isoformat()
        user_prompt = prompt["user_prompt_template"].format(
            today=today,
            candidates=json.dumps(candidates, ensure_ascii=False),
        )
        completion = self._client.chat.completions.parse(
            model=self._deployment_name,
            messages=[
                {"role": "system", "content": prompt["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            response_format=DailyNewsDigest,
        )
        digest = completion.choices[0].message.parsed
        if digest is None:
            raise ContentGenerationError("Azure OpenAI returned an empty news digest")
        self._validate_digest_provenance(digest, candidates)
        return digest

    def generate_workplace_lesson(self, prompt: Mapping[str, str]) -> DailyWorkplaceEnglishLesson:
        today = dt.datetime.now(TAIPEI).date().isoformat()
        completion = self._client.chat.completions.parse(
            model=self._deployment_name,
            messages=[
                {"role": "system", "content": prompt["system_prompt"]},
                {
                    "role": "user",
                    "content": prompt["user_prompt_template"].format(today=today),
                },
            ],
            response_format=DailyWorkplaceEnglishLesson,
        )
        lesson = completion.choices[0].message.parsed
        if lesson is None:
            raise ContentGenerationError("Azure OpenAI returned an empty workplace lesson")
        return lesson

    @staticmethod
    def _validate_digest_provenance(
        digest: DailyNewsDigest,
        candidates: Sequence[Mapping[str, Any]],
    ) -> None:
        candidates_by_url = {str(candidate["url"]): candidate for candidate in candidates}
        for item in digest.news_items:
            candidate = candidates_by_url.get(str(item.url))
            if candidate is None:
                raise ContentGenerationError(f"Digest contains an unknown URL: {item.url}")
            if item.source != str(candidate["source"]):
                raise ContentGenerationError(f"Digest changed the source for URL: {item.url}")
            if item.published_date != str(candidate["published_date"]):
                raise ContentGenerationError(f"Digest changed the published date for URL: {item.url}")

