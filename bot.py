import os
import time
import requests
import traceback

# --- Configuration ---
TOKEN = os.environ.get("RUBIKA_TOKEN", "").strip()
if not TOKEN:
    print("FATAL: RUBIKA_TOKEN is empty.", flush=True)
    exit(1)

POLL_INTERVAL = 3                 # seconds
RUN_DURATION = 5 * 3600 + 55 * 60

PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

BASE = f"https://botapi.rubika.ir/v3/{TOKEN}"

def safe_post(url, json_data=None, retries=1, timeout=10):
    """Post with retries, returns response or None."""
    for attempt in range(retries + 1):
        try:
            if json_data is not None:
                resp = requests.post(url, json=json_data, proxies=proxies, timeout=timeout)
            else:
                resp = requests.post(url, proxies=proxies, timeout=timeout)
            return resp  # return even if error, we'll print status
        except Exception as e:
            print(f"[Attempt {attempt+1}] Exception: {e}", flush=True)
            time.sleep(2)
    return None

def get_updates(offset_id=None, limit=10):
    payload = {"limit": limit}
    if offset_id is not None:
        payload["offset_id"] = offset_id
    resp = safe_post(f"{BASE}/getUpdates", json_data=payload)
    if resp:
        return resp.status_code, resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
    return None, None

def send_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    resp = safe_post(f"{BASE}/sendMessage", json_data=payload, timeout=15)
    if resp and resp.status_code == 200:
        print(f"[OK] Echo to {chat_id}: {text}", flush=True)
    else:
        status = resp.status_code if resp else 'None'
        print(f"[FAIL] sendMessage status {status}", flush=True)

def main():
    start_time = time.time()
    print(f"Token: {TOKEN[:6]}...{TOKEN[-4:]}", flush=True)

    # Fetch latest offset
    status, data = get_updates(limit=1)
    if status == 200 and isinstance(data, dict):
        next_offset = data.get("next_offset_id")
        print(f"Initial offset set to: {next_offset}", flush=True)
    else:
        print(f"Initial getUpdates failed (status {status})", flush=True)
        next_offset = None

    print(f"Polling every {POLL_INTERVAL}s. Send a message now...", flush=True)

    while time.time() - start_time < RUN_DURATION:
        status, data = get_updates(offset_id=next_offset, limit=10)
        if status == 200 and isinstance(data, dict):
            updates = data.get("updates", [])
            new_offset = data.get("next_offset_id")
            # Always print the status for debugging
            print(f"[Poll] offset={next_offset} => {len(updates)} updates, next={new_offset}", flush=True)
            if updates:
                for upd in updates:
                    print(f"  Update: {upd.get('type')} from chat {upd.get('chat_id')}", flush=True)
                    if upd.get("type") == "NewMessage":
                        msg = upd.get("new_message", {})
                        txt = msg.get("text", "")
                        cid = upd.get("chat_id")
                        stype = msg.get("sender_type", "")
                        if stype == "User" and txt and cid:
                            send_message(cid, txt)
            if new_offset:
                next_offset = new_offset
        else:
            print(f"[Poll] getUpdates error: status={status}, data={str(data)[:200]}", flush=True)
            time.sleep(5)
            continue

        elapsed = time.time() - start_time
        if elapsed >= RUN_DURATION:
            break
        time.sleep(POLL_INTERVAL)

    print("Time limit reached. Exiting.", flush=True)

if __name__ == "__main__":
    main()
