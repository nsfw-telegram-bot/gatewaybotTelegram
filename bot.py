import os
import logging
import httpx
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging setup
logging.basicConfig(level=logging.INFO)

SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Supported Gateways & Signatures
GATEWAYS = {
    "Shop Pay / Shopify": ["shop-pay", "shoppay", "cdn.shopify.com", "shopify-checkout", "shop.app/pay"],
    "Stripe": ["js.stripe.com", "stripe.com/pay", "stripe_checkout", "__stripe"],
    "PayPal": ["paypal.com/sdk", "paypalobjects.com", "paypal-button", "paypal-checkout"],
    "Adyen": ["checkoutshopper-live", "adyen.com"],
    "Razer Merchant": ["molpay", "razer.com/pay", "merchant.razer.com"]
}

async def detect_gateways(url: str) -> list:
    """Deep inspect source code to detect active payment gateways."""
    detected = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=4.0, verify=False) as client:
            response = await client.get(url)
            html = response.text.lower()
            for name, signatures in GATEWAYS.items():
                if any(sig in html for sig in signatures):
                    detected.append(name)
    except Exception:
        return ["Protected / Timeout"]
    
    return detected if detected else ["Custom / Unknown"]

async def search_serper_up_to_100(query: str) -> list:
    """Fetch up to 100 search result URLs from Serper API."""
    if not SERPER_API_KEY:
        return []

    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    all_urls = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for page in range(1, 11):
            payload = {"q": query, "num": 10, "page": page}
            try:
                response = await client.post(url, headers=headers, json=payload)
                data = response.json()
                organic = data.get("organic", [])
                
                if not organic:
                    break
                
                for item in organic:
                    if "link" in item and item["link"] not in all_urls:
                        all_urls.append(item["link"])
                        
                if len(all_urls) >= 100:
                    break
            except Exception as e:
                logging.error(f"Serper API Error (Page {page}): {e}")
                break

    return all_urls[:100]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Professional English Start Message."""
    welcome_text = (
        "⚙️ <b>GATEWAY INSPECTOR BOT v2.0</b>\n"
        "─────────────────────────────\n"
        "Welcome! I discover gaming marketplaces and deep-inspect active payment gateways.\n\n"
        "💡 <b>Usage Command:</b>\n"
        "<code>/search mobile legends top up</code>\n\n"
        "🎯 <b>Features:</b>\n"
        "• Real-time source code scraping\n"
        "• Deep gateway detection (Shop Pay, Stripe, PayPal, etc.)\n"
        "• Deep search capacity up to 100 stores"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search and inspect gateways with professional UI."""
    user_query = " ".join(context.args)
    if not user_query:
        await update.message.reply_text("⚠️ <b>Please specify a search query.</b>\nExample: <code>/search game top up store</code>", parse_mode="HTML")
        return

    status_msg = await update.message.reply_text("🌐 <i>Fetching marketplaces across the web (Up to 100 targets)...</i>", parse_mode="HTML")

    urls = await search_serper_up_to_100(user_query)

    if not urls:
        await status_msg.edit_text("❌ <b>No targets found.</b> Try using different search keywords.", parse_mode="HTML")
        return

    await status_msg.edit_text(f"🔍 <b>Discovered {len(urls)} targets.</b>\n⚡ <i>Executing deep gateway inspection...</i>", parse_mode="HTML")

    # Concurrent inspection
    tasks = [detect_gateways(url) for url in urls]
    gateways_list = await asyncio.gather(*tasks)

    results_text = []
    current_chunk = f"🚀 <b>INSPECTION RESULTS ({len(urls)} Targets Analyzed):</b>\n\n"

    for idx, (url, gateways) in enumerate(zip(urls, gateways_list), start=1):
        gw_str = " | ".join(gateways)
        badge = "🟢" if "Shop Pay / Shopify" in gateways else "🔵"
        entry = f"<b>[{idx:02d}]</b> {url}\n└ <b>{badge} Gateways:</b> <code>{gw_str}</code>\n\n"
        
        # Split message if exceeding Telegram capacity (4096 chars)
        if len(current_chunk) + len(entry) > 3800:
            results_text.append(current_chunk)
            current_chunk = entry
        else:
            current_chunk += entry

    if current_chunk:
        results_text.append(current_chunk)

    # Deliver output chunks
    for i, chunk in enumerate(results_text):
        if i == 0:
            await status_msg.edit_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await update.message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    if TOKEN:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("search", search_stores))
        app.run_polling(drop_pending_updates=True)
            current_chunk = entry
        else:
            current_chunk += entry

    if current_chunk:
        results_text.append(current_chunk)

    # إرسال الرسائل المقسمة
    for i, chunk in enumerate(results_text):
        if i == 0:
            await status_msg.edit_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await update.message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    if TOKEN:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("search", search_stores))
        app.run_polling(drop_pending_updates=True)
