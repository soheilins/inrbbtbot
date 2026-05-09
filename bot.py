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
OFFSET_FILE = "offset.txt"        # persistent offset

PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

BASE = f"https://botapi.rubika.ir/v3/{TOKEN}"

# Encryption settings – change BASE_OUT to 32 if you prefer base32
BASE_OUT = 16                     # output base (16 = hex, 32 = Base32)
# For base32 you may want a custom alphabet; this uses Python's built-in int→string conversion.
# Add a custom alphabet if desired.

# --- Helper functions ---
def api_call(method, payload=None):
    """Send a POST request. Returns (status_code, json_data_or_text)."""
    url = f"{BASE}/{method}"
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, proxies=proxies, timeout=10)
            ct = resp.headers.get("content-type", "")
            if "application/json" in ct:
                return resp.status_code, resp.json()
            else:
                return resp.status_code, resp.text
        except Exception as e:
            if attempt == 2:
                print(f"[{method}] Exception: {e}", flush=True)
                return None, str(e)
            time.sleep(2)
    return None, "unknown"

def send_message(chat_id, text):
    code, _ = api_call("sendMessage", {"chat_id": chat_id, "text": text})
    if code == 200:
        print(f"[OK] Sent → {chat_id}: {text[:50]}{'...' if len(text)>50 else ''}", flush=True)
    else:
        print(f"[FAIL] sendMessage {code}", flush=True)

def read_offset():
    try:
        if os.path.exists(OFFSET_FILE):
            with open(OFFSET_FILE, "r") as f:
                offset = f.read().strip()
                if offset:
                    print(f"Loaded offset: {offset}", flush=True)
                    return offset
    except Exception as e:
        print(f"Error reading offset: {e}", flush=True)
    return None

def write_offset(offset):
    try:
        with open(OFFSET_FILE, "w") as f:
            f.write(offset)
        # No log here to avoid flooding; only log when changed significantly if needed
    except Exception as e:
        print(f"Error writing offset: {e}", flush=True)

def text_to_binary_string(text: str) -> str:
    """Convert any string to a continuous binary string (UTF-8, no spaces)."""
    utf8_bytes = text.encode("utf-8")
    bits = ''.join(f'{byte:08b}' for byte in utf8_bytes)
    return bits

def encrypt_message(text: str, base: int = 16) -> str:
    """
    Encrypt text to a base representation.
    Process:
        text → UTF-8 bytes → binary string → integer → base-N string.
    """
    if not text:
        return ""
    bits = text_to_binary_string(text)
    # Convert the binary string to a large integer
    big_int = int(bits, 2)
    # Convert that integer to the desired base (uppercase)
    if base == 16:
        return hex(big_int)[2:].upper()   # remove '0x'
    else:
        # Custom base conversion (supports 2-36 with default alphabet)
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if base > len(alphabet):
            raise ValueError(f"Base {base} not supported with default alphabet")
        if big_int == 0:
            return "0"
        digits = []
        while big_int:
            big_int, rem = divmod(big_int, base)
            digits.append(alphabet[rem])
        return ''.join(reversed(digits))

def main():
    start_time = time.time()
    print(f"Bot token: {TOKEN[:6]}...{TOKEN[-4:]}", flush=True)

    # Check connectivity
    code, info = api_call("getMe")
    if code == 200 and isinstance(info, dict):
        bot = info.get("data", {}).get("bot", {})
        print(f"Bot alive: {bot.get('bot_title', '?')} (@{bot.get('username', '?')})", flush=True)
    else:
        print("Warning: getMe failed, continuing.", flush=True)

    # Startup ping
    send_message("b0JWE2R0cIy0e6f15e772458eede5497", "Encryption bot online. Send me any text.")

    # Load offset
    next_offset = read_offset()
    if not next_offset:
        code, data = api_call("getUpdates", {"limit": 1})
        if code == 200 and isinstance(data, dict):
            next_offset = data.get("data", {}).get("next_offset_id")
            print(f"No saved offset. Starting from: {next_offset}", flush=True)
        else:
            print("Could not get initial offset.", flush=True)
            next_offset = None

    print(f"Polling every {POLL_INTERVAL}s. Output base: {BASE_OUT}", flush=True)

    try:
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
                            # Encrypt and send
                            try:
                                encrypted = encrypt_message(text, BASE_OUT)
                                send_message(chat_id, encrypted)
                            except Exception as e:
                                print(f"Encryption error: {e}", flush=True)
                                send_message(chat_id, "⚠️ Encryption failed.")

                if new_offset:
                    next_offset = new_offset
                    write_offset(next_offset)   # save after every poll
            else:
                print(f"[Poll] getUpdates error: {code} {data}", flush=True)
                time.sleep(5)
                continue

            elapsed = time.time() - start_time
            sleep_time = max(0, min(POLL_INTERVAL, RUN_DURATION - elapsed))
            time.sleep(sleep_time)
    finally:
        if next_offset:
            write_offset(next_offset)
        print("Bot shutting down.", flush=True)

if __name__ == "__main__":
    main()
