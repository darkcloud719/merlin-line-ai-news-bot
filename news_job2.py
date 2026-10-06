import calendar
import datetime as dt
import json
import html
import feedparser
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from rich import print as pprint
from rich.logging import RichHandler
from rich.table import Table
from rich.console import Console

load_dotenv()

TAIPEI = ZoneInfo("Asia/Taipei")

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "BBC": "https://plink.anyfeeder.com/bbc/business"
}

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")

if not AZURE_OPENAI_API_KEY:
    raise ValueError("AZURE_OPENAI_API_KEY is not set") 
if not AZURE_OPENAI_API_VERSION:
    raise ValueError("AZURE_OPENAI_API_VERSION is not set")
if not AZURE_OPENAI_ENDPOINT:
    raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
if not AZURE_OPENAI_CHAT_DEPLOYMENT_NAME:
    raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME is not set")

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)

class NewsItem(BaseModel):
    title: str = Field(..., description="The title of the news item")
    summary: str = Field(..., description="The summary of the news item")
    link: str = Field(..., description="The link to the full news article")
    published_date: str = Field(..., description="The published date of the news item")
    why_important: list[str] = Field(..., description="The reasons why the news item is important")

class DailyNewsDigest(BaseModel):
    date: str = Field(..., description="The date of the daily news digest")
    news_items: list[NewsItem] = Field(..., description="The list of news items for the daily news digest")

def fetch_news_candiates(days_back: int = 3) -> list[dict]:
    today = dt.datetime.now(TAIPEI).date()
    earliest_date = today - dt.timedelta(days=days_back)
    candidates = []
    seen_urls = set()

    for source, feed_url in RSS_FEEDS.items():
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            url = entry.get("link", "No Link")
            published = entry.get("published_parsed")

            if not url or not published or url in seen_urls:
                continue

            published_utc = dt.datetime.fromtimestamp(
                calendar.timegm(published),
                tz=dt.timezone.utc
            )
            published_taipei = published_utc.astimezone(TAIPEI)

            if published_taipei.date() < earliest_date:
                continue

            raw_summary = entry.get("summary", "")
            summary = BeautifulSoup(raw_summary, "html.parser").get_text(
                " ", strip=True
            )

            candidates.append(
                {
                    "title": entry.get("title", "").strip(),
                    "published_date": published_taipei.date().isoformat(),
                    "source": source,
                    "url": url,
                    "article_excerpt": summary[:2000]
                }
            )
            seen_urls.add(url)

    candidates.sort(
        key=lambda x: x["published_date"],
        reverse=True
    )

    return candidates

def generate_daily_news_digest(candidates: list[dict]) -> DailyNewsDigest:

    today = dt.datetime.now(TAIPEI).date().isoformat()
    print(today)

    completion = client.chat.completions.parse(
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        messages=[
             {
                "role": "system",
                "content": (
                    "你是每日 AI 新聞分析師。"
                    "只能使用使用者提供的新聞候選資料，不得自行新增新聞、日期或網址。"
                    "優先選擇今天發布的新聞；不足時才選最近幾天的新聞。"
                    "避免收錄同一事件的重複報導。"
                    "請把 title 也用繁體中文呈現。"
                    "摘要使用繁體中文，每則 6 到 8 句。"
                    "每則新聞列出 1 到 3 個重要性項目，不要在項目開頭使用 1、2、3 等數字編號。"
                    "請依照指定的 JSON Schema 輸出。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"今天日期是 {today}。請從以下候選新聞挑選 10 則，"
                    "保留候選資料中的 title、published_date、source 和 url，"
                    "不得修改或捏造這些欄位。"
                    "\n候選新聞：\n"
                    + json.dumps(candidates, ensure_ascii=False)
                ),
            },
        ],
        response_format=DailyNewsDigest
    )

    digest = completion.choices[0].message.parsed

    if digest is None:
        raise ValueError("Failed to generate daily news digest")

    return digest

def save_digest(digest:DailyNewsDigest) -> None:
    output_path = Path.cwd() / f"daily_news_digest_{digest.date}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(digest.model_dump(mode="json"), f, ensure_ascii=False, indent=4)
    pprint(f"[green]Saved daily news digest to {output_path}[/green]")
    logging.info(f"Saved daily news digest to {output_path}")



if __name__ == "__main__":
    news_candidates = fetch_news_candiates()
    digest = generate_daily_news_digest(news_candidates)
    save_digest(digest)
