from datetime import date
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class NewsItem(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source: str = Field(min_length=1)
    url: str
    published_date: str
    why_important: list[str] = Field(min_length=1, max_length=3)

    @field_validator("url")
    @classmethod
    def validate_https_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("url must be an absolute HTTPS URL")
        return value

    @field_validator("published_date")
    @classmethod
    def validate_published_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class DailyNewsDigest(BaseModel):
    date: str
    news_items: list[NewsItem] = Field(min_length=1, max_length=10)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class WorkplaceExpression(BaseModel):
    phrase: str = Field(min_length=1)
    meaning_zh: str = Field(min_length=1)
    example_en: str = Field(min_length=1)
    example_zh: str = Field(min_length=1)
    usage_note_zh: str = Field(min_length=1)


class DialogueLine(BaseModel):
    speaker: str = Field(min_length=1)
    english: str = Field(min_length=1)
    chinese: str = Field(min_length=1)


class DailyWorkplaceEnglishLesson(BaseModel):
    date: str
    topic: str = Field(min_length=1)
    level: str = Field(min_length=1)
    expressions: list[WorkplaceExpression] = Field(min_length=10, max_length=10)
    dialogue: list[DialogueLine] = Field(min_length=1)
    practice_question: str = Field(min_length=1)
    practice_answer: str = Field(min_length=1)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value

