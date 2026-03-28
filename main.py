import requests
import time
from telethon import TelegramClient, events
import asyncio

BOT_TOKEN = "8580596413:AAFTTuDMNY1lhs1FFA4aoRTmXdV5C60l5A0"
CHANNEL_ID = "@blockalerts"

api_id = 10709169
api_hash = "a3909ade4b5edd72fc884710bb80af3c"

KEYWORDS = [
    "hack", "exploit", "drained",
    "stolen", "freeze", "frozen",
    "scam", "bounty", "launder"
]


CHANNELS_TO_TRACK = [
    "zachxbt",
    "certik_alerts",
    "whale_alert_io"
]


client = TelegramClient("session", int(api_id), api_hash)


@client.on(events.NewMessage(chats=CHANNELS_TO_TRACK))
async def handler(event):
    text = event.message.message

    if not text:
        return

    if not is_relevant(text):
        return

    source = event.chat.username or "unknown"
    msg = format_alert(source, text)

    send_telegram(msg)
    print(f"[ALERT] {event.chat.username}")


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHANNEL_ID,
        "text": text
    })


def is_relevant(text):
    text = text.lower()
    return any(word in text for word in KEYWORDS)


def format_alert(user, content):
    import re

    # 🔥 extract money amount (if exists)
    money_match = re.search(r"\$[\d,.]+[MK]?", content)
    amount = money_match.group(0) if money_match else "Funds involved"

    # 🔥 basic cleanup
    clean = content.strip()

    return (
        f"⚠️ JUST IN: {amount} event detected\n\n"
        f"{clean}\n\n"
        f"Source: {user}"
    )


def run():
    print("🚀 Block Alerts (Telegram Mode) running...")
    client.start()
    client.run_until_disconnected()


if __name__ == "__main__":
    run()
