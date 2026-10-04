import json
import os

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


# 讀取 app.py 同一個資料夾裡的 .env
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN:
    raise ValueError(
        "Missing CHANNEL_ACCESS_TOKEN. Please set it in the .env file."
    )

if not CHANNEL_SECRET:
    raise ValueError(
        "Missing CHANNEL_SECRET. Please set it in the .env file."
    )


# 設定 LINE Messaging API 和 Webhook Handler
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)


# 示範新聞資料：請換成實際新聞和有效的 HTTPS 原文網址
NEWS_ITEMS = [
    {
        "title": "示範新聞一：新 AI 模型推出",
        "summary": "用一到兩句話說明新聞發生了什麼，以及重要資訊。",
        "why_it_matters": "說明這項發展可能如何影響使用者或產業。",
        "source": "示範來源一",
        "url": "https://example.com/news-1",
    },
    {
        "title": "示範新聞二：企業導入 AI 工具",
        "summary": "整理新聞的主要內容，讓讀者快速掌握重點。",
        "why_it_matters": "說明這項消息為什麼值得關注。",
        "source": "示範來源二",
        "url": "https://example.com/news-2",
    },
    {
        "title": "示範新聞三：AI 研究新進展",
        "summary": "用簡短文字介紹研究結果或產品更新。",
        "why_it_matters": "補充這項進展可能帶來的改變。",
        "source": "示範來源三",
        "url": "https://example.com/news-3",
    },
]


def reply_text(reply_token: str, text: str) -> None:
    """用 LINE reply token 回覆文字。"""
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


def create_news_bubble(news: dict, number: int, total: int) -> dict:
    """把一則新聞轉成一張 Flex Message 卡片。"""
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
                    "text": f"AI NEWS  |  {number:02d}/{total:02d}",
                    "color": "#FFFFFF",
                    "weight": "bold",
                    "size": "sm",
                }
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "text",
                    "text": news["title"],
                    "weight": "bold",
                    "size": "lg",
                    "wrap": True,
                    "color": "#172B4D",
                },
                {
                    "type": "text",
                    "text": news["summary"],
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
                    "text": "WHY IT MATTERS",
                    "size": "xs",
                    "weight": "bold",
                    "color": "#2878C8",
                    "margin": "md",
                },
                {
                    "type": "text",
                    "text": news["why_it_matters"],
                    "size": "sm",
                    "wrap": True,
                    "color": "#44546A",
                },
                {
                    "type": "text",
                    "text": f"來源｜{news['source']}",
                    "size": "xs",
                    "color": "#7A8699",
                    "margin": "md",
                    "wrap": True,
                },
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#2878C8",
                    "action": {
                        "type": "uri",
                        "label": "閱讀原文",
                        "uri": news["url"],
                    },
                }
            ],
        },
    }


def build_ai_news_carousel() -> FlexMessage:
    """把多則新聞組合成一則可左右滑動的 Flex Message。"""
    # LINE Flex carousel 最多放 12 張 bubble 卡片
    news_list = NEWS_ITEMS[:12]
    total = len(news_list)

    bubbles = [
        create_news_bubble(news, number, total)
        for number, news in enumerate(news_list, start=1)
    ]

    carousel_json = {
        "type": "carousel",
        "contents": bubbles,
    }

    # 將 Python dict 轉成 JSON，再交給 SDK 轉成 Flex container
    carousel_json_text = json.dumps(
        carousel_json,
        ensure_ascii=False,
    )

    return FlexMessage(
        alt_text=f"AI 新知精選，共 {total} 則，請左右滑動閱讀。",
        contents=FlexContainer.from_json(carousel_json_text),
    )


@app.route("/callback", methods=["POST"])
def callback():
    # LINE 會在 header 放入簽章，程式用它驗證請求
    signature = request.headers.get("X-Line-Signature", "")

    # 讀取 LINE 傳來的原始 webhook 內容
    body = request.get_data(as_text=True)

    try:
        # 驗證簽章，再把事件交給下方註冊的 handler
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid LINE signature")
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """處理使用者傳送的文字訊息。"""
    user_text = event.message.text.strip()

    if user_text in {"AI新知", "AI 新知"}:
        flex_message = build_ai_news_carousel()
        reply_flex(event.reply_token, flex_message)
    else:
        reply_text(
            event.reply_token,
            "請輸入「AI新知」，我就會整理 AI 新聞給你。",
        )


@handler.add(FollowEvent)
def handle_follow(event):
    """使用者加入或重新加入好友時，傳送歡迎訊息。"""
    reply_text(
        event.reply_token,
        "你好！歡迎加入 Merlin。\n"
        "輸入「AI新知」，就能瀏覽 AI 新聞卡片。",
    )


if __name__ == "__main__":
    app.run(port=5000, debug=True)