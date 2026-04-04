import requests
import time
import re
import logging
import os

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
level=logging.INFO,
format=”%(asctime)s [%(levelname)s] %(message)s”,
datefmt=”%Y-%m-%d %H:%M:%S”
)
log = logging.getLogger(**name**)

# ── Config ────────────────────────────────────────────────────────────────────

BOT_TOKEN   = os.environ.get(“BOT_TOKEN”, “8580596413:AAFTTuDMNY1lhs1FFA4aoRTmXdV5C60l5A0”)
CHANNEL_ID  = os.environ.get(“CHANNEL_ID”, “@blockalerts”)
CHANNEL_TAG = “@BlockAlerts”          # shown at bottom of every post

ACCOUNTS = [
“zachxbt”,
“PeckShieldAlert”,
“CertiKAlert”,
“lookonchain”,
“realScamSniffer”,
]

# Nitter public instances – tried in order, falls back if one is down

NITTER_INSTANCES = [
“https://nitter.privacydev.net”,
“https://nitter.poast.org”,
“https://nitter.cz”,
“https://nitter.1d4.us”,
]

KEYWORDS = [
“hack”, “exploit”, “drain”, “drained”, “stolen”, “steal”,
“breach”, “attack”, “scam”, “rug”, “phish”, “phishing”,
“freeze”, “frozen”, “blacklist”, “launder”, “laundering”,
“bounty”, “alert”, “warning”, “suspicious”, “compromise”,
“vulnerability”, “social engineering”, “just in”, “breaking”,
“transfer”, “moved”, “whale”, “million”, “billion”,
]

POLL_INTERVAL   = 90   # seconds between full cycles
BETWEEN_USERS   = 5    # seconds between each account request
REQUEST_TIMEOUT = 15   # seconds for HTTP requests

# ── State (in-memory; resets on redeploy – good enough for MVP) ───────────────

seen_ids: set[str] = set()

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_nitter_rss(username: str) -> str | None:
“”“Try each Nitter instance and return raw RSS XML, or None on total failure.”””
for base in NITTER_INSTANCES:
url = f”{base}/{username}/rss”
try:
r = requests.get(url, timeout=REQUEST_TIMEOUT, headers={
“User-Agent”: “Mozilla/5.0 (compatible; NewsBot/1.0)”
})
if r.status_code == 200 and “<rss” in r.text:
log.info(f”  ✅ Got RSS for @{username} via {base}”)
return r.text
else:
log.warning(f”  ⚠️  {base} returned {r.status_code} for @{username}”)
except Exception as e:
log.warning(f”  ⚠️  {base} failed: {e}”)
log.error(f”  ❌ All Nitter instances failed for @{username}”)
return None

def parse_rss(xml: str, username: str) -> list[dict]:
“”“Extract tweet items from RSS XML. Returns list of dicts.”””
tweets = []
items = re.findall(r”<item>(.*?)</item>”, xml, re.DOTALL)
for item in items:
# ID from guid
guid = re.search(r”<guid[^>]*>(.*?)</guid>”, item)
if not guid:
continue
tweet_id = guid.group(1).strip()

```
    # Text – strip CDATA and HTML tags
    desc = re.search(r"<description>(.*?)</description>", item, re.DOTALL)
    if not desc:
        continue
    raw = desc.group(1)
    raw = re.sub(r"<!\[CDATA\[|\]\]>", "", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"&amp;", "&", raw)
    raw = re.sub(r"&lt;", "<", raw)
    raw = re.sub(r"&gt;", ">", raw)
    raw = re.sub(r"&quot;", '"', raw)
    raw = re.sub(r"&#39;", "'", raw)
    text = re.sub(r"\s+", " ", raw).strip()

    # Link
    link = re.search(r"<link>(.*?)</link>", item)
    url = link.group(1).strip() if link else ""
    # Convert nitter link → twitter link
    for base in NITTER_INSTANCES:
        url = url.replace(base, "https://twitter.com")

    tweets.append({"id": tweet_id, "text": text, "url": url, "username": username})
return tweets
```

def is_relevant(tweet: dict) -> bool:
text = tweet[“text”].lower()
username = tweet[“username”].lower()

```
# Always pass these accounts – everything they post is signal
if username in ("zachxbt", "realscamsniffer"):
    return True

# Everyone else – keyword match
return any(kw in text for kw in KEYWORDS)
```

def extract_amount(text: str) -> str:
“”“Pull the first dollar amount from text, e.g. ‘$4.2M’.”””
m = re.search(r”$[\d,.]+\s*[MBKmb]?”, text)
return m.group(0).strip() if m else “”

def source_emoji(username: str) -> str:
mapping = {
“zachxbt”:         “🕵️”,
“peckshieldalert”: “🛡️”,
“certikalert”:     “🔐”,
“lookonchain”:     “🐋”,
“realscamsniffer”: “🚨”,
}
return mapping.get(username.lower(), “📡”)

def format_message(tweet: dict) -> str:
text     = tweet[“text”]
username = tweet[“username”]
url      = tweet[“url”]
amount   = extract_amount(text)
emoji    = source_emoji(username)

```
# Build header line
if amount:
    header = f"⚠️ JUST IN: {amount} event detected"
else:
    header = "⚠️ JUST IN: New Alert"

# Clean up text – remove trailing URLs that Nitter appends
body = re.sub(r"https?://\S+", "", text).strip()
# Limit length
if len(body) > 600:
    body = body[:597] + "..."

msg = (
    f"{header}\n\n"
    f"{body}\n\n"
    f"{emoji} Source: @{username}\n"
    f"🔗 {url}\n\n"
    f"{CHANNEL_TAG}"
)
return msg
```

def send_telegram(text: str) -> bool:
url = f”https://api.telegram.org/bot{BOT_TOKEN}/sendMessage”
payload = {
“chat_id”:    CHANNEL_ID,
“text”:       text,
“parse_mode”: “HTML”,
“disable_web_page_preview”: False,
}
try:
r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
if r.status_code == 200:
return True
else:
log.error(f”Telegram error {r.status_code}: {r.text}”)
return False
except Exception as e:
log.error(f”Telegram send failed: {e}”)
return False

# ── Main loop ─────────────────────────────────────────────────────────────────

def run_cycle():
log.info(“🔄 Starting new cycle…”)
new_posts = 0

```
for username in ACCOUNTS:
    log.info(f"📡 Fetching @{username}...")
    xml = get_nitter_rss(username)

    if not xml:
        time.sleep(BETWEEN_USERS)
        continue

    tweets = parse_rss(xml, username)
    log.info(f"  Found {len(tweets)} tweets")

    for tweet in tweets:
        if tweet["id"] in seen_ids:
            continue

        seen_ids.add(tweet["id"])

        if not is_relevant(tweet):
            log.info(f"  ⏭️  Skipped (not relevant): {tweet['text'][:60]}...")
            continue

        msg = format_message(tweet)
        success = send_telegram(msg)

        if success:
            new_posts += 1
            log.info(f"  ✅ Posted: {tweet['text'][:60]}...")
        else:
            log.warning(f"  ❌ Failed to post: {tweet['text'][:60]}...")

        time.sleep(2)  # small delay between posts so channel doesn't flood

    time.sleep(BETWEEN_USERS)

log.info(f"✅ Cycle done. {new_posts} new alerts posted.")
```

def main():
log.info(“🚀 BlockAlerts bot starting…”)
log.info(f”   Tracking: {’, ’.join(ACCOUNTS)}”)
log.info(f”   Posting to: {CHANNEL_ID}”)
log.info(f”   Poll interval: {POLL_INTERVAL}s”)

```
# Seed seen_ids on first run so we don't spam old tweets
log.info("🌱 Seeding seen tweet IDs (ignoring existing tweets)...")
for username in ACCOUNTS:
    xml = get_nitter_rss(username)
    if xml:
        tweets = parse_rss(xml, username)
        for t in tweets:
            seen_ids.add(t["id"])
    time.sleep(BETWEEN_USERS)
log.info(f"   Seeded {len(seen_ids)} existing tweet IDs. Only NEW tweets will be posted.")

while True:
    try:
        run_cycle()
    except Exception as e:
        log.error(f"💥 Cycle crashed: {e}")
    log.info(f"⏳ Sleeping {POLL_INTERVAL}s...\n")
    time.sleep(POLL_INTERVAL)
```

if **name** == “**main**”:
main()
