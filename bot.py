import os
import time
import requests
import secrets

# --- Configuration ---
TOKEN = os.environ.get("RUBIKA_TOKEN", "").strip()
if not TOKEN:
    print("FATAL: RUBIKA_TOKEN is empty.", flush=True)
    exit(1)

POLL_INTERVAL = 3                 # seconds between polls
RUN_DURATION = 5 * 3600 + 55 * 60 # 5h 55m

OFFSET_FILE = "offset.txt"
ENC_OFFSET_FILE = "enc_offset.txt"
RANDOM_HEX_FILE = "random.txt"

MAGIC_PREFIX = "Ovagarava"

PROXY_URL = os.environ.get("PROXY_URL")
proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

BASE = f"https://botapi.rubika.ir/v3/{TOKEN}"

# Base32 alphabet
B32_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
B32_BASE = len(B32_ALPHABET)

# Fixed header lengths
OFFSET_B32_LEN = 8
LEN_B32_LEN = 3

# --- Helpers ---

def api_call(method, payload=None):
    url = f"{BASE}/{method}"
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, proxies=proxies, timeout=10)
            if "application/json" in resp.headers.get("content-type", ""):
                return resp.status_code, resp.json()
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
        print(f"[OK] Sent → {chat_id}: {text[:30]}...", flush=True)
    else:
        print(f"[FAIL] sendMessage {code}", flush=True)

def read_int_from_file(filename, default=0):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                val = f.read().strip()
                return int(val) if val else default
    except:
        pass
    return default

def write_int_to_file(filename, value):
    try:
        with open(filename, "w") as f:
            f.write(str(value))
    except Exception as e:
        print(f"Error writing {filename}: {e}", flush=True)

def base32_encode(number, pad_len=None):
    if number == 0:
        result = "0"
    else:
        result = []
        while number > 0:
            number, rem = divmod(number, B32_BASE)
            result.append(B32_ALPHABET[rem])
        result = ''.join(reversed(result))
    if pad_len:
        result = result.zfill(pad_len)
    return result

def base32_decode(b32_str):
    num = 0
    for ch in b32_str:
        num = num * B32_BASE + B32_ALPHABET.index(ch)
    return num

def text_to_hex(text):
    return text.encode("utf-8").hex().upper()

def hex_to_text(hex_str):
    return bytes.fromhex(hex_str).decode("utf-8")

# --- Encryption / Decryption ---

def encrypt(text, random_hex, enc_offset):
    H = text_to_hex(text)
    L = len(H)
    rand_len = len(random_hex)
    R = ''.join(random_hex[(enc_offset + i) % rand_len] for i in range(L))
    sum_int = int(H, 16) + int(R, 16)
    header = base32_encode(enc_offset, OFFSET_B32_LEN) + base32_encode(L, LEN_B32_LEN)
    sum_b32 = base32_encode(sum_int)
    encrypted = MAGIC_PREFIX + header + sum_b32
    new_offset = enc_offset + L
    return encrypted, new_offset

def decrypt(encrypted, random_hex):
    if not encrypted.startswith(MAGIC_PREFIX):
        return None
    payload = encrypted[len(MAGIC_PREFIX):]
    if len(payload) < OFFSET_B32_LEN + LEN_B32_LEN:
        return None
    off_str = payload[:OFFSET_B32_LEN]
    len_str = payload[OFFSET_B32_LEN:OFFSET_B32_LEN+LEN_B32_LEN]
    sum_b32 = payload[OFFSET_B32_LEN+LEN_B32_LEN:]
    if any(ch not in B32_ALPHABET for ch in off_str + len_str + sum_b32):
        return None
    try:
        offset = base32_decode(off_str)
        L = base32_decode(len_str)
        sum_int = base32_decode(sum_b32)
    except ValueError:
        return None
    rand_len = len(random_hex)
    R = ''.join(random_hex[(offset + i) % rand_len] for i in range(L))
    original_int = sum_int - int(R, 16)
    if original_int < 0:
        return None
    H = format(original_int, 'x').zfill(L).upper()
    try:
        return hex_to_text(H)
    except:
        return None

# --- Main bot ---

def main():
    start_time = time.time()
    print("Bot starting.", flush=True)

    # Token check
    code, info = api_call("getMe")
    if code == 200 and isinstance(info, dict):
        bot = info.get("data", {}).get("bot", {})
        print(f"Bot alive: {bot.get('bot_title', '?')} (@{bot.get('username', '?')})", flush=True)
    else:
        print("Warning: getMe failed, continuing.", flush=True)

    # Load or create random hex pad
    if not os.path.exists(RANDOM_HEX_FILE) or os.path.getsize(RANDOM_HEX_FILE) == 0:
        print("Creating random.txt...", flush=True)
        random_hex = secrets.token_hex(500_000)
        with open(RANDOM_HEX_FILE, "w") as f:
            f.write(random_hex)
        print("random.txt created.", flush=True)
    else:
        with open(RANDOM_HEX_FILE, "r") as f:
            random_hex = f.read().strip()
    if not random_hex:
        print("FATAL: random.txt empty.", flush=True)
        return

    # Load offsets
    next_offset_str = None
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE) as f:
            next_offset_str = f.read().strip() or None
    if not next_offset_str:
        code, data = api_call("getUpdates", {"limit": 1})
        if code == 200 and isinstance(data, dict):
            next_offset_str = data.get("data", {}).get("next_offset_id")
    enc_offset = read_int_from_file(ENC_OFFSET_FILE, 0)

    print(f"API offset: {next_offset_str}, enc offset: {enc_offset}", flush=True)

    # No startup message – bot remains silent

    try:
        while time.time() - start_time < RUN_DURATION:
            payload = {"limit": 10}
            if next_offset_str:
                payload["offset_id"] = next_offset_str

            code, data = api_call("getUpdates", payload)
            if code == 200 and isinstance(data, dict):
                inner = data.get("data", {})
                updates = inner.get("updates", [])
                new_offset_str = inner.get("next_offset_id")

                if updates:
                    print(f"Received {len(updates)} updates.", flush=True)
                    for upd in updates:
                        if upd.get("type") != "NewMessage":
                            continue
                        msg = upd.get("new_message", {})
                        if msg.get("sender_type") != "User":
                            continue
                        text = msg.get("text", "").strip()
                        chat_id = upd.get("chat_id")
                        if not text or not chat_id:
                            continue

                        if text.startswith(MAGIC_PREFIX):
                            # === DECRYPT ===
                            try:
                                decrypted = decrypt(text, random_hex)
                                if decrypted is not None:
                                    # Send only the original message, no "Decrypted:" label
                                    send_message(chat_id, decrypted)
                                else:
                                    send_message(chat_id, "❌ Invalid ciphertext.")
                            except Exception as e:
                                print(f"Decryption error: {e}", flush=True)
                                send_message(chat_id, "⚠️ Decryption failed.")
                        else:
                            # === ENCRYPT ===
                            try:
                                encrypted, enc_offset = encrypt(text, random_hex, enc_offset)
                                send_message(chat_id, encrypted)
                                write_int_to_file(ENC_OFFSET_FILE, enc_offset)
                            except Exception as e:
                                print(f"Encryption error: {e}", flush=True)
                                send_message(chat_id, "⚠️ Encryption failed.")

                # Save API offset after every poll
                if new_offset_str:
                    next_offset_str = new_offset_str
                    with open(OFFSET_FILE, "w") as f:
                        f.write(next_offset_str)
            else:
                print(f"[Poll] getUpdates error: {code} {data}", flush=True)
                time.sleep(5)
                continue

            elapsed = time.time() - start_time
            sleep_time = max(0, min(POLL_INTERVAL, RUN_DURATION - elapsed))
            time.sleep(sleep_time)
    finally:
        with open(OFFSET_FILE, "w") as f:
            f.write(next_offset_str or "")
        write_int_to_file(ENC_OFFSET_FILE, enc_offset)
        print("Bot shutting down.", flush=True)

if __name__ == "__main__":
    main()
