from __future__ import annotations

import logging

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexMessage,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from merlin_bot.constants import (
    AI_NEWS_ZH_DIGEST_FILE_NAME,
    CYBERSECURITY_NEWS_ZH_DIGEST_FILE_NAME,
    WORKPLACE_ENGLISH_LESSON_FILE_NAME,
)
from merlin_bot.storage import BlobJsonRepository
from news_views import (
    build_ai_news_carousel,
    build_cybersecurity_news_carousel,
    build_daily_workplace_english_carousel,
)

logger = logging.getLogger(__name__)


class LineBotService:
    def __init__(self, access_token: str, repository: BlobJsonRepository) -> None:
        self._configuration = Configuration(access_token=access_token)
        self._repository = repository

    def reply_text(self, reply_token: str, text: str) -> None:
        self._reply(reply_token, TextMessage(text=text))

    def reply_flex(self, reply_token: str, message: FlexMessage) -> None:
        self._reply(reply_token, message)

    def _reply(self, reply_token: str, message: TextMessage | FlexMessage) -> None:
        with ApiClient(self._configuration) as api_client:
            MessagingApi(api_client).reply_message_with_http_info(
                ReplyMessageRequest(reply_token=reply_token, messages=[message])
            )

    def handle_text_message(
        self,
        event: MessageEvent,
        destination: str | None = None,
    ) -> None:
        commands = {
            "AI 新知": (AI_NEWS_ZH_DIGEST_FILE_NAME, build_ai_news_carousel),
            "資安快訊": (CYBERSECURITY_NEWS_ZH_DIGEST_FILE_NAME, build_cybersecurity_news_carousel),
            "職場英文": (WORKPLACE_ENGLISH_LESSON_FILE_NAME, build_daily_workplace_english_carousel),
        }
        user_text = event.message.text.strip()
        command = commands.get(user_text)
        if command is None:
            self.reply_text(event.reply_token, "請輸入「AI 新知」、「資安快訊」或「職場英文」。")
            return

        blob_name, view_builder = command
        try:
            data = self._repository.load(blob_name)
            self.reply_flex(event.reply_token, view_builder(data))
        except Exception:
            logger.exception("Failed to serve LINE command", extra={"command": user_text, "blob_name": blob_name})
            self.reply_text(event.reply_token, "今日內容尚未準備完成，請稍後再試。")


def create_webhook_handler(channel_secret: str, service: LineBotService) -> WebhookHandler:
    handler = WebhookHandler(channel_secret)

    # line-bot-sdk counts declared parameters with inspect.getfullargspec().
    # Registering a bound method makes it count `self`, so use a plain wrapper.
    def on_text_message(event: MessageEvent, destination: str) -> None:
        service.handle_text_message(event, destination)

    handler.add(MessageEvent, message=TextMessageContent)(on_text_message)
    return handler

