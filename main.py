import requests
import time

BOT_TOKEN = "8580596413:AAFTTuDMNY1lhs1FFA4aoRTmXdV5C60l5A0"
CHANNEL_ID = "@blockalerts"

TWITTER_USERS = [
    "zachxbt",
    "certik",
    "whale_alert"
]

KEYWORDS = [
    "hack", "exploit", "drained",
    "stolen", "freeze", "frozen",
    "scam", "bounty", "launder"
]

LAST_SEEN = {}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHANNEL_ID,
        "text": text
    })


import snscrape.modules.twitter as sntwitter

def fetch_tweets(username):
    try:
        tweets = []

        for i, tweet in enumerate(sntwitter.TwitterUserScraper(username).get_items()):
            if i >= 1:  # only latest tweet
                break
            tweets.append(tweet.content)

        return tweets[0] if tweets else ""

    except Exception as e:
        print(f"[SCRAPE ERROR] {username} {e}")
        return ""


def is_relevant(text):
    text = text.lower()
    return any(word in text for word in KEYWORDS)


def format_alert(username, text):
    return f"""⚠️ JUST IN:

{text[:200]}...

@{username}
"""


def run():
    print("🚀 Block Alerts running...")

    while True:
        for user in TWITTER_USERS:
            content = fetch_tweets(user)

            if not content:
                continue

            if LAST_SEEN.get(user) == content:
                continue

            LAST_SEEN[user] = content

            if is_relevant(content):
                msg = format_alert(user, content)
                send_telegram(msg)
                print(f"[ALERT] {user}")

        time.sleep(30)


if __name__ == "__main__":
    run()
