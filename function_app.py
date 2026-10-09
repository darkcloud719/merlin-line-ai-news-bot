import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings
import logging
import calendar
import datetime as dt
import json
import html
import feedparser
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
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexContainer,
    FlexMessage,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent
)
from news_views import normalize_url, get_why_important, build_ai_news_carousel, build_cybersecurity_news_carousel, build_daily_workplace_english_carousel



load_dotenv()

TAIPEI = ZoneInfo("Asia/Taipei")

RSS_AI_FEEDS = {
    "TechCrunch": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "TheVerge": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "MITTechnologyReview": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"
}

RSS_CYBERSECURITY_FEEDS = {
    "TheHackerNews": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
}

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not AZURE_OPENAI_API_KEY:
    raise ValueError("AZURE_OPENAI_API_KEY is not set.")
if not AZURE_OPENAI_API_VERSION:
    raise ValueError("AZURE_OPENAI_API_VERSION is not set.")
if not AZURE_OPENAI_ENDPOINT:
    raise ValueError("AZURE_OPENAI_ENDPOINT is not set.")
if not AZURE_OPENAI_CHAT_DEPLOYMENT_NAME:
    raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME is not set.")
if not CHANNEL_ACCESS_TOKEN:
    raise ValueError("CHANNEL_ACCESS_TOKEN is not set.")
if not CHANNEL_SECRET:
    raise ValueError("CHANNEL_SECRET is not set.")
if not AZURE_STORAGE_CONNECTION_STRING:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set.")
if not AZURE_STORAGE_CONTAINER_NAME:
    raise ValueError("AZURE_STORAGE_CONTAINER_NAME is not set.")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)

# def setup_logging():

#     logger = logging.getLogger()
#     logger.setLevel(logging.INFO)

#     console_handler = RichHandler()
#     console_handler.setLevel(logging.WARNING)

#     file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
#     file_handler.setLevel(logging.INFO)

#     formatter = logging.Formatter(
#         "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#         datefmt="%Y-%m-%d %H:%M:%S"
#     )

#     file_handler.setFormatter(formatter)

#     logger.addHandler(console_handler)
#     logger.addHandler(file_handler)

#     return logger


ZH_DIGEST_PROMPT = {
    "system_prompt": (
        "你是每日新聞分析師。"
        "只能使用提供的新聞候選資料，不得自行新增新聞、日期或網址。"
        "優先選擇今天發布的新聞；不足時才選最近幾天的新聞。"
        "避免收錄同一事件的重複報導。"
        "title 請翻譯成繁體中文。"
        "摘要使用繁體中文，每則 6 到 8 句。"
        "每則新聞列出 1 到 3 個重要性項目，不要加數字編號。"
        "請依照指定的 JSON Schema 輸出。"
    ),
    "user_prompt_template": (
        "今天日期是 {today}。請從以下候選新聞挑選 10 則。"
        "保留候選資料中的 published_date、source 和 url，不得修改或捏造。"
        "\n候選新聞：\n{candidates}"
    ),
}

EN_DIGEST_PROMPT = {
    "system_prompt": (
        "You are a daily news analyst."
        "You can only use the provided news candidates and must not create new news, dates, or URLs."
        "Prioritize news published today; if insufficient, select news from the past few days."
        "Avoid including duplicate reports of the same event."
        "Translate the title into English."
        "Summarize each news item in English, with 6 to 8 sentences per item."
        "List 1 to 3 important points for each news item without numbering them."
        "Please output according to the specified JSON Schema."
    ),
    "user_prompt_template": (
        "Today's date is {today}. Please select 10 news items from the following candidates."
        "Keep the published_date, source, and url from the candidate data, and do not modify or fabricate them."
        "\nCandidate news:\n{candidates}"
    )
}

WORKPLACE_ENGLISH_PROMPT = {
    "system_prompt": (
        "You are a practical workplace English coach for a Taiwanese learner. "
        "Create a daily English lesson for a B1-B2 learner. "
        "Focus on one practical workplace situation. "
        "Use natural American English that people actually use at work. "
        "Avoid stiff textbook language, overly formal wording, and inappropriate slang. "
        "Create exactly 10 useful expressions. "
        "For each expression, provide the English phrase, its Traditional Chinese meaning, "
        "one natural English example, the Traditional Chinese translation, "
        "and a brief Traditional Chinese note about when to use it. "
        "Also create a short workplace dialogue using some of the expressions. "
        "End with one fill-in-the-blank practice question and its answer. "
        "Write explanations and translations in Traditional Chinese. "
        "Use the specified JSON Schema."
    ),
    "user_prompt_template": (
        "Create today's workplace English lesson. "
        "Return exactly 10 expressions."
    ),
}

AI_NEWS_ZH_DIGEST_FILE_NAME = "ai_daily_news_zh_digest.json"
AI_NEWS_EN_DIGEST_FILE_NAME = "ai_daily_news_en_digest.json"
CYBERSECURITY_NEWS_ZH_DIGEST_FILE_NAME = "cybersecurity_daily_news_zh_digest.json"
CYBERSECURITY_NEWS_EN_DIGEST_FILE_NAME = "cybersecurity_daily_news_en_digest.json"
WORKPLACE_ENGLISH_LESSON_FILE_NAME = "daily_workplace_english_lesson.json"

class NewsItem(BaseModel):
    title: str = Field(..., description="The title of the news item")
    summary: str = Field(..., description="The summary of the news item")
    url: str = Field(..., description="The URL of the news item")
    published_date: str = Field(..., description="The published date of the news item")
    why_important: list[str]

class DailyNewsDigest(BaseModel):
    date: str = Field(..., description="The date of the news digest")
    news_items: list[NewsItem] = Field(..., description="The list of news items in the digest")

class WorkplaceExpression(BaseModel):
    phrase: str = Field(..., description="A natural workplace English expression")
    meaning_zh: str = Field(..., description="Traditional Chinese meaning of the expression")
    example_en: str = Field(..., description="A natural English example using the expression")
    example_zh: str = Field(..., description="Traditional Chinese translation of the English example")
    usage_note_zh: str = Field(..., description="When to use this expression, in Traditional Chinese")

class DialogueLine(BaseModel):
    speaker: str = Field(..., description="The speaker of the dialogue line")
    english: str = Field(..., description="The English line spoken by the speaker")
    chinese: str = Field(..., description="The Chinese translation of the English line")

class DailyWorkplaceEnglishLesson(BaseModel):
    date: str = Field(..., description="The date of the lesson")
    topic: str = Field(..., description="The topic of the lesson")
    level: str = Field(..., description="The difficulty level of the lesson")
    expressions: list[WorkplaceExpression] = Field(..., description="Exactly 10 workplace English expressions")
    dialogue: list[DialogueLine] = Field(..., description="The dialogue lines for the lesson")
    practice_question: str = Field(..., description="The practice question for the lesson")
    practice_answer: str = Field(..., description="The answer to the practice question for the lesson")

def fetch_news_candidates(days_back: int = 3, rss_feeds: dict[str, str] = RSS_AI_FEEDS) -> list[dict]:
    try:

        today = dt.datetime.now(TAIPEI).date()
        earliest_date = today - dt.timedelta(days=days_back)
        candidates = []
        seen_urls = set()

        for source, feed_url in rss_feeds.items():
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
                summary = BeautifulSoup(raw_summary, "html.parser").get_text(" ", strip=True)

                candidates.append(
                    {
                        "title": html.unescape(entry.get("title", "")).strip(),
                        "published_date": published_taipei.date().isoformat(),
                        "source": source,
                        "url": url,
                        "article_excerpt": summary[:500]
                    }
                )
                seen_urls.add(url)

        candidates.sort(
            key=lambda x: x["published_date"],
            reverse=True
        )

        return candidates
    
    except Exception as e:
        logging.error(f"Failed to fetch news candidates: {e}")
        return []

def generate_daily_news_digest(candidates: list[dict], prompt: dict) -> DailyNewsDigest:

    try:
        
        today = dt.datetime.now(TAIPEI).date().isoformat()
        system_prompt = prompt.get("system_prompt", "")
        user_prompt_template = prompt.get("user_prompt_template", "")

        completion = client.chat.completions.parse(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        system_prompt
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        user_prompt_template.format(today=today, candidates=json.dumps(candidates, ensure_ascii=False))
                    ),
                },
            ],
            response_format=DailyNewsDigest
        )

        digest = completion.choices[0].message.parsed

        if digest is None:
            raise ValueError("Failed to generate daily news digest.")

        return digest
    
    except Exception as e:
        logging.error(f"Failed to generate daily news digest: {e}")
        return None

def generate_daily_workplace_english_lesson(prompt: dict) -> DailyWorkplaceEnglishLesson:
    try:
        system_prompt = prompt.get("system_prompt", "")
        user_prompt = prompt.get("user_prompt", "")

        completion = client.chat.completions.parse(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                },
            ],
            response_format=DailyWorkplaceEnglishLesson
        )

        lesson = completion.choices[0].message.parsed

        if lesson is None:
            raise ValueError("Failed to generate workplace English lesson.")

        return lesson

    except Exception as e:
        logging.exception("Failed to generate workplace English lesson.")
        return None

def save_daily_news_digest(digest:DailyNewsDigest, blob_name: str) -> None:
    # output_path = Path.cwd() / f"daily_news_digest_zh_{digest.date}.json"
    if digest is None:
        raise ValueError("Cannot save an empty news digest.")

    news_zh_json = json.dumps(digest.model_dump(mode="json"), ensure_ascii=False, indent=4)

    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

    blob_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER_NAME, blob=blob_name)

    # blob_client.upload_blob(data=json_bytes, overwrite=True, content_settings=ContentSettings(content_type="application/json; charset=utf-8"))

    blob_client.upload_blob(data=news_zh_json, overwrite=True, content_settings=ContentSettings(content_type="application/json; charset=utf-8"))

    logging.info(f"Saved {blob_name} to container {AZURE_STORAGE_CONTAINER_NAME}")

    # output_path = Path.cwd() / f"daily_news_zh_digest.json"
    # with open(output_path, "w", encoding="utf-8") as f:
    #     json.dump(digest.model_dump(mode="json"), f, ensure_ascii=False, indent=4)
    # logging.info(f"Saved daily news digest to {output_path}")

def save_daily_workplace_english_lesson(lesson: DailyWorkplaceEnglishLesson, blob_name: str) -> None:

    workplace_english_json = json.dumps(lesson.model_dump(mode="json"), ensure_ascii=False, indent=4)

    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

    blob_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER_NAME, blob=blob_name)

    blob_client.upload_blob(data=workplace_english_json, overwrite=True, content_settings=ContentSettings(content_type="application/json; charset=utf-8"))

    logging.info(f"Saved {blob_name} to container {AZURE_STORAGE_CONTAINER_NAME}")


def load_news_data(blob_name: str) -> dict:

    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER_NAME, blob=blob_name)
        blob_data = blob_client.download_blob().readall()
        return json.loads(blob_data)
    except Exception as e:
        logging.error(f"Failed to load `{blob_name}`: {e}")
        return {}

def reply_text(reply_token: str, text: str) -> None:
    try:
        with ApiClient(configuration) as api_client:
            line_api = MessagingApi(api_client)
            line_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)]
                )
            )
    except Exception as e:
        logging.error(f"Failed to reply text message: {e}")

def reply_flex(reply_token: str, flex_message: FlexMessage) -> None:
    try:
        with ApiClient(configuration) as api_client:
            line_api = MessagingApi(api_client)
            line_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[flex_message]
                )
            )
    except Exception as e:
        logging.error(f"Failed to reply flex message: {e}")



@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_text = event.message.text.strip()

    # if user_text in {"AI 新知", "資安快訊"}:
    #     news_data = load_news_data()
    #     flex_message = build_ai_news_carousel(news_data)
    #     reply_flex(event.reply_token, flex_message)
    # else:
    #     reply_text(
    #         event.reply_token,
    #         "抱歉，我無法理解您的訊息",
    #     )

    if user_text == "AI 新知":
        news_data = load_news_data(AI_NEWS_ZH_DIGEST_FILE_NAME)
        flex_message = build_ai_news_carousel(news_data)
        reply_flex(event.reply_token, flex_message)
    elif user_text == "資安快訊":
        news_data = load_news_data(CYBERSECURITY_NEWS_ZH_DIGEST_FILE_NAME)
        flex_message = build_cybersecurity_news_carousel(news_data)
        reply_flex(event.reply_token, flex_message)
    elif user_text == "職場英文":
        workplace_english_lesson = load_news_data(WORKPLACE_ENGLISH_LESSON_FILE_NAME)
        flex_message = build_daily_workplace_english_carousel(workplace_english_lesson)
        reply_flex(event.reply_token, flex_message)


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="callback", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def callback(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Callback function received a request.")

    signature = req.headers.get("X-Line-Signature", "")

    body = req.get_body().decode("utf-8")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logging.warning("Invalid LINE signature")
        return func.HttpResponse("Invalid signature", status_code=400)
    except Exception as e:
        logging.exception("Failed to handle LINE callback")
        return func.HttpResponse("Internal server error", status_code=500)
    return func.HttpResponse(
        "Callback function executed successfully.",
        status_code=200
    )

# @app.route(route="http_trigger")
# def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Python HTTP trigger function processed a request. Nick')

#     name = req.params.get('name')
#     if not name:
#         try:
#             req_body = req.get_json()
#         except ValueError:
#             pass
#         else:
#             name = req_body.get('name')

#     if name:
#         return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
#     else:
#         return func.HttpResponse(
#              "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
#              status_code=200
#         )

@app.timer_trigger(schedule="0 0 */6 * * *", arg_name="mytimer", run_on_startup=False, use_monitor=True)
def daily_news_timer(mytimer: func.TimerRequest) -> None:
    if mytimer.past_due:
        logging.info("Daily news timer is past due.")

    try:
        ai_candidates = fetch_news_candidates(3, RSS_AI_FEEDS)
        cybersecurity_candidates = fetch_news_candidates(3, RSS_CYBERSECURITY_FEEDS)
        

        # if not candidates:
        #     logging.warning("No news candidates found; skipping digest generation.")
        #     return 

        logging.info(f"Fetched {len(ai_candidates)} AI news candidates.")
        logging.info(f"Fetched {len(cybersecurity_candidates)} cybersecurity news candidates.")

        # digest = generate_daily_news_zh_digest(candidates)
        ai_zh_digest = generate_daily_news_digest(ai_candidates, ZH_DIGEST_PROMPT)
        ai_en_digest = generate_daily_news_digest(ai_candidates, EN_DIGEST_PROMPT)
        cybersecurity_zh_digest = generate_daily_news_digest(cybersecurity_candidates, ZH_DIGEST_PROMPT)
        cybersecurity_en_digest = generate_daily_news_digest(cybersecurity_candidates, EN_DIGEST_PROMPT)
        workplace_english_lesson = generate_daily_workplace_english_lesson(WORKPLACE_ENGLISH_PROMPT)

        # if digest is None:
        #     raise ValueError("Digest  generation returned no result.")

        # save_daily_news_zh_digest(digest)
        save_daily_news_digest(ai_zh_digest, AI_NEWS_ZH_DIGEST_FILE_NAME)
        save_daily_news_digest(ai_en_digest, AI_NEWS_EN_DIGEST_FILE_NAME)
        save_daily_news_digest(cybersecurity_zh_digest, CYBERSECURITY_NEWS_ZH_DIGEST_FILE_NAME)
        save_daily_news_digest(cybersecurity_en_digest, CYBERSECURITY_NEWS_EN_DIGEST_FILE_NAME)
        save_daily_workplace_english_lesson(workplace_english_lesson, WORKPLACE_ENGLISH_LESSON_FILE_NAME)

        logging.info("Daily news digests generated and saved successfully.")

    except Exception as e:
        logging.error(f"Failed to generate and save daily news digests: {e}")

