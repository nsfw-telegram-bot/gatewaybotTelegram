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

GATEWAYS = {
    "Shop Pay / Shopify": ["shop-pay", "shoppay", "cdn.shopify.com", "shopify-checkout", "shop.app/pay"],
    "Stripe": ["js.stripe.com", "stripe.com/pay", "stripe_checkout", "__stripe"],
    "PayPal": ["paypal.com/sdk", "paypalobjects.com", "paypal-button", "paypal-checkout"],
    "Adyen": ["checkoutshopper-live", "adyen.com"],
    "Razer Merchant": ["molpay", "razer.com/pay", "merchant.razer.com"]
}

async def detect_gateways(url: str) -> list:
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
    if not SERPER_API_KEY:
        return []

    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    all_urls = []
    
    # جلب حتى 10 صفحات (10 × 10 = 100 نتيجة كحد أقصى)
    async with httpx.AsyncClient(timeout=10.0) as client:
        for page in range(1, 11):
            payload = {"q": query, "num": 10, "page": page}
            try:
                response = await client.post(url, headers=headers, json=payload)
                data = response.json()
                organic = data.get("organic", [])
                
                if not organic:
                    break  # التوقف إذا لم تعد هناك نتائج في الصفحات التالية
                
                for item in organic:
                    if "link" in item and item["link"] not in all_urls:
                        all_urls.append(item["link"])
                        
                if len(all_urls) >= 100:
                    break
            except Exception as e:
                logging.error(f"Serper API Page {page} Error: {e}")
                break

    return all_urls[:100]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ البوت جاهز للبحث الموسع (حتى 100 موقع)!\n\nأرسل: <code>/search mobile legends top up</code>", parse_mode="HTML")

async def search_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = " ".join(context.args)
    if not user_query:
        await update.message.reply_text("يرجى كتابة كلمة البحث بعد الأمر.")
        return

    status_msg = await update.message.reply_text("🔍 جاري جلب كافة المتاجر المتاحة (حتى 100 موقع) وفحص البوابات...")

    urls = await search_serper_up_to_100(user_query)

    if not urls:
        await status_msg.edit_text("لم يتم العثور على نتائج.")
        return

    await status_msg.edit_text(f"⚡ تم جلب {len(urls)} موقعاً، جاري الفحص العميق للبوابات...")

    results_text = []
    current_chunk = f"<b>النتائج المكتشفة ({len(urls)} موقع):</b>\n\n"

    # فحص المواقع بالتوازي لتسريع العملية
    tasks = [detect_gateways(url) for url in urls]
    gateways_list = await asyncio.gather(*tasks)

    for idx, (url, gateways) in enumerate(zip(urls, gateways_list), start=1):
        gw_str = " | ".join(gateways)
        badge = "🟢" if "Shop Pay / Shopify" in gateways else "🔵"
        entry = f"{idx}. {url}\n   └ <b>{badge} Gateways:</b> {gw_str}\n\n"
        
        # تقسيم الرسائل لتجنب تجاوز حد تليجرام (4096 حرف)
        if len(current_chunk) + len(entry) > 3900:
            results_text.append(current_chunk)
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
