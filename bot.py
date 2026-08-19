import os
import logging
import httpx
import urllib.parse
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

GATEWAYS = {
    "Shop Pay / Shopify": ["shop-pay", "shoppay", "cdn.shopify.com", "shopify-checkout", "shop.app/pay"],
    "Stripe": ["js.stripe.com", "stripe.com/pay", "stripe_checkout", "__stripe"],
    "PayPal": ["paypal.com/sdk", "paypalobjects.com", "paypal-button", "paypal-checkout"],
    "Adyen": ["checkoutshopper-live", "adyen.com", "adyen.pay"],
    "Razer Merchant": ["molpay", "razer.com/pay", "merchant.razer.com"]
}

async def detect_gateways(url: str) -> list:
    detected = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=6.0, verify=False) as client:
            response = await client.get(url)
            html = response.text.lower()
            for name, signatures in GATEWAYS.items():
                if any(sig in html for sig in signatures):
                    detected.append(name)
    except Exception:
        return ["Timeout / Protected"]
    
    return detected if detected else ["Custom / Unknown"]

async def search_google(query: str) -> list:
    urls = []
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=8.0) as client:
            resp = await client.get(search_url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.find_all('a', class_='result__url'):
                href = a.get('href', '')
                if href.startswith('http') and 'duckduckgo' not in href:
                    urls.append(href.strip())
                if len(urls) >= 5:
                    break
    except Exception as e:
        logging.error(f"Search Error: {e}")
    
    # إذا لم يجد روابط، يتصل بمحرك تجاري احترافي لا يحظر IP
    if not urls:
        try:
            alt_url = f"https://api.allorigins.win/get?url={urllib.parse.quote('https://html.duckduckgo.com/html/?q=' + query)}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(alt_url)
                data = resp.json()
                soup = BeautifulSoup(data.get('contents', ''), 'html.parser')
                for a in soup.find_all('a', class_='result__url'):
                    href = a.get('href', '')
                    if href.startswith('http'):
                        urls.append(href.strip())
                    if len(urls) >= 5:
                        break
        except Exception as e:
            logging.error(f"Proxy Search Error: {e}")

    return urls

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ البوت جاهز للاستخدام!\n\nأرسل الأمر كالتالي:\n<code>/search mobile legends top up</code>", parse_mode="HTML")

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = " ".join(context.args)
    if not user_query:
        await update.message.reply_text("يرجى كتابة كلمة البحث.\nمثال: <code>/search mobile legends top up</code>", parse_mode="HTML")
        return

    status_msg = await update.message.reply_text("🔍 جاري فحص الشبكة وجلب المتاجر المتاحة...")

    urls = await search_google(user_query)

    if not urls:
        await status_msg.edit_text("تعذر العثور على نتائج، يرجى المحاولة بعد قليل.")
        return

    response_text = f"<b>النتائج والبوابات المكتشفة:</b>\n\n"
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
