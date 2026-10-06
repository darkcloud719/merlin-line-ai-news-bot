import feedparser
import datetime as dt
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

feed_url = "https://plink.anyfeeder.com/bbc/business"

feed = feedparser.parse(feed_url)

print("Feed Count:", len(feed.entries))

print("Website Name:", feed.feed.get("title", "Unknown Website"))
print("Website Description:", feed.feed.get("description", "No Description"))

for entry in feed.entries[:5]:
    print("Title:", entry.get("title", "No Title"))
    print("Link:", entry.get("link", "No Link"))
    print("Published Date:", entry.get("published_parsed", "No Published Date"))
    # print("Summary:", entry.get("summary", "No Summary"))
    print("Summary:", BeautifulSoup(entry.get("summary", "No Summary"), "html.parser").get_text(" ", strip=True))
    print("Source:", feed.feed.get("source", "No Source"))
    print("Description:", feed.feed.get("description", "No Description"))
    print("===")

TAIPEI = ZoneInfo("Asia/Taipei")
today = dt.datetime.now(TAIPEI).date().isoformat()

print(today)