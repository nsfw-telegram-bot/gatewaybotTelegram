import os
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

GATEWAYS = {
    "Shop Pay / Shopify": ["shop-pay", "shoppay", "cdn.shopify.com", "shopify-checkout", "shop.app/pay"],
    "Stripe": ["js.stripe.com", "stripe.com/pay", "stripe_checkout"],
    "PayPal": ["paypal.com/sdk", "paypalobjects.com", "paypal-button"],
    "Adyen": ["checkoutshopper-live", "adyen.com"],
    "Razer Merchant": ["molpay", "razer.com/pay"]
}

async def detect_gateways(url: str) -> list:
    detected = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=5.0, verify=False) as client:
            response = await client.get(url)
            html = response.text.lower()
            for name, signatures in GATEWAYS.items():
                if any(sig in html for sig in signatures):
                    detected.append(name)
    except Exception:
        return ["Protected / Timeout"]
    
    return detected if detected else ["Custom / Unknown"]

async def search_serper(query: str) -> list:
    if not SERPER_API_KEY:
        logging.error("SERPER_API_KEY is missing from environment variables!")
        return []

    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": 5}
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    urls = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()
            if "organic" in data:
                urls = [item["link"] for item in data["organic"]]
    except Exception as e:
        logging.error(f"Serper API Request Error: {e}")
        
    return urls

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ البوت متصل ومستعد للبحث!\n\nأرسل الأمر كالتالي:\n<code>/search mobile legends top up</code>", parse_mode="HTML")

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = " ".join(context.args)
    if not user_query:
        await update.message.reply_text("يرجى كتابة كلمة البحث بعد الأمر.")
        return

    status_msg = await update.message.reply_text("🔍 جاري البحث وفحص المتاجر...")

    urls = await search_serper(user_query)

    if not urls:
        await status_msg.edit_text("لم يتم العثور على نتائج. تأكد من إضافة SERPER_API_KEY في Variables بطريقة صحيحة.")
        return

    response_text = f"<b>النتائج للبوابات المكتشفة:</b>\n\n"
    for idx, url in enumerate(urls, start=1):
        gateways = await detect_gateways(url)
        gw_str = " | ".join(gateways)
        badge = "🟢" if "Shop Pay / Shopify" in gateways else "🔵"
        response_text += f"{idx}. {url}\n   └ <b>{badge} Gateways:</b> {gw_str}\n\n"

    await status_msg.edit_text(response_text, parse_mode="HTML", disable_web_page_preview=True)

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    if TOKEN:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("search", search_stores))
        app.run_polling(drop_pending_updates=True)
