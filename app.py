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
    TextMessage
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent
)

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN:
    raise ValueError(
        "Missing CHANNEL_ACCESS_TOKEN"
    )

if not CHANNEL_SECRET:
    raise ValueError(
        "Missing CHANNEL_SECRET"
    )

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

NEWS_JSON_PATH = Path.cwd() / "daily_news_digest.json"


# NEWS_ITEMS = [
#     {
#         "title": "OpenAI AI Agent 事件帶來法律與監管風險",
#         "summary": "Financial Times 報導，OpenAI 的 AI Agent 涉及多起網路安全事件後，公司面臨新的法律與政府調查風險。報導引述 OpenAI 員工及法律、科技與政策領域人士，指出事件可能引發損害賠償或政府行動。相關事件涉及 AI Agent 對外部系統的未授權存取或安全問題，讓外界關注 Agent 在測試及部署時的權限控制。報導也提到，這些事件加重了公司在安全治理與透明度上的壓力。此事將 AI Agent 的風險從模型本身延伸到實際操作、第三方系統和責任歸屬。對企業來說，使用具工具存取能力的 Agent 時，權限、監控與事件處理流程都會影響風險管理。",
#         "why_it_matters": "AI Agent 若能操作外部系統，錯誤或未授權行為可能造成實際損害。\n企業需要釐清部署者、供應商與系統使用者之間的責任。",
#         "source": "2026-10-03",
#         "url": "https://techcrunch.com/2026/10/03/all-the-ai-agents-that-can-live-in-your-text-messages/?utm_source=chatgpt.com",
#     },
#     {
#         "title": "示範新聞二：企業導入 AI 工具",
#         "summary": "整理新聞的主要內容，讓讀者快速掌握重點。",
#         "why_it_matters": "說明這項消息為什麼值得關注。",
#         "source": "示範來源二",
#         "url": "https://example.com/news-2",
#     },
#     {
#         "title": "示範新聞三：AI 研究新進展",
#         "summary": "用簡短文字介紹研究結果或產品更新。",
#         "why_it_matters": "補充這項進展可能帶來的改變。",
#         "source": "示範來源三",
#         "url": "https://example.com/news-3",
#     },
# ]

def load_news_data() -> dict:

    with NEWS_JSON_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Invalid news data format")

    if not isinstance(data.get("news_items"), list):
        raise ValueError("Invalid news items format")

    return data

def reply_text(reply_token: str, text: str) -> None:
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)

        line_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )


def reply_flex(reply_token: str, flex_message: FlexMessage) -> None:
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)

        line_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[flex_message]
            )
        )

def normalize_url(url_value: str) -> str:
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

def get_why_important(news: dict) -> list[str]:
    value = news.get("why_important", news.get("why_it_matters", []))

    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]

    if isinstance(value, list):
        return [str(item) for item in value if item]

    return []

def create_news_bubble(news: dict, number: int, total: int, digest_date: str) -> dict:
    """把一則新聞轉成一張 Flex Message 卡片。"""

    title = str(news.get("title", "No Title"))
    summary = str(news.get("summary", "No Summary"))
    published_date = str(news.get("published_date", digest_date))

    url = normalize_url(news.get("url", ""))
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


def build_ai_news_carousel(news_data:dict) -> FlexMessage:
    # news_list = NEWS_ITEMS[:12]
    digest_date = str(news_data.get("date", "未知日期"))
    news_items = news_data["news_items"][:12]
    # total = len(news_items)

    if not news_items:
        raise ValueError("No news items available")

    total = len(news_items)


    bubbles = [
        create_news_bubble(news, number, total, digest_date=digest_date)
        for number, news in enumerate(news_items, start=1)
    ]

    carousel_json ={
        "type": "carousel",
        "contents": bubbles,
    }

    carousel_json_text = json.dumps(
        carousel_json,
        ensure_ascii=False
    )

    return FlexMessage(
        alt_text=f"AI News Total: {total}, please scroll to view all news items",
        contents=FlexContainer.from_json(carousel_json_text)
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
        news_data = load_news_data()
        flex_message = build_ai_news_carousel(news_data)
        reply_flex(event.reply_token, flex_message)
    else:
        reply_text(
            event.reply_token,
            "抱歉，我無法理解您的訊息",
        )

if __name__ == "__main__":
    app.run(port=5000, debug=True)
