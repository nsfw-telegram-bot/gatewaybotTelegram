import os
import logging
import httpx
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# موسعة وتشمل توقيعات دقيقة لبوابات الدفع
GATEWAYS = {
    "Shop Pay / Shopify": ["shop-pay", "shoppay", "cdn.shopify.com", "shopify-checkout", "shop.app/pay"],
    "Stripe": ["js.stripe.com", "stripe.com/pay", "stripe_checkout", "__stripe", "pay.stripe.com"],
    "PayPal": ["paypal.com/sdk", "paypalobjects.com", "paypal-button", "paypal-checkout"],
    "Adyen": ["checkoutshopper-live", "adyen.com", "adyen-component"],
    "Razer Merchant / MOLPay": ["molpay", "razer.com/pay", "merchant.razer.com"],
    "Square": ["squareupsandbox.com", "squareup.com", "sq-payment-form"],
    "Authorize.Net": ["authorizenet", "accept.authorize.net"],
    "Checkout.com": ["checkout.com", "frames.checkout.com"]
}

async def deep_inspect_single_url(url: str) -> dict:
    """فحص عميق ومفصل لرابط موجه مفرد."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    detected = []
    headers_info = []
    
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=8.0, verify=False) as client:
            response = await client.get(url)
            html = response.text.lower()
            
            # 1. فحص توقيعات البوابات في كود HTML
            for name, signatures in GATEWAYS.items():
                if any(sig in html for sig in signatures):
                    detected.append(name)
            
            # 2. فحص العناوين (Headers) لمؤشرات إضافية
            server = response.headers.get("Server", "Unknown")
            if "cloudflare" in server.lower():
                headers_info.append("Protected by Cloudflare")
            if "shopify" in response.headers.get("X-ShopId", "").lower() or "myshopify" in html:
                if "Shop Pay / Shopify" not in detected:
                    detected.append("Shop Pay / Shopify")

            final_url = str(response.url)

            return {
                "status": "Success",
                "final_url": final_url,
                "gateways": detected if detected else ["Custom / Unknown"],
                "info": headers_info
            }

    except Exception as e:
        return {
            "status": "Error",
            "error_msg": str(e),
            "gateways": ["Protected / Timeout"],
            "info": []
        }

async def detect_gateways(url: str, semaphore: asyncio.Semaphore) -> list:
    """فحص سريع مخصص لأمر البحث الجماعي."""
    async with semaphore:
        res = await deep_inspect_single_url(url)
        return res["gateways"]

async def search_serper_up_to_100(query: str) -> list:
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
                logging.error(f"Serper API Error: {e}")
                break

    return all_urls[:100]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚙️ <b>GATEWAY INSPECTOR BOT v2.5</b>\n"
        "─────────────────────────────\n"
        "Welcome! Choose an option to inspect gateways:\n\n"
        "🔍 <b>Bulk Store Search:</b>\n"
        "<code>/search mobile legends top up</code>\n\n"
        "🎯 <b>Deep Single Target Inspection:</b>\n"
        "<code>/check https://example-store.com</code>"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")

async def check_single_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر جديد لفحص موقع واحد بدقة وعمق"""
    if not context.args:
        await update.message.reply_text("⚠️ <b>Please specify a target URL.</b>\nExample: <code>/check https://example.com</code>", parse_mode="HTML")
        return

    target_url = context.args[0]
    status_msg = await update.message.reply_text(f"🔍 <i>Executing deep inspection on:</i>\n<code>{target_url}</code>", parse_mode="HTML")

    result = await deep_inspect_single_url(target_url)

    if result["status"] == "Error":
        report = (
            "🚨 <b>INSPECTION FAILED</b>\n"
            "─────────────────────────────\n"
            f"<b>Target:</b> {target_url}\n"
            f"<b>Status:</b> Request Timeout or Cloud Shield Protection.\n"
        )
    else:
        gw_str = " | ".join(result["gateways"])
        badge = "🟢" if "Shop Pay / Shopify" in result["gateways"] else "🔵"
        info_str = "\n• " + "\n• ".join(result["info"]) if result["info"] else " None"

        report = (
            "🎯 <b>SINGLE TARGET INSPECTION REPORT</b>\n"
            "─────────────────────────────\n"
            f"🔗 <b>Target:</b> {result['final_url']}\n"
            f"💳 <b>Detected Gateways:</b>\n└ <b>{badge}</b> <code>{gw_str}</code>\n\n"
            f"🛡️ <b>Security / Extra Info:</b>{info_str}\n"
            "─────────────────────────────"
        )

    await status_msg.edit_text(report, parse_mode="HTML", disable_web_page_preview=True)

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = " ".join(context.args)
    if not user_query:
        await update.message.reply_text("⚠️ <b>Please specify a search query.</b>\nExample: <code>/search game top up</code>", parse_mode="HTML")
        return

    status_msg = await update.message.reply_text("🌐 <i>Fetching marketplaces (Up to 100 targets)...</i>", parse_mode="HTML")

    urls = await search_serper_up_to_100(user_query)

    if not urls:
        await status_msg.edit_text("❌ <b>No targets found.</b>", parse_mode="HTML")
        return

    await status_msg.edit_text(f"🔍 <b>Discovered {len(urls)} targets.</b>\n⚡ <i>Executing safe deep inspection...</i>", parse_mode="HTML")

    semaphore = asyncio.Semaphore(10)
    tasks = [detect_gateways(url, semaphore) for url in urls]
    gateways_list = await asyncio.gather(*tasks)

    results_text = []
    current_chunk = f"🚀 <b>INSPECTION RESULTS ({len(urls)} Targets Analyzed):</b>\n\n"

    for idx, (url, gateways) in enumerate(zip(urls, gateways_list), start=1):
        gw_str = " | ".join(gateways)
        badge = "🟢" if "Shop Pay / Shopify" in gateways else "🔵"
        entry = f"<b>[{idx:02d}]</b> {url}\n└ <b>{badge} Gateways:</b> <code>{gw_str}</code>\n\n"
        
        if len(current_chunk) + len(entry) > 3800:
            results_text.append(current_chunk)
            current_chunk = entry
        else:
            current_chunk += entry

    if current_chunk:
        results_text.append(current_chunk)

    for i, chunk in enumerate(results_text):
        if i == 0:
            await status_msg.edit_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await update.message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
        await asyncio.sleep(0.5)

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    if TOKEN:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("search", search_stores))
        app.add_handler(CommandHandler("check", check_single_store))
        app.run_polling(drop_pending_updates=True)
