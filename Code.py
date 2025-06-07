import os
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes
)
from aiohttp import web

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8022455169:AAGCagv263tYQUhxdABxwhwyad16AJmMU8M")
PORT = int(os.environ.get("PORT", "8080"))
APP_URL = os.environ.get("APP_URL")  # e.g. https://your-app.onrender.com

DATA_DIR = "user_data"
USERS_FILE = os.path.join(DATA_DIR, "all_users.json")
os.makedirs(DATA_DIR, exist_ok=True)

def get_user_file(user_id):
    return os.path.join(DATA_DIR, f"{user_id}.json")

def load_user_data(user_id):
    fp = get_user_file(user_id)
    if os.path.exists(fp):
        with open(fp, "r") as f:
            return json.load(f)
    return {"list": [], "date": "", "next_insert_index": 0}

def save_user_data(user_id, data):
    with open(get_user_file(user_id), "w") as f:
        json.dump(data, f, indent=2)

def load_all_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_all_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f, indent=2)

def clean_list(lines):
    cleaned = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln[0].isdigit():
            parts = ln.split()
            serial = int(parts[0].rstrip("."))
            if len(parts) == 1 or "del" in ln.lower():
                cleaned.append({"serial": serial, "value": "deleted"})
            else:
                cleaned.append({"serial": serial, "value": parts[-1]})
    return cleaned

def format_show_done_output(data):
    date_text = data["date"].lstrip("List Of")
    lines = [
        f"**List Of {date_text}**",
        "",
        "**MUNNA BHAIYA GIVEAWAY**",
        ""
    ]
    for item in data["list"]:
        val = re.sub(r"\b([A-Za-z0-9]{9})\b", r"`\1`", item["value"])
        lines.append(f"{item['serial']}.   {val}")
        lines.append("")
    return "\n".join(lines)

INLINE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 List", callback_data="list"),
     InlineKeyboardButton("👀 Show", callback_data="show")]
])

user_states = {}

# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = load_all_users()
    if uid not in users:
        users.add(uid)
        save_all_users(users)
    await update.message.reply_text(
        "👋 *Welcome!*  Commands: 📋 List  🔤 Mono  👀 Show\nTap a button below to begin.",
        reply_markup=INLINE_KB,
        parse_mode="Markdown"
    )

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user_states[uid] = {"mode": "waiting_for_date"}
    await update.message.reply_text("```Pehle date bhejiye``` (e.g., 14 May):", reply_markup=INLINE_KB, parse_mode="Markdown")

async def mono_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user_states[uid] = {"mode": "mono_mode"}
    await update.message.reply_text("```Send the list``` — mono format (9-digit codes) with 1 line gap.", reply_markup=INLINE_KB, parse_mode="Markdown")

async def show_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_user_data(uid)
    if not data["list"]:
        await update.message.reply_text("```Koi list stored nahi hai.```", reply_markup=INLINE_KB, parse_mode="Markdown")
        return
    out = format_show_done_output(data)
    await update.message.reply_text(f"```\n{out}```", reply_markup=INLINE_KB, parse_mode="Markdown")

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    save_user_data(uid, {"list": [], "date": "", "next_insert_index": 0})
    await update.message.reply_text("```List reset kar diya gaya hai.```", reply_markup=INLINE_KB, parse_mode="Markdown")

async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user_states[uid] = {"mode": "waiting_for_add_details"}
    await update.message.reply_text(
        "Send me your all details (5 lines):\nCODE AMOUNT\nCHANNEL\nTOTAL\nDATE\nID",
        reply_markup=INLINE_KB
    )

async def inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = str(query.from_user.id)
    await query.answer()
    if query.data == "list":
        user_states[uid] = {"mode": "waiting_for_date"}
        await query.edit_message_text("```Pehle date bhejiye``` (e.g., 14 May):", reply_markup=INLINE_KB, parse_mode="Markdown")
    elif query.data == "show":
        data = load_user_data(uid)
        if not data["list"]:
            await query.edit_message_text("```Koi list stored nahi hai.```", reply_markup=INLINE_KB, parse_mode="Markdown")
        else:
            out = format_show_done_output(data)
            await query.edit_message_text(f"```\n{out}```", reply_markup=INLINE_KB, parse_mode="Markdown")

# ---------- Message Handler ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = str(msg.from_user.id)
    txt = msg.text.strip()

    if txt.startswith("/"):
        return

    users = load_all_users()
    if uid not in users:
        users.add(uid)
        save_all_users(users)

    st = user_states.get(uid, {})

    if st.get("mode") == "mono_mode":
        user_states.pop(uid, None)
        formatted = "\n\n".join(
            [re.sub(r"\b([A-Za-z0-9]{9})\b", r"`\1`", l.strip()) for l in txt.splitlines() if l.strip()]
        )
        await msg.reply_text(f"```\n{formatted}```", reply_markup=INLINE_KB, parse_mode="Markdown")
        return

    if st.get("mode") == "waiting_for_date":
        user_states[uid] = {"mode": "waiting_for_list", "temp_date": txt}
        await msg.reply_text("```Ab apna list bhejiye``` (multi-line format):", reply_markup=INLINE_KB, parse_mode="Markdown")
        return

    if st.get("mode") == "waiting_for_list":
        user_states.pop(uid, None)
        cleaned = clean_list(txt.splitlines())
        save_user_data(uid, {"list": cleaned, "date": st["temp_date"], "next_insert_index": 0})
        await msg.reply_text(f"{len(cleaned)} serials store kiya gaya.\nAb code + number bhejiye.", reply_markup=INLINE_KB)
        return

    if st.get("mode") == "waiting_for_add_details":
        user_states.pop(uid, None)
        lines = txt.strip().split("\n")
        if len(lines) != 5:
            await msg.reply_text("❌ Please send exactly 5 lines:\nCODE AMOUNT\nCHANNEL\nTOTAL\nDATE\nID", reply_markup=INLINE_KB)
            return

        match = re.match(r'^(\w+)\s+(\d+)$', lines[0].strip())
        if not match:
            await msg.reply_text("❌ First line should be like `ABC123 4`", reply_markup=INLINE_KB)
            return

        code, amount = match.groups()
        formatted_code = f"`{code}` {{{amount}}}"
        channel = lines[1].strip()
        total = lines[2].strip()
        date = lines[3].strip()
        user_id = lines[4].strip()

        output = f"""```
𝗡𝗨𝗠𝗕𝗘R:  {formatted_code}

𝗖𝗛𝗔𝗡𝗡𝗘𝗟 𝗡AME--  {channel} ✅

𝗧𝗢𝗧𝗔𝗟 N𝗨𝗠𝗕𝗘𝗥 :-  {total} ✅

𝗗𝗔𝗧𝗘 :- {date} ✅

𝗣𝗘𝗡𝗗𝗜𝗡𝗚 𝗣𝗔𝗬𝗠𝗘𝗡𝗧:-

ID:- {user_id} ✅
```"""
        await msg.reply_text(output, reply_markup=INLINE_KB, parse_mode="Markdown")
        return

    data = load_user_data(uid)
    if not data["list"]:
        await msg.reply_text("```Pehle /list se list bhejiye.```", reply_markup=INLINE_KB, parse_mode="Markdown")
        return

    parts = txt.split()
    if len(parts) != 2 or len(parts[0]) != 9 or not parts[1].isdigit():
        await msg.reply_text("```Format galat hai.``` Use: ABCDJDJDJ 2300", reply_markup=INLINE_KB, parse_mode="Markdown")
        return

    code, number = parts
    inserted = False
    for i in range(data["next_insert_index"], len(data["list"])):
        itm = data["list"][i]
        if itm["value"] != "deleted" and ' ' not in itm["value"]:
            itm["value"] = f"{code}   {number}   {itm['value']}"
            data["next_insert_index"] = i + 1
            inserted = True
            break

    if inserted:
        save_user_data(uid, data)
        next_serial = itm["serial"] + 1
        await msg.reply_text(
            f"Code inserted at serial {itm['serial']}.\n👉 Next code: send serial **{next_serial}**",
            reply_markup=INLINE_KB, parse_mode="Markdown"
        )
    else:
        await msg.reply_text("```Koi khaali jagah nahi mila insert karne ke liye.```", reply_markup=INLINE_KB, parse_mode="Markdown")

# ---------- Main for Render ----------
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("mono", mono_cmd))
    app.add_handler(CommandHandler("show", show_cmd))
    app.add_handler(CommandHandler("done", show_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CallbackQueryHandler(inline_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    async def webhook_handler(request):
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(text="ok")

    async def on_startup(app_):
        webhook_url = f"{APP_URL}/webhook"
        await app.bot.set_webhook(webhook_url)

    web_app = web.Application()
    web_app.router.add_post("/webhook", webhook_handler)
    web_app.on_startup.append(on_startup)
    await app.initialize()
    await app.start()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    print(f"Bot is running at {APP_URL}/webhook")
    await site.start()

    # Keep running forever
    import asyncio
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
