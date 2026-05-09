import os
import time
import requests

# --- Configuration ---
TOKEN = os.environ["RUBIKA_TOKEN"]            # from GitHub secret
USER_GUID = "u0JWE2R02172d15a02bb742a785ac9f8"        # replace with the recipient's object_guid
MESSAGE = "Bot is alive"                      # text to send
SEND_INTERVAL = 5 * 1                        # 5 minutes in seconds
RUN_DURATION = 5 * 3600 + 55 * 60             # 5 hours 55 minutes (21300 seconds)
# ---------------------

def send_message(token: str, chat_id: str, text: str) -> None:
    """Send a text message via Rubika Bot API."""
    url = "https://messengerg2b1.iranlms.ir/sendMessage"
    payload = {
        "token": token,
        "object_guid": chat_id,
        "text": text,
    }
    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[OK] Message sent: {text}")
        else:
            print(f"[FAIL] Status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Exception while sending: {e}")

def main():
    start = time.time()
    iteration = 0

    print("Bot started. Will run for 5h 55m, sending a message every 5 minutes.")
    while time.time() - start < RUN_DURATION:
        iteration += 1
        print(f"Iteration {iteration} at {time.strftime('%H:%M:%S')}")
        send_message(TOKEN, USER_GUID, MESSAGE)

        # Sleep, but account for the time already spent in this iteration
        elapsed = time.time() - start
        remaining_in_loop = RUN_DURATION - elapsed
        if remaining_in_loop <= 0:
            break
        sleep_time = min(SEND_INTERVAL, remaining_in_loop)
        time.sleep(sleep_time)

    print(f"Time limit reached ({RUN_DURATION}s). Exiting cleanly.")

if __name__ == "__main__":
    main()
