import os
import time
import requests

# --- Configuration ---
TOKEN = os.environ.get("RUBIKA_TOKEN", "").strip()
if not TOKEN:
    print("FATAL: RUBIKA_TOKEN is empty.", flush=True)
    exit(1)

POLL_INTERVAL = 3                 # seconds between polls
RUN_DURATION = 5 * 3600 + 55 * 60 # 5 hours 55 minutes

PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

BASE = f"https://botapi.rubika.ir/v3/{TOKEN}"

def api_call(method, payload=None):
    """Send a POST request to the Rubika API. Returns (status_code, json_data_or_text)."""
    url = f"{BASE}/{method}"
    for attempt in range(3):  # 3 retries
        try:
            resp = requests.post(url, json=payload, proxies=proxies, timeout=10)
            ct = resp.headers.get("content-type", "")
            if "application/json" in ct:
                return resp.status_code, resp.json()
            else:
                return resp.status_code, resp.text
        except Exception as e:
            if attempt == 2:
                print(f"[{method}] Exception after retries: {e}", flush=True)
                return None, str(e)
            time.sleep(2)
    return None, "unknown error"

def send_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    code, data = api_call("sendMessage", payload)
    if code == 200:
        print(f"[OK] Echo → {chat_id}: {text}", flush=True)
    else:
        print(f"[FAIL] sendMessage ({code}): {data}", flush=True)

def main():
    start_time = time.time()
    print(f"Bot token: {TOKEN[:6]}...{TOKEN[-4:]}", flush=True)

    # Test connectivity and get current offset to skip old messages
    code, info = api_call("getMe")
    if code == 200 and isinstance(info, dict):
        bot = info.get("data", {}).get("bot", {})
        print(f"Bot is alive: {bot.get('bot_title', '?')} (@{bot.get('username', '?')})", flush=True)
    else:
        print(f"Warning: getMe failed ({code}), but will continue.", flush=True)

    # Send a startup ping so the user knows the bot is online (use your chat_id)
    send_message("b0JWE2R0cIy0e6f15e772458eede5497", "Echo bot is online. Reply to me!")

    # Get latest offset to avoid processing old messages
    code, data = api_call("getUpdates", {"limit": 1})
    if code == 200 and isinstance(data, dict):
        inner = data.get("data", {})
        next_offset = inner.get("next_offset_id")
        print(f"Starting offset: {next_offset}", flush=True)
    else:
        print("Could not fetch initial offset, starting without (may re-echo old messages).", flush=True)
        next_offset = None

    print("Listening for messages...", flush=True)

    while time.time() - start_time < RUN_DURATION:
        payload = {"limit": 10}
        if next_offset:
            payload["offset_id"] = next_offset

        code, data = api_call("getUpdates", payload)
        if code == 200 and isinstance(data, dict):
            inner = data.get("data", {})
            updates = inner.get("updates", [])
            new_offset = inner.get("next_offset_id")

            if updates:
                print(f"Received {len(updates)} update(s)", flush=True)
                for upd in updates:
                    if upd.get("type") != "NewMessage":
                        continue
                    msg = upd.get("new_message", {})
                    if msg.get("sender_type") != "User":
                        continue
                    text = msg.get("text", "")
                    chat_id = upd.get("chat_id")
                    if text and chat_id:
                        send_message(chat_id, text)

            if new_offset:
                next_offset = new_offset
        else:
            print(f"[Poll] getUpdates error: {code} {data}", flush=True)
            time.sleep(5)
            continue

        elapsed = time.time() - start_time
        sleep_time = min(POLL_INTERVAL, max(0, RUN_DURATION - elapsed))
        time.sleep(sleep_time)

    print("Time limit reached. Exiting.", flush=True)

if __name__ == "__main__":
    main()
