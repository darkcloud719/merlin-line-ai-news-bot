import calendar
import datetime as dt
import json
from turtle import pu
import feedparser
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field

from rich import print as pprint
from rich.logging import RichHandler
from rich.table import Table
from rich.console import Console

load_dotenv()


AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_API_ENDPOINT = os.getenv("AZURE_OPENAI_API_ENDPOINT")
AZURE_OPENAI_API_DEPLOYMENT = os.getenv("AZURE_OPENAI_API_DEPLOYMENT")

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_API_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)

response = client.chat.completions.create(
        model=AZURE_OPENAI_API_DEPLOYMENT,
        messages=[
            {
                "role": "user",
                "content": "請去https://venturebeat.com/category/ai/feed 這個網址，總結一下重要資訊"
            }
        ]
    )

print(response.choices[0].message.content)