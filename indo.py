import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import nest_asyncio

# Apply nest_asyncio to fix event loop issue
nest_asyncio.apply()

# ===== CONFIGURATION =====
TOKEN = "8160920308:AAE6YxXDNXxwQ1ZOkx0kNue4TQQo592SrVI"
ADMIN_ID = 7646520243
QR_IMAGE_URL = "https://res.cloudinary.com/dldj8zqsf/image/upload/v1718123456/qr-code-indo_upi.png"
PRICE_PER_DAY = 1.2

# ===== LOGGING =====
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ===== STATES =====
MAIN_MENU, BUY_DAYS, BUY_QUANTITY, WAITING_PAYMENT = range(4)

# ===== HELPER BUTTONS =====
def main_menu():
    buttons = [
        [KeyboardButton("🛒 Buy ID"), KeyboardButton("💬 Contact Admin")],
        [KeyboardButton("📦 Check Stock"), KeyboardButton("ℹ Help")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def days_menu():
    buttons = [
        [KeyboardButton("10"), KeyboardButton("20"), KeyboardButton("30"), KeyboardButton("60")],
        [KeyboardButton("🔙 Back"), KeyboardButton("🏠 Main Menu")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def quantity_menu():
    buttons = [
        [KeyboardButton("1"), KeyboardButton("3"), KeyboardButton("5")],
        [KeyboardButton("10"), KeyboardButton("15"), KeyboardButton("20")],
        [KeyboardButton("🔙 Back"), KeyboardButton("🏠 Main Menu")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Indo Seller Bot!", reply_markup=main_menu())
    return MAIN_MENU

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🛒 Buy ID":
        await update.message.reply_text("👉 Kitne din purani ID chahiye?", reply_markup=days_menu())
        return BUY_DAYS

    elif text == "💬 Contact Admin":
        await update.message.reply_text("Contact Admin: @YourAdminUsername")
        return MAIN_MENU

    elif text == "📦 Check Stock":
        await update.message.reply_text("Stock abhi local server pe maintain ho raha hai.")
        return MAIN_MENU

    elif text == "ℹ Help":
        await update.message.reply_text("Ye Indo Seller Bot hai. Yahan aap ID kharid sakte hain.")
        return MAIN_MENU

    else:
        await update.message.reply_text("Kripya menu se option select kare.", reply_markup=main_menu())
        return MAIN_MENU

async def handle_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text in ["10", "20", "30", "60"]:
        context.user_data["days"] = int(text)
        await update.message.reply_text("👉 Kitni ID chahiye?", reply_markup=quantity_menu())
        return BUY_QUANTITY

    elif text == "🔙 Back" or text == "🏠 Main Menu":
        await update.message.reply_text("Main Menu:", reply_markup=main_menu())
        return MAIN_MENU

    else:
        await update.message.reply_text("Valid din select kare.", reply_markup=days_menu())
        return BUY_DAYS

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text in ["1", "3", "5", "10", "15", "20"]:
        context.user_data["quantity"] = int(text)
        days = context.user_data["days"]
        quantity = context.user_data["quantity"]
        price = days * quantity * PRICE_PER_DAY

        context.user_data["price"] = price

        await update.message.reply_photo(QR_IMAGE_URL, caption=f"Total Price: ₹{price}\n\nUPI se payment kare aur screenshot bhejein.")
        return WAITING_PAYMENT

    elif text == "🔙 Back":
        await update.message.reply_text("👉 Kitne din purani ID chahiye?", reply_markup=days_menu())
        return BUY_DAYS

    elif text == "🏠 Main Menu":
        await update.message.reply_text("Main Menu:", reply_markup=main_menu())
        return MAIN_MENU

    else:
        await update.message.reply_text("Valid quantity select kare.", reply_markup=quantity_menu())
        return BUY_QUANTITY

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        days = context.user_data["days"]
        quantity = context.user_data["quantity"]
        price = context.user_data["price"]

        await update.message.reply_text("✅ Payment screenshot mil gaya. Admin approval pending hai.")

        await context.bot.send_message(
            ADMIN_ID,
            f"📥 New Order:\nUser ID: {update.effective_user.id}\nDays: {days}\nQuantity: {quantity}\nTotal: ₹{price}"
        )
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)

        await update.message.reply_text("⚠ Admin confirmation ka intezar karein.", reply_markup=main_menu())
        return MAIN_MENU

    else:
        await update.message.reply_text("❌ Sirf payment screenshot bhejein.")
        return WAITING_PAYMENT

# Admin command handler (admin ka /start yahi handle karega)
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Welcome Admin! Aapka system sahi kaam kar raha hai.")

# ===== MAIN FUNCTION =====
async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Conversation for users
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            BUY_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_days)],
            BUY_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)],
            WAITING_PAYMENT: [MessageHandler(filters.ALL, handle_payment)],
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)

    # Admin separate handler (Global Admin Handler)
    application.add_handler(CommandHandler("start", admin_start, filters.User(ADMIN_ID)))
    application.add_handler(MessageHandler(filters.User(ADMIN_ID), admin_start))  # for any message from admin

    print("✅ Indo Seller Bot Started Successfully!")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())