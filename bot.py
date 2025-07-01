# bot.py - Main bot logic using Pyrogram

import asyncio
import os
from pyrogram import Client, filters
from extract import load_batches, search_batches, extract_batch_summary, extract_full_batch

BOT_TOKEN = os.getenv("BOT_TOKEN") or "7398473332:AAEuhO273fwXhuqxdzCcmmiOlkQgXSlmw_k"
API_ID = int(os.getenv("API_ID") or 15964777)  # Replace with your API ID
API_HASH = os.getenv("API_HASH") or "ef448f85b780cdf26f8ffe390a5d8262"

bot = Client("kgs_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# In-memory session cache
user_sessions = {}

@bot.on_message(filters.private & filters.text & ~filters.command(["start", "extract"]))
async def search_batch(client, message):
    query = message.text.strip()
    matches = search_batches(query)
    if not matches:
        await message.reply_text("❌ No matching batches found.")
        return

    session = []
    lines = [f"🔍 Found {len(matches)} results for \"{query}\":\n"]
    for i, (bid, name) in enumerate(matches):
        lines.append(f"{i}. {name} [ID: {bid}]")
        session.append((bid, name))

    user_sessions[message.chat.id] = session

    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > 4000:
            await message.reply_text(chunk)
            chunk = line + "\n"
        else:
            chunk += line + "\n"

    if chunk:
        chunk += "\nSend the index (e.g. 0 or 1) to select."
        await message.reply_text(chunk)

@bot.on_message(filters.private & filters.text & filters.regex("^\d+$"))
async def select_batch(client, message):
    index = int(message.text.strip())
    session = user_sessions.get(message.chat.id)
    if not session or index >= len(session):
        await message.reply_text("❌ Invalid selection.")
        return

    batch_id, batch_name = session[index]
    user_sessions[message.chat.id] = {"id": batch_id, "name": batch_name}

    summary_text = await extract_batch_summary(batch_id, batch_name)
    await message.reply_text(summary_text + "\n\nSend /extract to generate the file.")

@bot.on_message(filters.private & filters.command("extract"))
async def extract_command(client, message):
    session = user_sessions.get(message.chat.id)
    if not isinstance(session, dict):
        await message.reply_text("❌ No batch selected. Search and select a batch first.")
        return

    batch_id = session["id"]
    batch_name = session["name"]
    file_path, total = await extract_full_batch(batch_id, batch_name)

    await message.reply_document(file_path, caption=f"📦 Extracted {total} entries from {batch_name}!")
    os.remove(file_path)

if __name__ == "__main__":
    print("🚀 Bot running...")
    bot.run()
