import os
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

GATEWAYS = {
    "Shop Pay / Shopify": ["shop-pay", "shoppay", "cdn.shopify.com", "shopify-checkout", "shop.app/pay"],
    "Stripe": ["js.stripe.com", "stripe.com/pay", "stripe_checkout", "__stripe"],
    "PayPal": ["paypal.com/sdk", "paypalobjects.com", "paypal-button", "paypal-checkout"],
    "Adyen": ["checkoutshopper-live", "adyen.com", "adyen.pay"],
    "Checkout.com": ["checkout.com", "frames.checkout.com"],
    "Razer Merchant": ["molpay", "razer.com/pay", "merchant.razer.com"],
    "Klarna": ["klarna.com", "klarna-checkout"]
}

async def detect_gateways(url: str) -> dict:
    detected = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=6.0, verify=False) as client:
            response = await client.get(url)
            html = response.text.lower()
            for name, signatures in GATEWAYS.items():
                if any(sig in html for sig in signatures):
                    detected.append(name)
    except Exception:
        return {"url": url, "gateways": ["Timeout / Protected"]}
    
    if not detected:
        detected.append("Custom / Unknown Gateway")
        
    return {"url": url, "gateways": detected}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ Gateway Inspector Online!\n\nSend /search <keywords> to find stores.", parse_mode="HTML")

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = " ".join(context.args)
    if not user_query:
        await update.message.reply_text("Please specify a search term.\nExample: <code>/search mobile legends</code>", parse_mode="HTML")
        return

    status_msg = await update.message.reply_text(f"🔍 Inspecting gateways for: <code>{user_query}</code>...", parse_mode="HTML")

    try:
        raw_urls = []
        with DDGS() as ddgs:
            results = ddgs.text(f'"{user_query}" "powered by shopify" OR "top up"', max_results=8)
            if results:
                for r in results:
                    raw_urls.append(r.get('href'))

        if not raw_urls:
            await status_msg.edit_text("No stores found.")
            return

        verified_results = []
        for url in raw_urls:
            res = await detect_gateways(url)
            verified_results.append(res)

        response_text = f"<b>Stores Found:</b>\n\n"
        for idx, item in enumerate(verified_results, start=1):
            gateways_str = " | ".join(item["gateways"])
            badge = "🟢" if "Shop Pay / Shopify" in item["gateways"] else "🔵"
            response_text += f"{idx}. {item['url']}\n   └ <b>{badge} Gateway:</b> {gateways_str}\n\n"

        await status_msg.edit_text(response_text, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("Search failed. Please try again in a few moments.")

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    if TOKEN:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("search", search_stores))
        print("Bot Started!")
        app.run_polling()
    else:
        print("BOT_TOKEN is missing!")
