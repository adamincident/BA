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


def fetch_tweets(username):
    url = f"https://cdn.syndication.twimg.com/widgets/timelines/profile?screen_name={username}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return str(data)
    except:
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
