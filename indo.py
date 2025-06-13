import asyncio
import json
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Config
TOKEN = "8160920308:AAE6YxXDNXxwQ1ZOkx0kNue4TQQo592SrVI"
ADMIN_ID = 7646520243
QR_IMAGE_URL = "https://res.cloudinary.com/dldj8zqsf/image/upload/v1718123456/qr-code-indo_upi.png"
PRICE_PER_DAY = 1.2
STOCK_FILE = "stock.json"

# States
MAIN_MENU, BUY_DAYS, BUY_QUANTITY, WAITING_PAYMENT, ADMIN_PANEL, ADD_ID, CHECK_STOCK_SELECT = range(7)

# Create stock file if not exist
if not os.path.exists(STOCK_FILE):
    with open(STOCK_FILE, "w") as f:
        json.dump([], f)

# Buttons
def main_menu(is_admin=False):
    buttons = [
        [KeyboardButton("🛒 Buy ID"), KeyboardButton("📦 Check Stock")],
        [KeyboardButton("ℹ Help"), KeyboardButton("💬 Contact Admin")]
    ]
    if is_admin:
        buttons.append([KeyboardButton("➕ Add ID")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def days_menu():
    buttons = [
        [KeyboardButton("5"), KeyboardButton("10"), KeyboardButton("20"), KeyboardButton("30"), KeyboardButton("All")],
        [KeyboardButton("🔙 Back")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def buy_days_menu():
    buttons = [
        [KeyboardButton("5"), KeyboardButton("10"), KeyboardButton("20"), KeyboardButton("30")],
        [KeyboardButton("🔙 Back")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def quantity_menu():
    buttons = [
        [KeyboardButton("1"), KeyboardButton("3"), KeyboardButton("5"), KeyboardButton("10"), KeyboardButton("15"), KeyboardButton("20")],
        [KeyboardButton("🔙 Back")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Load stock
def load_stock():
    with open(STOCK_FILE, "r") as f:
        return json.load(f)

# Save stock
def save_stock(data):
    with open(STOCK_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Calculate age
def calculate_age(upload_date):
    upload_dt = datetime.strptime(upload_date, "%Y-%m-%d")
    return (datetime.now() - upload_dt).days

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID
    await update.message.reply_text("👋 Welcome to Indo Seller Bot!", reply_markup=main_menu(is_admin))
    return MAIN_MENU

# Handle main menu
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID

    if text == "🛒 Buy ID":
        await update.message.reply_text("Kitne din purani ID chahiye?", reply_markup=buy_days_menu())
        return BUY_DAYS

    elif text == "📦 Check Stock":
        await update.message.reply_text("Kaunsa stock dekhna hai?", reply_markup=days_menu())
        return CHECK_STOCK_SELECT

    elif text == "ℹ Help":
        await update.message.reply_text("Yeh Indo Seller Bot hai. ID kharidne ke liye Buy ID karein.")
        return MAIN_MENU

    elif text == "💬 Contact Admin":
        await update.message.reply_text("Contact Admin: @BADMOSH_X_GYRANGE")
        return MAIN_MENU

    elif text == "➕ Add ID" and is_admin:
        await update.message.reply_text("Send ID like:\n`userid password`")
        return ADD_ID

    else:
        await update.message.reply_text("Sahi option choose kare.", reply_markup=main_menu(is_admin))
        return MAIN_MENU

# Handle Buy Days
async def handle_buy_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["5", "10", "20", "30"]:
        context.user_data["days"] = int(text)
        await update.message.reply_text("Kitni ID chahiye?", reply_markup=quantity_menu())
        return BUY_QUANTITY
    elif text == "🔙 Back":
        await update.message.reply_text("Main menu:", reply_markup=main_menu(update.effective_user.id == ADMIN_ID))
        return MAIN_MENU
    else:
        await update.message.reply_text("Valid din choose kare.")
        return BUY_DAYS

# Handle Buy Quantity
async def handle_buy_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["1", "3", "5", "10", "15", "20"]:
        context.user_data["quantity"] = int(text)
        days = context.user_data["days"]
        quantity = context.user_data["quantity"]
        price = days * quantity * PRICE_PER_DAY
        context.user_data["price"] = price
        await update.message.reply_photo(QR_IMAGE_URL, caption=f"Total Price: ₹{price}\n\nPayment ke baad screenshot bhejein.")
        return WAITING_PAYMENT
    elif text == "🔙 Back":
        await update.message.reply_text("Kitne din purani ID chahiye?", reply_markup=buy_days_menu())
        return BUY_DAYS
    else:
        await update.message.reply_text("Valid quantity choose kare.")
        return BUY_QUANTITY

# Handle Payment Screenshot
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        days = context.user_data["days"]
        quantity = context.user_data["quantity"]
        price = context.user_data["price"]

        await update.message.reply_text("✅ Payment screenshot mil gaya. Admin verify karega.")

        await context.bot.send_message(
            ADMIN_ID,
            f"📥 New Order:\nUser: {update.effective_user.id}\nDays: {days}\nQuantity: {quantity}\nTotal: ₹{price}"
        )
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)
        return MAIN_MENU
    else:
        await update.message.reply_text("❌ Screenshot bhejo.")
        return WAITING_PAYMENT

# Handle Add ID (Admin)
async def handle_add_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if " " not in text:
        await update.message.reply_text("Format galat hai.\nUse: `userid password`")
        return ADD_ID

    userid, password = text.split(" ", 1)
    new_entry = {
        "userid": userid.strip(),
        "password": password.strip(),
        "upload_date": datetime.now().strftime("%Y-%m-%d")
    }

    stock = load_stock()
    stock.append(new_entry)
    save_stock(stock)

    await update.message.reply_text("✅ ID add hogayi.")
    return MAIN_MENU

# Handle Stock Check
async def handle_stock_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    stock = load_stock()

    if text == "🔙 Back":
        await update.message.reply_text("Main menu:", reply_markup=main_menu(update.effective_user.id == ADMIN_ID))
        return MAIN_MENU

    elif text == "All":
        count = len(stock)
        await update.message.reply_text(f"Total Stock: {count}")
        return MAIN_MENU

    elif text in ["5", "10", "20", "30"]:
        days_target = int(text)
        filtered = [s for s in stock if calculate_age(s["upload_date"]) >= days_target]
        await update.message.reply_text(f"{days_target} days old stock: {len(filtered)}")
        return MAIN_MENU

    else:
        await update.message.reply_text("Valid option select kare.")
        return CHECK_STOCK_SELECT

# Admin Command (for users to contact admin)
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(ADMIN_ID, f"⚠ User {update.effective_user.id} wants to contact you.")
    await update.message.reply_text("✅ Admin ko request chali gayi.")
    return MAIN_MENU

# Main Function
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            BUY_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buy_days)],
            BUY_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buy_quantity)],
            WAITING_PAYMENT: [MessageHandler(filters.ALL, handle_payment)],
            ADD_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_id)],
            CHECK_STOCK_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_select)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("admin", admin_command))

    print("✅ Indo Seller Bot Started Successfully!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())