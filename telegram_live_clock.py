import asyncio
import time
from datetime import datetime, timezone, timedelta
import httpx

BOT_TOKEN = "8906330737:AAHoSB6YZXCTGEqkuKeVYACgJqhyefvb3Vk"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Bangladesh timezone (UTC+6)
BD_TZ = timezone(timedelta(hours=6))

async def get_updates(client, offset=None):
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    r = await client.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
    return r.json()

async def send_message(client, chat_id, text):
    r = await client.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })
    return r.json()

async def edit_message(client, chat_id, message_id, text):
    try:
        r = await client.post(f"{BASE_URL}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        })
        return r.json()
    except Exception:
        return None

def format_clock():
    now = datetime.now(BD_TZ)
    hour = now.hour
    minute = now.minute
    second = now.second

    # Clock emoji hands (rough approximation)
    clock_emojis = ["🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚"]
    clock_icon = clock_emojis[hour % 12]

    # Progress bar for seconds (0-59)
    filled = int(second / 59 * 20)
    bar = "█" * filled + "░" * (20 - filled)

    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M:%S %p")

    text = (
        f"{clock_icon} <b>LIVE CLOCK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗓 <b>Date:</b> {date_str}\n"
        f"⏰ <b>Time:</b> <code>{time_str}</code>\n"
        f"🌏 <b>Zone:</b> Bangladesh (UTC+6)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"[{bar}]\n"
        f"<i>Updates every second...</i>"
    )
    return text

async def run_clock(client, chat_id, duration=60):
    """Run a live clock for `duration` seconds in a single message."""
    # Send initial message
    resp = await send_message(client, chat_id, format_clock())
    msg_id = resp.get("result", {}).get("message_id")
    if not msg_id:
        print("Failed to send initial message.")
        return

    for _ in range(duration - 1):
        await asyncio.sleep(1)
        await edit_message(client, chat_id, msg_id, format_clock())

    # Final message
    await asyncio.sleep(1)
    now = datetime.now(BD_TZ)
    final = format_clock() + f"\n\n✅ <b>Clock stopped after {duration}s.</b>"
    await edit_message(client, chat_id, msg_id, final)
    print(f"Clock finished for chat {chat_id}.")

async def main():
    print("Bot started. Send /clock to any chat to start a 60-second live clock.")
    offset = None
    active_clocks = {}  # chat_id -> task

    async with httpx.AsyncClient() as client:
        while True:
            try:
                data = await get_updates(client, offset)
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")

                    if chat_id and text.startswith("/clock"):
                        # Parse optional duration: /clock 120
                        parts = text.split()
                        duration = 60
                        if len(parts) > 1:
                            try:
                                duration = max(5, min(int(parts[1]), 300))
                            except ValueError:
                                pass

                        # Cancel existing clock for this chat if running
                        if chat_id in active_clocks and not active_clocks[chat_id].done():
                            active_clocks[chat_id].cancel()

                        print(f"Starting {duration}s clock for chat {chat_id}")
                        task = asyncio.create_task(run_clock(client, chat_id, duration))
                        active_clocks[chat_id] = task

            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main())
