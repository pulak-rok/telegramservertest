import asyncio
from datetime import datetime, timezone, timedelta
import httpx

BOT_TOKEN = "token"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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
    second = now.second

    clock_emojis = ["🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚"]
    clock_icon = clock_emojis[hour % 12]

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
        f"<i>Send /stop to stop the clock</i>"
    )
    return text

async def run_clock(client, chat_id, stop_event):
    """Run clock forever until stop_event is set."""
    resp = await send_message(client, chat_id, format_clock())
    msg_id = resp.get("result", {}).get("message_id")
    if not msg_id:
        print("Failed to send initial message.")
        return

    while not stop_event.is_set():
        await asyncio.sleep(1)
        if stop_event.is_set():
            break
        await edit_message(client, chat_id, msg_id, format_clock())

    now = datetime.now(BD_TZ)
    stopped_text = (
        f"⏹ <b>Clock Stopped</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗓 <b>Date:</b> {now.strftime('%A, %d %B %Y')}\n"
        f"⏰ <b>Stopped at:</b> <code>{now.strftime('%I:%M:%S %p')}</code>\n"
        f"🌏 <b>Zone:</b> Bangladesh (UTC+6)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Send /clock to start again</i>"
    )
    await edit_message(client, chat_id, msg_id, stopped_text)
    print(f"Clock stopped for chat {chat_id}.")

async def main():
    print("Bot started.")
    print("Send /clock to start unlimited live clock.")
    print("Send /stop to stop it.")
    offset = None
    active_clocks = {}

    async with httpx.AsyncClient() as client:
        while True:
            try:
                data = await get_updates(client, offset)
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")

                    if not chat_id:
                        continue

                    if text.startswith("/clock"):
                        if chat_id in active_clocks:
                            active_clocks[chat_id]["stop_event"].set()
                            active_clocks[chat_id]["task"].cancel()

                        stop_event = asyncio.Event()
                        task = asyncio.create_task(run_clock(client, chat_id, stop_event))
                        active_clocks[chat_id] = {"task": task, "stop_event": stop_event}
                        print(f"Clock started for chat {chat_id}")

                    elif text.startswith("/stop"):
                        if chat_id in active_clocks and not active_clocks[chat_id]["task"].done():
                            active_clocks[chat_id]["stop_event"].set()
                            print(f"Stop requested for chat {chat_id}")
                        else:
                            await send_message(client, chat_id, "⚠️ No clock is running. Send /clock to start.")

            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main())
