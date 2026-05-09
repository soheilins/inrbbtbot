import os
import time
import requests
import traceback

# --- Configuration ---
TOKEN = os.environ.get("RUBIKA_TOKEN", "")
if not TOKEN:
    print("FATAL: RUBIKA_TOKEN environment variable is empty or not set.", flush=True)
    exit(1)

MESSAGE_POLL_INTERVAL = 3          # seconds between getUpdates calls
RUN_DURATION = 5 * 3600 + 55 * 60  # 5 hours 55 minutes

PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

BASE_URL = f"https://botapi.rubika.ir/v3/{TOKEN}"
# ---------------------

def get_me():
    """Return bot info dict or None on failure."""
    try:
        url = f"{BASE_URL}/getMe"
        print(f"DEBUG getMe URL: {url[:50]}...", flush=True)
        resp = requests.post(url, proxies=proxies, timeout=10)
        print(f"DEBUG getMe status: {resp.status_code}", flush=True)
        if resp.status_code == 200:
            return resp.json().get("bot", {})
        else:
            print(f"getMe non-200: {resp.text}", flush=True)
    except Exception as e:
        print(f"getMe exception: {e}", flush=True)
    return None

def get_updates(offset_id: str | None = None, limit: int = 10) -> dict | None:
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
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, proxies=proxies, timeout=15)
        if resp.status_code == 200:
            print(f"[OK] Echo → {chat_id}: {text}", flush=True)
            return True
        else:
            print(f"[FAIL] sendMessage {resp.status_code}: {resp.text}", flush=True)
    except Exception:
        print(f"sendMessage exception: {traceback.format_exc()}", flush=True)
    return False

def main():
    start_time = time.time()
    print(f"Bot starting. Token prefix: {TOKEN[:4]}... suffix: ...{TOKEN[-4:]}", flush=True)

    # Verify token
    bot_info = get_me()
    if not bot_info:
        print("FATAL: getMe failed. Check token, network, or proxy.", flush=True)
        return

    bot_id = bot_info.get("bot_id", "")
    print(f"Bot online: {bot_info.get('bot_title', 'Unknown')} (@{bot_info.get('username', '?'))}", flush=True)

    # Skip old messages
    initial = get_updates(limit=1)
    next_offset = initial.get("next_offset_id") if initial else None
    print(f"Start offset: {next_offset}. Polling every {MESSAGE_POLL_INTERVAL}s.", flush=True)

    # Main loop
    while time.time() - start_time < RUN_DURATION:
        data = get_updates(offset_id=next_offset, limit=10)
        if data:
            updates = data.get("updates", [])
            new_offset = data.get("next_offset_id")
            if updates:
                print(f"Got {len(updates)} updates.", flush=True)
            for upd in updates:
                if upd.get("type") != "NewMessage":
                    continue
                msg = upd.get("new_message", {})
                sender_id = msg.get("sender_id")
                text = msg.get("text", "")
                chat_id = upd.get("chat_id")

                if sender_id == bot_id or not text or not chat_id:
                    continue
                # Echo the message
                send_message(chat_id, text)

            if new_offset:
                next_offset = new_offset
        else:
            time.sleep(5)
            continue

        elapsed = time.time() - start_time
        remain = max(0, RUN_DURATION - elapsed)
        time.sleep(min(MESSAGE_POLL_INTERVAL, remain))

    print("Run duration ended. Shutting down.", flush=True)

if __name__ == "__main__":
    main()
