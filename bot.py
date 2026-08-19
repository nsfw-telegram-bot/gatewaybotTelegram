import os
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from googlesearch import search

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Supported Gateways & Signatures Dictionary
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
    """Inspects the website source code to identify all active payment gateways."""
    detected = []
    
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=8.0) as client:
            response = await client.get(url)
            html = response.text.lower()

            for name, signatures in GATEWAYS.items():
                if any(sig in html for sig in signatures):
                    detected.append(name)

    except Exception:
        return {"url": url, "gateways": ["Timeout / Protected"], "status": "Error"}

    if not detected:
        detected.append("Custom / Unknown Gateway")

    return {"url": url, "gateways": detected, "status": "Success"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ <b>Advanced Multi-Gateway Gaming Store Finder</b>\n\n"
        "Send /search with any keyword. The bot will automatically inspect and identify the payment gateways used on each site.\n\n"
        "<b>Examples:</b>\n"
        "• <code>/search mobile legends top up</code>\n"
        "• <code>/search razer gold shop pay</code>",
        parse_mode="HTML"
    )

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = " ".join(context.args)
    
    if not user_query:
        await update.message.reply_text("Please provide a query.\nExample: <code>/search genshin top up</code>", parse_mode="HTML")
        return

    status_msg = await update.message.reply_text(f"🔍 Searching Google & inspecting site gateways for: <code>{user_query}</code>...", parse_mode="HTML")

    # Dynamic search query optimizer
    if "shopify" not in user_query.lower() and "shop pay" not in user_query.lower():
        dork_query = f'{user_query} "top up" OR "gaming store"'
    else:
        dork_query = user_query

    raw_urls = []
    try:
        for url in search(dork_query, num_results=12):
            raw_urls.append(url)
            
        if not raw_urls:
            await status_msg.edit_text("No matching stores found.")
            return

        verified_results = []
        for url in raw_urls:
            res = await detect_gateways(url)
            verified_results.append(res)

        response_text = f"<b>Stores Found & Gateways Detected:</b>\n\n"
        for idx, item in enumerate(verified_results, start=1):
            url = item["url"]
            gateways_str = " | ".join(item["gateways"])
            
            # Highlight Shop Pay / Shopify if present
            if "Shop Pay / Shopify" in item["gateways"]:
                badge = f"🟢 <b>[{gateways_str}]</b>"
            elif item["gateways"][0] == "Timeout / Protected":
                badge = "🔴 <i>[Access Blocked / Protection On]</i>"
            else:
                badge = f"🔵 <b>[{gateways_str}]</b>"

            response_text += f"{idx}. {url}\n   └ <b>Gateway:</b> {badge}\n\n"

        await status_msg.edit_text(response_text, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        logging.error(f"Search error: {e}")
        await status_msg.edit_text("An error occurred during search and inspection. Please try again.")

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    
    if not TOKEN:
        print("Error: BOT_TOKEN is missing!")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_stores))
    
    print("Multi-Gateway Inspector Bot is running...")
    app.run_polling()

