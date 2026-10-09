import json
import re
from linebot.v3.messaging import FlexContainer, FlexMessage

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

def create_ai_news_bubble(news: dict, number: int, total: int, digest_date: str) -> dict:
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

def create_cybersecurity_news_bubble(
    news: dict,
    number: int,
    total: int,
    digest_date: str,
) -> dict:
    """把一則資安新聞轉成紅色系 Flex Message 卡片。"""

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
            "color": "#4B5563",
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
                "color": "#4B5563",
            }
        ]

    body_contents = [
        {
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "lg",
            "wrap": True,
            "color": "#252525",
        },
        {
            "type": "text",
            "text": f"發布日期｜{published_date}",
            "size": "xs",
            "wrap": True,
            "color": "#858585",
        },
        {
            "type": "separator",
            "margin": "md",
            "color": "#F0D9DC",
        },
        {
            "type": "text",
            "text": "新聞摘要",
            "size": "sm",
            "weight": "bold",
            "color": "#C62828",
            "margin": "md",
        },
        {
            "type": "text",
            "text": summary,
            "size": "sm",
            "wrap": True,
            "color": "#4B5563",
        },
        {
            "type": "separator",
            "margin": "md",
            "color": "#F0D9DC",
        },
        {
            "type": "text",
            "text": "為什麼重要",
            "size": "sm",
            "weight": "bold",
            "color": "#C62828",
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
                "color": "#C62828",
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
            "backgroundColor": "#8E2430",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "text",
                    "text": f"資安快訊｜{digest_date}｜{number:02d}/{total:02d}",
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

def create_workplace_english_bubble(
    lesson: dict,
    expression: dict,
    number: int,
    total: int   
) -> dict:

    topic = str(lesson.get("topic", "Workplace English"))
    lesson_date = str(lesson.get("date", ""))

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#433878",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "text",
                    "text": f"職場英文｜{number:02d}/{total:02d}",
                    "color": "#FFFFFF",
                    "weight": "bold",
                    "size": "sm",
                },
                {
                    "type": "text",
                    "text": f"{topic}｜{lesson_date}",
                    "color": "#E9E5FF",
                    "size": "xs",
                    "margin": "sm",
                    "wrap": True,
                },
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
                    "text": str(expression.get("phrase", "")),
                    "weight": "bold",
                    "size": "lg",
                    "wrap": True,
                    "color": "#25223A",
                },
                {
                    "type": "text",
                    "text": str(expression.get("meaning_zh", "")),
                    "size": "sm",
                    "wrap": True,
                    "color": "#5D5680",
                },
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#E5E1F2",
                },
                {
                    "type": "text",
                    "text": "EXAMPLE",
                    "size": "xs",
                    "weight": "bold",
                    "color": "#7463C6",
                },
                {
                    "type": "text",
                    "text": str(expression.get("example_en", "")),
                    "size": "sm",
                    "wrap": True,
                    "color": "#343247",
                },
                {
                    "type": "text",
                    "text": str(expression.get("example_zh", "")),
                    "size": "sm",
                    "wrap": True,
                    "color": "#6B687A",
                },
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#E5E1F2",
                },
                {
                    "type": "text",
                    "text": "WHEN TO USE IT",
                    "size": "xs",
                    "weight": "bold",
                    "color": "#7463C6",
                },
                {
                    "type": "text",
                    "text": str(expression.get("usage_note_zh", "")),
                    "size": "sm",
                    "wrap": True,
                    "color": "#4B485C",
                },
            ],
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
        create_ai_news_bubble(news, number, total, digest_date=digest_date)
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

def build_cybersecurity_news_carousel(news_data:dict) -> FlexMessage:
    # news_list = NEWS_ITEMS[:12]
    digest_date = str(news_data.get("date", "未知日期"))
    news_items = news_data["news_items"][:12]
    # total = len(news_items)

    if not news_items:
        raise ValueError("No news items available")

    total = len(news_items)


    bubbles = [
        create_cybersecurity_news_bubble(news, number, total, digest_date=digest_date)
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
        alt_text=f"Cybersecurity News Total: {total}, please scroll to view all news items",
        contents=FlexContainer.from_json(carousel_json_text)
    )

def build_daily_workplace_english_carousel(lesson: dict) -> FlexMessage:

    expressions = lesson.get("expressions", [])

    if not expressions:
        raise ValueError("No workplace English expressions available")

    expressions = expressions[:10]
    total = len(expressions)

    bubbles = [
        create_workplace_english_bubble(
            lesson=lesson,
            expression=expression,
            number=number,
            total=total
        )
        for number, expression in enumerate(expressions, start=1)
    ]

    carousel_json = {
        "type": "carousel",
        "contents": bubbles
    }

    carousel_json_text = json.dumps(
        carousel_json,
        ensure_ascii=False
    )

    return FlexMessage(
        alt_text=f"美日職場英文 | {lesson.get('topic', '')}",
        contents=FlexContainer.from_json(carousel_json_text)
    )

    

