from __future__ import annotations

import calendar
import datetime as dt
import html
import logging
from collections.abc import Mapping
from typing import Any
from urllib.request import Request, urlopen

import feedparser
from bs4 import BeautifulSoup

from merlin_bot.constants import TAIPEI

logger = logging.getLogger(__name__)


class FeedFetchError(RuntimeError):
    """Raised when every configured RSS feed fails."""


def _load_feed(feed_url: str) -> Any:
    request = Request(feed_url, headers={"User-Agent": "MerlinNewsBot/1.0"})
    with urlopen(request, timeout=15) as response:
        return feedparser.parse(response.read())


def fetch_news_candidates(
    rss_feeds: Mapping[str, str],
    days_back: int = 3,
    *,
    now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    if days_back < 0:
        raise ValueError("days_back must be non-negative")

    current = now.astimezone(TAIPEI) if now else dt.datetime.now(TAIPEI)
    earliest_date = current.date() - dt.timedelta(days=days_back)
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    successful_feeds = 0

    for source, feed_url in rss_feeds.items():
        try:
            feed = _load_feed(feed_url)
            if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
                raise FeedFetchError(str(getattr(feed, "bozo_exception", "invalid feed")))
            successful_feeds += 1
        except Exception:
            logger.exception("Failed to fetch RSS feed", extra={"source": source, "feed_url": feed_url})
            continue

        for entry in feed.entries:
            url = entry.get("link")
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if not url or not published or url in seen_urls:
                continue

            published_utc = dt.datetime.fromtimestamp(calendar.timegm(published), tz=dt.timezone.utc)
            published_taipei = published_utc.astimezone(TAIPEI)
            if published_taipei.date() < earliest_date:
                continue

            summary_html = entry.get("summary", "")
            summary = BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True)
            candidates.append(
                {
                    "title": html.unescape(entry.get("title", "")).strip(),
                    "published_date": published_taipei.date().isoformat(),
                    "source": source,
                    "url": url,
                    "article_excerpt": summary[:500],
                }
            )
            seen_urls.add(url)

    if rss_feeds and successful_feeds == 0:
        raise FeedFetchError("All configured RSS feeds failed")

    return sorted(candidates, key=lambda item: item["published_date"], reverse=True)

