import os

from dotenv import load_dotenv
from flask import Flask, abort, request

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
)


# 讀取同一個資料夾裡的 .env
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


def reply_text(reply_token: str, text: str) -> None:
    """用 LINE 提供的 reply token 回覆一則文字訊息。"""
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)

        line_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[
                    TextMessage(text=text)
                ],
            )
        )


def build_ai_news_message() -> str:
    """
    組合 AI 新聞回覆文字。

    目前使用的是示範資料，不是即時新聞。
    之後可以把這裡的資料換成新聞 API 或 RSS 取得的內容。
    """
    news_items = [
        {
            "title": "範例：新 AI 模型推出",
            "summary": "用一到兩句話說明這則新聞發生了什麼。",
            "why_it_matters": "簡單說明這則新聞對使用者或產業有什麼影響。",
            "source": "新聞來源名稱",
        },
        {
            "title": "範例：企業導入 AI 工具",
            "summary": "用一到兩句話整理新聞的主要內容。",
            "why_it_matters": "說明這項發展可能帶來的改變。",
            "source": "新聞來源名稱",
        },
    ]

    lines = [
        "🧠 AI 新知｜今日精選",
        "━━━━━━━━━━━━━━",
        "",
    ]

    for number, news in enumerate(news_items, start=1):
        lines.extend([
            f"{number:02d}｜{news['title']}",
            f"📝 新聞摘要：{news['summary']}",
            f"💡 為什麼重要：{news['why_it_matters']}",
            f"🔎 來源：{news['source']}",
            "",
        ])

    lines.append("想看更多 AI 新聞，請輸入「AI新知」。")

    return "\n".join(lines)


@app.route("/callback", methods=["POST"])
def callback():
    # 取得 LINE 傳來的簽章和原始請求內容
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        # 驗證簽章，並將事件交給已註冊的 handler
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
        reply_text(
            event.reply_token,
            build_ai_news_message(),
        )
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
        "輸入「AI新知」，我就會整理 AI 新聞給你。",
    )


if __name__ == "__main__":
    app.run(port=5000, debug=True)