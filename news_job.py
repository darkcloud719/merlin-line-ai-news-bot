import calendar
import datetime as dt
import json
import html
from turtle import pu
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
}

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_API_ENDPOINT = os.getenv("AZURE_OPENAI_API_ENDPOINT")
AZURE_OPENAI_API_DEPLOYMENT = os.getenv("AZURE_OPENAI_API_DEPLOYMENT")

if not AZURE_OPENAI_API_KEY:
    raise ValueError("AZURE_OPENAI_API_KEY is not set")
if not AZURE_OPENAI_API_VERSION:
    raise ValueError("AZURE_OPENAI_API_VERSION is not set")
if not AZURE_OPENAI_API_ENDPOINT:
    raise ValueError("AZURE_OPENAI_API_ENDPOINT is not set")
if not AZURE_OPENAI_API_DEPLOYMENT:
    raise ValueError("AZURE_OPENAI_API_DEPLOYMENT is not set")

SYSTEM_PROMPT = """
你是我的每日 AI 新聞分析師。
你的任務是檢視最新且最重要的人工智慧新聞，並製作一份精簡的每日 AI 新聞摘要。
目標
每天挑選 10 則最新且最具關聯性的 AI 新聞。
選擇今天發布的新聞。
避免重複報導同一則新聞，或收錄多篇本質上報導同一事件的文章；除非它們提供了明顯不同的資訊或觀點。
優先關注的主題
特別關注以下領域：
- AI 模型發布與更新
- 生成式 AI
- AI Agent 與代理式系統
- RAG 與 Agentic RAG
- AI 基礎設施
- GPU 與 AI 晶片
- OpenAI
- Microsoft / Azure AI
- Google / Gemini
- Anthropic / Claude
- Meta / Llama
- xAI / Grok
- DeepSeek
- Qwen
- NVIDIA
- AI 新創公司
- AI 投資、募資與併購
- 企業導入 AI
- AI 安全與網路安全
- AI 監管與政策
- AI 研究
- 主要 AI 產業趨勢
來源要求
請使用可靠且最新的來源。
優先參考以下來源：
- TechCrunch
- Reuters
- The Verge
- Bloomberg
- Microsoft
- OpenAI
- Google
- Anthropic
- NVIDIA
- Meta
- DeepSeek 官方來源
- Qwen 官方來源
- 公司官方部落格
- 主要科技媒體
可能的情況下，優先採用原始來源或官方來源。
輸出格式
請以以下格式開頭：
每日 AI 新聞摘要
日期：YYYY-MM-DD
"""

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_API_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)


class NewsItem(BaseModel):
    title: str = Field(..., description="The title of the news item")
    summary: str = Field(..., description="The summary of the news item")
    url: str = Field(..., description="The URL of the news item")
    published_date: str = Field(..., description="The published date of the news item")
    why_important: list[str]

class DailyNewsDigest(BaseModel):
    date: str = Field(..., description="The date of the daily news digest")
    news_items: list[NewsItem] = Field(..., description="The list of news items for the daily news digest")

def setup_logging():

    logger =logging.getLogger()
    logger.setLevel(logging.INFO)

    console_handler = RichHandler()
    console_handler.setLevel(logging.WARNING)

    file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logging()

def fetch_news_candidates(days_back: int = 3) -> list[dict]:
    today = dt.datetime.now(TAIPEI).date()
    earliest_date = today - dt.timedelta(days=days_back)
    candidates = []
    seen_urls = set()

    for source, feed_url in RSS_FEEDS.items():
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            url = entry.get("link")
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
                    "title": html.unescape(entry.get("title", "")).strip(),
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

    # completion = client.chat.completions.create(
    completion = client.chat.completions.parse(
        model=AZURE_OPENAI_API_DEPLOYMENT,
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
                    "每則新聞列出 1 到 3 個重要性項目。"
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
        logger.error("Failed to generate daily news digest.")

    return digest

def save_digest(digest:DailyNewsDigest) -> None:
    output_path = Path.cwd() / f"daily_news_digest_{digest.date}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(digest.model_dump(mode="json"), f, ensure_ascii=False, indent=4)
    pprint(f"[green]Saved daily news digest to {output_path}[/green]")
    logger.info(f"Saved daily news digest to {output_path}")
    

def main() -> None:
    logger = setup_logging()

    try:
        candidates = fetch_news_candidates()
        digest = generate_daily_news_digest(candidates)
        save_digest(digest)
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()


