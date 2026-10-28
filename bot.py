import os, asyncio, threading, json, random
from datetime import datetime
import pytz
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Smart Salah Bot Alive"
def run_flask(): flask_app.run(host='0.0.0.0', port=10000)
threading.Thread(target=run_flask, daemon=True).start()

TOKEN = os.getenv("TOKEN")
GROUP_ID = -1003710189896
EAT = pytz.timezone("Africa/Nairobi")

TIMES = {"Fajr":"05:09","Dhuhr":"12:23","Asr":"15:42","Maghrib":"18:26","Isha":"19:32"}

FILE = "data.json"
try:
    with open(FILE) as f: DATA = json.load(f)
except:
    DATA = {"prayers": {}, "users": {}}

def save():
    with open(FILE, "w") as f: json.dump(DATA, f)

HADITH = [
    "Prayer is the pillar of religion.",
    "Between man and disbelief is leaving prayer.",
    "Closest servant is to Allah in sujood.",
    "Guard Fajr & Asr and you enter Jannah.",
    "Prayer prevents immorality - Quran 29:45"
]

active = {}

async def checker(app: Application):
    while True:
        now = datetime.now(EAT)
        now_str = now.strftime("%H:%M")
        date = str(now.date())
        for name, t in TIMES.items():
            key = f"{date}:{name}"
            if now_str == t and key not in active:
                if date not in DATA["prayers"]: DATA["prayers"][date] = {}
                if name not in DATA["prayers"][date]: DATA["prayers"][date][name] = []
                save()
                kb = [
                    [InlineKeyboardButton("✅ I Prayed", callback_data=f"do:pray:{name}:{date}"), InlineKeyboardButton("⏰ Late", callback_data=f"do:late:{name}:{date}")],
                    [InlineKeyboardButton("❌ Missed", callback_data=f"do:miss:{name}:{date}"), InlineKeyboardButton("🤲 Dua", callback_data="dua")],
                    [InlineKeyboardButton("🏆 Leaderboard", callback_data="board"), InlineKeyboardButton("📊 My Stats", callback_data="stats")]
                ]
                txt = f"⏰ *{name} Salah - {t}*\n📍 Eldoret\n\n_{random.choice(HADITH)}_\n\n👇 Tap when you pray:"
                try:
                    msg = await app.bot.send_message(GROUP_ID, txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
                    active[key] = msg.message_id
                except Exception as e:
                    print(e)
        await asyncio.sleep(20)

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    name_user = q.from_user.first_name
    data = q.data
    if data == "dua":
        await q.answer("اللهم تقبل منا - May Allah accept 🤲", show_alert=True)
        return
    if data == "board":
        board = sorted(DATA["users"].items(), key=lambda x: x[1]['total'], reverse=True)[:10]
        if not board: await q.answer("No prayers yet! Be first!", show_alert=True); return
        txt = "🏆 Leaderboard\n" + "\n".join([f"{i}. {info['name']} - {info['total']} ✅" for i,(uid2,info) in enumerate(board,1)])
        await q.answer(txt, show_alert=True)
        return
    if data == "stats":
        info = DATA["users"].get(uid, {"total":0})
        await q.answer(f"📊 You prayed {info['total']} times. MashAllah!", show_alert=True)
        return
    _, action, prayer, date = data.split(":")
    if uid not in DATA["users"]: DATA["users"][uid] = {"name": name_user, "total":0}
    already = any(name_user in x for x in DATA["prayers"].get(date,{}).get(prayer,[]))
    if not already:
        emoji = "✅" if action=="pray" else "⏰" if action=="late" else "❌"
        if action=="pray": DATA["users"][uid]["total"]+=1
        DATA["prayers"][date][prayer].append(f"{emoji} {name_user} ({datetime.now(EAT).strftime('%H:%M')})")
        save()
    prayed_list = "\n".join(DATA["prayers"][date][prayer]) if DATA["prayers"][date][prayer] else "Be first!"
    count = len(DATA["prayers"][date][prayer])
    new_txt = f"⏰ *{prayer} Salah - {TIMES[prayer]}*\n📍 Eldoret\n\n*Prayed ({count}):*\n{prayed_list}\n\n_{random.choice(HADITH)}_"
    kb = [
        [InlineKeyboardButton("✅ I Prayed", callback_data=f"do:pray:{prayer}:{date}"), InlineKeyboardButton("⏰ Late", callback_data=f"do:late:{prayer}:{date}")],
        [InlineKeyboardButton("❌ Missed", callback_data=f"do:miss:{prayer}:{date}"), InlineKeyboardButton("🤲 Dua", callback_data="dua")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="board"), InlineKeyboardButton("📊 My Stats", callback_data="stats")]
    ]
    try: await q.edit_message_text(new_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    except: pass

async def cmd_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = sorted(DATA["users"].items(), key=lambda x: x[1]['total'], reverse=True)[:10]
    if not board: await update.message.reply_text("No one prayed yet!"); return
    txt = "🏆 *Eldoret Salah Leaderboard*\n\n" + "\n".join([f"{i}. {info['name']} — {info['total']} prayers" for i,(uid,info) in enumerate(board,1)])
    await update.message.reply_text(txt, parse_mode='Markdown')

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = DATA["users"].get(str(update.effective_user.id), {"total":0,"name":"You"})
    await update.message.reply_text(f"📊 *{info.get('name','You')}*: {info['total']} prayers total.", parse_mode='Markdown')

async def cmd_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = "🕋 *Today Eldoret*\n" + "\n".join([f"{k}: {v}" for k,v in TIMES.items()])
    await update.message.reply_text(txt, parse_mode='Markdown')

async def post_init(app: Application):
    print("Smart Bot ONLINE")
    try: await app.bot.send_message(GROUP_ID, "✅ *Smart Salah Bot is LIVE!*\n\nInteractive now:\n• Tap ✅ see name live\n• /leaderboard\n• /stats\n• /times", parse_mode='Markdown')
    except Exception as e: print(e)
    asyncio.create_task(checker(app))

async def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(CommandHandler("leaderboard", cmd_board))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("times", cmd_times))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
