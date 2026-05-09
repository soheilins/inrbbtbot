import os
import time
import requests

# --- Configuration ---
TOKEN = os.environ["RUBIKA_TOKEN"]
USER_GUID = "YOUR_HARDCODED_USER_GUID"    # <-- change this to the real GUID
MESSAGE = "Bot is alive"
SEND_INTERVAL = 5 * 60                    # 5 minutes in seconds
RUN_DURATION = 5 * 3600 + 55 * 60         # 5 hours 55 minutes
# ---------------------

def send_message(token: str, chat_id: str, text: str) -> None:
    url = "https://messengerg2b1.iranlms.ir/sendMessage"
    payload = {
        "token": token,
        "object_guid": chat_id,
        "text": text,
    }
    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[OK] Message sent: {text}", flush=True)
        else:
            print(f"[FAIL] Status {resp.status_code}: {resp.text}", flush=True)
    except Exception as e:
        print(f"[ERROR] Exception while sending: {e}", flush=True)

def main():
    start = time.time()
    iteration = 0

    print("Bot started. Will run for 5h 55m, sending a message every 5 minutes.", flush=True)
    print(f"Target GUID: {USER_GUID}", flush=True)   # helpful for debugging

    # Quick connectivity test at the very start
    print("Testing connectivity to Rubika API...", flush=True)
    try:
        test = requests.get("https://messengerg2b1.iranlms.ir/", timeout=5)
        print(f"API reachable, status {test.status_code}", flush=True)
    except Exception as e:
        print(f"API unreachable: {e}", flush=True)

    while time.time() - start < RUN_DURATION:
        iteration += 1
        elapsed = time.time() - start
        print(f"Iteration {iteration} at {time.strftime('%H:%M:%S')} (elapsed {int(elapsed)}s)", flush=True)
        send_message(TOKEN, USER_GUID, MESSAGE)

        remaining = RUN_DURATION - elapsed
        if remaining <= 0:
            break
        sleep_for = min(SEND_INTERVAL, remaining)
        print(f"Sleeping for {int(sleep_for)} seconds...", flush=True)
        time.sleep(sleep_for)

    print("Time limit reached. Exiting cleanly.", flush=True)

if __name__ == "__main__":
    main()
