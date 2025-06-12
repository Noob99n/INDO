import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bson.objectid import ObjectId

# --- CONFIG ---
BOT_TOKEN = "8160920308:AAE6YxXDNXxwQ1ZOkx0kNue4TQQo592SrVI"
ADMIN_ID = 7646520243
UPI_ID = "gyrange.satyam@fam"
QR_IMAGE_URL = "https://res.cloudinary.com/djbiyudvw/image/upload/v1749710777/6222145007939337666_cu13he.jpg"
RATE_PER_DAY = 1.2
DISCOUNT = 0.05

# MongoDB setup
client = MongoClient("mongodb+srv://badmosh_indo:Gyrange9876@indo.w5sols1.mongodb.net/?retryWrites=true&w=majority&appName=INDO")
db = client["insta_bot"]
collection = db["accounts"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()
logging.basicConfig(level=logging.INFO)

# --- UTILITIES ---
def calculate_price(created):
    days_old = (datetime.now() - created).days
    price = days_old * RATE_PER_DAY
    return round(price, 2), days_old

def filter_accounts(min_days):
    results = []
    for acc in collection.find({"status": "available"}):
        price, days = calculate_price(acc['created_at'])
        if days >= min_days:
            results.append({"_id": str(acc['_id']), "price": price, "days": days})
    return results

# --- KEYBOARDS ---
def filter_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("10 Days Old", callback_data="filter_10"),
        InlineKeyboardButton("20 Days Old", callback_data="filter_20"),
        InlineKeyboardButton("30 Days Old", callback_data="filter_30"),
        InlineKeyboardButton("Show All", callback_data="filter_0")
    )
    return kb

# --- COMMANDS ---
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("Welcome to Insta ID Store!\nChoose a category:", reply_markup=filter_keyboard())

@dp.message_handler(commands=['add'])
async def add_id(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, username, password = msg.text.split()
        doc = {
            "username": username,
            "password": password,
            "created_at": datetime.now(),
            "status": "available"
        }
        collection.insert_one(doc)
        await msg.reply("✅ ID added successfully!")
    except:
        await msg.reply("❌ Usage: /add <username> <password>")

# --- FILTER HANDLER ---
@dp.callback_query_handler(lambda c: c.data.startswith("filter_"))
async def show_ids(callback: types.CallbackQuery):
    min_days = int(callback.data.split("_")[1])
    accounts = filter_accounts(min_days)
    if not accounts:
        await callback.message.edit_text("No accounts available in this category.", reply_markup=filter_keyboard())
        return

    msg = ""
    for idx, acc in enumerate(accounts):
        msg += f"\n🔢 ID #{idx+1}\n📅 Age: {acc['days']} days\n💰 Price: ₹{acc['price']:.2f}\n/buy_{acc['_id'][:6]}\n"
    await callback.message.edit_text(msg[:4096], reply_markup=filter_keyboard())

# --- BUY HANDLER ---
@dp.message_handler(lambda m: m.text.startswith("/buy_"))
async def buy_id(msg: types.Message):
    short_id = msg.text[5:]
    acc = collection.find_one({"_id": {"$regex": f"^{short_id}"}, "status": "available"})
    if not acc:
        await msg.reply("❌ ID not available or already sold.")
        return
    price, days = calculate_price(acc['created_at'])
    collection.update_one({"_id": acc['_id']}, {"$set": {"status": "pending", "buyer": msg.from_user.id}})

    summary = f"🧾 Order Summary:\nID Age: {days} days\nPrice: ₹{price:.2f}\nPlease scan the QR below and send payment screenshot."
    await msg.reply_photo(QR_IMAGE_URL, caption=summary)

# --- CONFIRM HANDLER ---
@dp.message_handler(commands=['confirm'])
async def confirm(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, short_id = msg.text.split()
        acc = collection.find_one({"_id": {"$regex": f"^{short_id}"}})
        if acc:
            collection.update_one({"_id": acc['_id']}, {"$set": {"status": "sold", "sold_at": datetime.now()}})
            await msg.reply("✅ ID marked as sold!")
        else:
            await msg.reply("❌ ID not found.")
    except:
        await msg.reply("❌ Usage: /confirm <short_id>")

# --- AUTO DELETE JOB ---
async def delete_sold():
    cutoff = datetime.now() - timedelta(days=2)
    collection.delete_many({"status": "sold", "sold_at": {"$lte": cutoff}})

scheduler.add_job(delete_sold, 'interval', hours=12)
scheduler.start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
