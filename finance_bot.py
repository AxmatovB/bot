import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json
import os
from datetime import datetime
from collections import defaultdict

# Logging sozlamalari
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Ma'lumotlar fayli
DATA_FILE = 'user_data.json'

# Ma'lumotlarni yuklash
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Ma'lumotlarni saqlash
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Foydalanuvchi ma'lumotlarini olish
def get_user_data(user_id):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            'income': [],
            'expense': []
        }
        save_data(data)
    return data[user_id]

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("💰 Daromad qo'shish", callback_data='add_income')],
        [InlineKeyboardButton("💸 Xarajat qo'shish", callback_data='add_expense')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("📱 Web App ochish", web_app=WebAppInfo(url=f"https://your-domain.com/webapp.html?user_id={user.id}"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎉 Assalomu alaykum, {user.first_name}!

Men sizning moliyaviy botingizman. 
Daromad va xarajatlaringizni kuzatishda yordam beraman.

📌 Quyidagi tugmalardan foydalaning:
"""
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Tugma bosilganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add_income':
        context.user_data['waiting_for'] = 'income'
        await query.edit_message_text(
            "💰 Daromad kiritish:\n\n"
            "Format: summa kategoriya izoh\n"
            "Misol: 500000 maosh Iyul oyi maoshi\n\n"
            "Kategoriyalar: maosh, biznes, sovg'a, boshqa"
        )
    
    elif query.data == 'add_expense':
        context.user_data['waiting_for'] = 'expense'
        await query.edit_message_text(
            "💸 Xarajat kiritish:\n\n"
            "Format: summa kategoriya izoh\n"
            "Misol: 50000 oziq-ovqat Do'konda xarid\n\n"
            "Kategoriyalar: oziq-ovqat, transport, uy-joy, kiyim, o'yin-kulgi, sog'liq, ta'lim, boshqa"
        )
    
    elif query.data == 'stats':
        await show_stats(query, context)
    
    elif query.data == 'back':
        keyboard = [
            [InlineKeyboardButton("💰 Daromad qo'shish", callback_data='add_income')],
            [InlineKeyboardButton("💸 Xarajat qo'shish", callback_data='add_expense')],
            [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Kerakli bo'limni tanlang:", reply_markup=reply_markup)

# Statistikani ko'rsatish
async def show_stats(query, context):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    total_income = sum(item['amount'] for item in user_data['income'])
    total_expense = sum(item['amount'] for item in user_data['expense'])
    balance = total_income - total_expense
    
    # Kategoriya bo'yicha xarajatlar
    expense_by_category = defaultdict(float)
    for item in user_data['expense']:
        expense_by_category[item['category']] += item['amount']
    
    # Holat baholash
    if balance > total_income * 0.5:
        status = "🟢 A'lo! Yaxshi tejayapsiz!"
    elif balance > total_income * 0.2:
        status = "🟡 Yaxshi, lekin ko'proq tejamoqchi bo'lsangiz mumkin"
    elif balance > 0:
        status = "🟠 Ehtiyot bo'ling! Xarajatlaringiz ko'p"
    else:
        status = "🔴 Xavfli! Xarajatlar daromaddan oshib ketgan!"
    
    stats_text = f"""
📊 **MOLIYAVIY STATISTIKA**

💰 Jami daromad: {total_income:,.0f} so'm
💸 Jami xarajat: {total_expense:,.0f} so'm
💵 Balans: {balance:,.0f} so'm

{status}

📈 **Xarajatlar kategoriya bo'yicha:**
"""
    
    for category, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_expense * 100) if total_expense > 0 else 0
        stats_text += f"\n{category}: {amount:,.0f} so'm ({percentage:.1f}%)"
    
    stats_text += f"\n\n📝 Jami operatsiyalar: {len(user_data['income']) + len(user_data['expense'])}"
    
    keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

# Xabar qabul qilish
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if 'waiting_for' not in context.user_data:
        await update.message.reply_text("Iltimos, /start buyrug'ini yuboring")
        return
    
    waiting_for = context.user_data['waiting_for']
    
    try:
        parts = text.split(maxsplit=2)
        if len(parts) < 2:
            await update.message.reply_text("❌ Noto'g'ri format! Iltimos, qaytadan kiriting.")
            return
        
        amount = float(parts[0])
        category = parts[1]
        description = parts[2] if len(parts) > 2 else ""
        
        data = load_data()
        user_id_str = str(user_id)
        
        if user_id_str not in data:
            data[user_id_str] = {'income': [], 'expense': []}
        
        entry = {
            'amount': amount,
            'category': category,
            'description': description,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if waiting_for == 'income':
            data[user_id_str]['income'].append(entry)
            emoji = "💰"
            type_text = "Daromad"
        else:
            data[user_id_str]['expense'].append(entry)
            emoji = "💸"
            type_text = "Xarajat"
        
        save_data(data)
        
        keyboard = [
            [InlineKeyboardButton("➕ Yana qo'shish", callback_data=f'add_{waiting_for}')],
            [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
            [InlineKeyboardButton("◀️ Bosh menyu", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ {emoji} {type_text} qo'shildi!\n\n"
            f"Summa: {amount:,.0f} so'm\n"
            f"Kategoriya: {category}\n"
            f"Izoh: {description}",
            reply_markup=reply_markup
        )
        
        context.user_data.pop('waiting_for', None)
        
    except ValueError:
        await update.message.reply_text("❌ Summani raqam formatida kiriting!")
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")

# /history buyrug'i
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    all_transactions = []
    for item in user_data['income']:
        all_transactions.append({**item, 'type': 'income'})
    for item in user_data['expense']:
        all_transactions.append({**item, 'type': 'expense'})
    
    all_transactions.sort(key=lambda x: x['date'], reverse=True)
    
    if not all_transactions:
        await update.message.reply_text("📋 Hali hech qanday operatsiya yo'q")
        return
    
    history_text = "📋 **TARIX** (oxirgi 10 ta):\n\n"
    
    for transaction in all_transactions[:10]:
        emoji = "💰" if transaction['type'] == 'income' else "💸"
        history_text += f"{emoji} {transaction['amount']:,.0f} so'm - {transaction['category']}\n"
        history_text += f"   📅 {transaction['date']}\n"
        if transaction['description']:
            history_text += f"   📝 {transaction['description']}\n"
        history_text += "\n"
    
    await update.message.reply_text(history_text, parse_mode='Markdown')

# Xatoliklarni boshqarish
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Xatolik: {context.error}")

def main():
    # Bot tokenini kiriting
    TOKEN = "8282248778:AAGvpkNLh-sAvdXB7gzlP7uyiRJMGeiopGQ"
    
    application = Application.builder().token(TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    print("🤖 Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()