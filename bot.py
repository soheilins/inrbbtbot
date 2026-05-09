import os
import time
import requests
import traceback

# --- Configuration ---
TOKEN = os.environ.get("RUBIKA_TOKEN", "").strip()
if not TOKEN:
    print("FATAL: RUBIKA_TOKEN is empty.", flush=True)
    exit(1)

POLL_INTERVAL = 3                 # seconds between getUpdates calls
RUN_DURATION = 5 * 3600 + 55 * 60 # 5h 55m

PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

BASE = f"https://botapi.rubika.ir/v3/{TOKEN}"

# --- Helper functions ---
def safe_post(url, json_data=None, retries=2, timeout=10):
    """Wrapper with retries."""
    for attempt in range(retries + 1):
        try:
            if json_data is not None:
                resp = requests.post(url, json=json_data, proxies=proxies, timeout=timeout)
            else:
                resp = requests.post(url, proxies=proxies, timeout=timeout)
            if resp.status_code == 200:
                return resp
            print(f"[Attempt {attempt+1}] Status {resp.status_code}: {resp.text[:200]}", flush=True)
        except Exception as e:
            print(f"[Attempt {attempt+1}] Exception: {e}", flush=True)
        if attempt < retries:
            time.sleep(2)
    return None

def get_me():
    """Fetch bot info (tolerant to failure)."""
    resp = safe_post(f"{BASE}/getMe")
    if resp:
        return resp.json().get("bot", {})
    return {}

def get_updates(offset_id=None, limit=10):
    payload = {"limit": limit}
    if offset_id is not None:
        payload["offset_id"] = offset_id
    resp = safe_post(f"{BASE}/getUpdates", json_data=payload)
    if resp:
        return resp.json()
    return None

def send_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    resp = safe_post(f"{BASE}/sendMessage", json_data=payload, timeout=15)
    if resp:
        print(f"[OK] Echo to {chat_id}: {text}", flush=True)
        return True
    else:
        print(f"[FAIL] sendMessage failed.", flush=True)
        return False

# --- Main ---
def main():
    start_time = time.time()
    print(f"Bot starting. Token prefix: {TOKEN[:6]}... suffix: ...{TOKEN[-4:]}", flush=True)

    # Try getMe, but continue anyway
    bot_info = get_me()
    if bot_info:
        # FIXED: removed extra parenthesis after '?'  → now valid f-string
        print(f"Bot is alive: {bot_info.get('bot_title', 'Unknown')} (@{bot_info.get('username', '?')})", flush=True)
    else:
        print("WARNING: getMe failed. Will still attempt to poll and reply.", flush=True)

    # Skip old messages (get latest offset)
    initial = get_updates(limit=1)
    next_offset = initial.get("next_offset_id") if initial else None
    print(f"Start offset: {next_offset}. Polling every {POLL_INTERVAL}s.", flush=True)

    while time.time() - start_time < RUN_DURATION:
        data = get_updates(offset_id=next_offset, limit=10)
        if data:
            updates = data.get("updates", [])
            new_offset = data.get("next_offset_id")
            if updates:
                print(f"Received {len(updates)} update(s).", flush=True)
            for upd in updates:
                if upd.get("type") != "NewMessage":
                    continue
                msg = upd.get("new_message", {})
                sender_type = msg.get("sender_type")     # "User" or "Bot"
                text = msg.get("text", "")
                chat_id = upd.get("chat_id")

                # Only reply to users, ignore bots (including self)
                if sender_type == "User" and text and chat_id:
                    send_message(chat_id, text)

            if new_offset:
                next_offset = new_offset
        else:
            # getUpdates failed, wait a bit longer
            time.sleep(5)
            continue

        elapsed = time.time() - start_time
        sleep_time = min(POLL_INTERVAL, max(0, RUN_DURATION - elapsed))
        time.sleep(sleep_time)

    print("Time limit reached. Exiting.", flush=True)

if __name__ == "__main__":
    main()
