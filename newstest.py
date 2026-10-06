import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, abort, request

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexContainer,
    FlexMessage,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
)


load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN:
    raise ValueError("Missing CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET:
    raise ValueError("Missing CHANNEL_SECRET")


configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

# JSON 檔案需與 app.py 放在同一個資料夾
NEWS_JSON_PATH = Path(__file__).resolve().parent / "daily_news_digest.json"


def load_news_data() -> dict:
    """讀取並解析新聞 JSON 檔案。"""
    with NEWS_JSON_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("JSON 根節點必須是物件。")

    if not isinstance(data.get("news_items"), list):
        raise ValueError("JSON 必須包含 news_items 陣列。")

    return data


def reply_text(reply_token: str, text: str) -> None:
    """用 LINE reply token 回覆文字訊息。"""
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)
        line_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


def reply_flex(reply_token: str, flex_message: FlexMessage) -> None:
    """用 LINE reply token 回覆 Flex Message。"""
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)
        line_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[flex_message],
            )
        )


def normalize_url(url_value: str) -> str:
    """
    接受一般網址，也能處理 Markdown 格式：
    [https://example.com](https://example.com)
    """
    if not isinstance(url_value, str):
        return ""

    url_value = url_value.strip()

    markdown_match = re.fullmatch(
        r"\[[^\]]+\]\((https?://[^)]+)\)",
        url_value,
    )
    if markdown_match:
        url_value = markdown_match.group(1)

    if url_value.startswith("https://"):
        return url_value

    return ""


def get_source_name(url: str, news: dict) -> str:
    """優先讀取 JSON 的 source；若沒有，從網址推測來源。"""
    source = news.get("source")
    if source:
        return str(source)

    hostname = urlparse(url).hostname
    if not hostname:
        return "新聞來源"

    hostname = hostname.removeprefix("www.")

    if hostname == "techcrunch.com":
        return "TechCrunch"

    return hostname


def get_why_important(news: dict) -> list[str]:
    """支援 why_important 陣列及 why_it_matters 字串兩種格式。"""
    value = news.get("why_important", news.get("why_it_matters", []))

    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]

    if isinstance(value, list):
        return [str(item) for item in value if item]

    return []


def create_news_bubble(
    news: dict,
    number: int,
    total: int,
    digest_date: str,
) -> dict:
    """將一則新聞轉成一張 Flex Message 卡片。"""
    title = str(news.get("title", "未提供標題"))
    summary = str(news.get("summary", "未提供摘要"))
    published_date = str(
        news.get("published_date", digest_date)
    )

    url = normalize_url(news.get("url", ""))
    source = get_source_name(url, news)
    why_items = get_why_important(news)

    why_components = [
        {
            "type": "text",
            "text": f"• {item}",
            "size": "sm",
            "wrap": True,
            "color": "#44546A",
        }
        for item in why_items
    ]

    if not why_components:
        why_components = [
            {
                "type": "text",
                "text": "這則新聞沒有提供重要性說明。",
                "size": "sm",
                "wrap": True,
                "color": "#44546A",
            }
        ]

    body_contents = [
        {
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "lg",
            "wrap": True,
            "color": "#172B4D",
        },
        {
            "type": "text",
            "text": f"發布日期｜{published_date}",
            "size": "xs",
            "wrap": True,
            "color": "#7A8699",
        },
        {
            "type": "separator",
            "margin": "md",
            "color": "#DFE5EE",
        },
        {
            "type": "text",
            "text": "新聞摘要",
            "size": "sm",
            "weight": "bold",
            "color": "#2878C8",
            "margin": "md",
        },
        {
            "type": "text",
            "text": summary,
            "size": "sm",
            "wrap": True,
            "color": "#44546A",
        },
        {
            "type": "separator",
            "margin": "md",
            "color": "#DFE5EE",
        },
        {
            "type": "text",
            "text": "為什麼重要",
            "size": "sm",
            "weight": "bold",
            "color": "#2878C8",
            "margin": "md",
        },
    ]

    body_contents.extend(why_components)

    body_contents.append(
        {
            "type": "text",
            "text": f"來源｜{source}",
            "size": "xs",
            "color": "#7A8699",
            "margin": "md",
            "wrap": True,
        }
    )

    footer_contents = []

    if url:
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "color": "#2878C8",
                "action": {
                    "type": "uri",
                    "label": "閱讀原文",
                    "uri": url,
                },
            }
        )

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#173B70",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "text",
                    "text": f"AI 新知｜{digest_date}｜{number:02d}/{total:02d}",
                    "color": "#FFFFFF",
                    "weight": "bold",
                    "size": "sm",
                    "wrap": True,
                }
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "18px",
            "contents": body_contents,
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "contents": footer_contents,
        },
    }


def build_ai_news_carousel(news_data: dict) -> FlexMessage:
    """將 JSON 裡的新聞組合成一則可左右滑動的 carousel。"""
    digest_date = str(news_data.get("date", "日期未提供"))
    news_items = news_data["news_items"][:12]

    if not news_items:
        raise ValueError("news_items 是空的。")

    total = len(news_items)

    bubbles = [
        create_news_bubble(
            news=news,
            number=number,
            total=total,
            digest_date=digest_date,
        )
        for number, news in enumerate(news_items, start=1)
    ]

    carousel_json = {
        "type": "carousel",
        "contents": bubbles,
    }

    carousel_json_text = json.dumps(
        carousel_json,
        ensure_ascii=False,
    )

    return FlexMessage(
        alt_text=f"AI 新知摘要：{digest_date}，共 {total} 則，請左右滑動閱讀。",
        contents=FlexContainer.from_json(carousel_json_text),
    )


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid LINE signature")
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_text = event.message.text.strip()

    if user_text in {"AI新知", "AI 新知"}:
        try:
            news_data = load_news_data()
            flex_message = build_ai_news_carousel(news_data)
            reply_flex(event.reply_token, flex_message)

        except FileNotFoundError:
            app.logger.exception("News JSON file was not found.")
            reply_text(
                event.reply_token,
                "找不到 daily_news_digest.json，請確認它和 app.py 在同一個資料夾。",
            )

        except json.JSONDecodeError:
            app.logger.exception("News JSON file contains invalid JSON.")
            reply_text(
                event.reply_token,
                "daily_news_digest.json 的 JSON 格式有錯，請檢查檔案。",
            )

        except (KeyError, TypeError, ValueError):
            app.logger.exception("Could not build AI news carousel.")
            reply_text(
                event.reply_token,
                "新聞 JSON 的資料格式有誤，請檢查 date 和 news_items 欄位。",
            )

    else:
        reply_text(
            event.reply_token,
            "請輸入「AI新知」，我就會整理 AI 新聞給你。",
        )


@handler.add(FollowEvent)
def handle_follow(event):
    reply_text(
        event.reply_token,
        "你好！歡迎加入 Merlin。\n"
        "輸入「AI新知」，就能瀏覽 AI 新聞。",
    )


if __name__ == "__main__":
    app.run(port=5000, debug=True)