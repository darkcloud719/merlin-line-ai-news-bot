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
    PostbackEvent,
    TextMessageContent,
)


# 讀取 .env 裡的環境變數
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN:
    raise ValueError("Missing CHANNEL_ACCESS_TOKEN. Please set it in the .env file.")

if not CHANNEL_SECRET:
    raise ValueError("Missing CHANNEL_SECRET. Please set it in the .env file.")


# 建立 LINE API 設定和 Webhook 事件處理器
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)


def reply_text(reply_token: str, text: str) -> None:
    """使用 LINE 的 reply token 回覆一則文字訊息。"""
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)

        line_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


@app.route("/callback", methods=["POST"])
def callback():
    # LINE 用這個簽章確認請求來自 LINE，並且內容沒有被竄改
    signature = request.headers.get("X-Line-Signature", "")

    # 取出 LINE 傳來的原始 webhook 內容
    body = request.get_data(as_text=True)

    try:
        # 驗證簽章，並把事件交給下方已註冊的 handler
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid LINE signature")
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """使用者傳送文字時，回覆相同內容。"""
    user_text = event.message.text
    reply_text(event.reply_token, f"You said: {user_text}")


@handler.add(PostbackEvent)
def handle_postback(event):
    """使用者按下 Postback 按鈕時，讀取按鈕傳來的 data。"""
    postback_data = event.postback.data

    topic_replies = {
        "topic=ai_news": "你選擇了：AI 新知",
        "topic=cybersecurity": "你選擇了：資安快訊",
        "topic=workplace_english": "你選擇了：職場英文",
    }

    reply = topic_replies.get(
        postback_data,
        f"收到 Postback 資料：{postback_data}",
    )

    reply_text(event.reply_token, reply)


@handler.add(FollowEvent)
def handle_follow(event):
    """使用者加入或重新加入好友時，傳送歡迎訊息。"""
    reply_text(
        event.reply_token,
        "你好！歡迎加入 Merlin。請傳送文字，或使用下方選單開始探索。",
    )


@handler.default()
def handle_unmatched_event(event):
    """沒有其他 handler 接手的事件會到這裡。"""
    app.logger.info("No handler for event type: %s", type(event).__name__)


if __name__ == "__main__":
    app.run(port=5000, debug=True)