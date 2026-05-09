import os
import time
import requests

# --- Configuration ---
TOKEN = os.environ["RUBIKA_TOKEN"]                          # bot token
USER_GUID = "u0JWE2R02172d15a02bb742a785ac9f8"              # hardcoded GUID (your target user)
MESSAGE = "Bot is alive"
SEND_INTERVAL = 5 * 60                                      # 5 minutes
RUN_DURATION = 5 * 3600 + 55 * 60                           # 5h 55m

# Optional HTTP/HTTPS proxy for geo‑blocked environments
PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
# ---------------------

def send_message(text: str) -> bool:
    """Send a plain text message to USER_GUID using the Rubika Bot API."""
    url = f"https://botapi.rubika.ir/v3/{TOKEN}/sendMessage"
    payload = {
        "chat_id": USER_GUID,
        "text": text
    }
    try:
        resp = requests.post(url, json=payload, proxies=proxies, timeout=15)
        if resp.status_code == 200:
            print(f"[OK] Message sent: {text}", flush=True)
            return True
        else:
            print(f"[FAIL] HTTP {resp.status_code}: {resp.text}", flush=True)
            return False
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        return False

def test_connectivity():
    """Quick check: call getMe to verify token and reachability."""
    url = f"https://botapi.rubika.ir/v3/{TOKEN}/getMe"
    try:
        resp = requests.post(url, proxies=proxies, timeout=10)
        if resp.status_code == 200:
            print(f"[INFO] Token is valid! Bot: {resp.json().get('bot', {}).get('bot_title', 'unknown')}", flush=True)
            return True
        else:
            print(f"[INFO] getMe returned {resp.status_code}: {resp.text}", flush=True)
            return False
    except Exception as e:
        print(f"[INFO] getMe failed: {e}", flush=True)
        return False

def main():
    start = time.time()
    iteration = 0
    print("Bot started. Using official Rubika bot API.", flush=True)
    if proxies:
        print(f"Using proxy: {PROXY_URL}", flush=True)

    # Test token/connectivity once at startup
    if not test_connectivity():
        print("[WARN] Connectivity test failed. Will still try to send messages, but check your token/GUID/proxy.", flush=True)

    while time.time() - start < RUN_DURATION:
        iteration += 1
        elapsed = time.time() - start
        print(f"Iteration {iteration} at {time.strftime('%H:%M:%S')} (elapsed {int(elapsed)}s)", flush=True)
        send_message(MESSAGE)

        remaining = RUN_DURATION - elapsed
        if remaining <= 0:
            break
        sleep_for = min(SEND_INTERVAL, remaining)
        print(f"Sleeping for {int(sleep_for)} seconds...", flush=True)
        time.sleep(sleep_for)

    print("Time limit reached. Exiting cleanly.", flush=True)

if __name__ == "__main__":
    main()
