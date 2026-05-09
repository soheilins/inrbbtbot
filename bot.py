import os
import time
import requests
import traceback

# --- Configuration ---
TOKEN = os.environ["RUBIKA_TOKEN"]               # bot token from @BotFather
MESSAGE_POLL_INTERVAL = 3                        # seconds between getUpdates calls
RUN_DURATION = 5 * 3600 + 55 * 60                # 5 hours 55 minutes

# Optional proxy (set PROXY_URL secret if needed)
PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

BASE_URL = f"https://botapi.rubika.ir/v3/{TOKEN}"
# ---------------------

def get_me():
    """Return bot info dict or None."""
    try:
        resp = requests.post(f"{BASE_URL}/getMe", proxies=proxies, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("bot", {})
    except Exception:
        pass
    return None

def get_updates(offset_id: str | None = None, limit: int = 10) -> dict | None:
    """Fetch new updates. Pass offset_id to get only newer ones."""
    payload = {"limit": limit}
    if offset_id is not None:
        payload["offset_id"] = offset_id
    try:
        resp = requests.post(f"{BASE_URL}/getUpdates", json=payload, proxies=proxies, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"getUpdates error {resp.status_code}: {resp.text}", flush=True)
    except Exception:
        print(f"getUpdates exception: {traceback.format_exc()}", flush=True)
    return None

def send_message(chat_id: str, text: str) -> bool:
    """Send a text message to a chat."""
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, proxies=proxies, timeout=15)
        if resp.status_code == 200:
            print(f"[OK] Replied to {chat_id}: {text}", flush=True)
            return True
        else:
            print(f"[FAIL] sendMessage {resp.status_code}: {resp.text}", flush=True)
    except Exception:
        print(f"sendMessage exception: {traceback.format_exc()}", flush=True)
    return False

def main():
    start_time = time.time()

    # Verify token
    bot_info = get_me()
    if not bot_info:
        print("FATAL: Unable to verify bot token. Exiting.", flush=True)
        return
    bot_id = bot_info.get("bot_id", "")
    print(f"Bot online: {bot_info.get('bot_title', 'Unknown')} (@{bot_info.get('username', 'unknown')})", flush=True)

    next_offset = None   # start without offset to get all pending messages (or we could start from latest)
    # To avoid processing very old messages, we could first fetch once with limit=1 to get the latest offset,
    # then use that as starting point. But the user might want old messages replied to? Usually no.
    # We'll fetch the latest update's offset_id and start after that.
    initial = get_updates(limit=1)
    if initial and initial.get("updates"):
        # take the last (most recent) update's message_id? No, next_offset_id tells us the next offset.
        next_offset = initial.get("next_offset_id")
    print(f"Starting echo loop. Polling every {MESSAGE_POLL_INTERVAL}s for {RUN_DURATION//3600}h{(RUN_DURATION%3600)//60}m.", flush=True)

    while time.time() - start_time < RUN_DURATION:
        # Fetch updates since last offset
        data = get_updates(offset_id=next_offset, limit=10)
        if data:
            updates = data.get("updates", [])
            new_offset = data.get("next_offset_id")
            if updates:
                print(f"Received {len(updates)} update(s).", flush=True)
            for upd in updates:
                # Process only NewMessage type with text
                if upd.get("type") == "NewMessage":
                    msg = upd.get("new_message", {})
                    sender_type = msg.get("sender_type")
                    sender_id = msg.get("sender_id")
                    text = msg.get("text", "")
                    chat_id = upd.get("chat_id")

                    # Don't reply to our own bot messages
                    if sender_id == bot_id:
                        continue
                    # Only reply to user messages (skip unknown types)
                    if sender_type == "User" and text and chat_id:
                        # Echo the text back
                        send_message(chat_id, text)
            if new_offset:
                next_offset = new_offset  # advance the cursor
        else:
            # If get_updates fails, wait a bit and retry
            time.sleep(5)
            continue

        # Sleep for the remaining poll interval (accounting for request time)
        elapsed = time.time() - start_time
        remain = RUN_DURATION - elapsed
        sleep_time = min(MESSAGE_POLL_INTERVAL, remain)
        if sleep_time > 0:
            time.sleep(sleep_time)

    print("Run time limit reached. Echo bot shutting down.", flush=True)

if __name__ == "__main__":
    main()
