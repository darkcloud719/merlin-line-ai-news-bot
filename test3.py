from bs4 import BeautifulSoup

summary_html = '<p>AI news summary</p><a href="xxx">Read more</a>123'

soup = BeautifulSoup(summary_html, "html.parser")

summary_text = soup.get_text("", strip=True)

print(summary_text)