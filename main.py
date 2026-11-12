import asyncio
import io
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, ADMIN_ID
from gemini_service import GeminiService
from memory import (
    init_db,
    add_message,
    get_history,
    get_memory_stats,
    clear_user_memory,
    upsert_user,
    log_interaction,
    get_admin_stats,
    get_recent_users,
    get_recent_chat_logs,
    get_all_user_ids
)
from keyboards import (
    get_main_keyboard,
    get_clear_confirm_keyboard,
    get_admin_panel_keyboard,
    get_chat_logs_keyboard
)
from formatter import markdown_to_telegram_html, strip_all_markdown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
gemini = GeminiService()

MAX_DOC_SIZE = 2 * 1024 * 1024      # 2 MB hujjatlar uchun
MAX_AUDIO_SIZE = 20 * 1024 * 1024   # 20 MB audio va ovozli xabarlar uchun

class BroadcastState(StatesGroup):
    waiting_for_message = State()

def make_progress_bar(percent: int, length: int = 10) -> str:
    filled = int(length * (percent / 100))
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {percent}%"

async def safe_reply(message: Message, raw_text: str):
    """Telegram HTML formatida xavfsiz javob yuborish."""
    html_text = markdown_to_telegram_html(raw_text)
    max_length = 4000
    chunks = [html_text[i:i + max_length] for i in range(0, len(html_text), max_length)]
    
    for chunk in chunks:
        try:
            await message.reply(chunk, parse_mode=ParseMode.HTML)
        except TelegramBadRequest as e:
            logger.warning(f"HTML formatlash xatosi: {e}. Toza matn jo'natilmoqda.")
            clean_chunk = strip_all_markdown(raw_text)
            await message.reply(clean_chunk[:4000])

@dp.message(CommandStart())
async def handle_start(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    
    welcome_text = (
        "<b>Assalomu alaykum!</b>\n\n"
        "Men Google Gemini sun'iy intellekti bilan ishlovchi shaxsiy yordamchingizman.\n\n"
        "✨ <b>4-bosqich yangiliklari:</b>\n"
        "• 🌐 <b>Internetdan qidiruv:</b> So'nggi yangiliklar, ob-havo va faktlarni Google qidiruvi orqali topib beraman.\n"
        "• 🎙 <b>Ovozli muloqot:</b> Ovozli xabaringizni to'liq o'zbek tilida transkripsiya qilib, savolingizga javob qaytaraman.\n"
        "• ⚡ <b>Zaxira modellar:</b> Serverda yuklanish bo'lsa ham uzilishlarsiz, tez va barqaror ishlayman.\n"
        "• 🧠 <b>Aqlli xotira:</b> So'nggi 50 ta xabarni eslab qolaman.\n\n"
        "<i>Menga istalgan savolingizni matn, rasm, fayl yoki ovozli xabar ko'rinishida yuborishingiz mumkin!</i>"
    )
    if user.id == ADMIN_ID:
        welcome_text += "\n\n👑 <i>Siz botsizda <b>Admin</b> huquqiga egasiz!</i>"

    await message.answer(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard(user.id)
    )

# --- XOTIRA BOSHQARUVI ---

@dp.message(F.text == "📊 Xotira holati")
async def handle_memory_status(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    stats = get_memory_stats(user.id)
    bar = make_progress_bar(stats["percent"])
    
    status_text = (
        "🧠 <b>Xotira boshqaruv paneli</b>\n\n"
        f"📊 <b>To'lganlik darajasi:</b>\n<code>{bar}</code>\n\n"
        f"💬 <b>Saqlangan xabarlar:</b> <code>{stats['count']} / {stats['max']} ta</code>\n"
        f"📉 <b>Minimal saqlash:</b> 20 ta xabar\n"
        f"📈 <b>Maksimal sig'im:</b> 50 ta xabar\n\n"
    )
    if stats["is_full"]:
        status_text += "⚠️ <i>Xotira to'lgan. Eng eski xabarlar avtomatik yangilanib boradi.</i>"
    elif stats["count"] == 0:
        status_text += "ℹ️ <i>Xotira hozircha bo'sh.</i>"
    else:
        status_text += "✅ <i>Xotira me'yorida. Suhbat konteksti to'liq esda saqlanmoqda.</i>"
        
    await message.answer(status_text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(user.id))

@dp.message(F.text == "🗑 Xotirani tozalash")
async def handle_clear_request(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    stats = get_memory_stats(user.id)
    if stats["count"] == 0:
        await message.answer("ℹ️ Xotirangiz allaqachon bo'sh.", reply_markup=get_main_keyboard(user.id))
        return

    text = (
        f"⚠️ <b>Xotirada {stats['count']} ta xabar saqlanmoqda.</b>\n\n"
        "Rostdan ham suhbat xotirasini tozalamoqchimisiz?"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_clear_confirm_keyboard())

@dp.callback_query(F.data == "confirm_clear_memory")
async def handle_confirm_clear(callback: CallbackQuery):
    clear_user_memory(callback.from_user.id)
    await callback.message.edit_text("✅ <b>Xotira muvaffaqiyatli tozalandi!</b>", parse_mode=ParseMode.HTML)
    await callback.answer("Tozalandi")

@dp.callback_query(F.data == "cancel_clear_memory")
async def handle_cancel_clear(callback: CallbackQuery):
    await callback.message.edit_text("❌ Tozalash bekor qilindi.", parse_mode=ParseMode.HTML)
    await callback.answer("Bekor qilindi")

@dp.message(F.text == "ℹ️ Bot haqida")
async def handle_about(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    about_text = (
        "🤖 <b>Titan Gemini Bot (4-bosqich):</b>\n\n"
        "• <b>Dvigatel:</b> Google Gemini Sun'iy Intellekti (Search Grounding ulandi)\n"
        "• <b>Muloqot tili:</b> Faqat O'zbek tili 🇺🇿\n"
        "• <b>Internetdan qidiruv:</b> Haqiqiy vaqt rejimida Google orqali ma'lumot izlash\n"
        "• <b>Ovozli xabarlar:</b> 20 MB gacha transkripsiya + to'liq javob\n"
        "• <b>Fayllar sig'imi:</b> PDF, Word, Excel, TXT (2 MB gacha)\n"
        "• <b>Xotira:</b> So'nggi 20-50 ta suhbat xabari"
    )
    await message.answer(about_text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(user.id))

# --- ADMIN PANEL ---

@dp.message((F.text == "👑 Admin Panel") | Command("admin"))
async def handle_admin_panel(message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.reply("⛔ Kechirasiz, ushbu bo'lim faqat bot administratori uchun ochiq.")
        return

    admin_text = (
        "👑 <b>Admin Boshqaruv Paneli</b>\n\n"
        "Quyidagi menyu orqali bot foydalanuvchilari statistikasi, jonli suhbatlar monitoringi "
        "va umumiy e'lonlar yuborish imkoniyatidan foydalanishingiz mumkin:"
    )
    await message.answer(
        admin_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_panel_keyboard()
    )

@dp.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    stats = get_admin_stats()
    text = (
        "📊 <b>Umumiy Bot Statistikasi:</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> <code>{stats['total_users']} ta</code>\n"
        f"💬 <b>Jami savol-javoblar:</b> <code>{stats['total_logs']} ta</code>\n"
        f"🔥 <b>Bugun faol bo'lganlar:</b> <code>{stats['today_active']} ta</code>\n"
    )
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def handle_admin_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    users = get_recent_users(limit=10)
    if not users:
        text = "👥 <b>Hozircha foydalanuvchilar yo'q.</b>"
    else:
        text = "👥 <b>So'nggi faol foydalanuvchilar:</b>\n\n"
        for idx, u in enumerate(users, 1):
            uname = f"@{u['username']}" if u['username'] else "Mavjud emas"
            text += (
                f"{idx}. <b>{u['full_name']}</b> ({uname})\n"
                f"   ├ ID: <code>{u['user_id']}</code>\n"
                f"   ├ Xabarlar soni: <code>{u['msg_count']} ta</code>\n"
                f"   └ Oxirgi kirish: <code>{u['last_seen']}</code>\n\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_chats_"))
async def handle_admin_chats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    offset = int(callback.data.split("_")[-1])
    logs = get_recent_chat_logs(limit=5, offset=offset)
    total_logs = get_admin_stats()["total_logs"]
    has_more = (offset + 5) < total_logs

    if not logs:
        text = "💬 <b>Hozircha savol-javoblar qayd etilmagan.</b>"
    else:
        text = f"💬 <b>Suhbatlar monitoringi ({offset + 1} - {min(offset + 5, total_logs)} / {total_logs}):</b>\n\n"
        for log in logs:
            user_question = log['user_text'][:150] + ("..." if len(log['user_text']) > 150 else "")
            bot_answer = log['bot_response'][:180] + ("..." if len(log['bot_response']) > 180 else "")
            text += (
                f"👤 <b>{log['full_name']}</b> (<code>{log['user_id']}</code>) | <i>{log['msg_type']}</i>\n"
                f"❓ <b>Savol:</b> {user_question}\n"
                f"🤖 <b>Javob:</b> {bot_answer}\n"
                f"⏰ <code>{log['created_at']}</code>\n"
                f"{'─' * 25}\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_logs_keyboard(offset, has_more)
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_back")
async def handle_admin_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "👑 <b>Admin Boshqaruv Paneli:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_close")
async def handle_admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Yopildi")

@dp.callback_query(F.data == "admin_broadcast")
async def handle_broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.answer(
        "📢 <b>Barcha foydalanuvchilarga xabar tarqatish:</b>\n\n"
        "Iltimos, yubormoqchi bo'lgan xabaringizni yozib yuboring (yoki bekor qilish uchun /cancel deb yozing):",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.reply("Xabar tarqatish bekor qilindi.")
        return

    user_ids = get_all_user_ids()
    sent_count = 0
    fail_count = 0

    progress_msg = await message.reply("⏳ Xabar tarqatilmoqda...")
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=message.text, parse_mode=ParseMode.HTML)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail_count += 1

    await state.clear()
    await progress_msg.edit_text(
        f"✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"• Yuborildi: <code>{sent_count} ta</code>\n"
        f"• Yuborilmadi: <code>{fail_count} ta</code>",
        parse_mode=ParseMode.HTML
    )

# --- MULTIMODAL VA XABARLAR HANDLERLARI ---

# 1. Rasmlar
@dp.message(F.photo)
async def handle_photo(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    caption = message.caption or ""
    photo = message.photo[-1]

    if photo.file_size and photo.file_size > MAX_DOC_SIZE:
        size_mb = photo.file_size / (1024 * 1024)
        await message.reply(
            f"⚠️ <b>Rasm hajmi juda katta ({size_mb:.2f} MB)!</b>\n"
            "Iltimos, hajmi 2 megabaytgacha bo'lgan rasm yuboring.",
            parse_mode=ParseMode.HTML
        )
        return

    status_msg = await message.reply("🖼 <i>Rasm tahlil qilinmoqda...</i>", parse_mode=ParseMode.HTML)
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    file_io = io.BytesIO()
    await bot.download(photo.file_id, destination=file_io)
    image_bytes = file_io.getvalue()

    history = get_history(user.id)
    response_text = await gemini.analyze_image(
        image_bytes=image_bytes,
        mime_type="image/jpeg",
        caption=caption,
        history=history
    )

    add_message(user.id, "user", f"[Rasm] {caption}".strip())
    add_message(user.id, "model", response_text)
    log_interaction(user.id, user.full_name, "Rasm", caption, response_text)

    await status_msg.delete()
    await safe_reply(message, response_text)

# 2. Ovozli xabarlar va audio (Transkripsiya + Savolga javob)
@dp.message(F.voice | F.audio)
async def handle_voice_and_audio(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    audio_obj = message.voice or message.audio
    file_size = audio_obj.file_size or 0

    if file_size > MAX_AUDIO_SIZE:
        size_mb = file_size / (1024 * 1024)
        await message.reply(
            f"⚠️ <b>Audio hajmi juda katta ({size_mb:.2f} MB)!</b>\n"
            "Iltimos, hajmi 20 megabaytdan oshmaydigan audio yuboring.",
            parse_mode=ParseMode.HTML
        )
        return

    status_msg = await message.reply(
        "🎧 <b>Ovozli xabar eshitilmoqda va tahlil qilinmoqda...</b>",
        parse_mode=ParseMode.HTML
    )
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    file_io = io.BytesIO()
    await bot.download(audio_obj.file_id, destination=file_io)
    audio_bytes = file_io.getvalue()

    mime_type = getattr(audio_obj, "mime_type", None) or "audio/ogg"
    transcription, answer = await gemini.transcribe_and_answer(audio_bytes=audio_bytes, mime_type=mime_type)

    await status_msg.delete()

    # Xotiraga va admin jurnaliga yozish
    add_message(user.id, "user", f"[Ovozli xabar]: {transcription}")
    add_message(user.id, "model", answer)
    log_interaction(user.id, user.full_name, "Audio", transcription, answer)

    # Natijani chatda chiroyli ko'rsatish
    reply_text = (
        f"🎙 <b>Ovozli xabar matni (Transkripsiya):</b>\n"
        f"<i>\"{transcription}\"</i>\n\n"
        f"🤖 <b>Gemini javobi:</b>\n"
        f"{answer}"
    )

    # .txt fayl tayyorlash
    txt_content = (
        f"=== OVOZLI XABAR TRANSKRIPSIYASI ===\n"
        f"Vaqt: {message.date}\n\n"
        f"[TRANSKRIPSIYA MATNI]:\n{transcription}\n\n"
        f"[SUN'IY INTELLEKT JAVOBI]:\n{answer}\n"
    )
    txt_file = BufferedInputFile(txt_content.encode("utf-8"), filename="ovozli_xabar.txt")

    await message.reply_document(
        document=txt_file,
        caption=reply_text[:1024],
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard(user.id)
    )

    # Agar javob caption chegarasidan (1024) oshgan bo'lsa, davomini alohida matn qilib jo'natish
    if len(reply_text) > 1024:
        await safe_reply(message, reply_text[1024:])

# 3. Hujjatlar (PDF, Word, Excel, TXT)
@dp.message(F.document)
async def handle_document(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    doc = message.document
    filename = doc.file_name or "fayl"
    file_size = doc.file_size or 0
    caption = message.caption or ""

    if file_size > MAX_DOC_SIZE:
        size_mb = file_size / (1024 * 1024)
        await message.reply(
            f"⚠️ <b>Fayl hajmi 2 megabaytdan oshmasligi kerak!</b>\n"
            f"Siz yuborgan fayl: <code>{size_mb:.2f} MB</code>.\n"
            "Iltimos, hajmi 2 MB dan kam bo'lgan fayl yuboring.",
            parse_mode=ParseMode.HTML
        )
        return

    status_msg = await message.reply(
        f"📄 <i>'{filename}' hujjati o'qilmoqda va tahlil qilinmoqda...</i>",
        parse_mode=ParseMode.HTML
    )
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    file_io = io.BytesIO()
    await bot.download(doc.file_id, destination=file_io)
    doc_bytes = file_io.getvalue()

    history = get_history(user.id)
    response_text = await gemini.analyze_document(
        doc_bytes=doc_bytes,
        filename=filename,
        mime_type=doc.mime_type or "",
        caption=caption,
        history=history
    )

    add_message(user.id, "user", f"[Hujjat: {filename}] {caption}".strip())
    add_message(user.id, "model", response_text)
    log_interaction(user.id, user.full_name, "Hujjat", f"{filename}: {caption}", response_text)

    await status_msg.delete()
    await safe_reply(message, response_text)

# 4. Matnli xabarlar (Internetdan qidiruv bilan)
@dp.message(F.text)
async def handle_text(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username, user.full_name)
    user_text = message.text.strip()

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    history = get_history(user.id)
    response_text = await gemini.get_response(history=history, current_message=user_text)

    if not response_text.startswith("⚠️"):
        add_message(user.id, "user", user_text)
        add_message(user.id, "model", response_text)
        log_interaction(user.id, user.full_name, "Matn", user_text, response_text)

    await safe_reply(message, response_text)

async def handle_ping(request):
    """Render health-check va cron-job ping uchun javob."""
    return web.Response(text="Titan Bot is active and running 24/7!", status=200)

async def start_web_server():
    """Render serveri uchun fon veb-serveri."""
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Render health-check server {port}-portda ishga tushdi.")

async def main():
    logger.info("Ma'lumotlar bazasi ishga tushirilmoqda...")
    init_db()
    
    # Render Web Service va Cron-job uchun fon web-serverni ishga tushirish
    await start_web_server()
    
    logger.info("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
