import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Received /start command")
    await update.message.reply_text("⚡ البوت يعمل بنجاح! أرسل /search متبوعة باسم اللعبة.")

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = " ".join(context.args)
    if not user_query:
        await update.message.reply_text("يرجى كتابة كلمة البحث، مثال: /search genshin")
        return

    status_msg = await update.message.reply_text("🔍 جاري البحث...")
    try:
        results = []
        with DDGS() as ddgs:
            res = ddgs.text(f'{user_query} top up', max_results=5)
            if res:
                results = [r['href'] for r in res]

        if not results:
            await status_msg.edit_text("لم يتم العثور على نتائج.")
            return

        text = "<b>النتائج:</b>\n\n" + "\n".join(results)
        await status_msg.edit_text(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("حدث خطأ أثناء البحث.")

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    if TOKEN:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("search", search_stores))
        print("--- BOT IS RUNNING NOW ---")
        app.run_polling(drop_pending_updates=True)
