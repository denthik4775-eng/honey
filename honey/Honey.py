import logging
import json
import os
import re

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


BOT_TOKEN = "--------"
ADMIN_ID = ---------          

VOTE_LIMIT = 7
MAX_SAMPLES = 60
RESULTS_FILE = "honey_votes.json"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


votes = {i: 0 for i in range(1, MAX_SAMPLES + 1)}   
user_votes = {}                                    


def load_votes():
    """Загрузка голосов из файла при старте бота."""
    global votes, user_votes
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            file_votes = data.get("votes", {})
            for k, v in file_votes.items():
                votes[int(k)] = int(v)
            user_votes = {int(k): int(v) for k, v in data.get("user_votes", {}).items()}
        except Exception as e:
            logger.error(f"Ошибка загрузки файла голосов: {e}")


def save_votes():
    """Сохранение голосов в файл после каждого голосования."""
    try:
        data = {
            "votes": votes,
            "user_votes": user_votes,
        }
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения файла голосов: {e}")


def make_main_keyboard():
    keyboard = [
        [KeyboardButton("📊 Результаты"), KeyboardButton("ℹ️ Помощь")],
        [KeyboardButton("🔄 Меню"), KeyboardButton("📈 Статистика")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_votes()

    user_id = update.effective_user.id
    used = user_votes.get(user_id, 0)
    remain = max(0, VOTE_LIMIT - used)

    await update.message.reply_text(
        "🍯 *Конкурс мёда!*\n\n"
        f"👤 Ваши голоса: {used}/{VOTE_LIMIT} (осталось: *{remain}*)\n\n"
        "💡 *Напишите номер мёда (1–60):*\n"
        "• Сканируйте QR-код баночки\n"
        "• Введите номер\n"
        "• Получите контакты пчеловода\n\n"
        "*Примеры:* `5`, `42`, `60`, `Мёд 3`",
        parse_mode="Markdown",
        reply_markup=make_main_keyboard(),
    )


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Любое текстовое сообщение: выдёргиваем первое число и считаем голос."""
    load_votes()

    user_id = update.effective_user.id
    used = user_votes.get(user_id, 0)
    text = (update.message.text or "").strip()

    nums = re.findall(r"\d+", text)
    if not nums:
        await update.message.reply_text(
            "❌ Напишите номер мёда (число от 1 до 60)."
        )
        return

    sample_num = int(nums[0])

    if not 1 <= sample_num <= MAX_SAMPLES:
        await update.message.reply_text(
            f"❌ Номер мёда должен быть от 1 до {MAX_SAMPLES}."
        )
        return

    if used >= VOTE_LIMIT:
        await update.message.reply_text(
            f"❌ Лимит голосов исчерпан. Вы уже отдали {VOTE_LIMIT} голосов."
        )
        return

    votes[sample_num] = votes.get(sample_num, 0) + 1
    user_votes[user_id] = used + 1
    save_votes()

    try:
        await context.bot.send_message(
            ADMIN_ID,
            "🗳️ *Новый голос!*\n"
            f"Мёд №{sample_num}\n"
            f"Всего голосов за него: *{votes[sample_num]}*\n"
            f"Пользователь: `{user_id}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админу: {e}")

    beekeeper_info = {
        1: "🍯 Иванов И.И.\n🏠 Медовый Рай\n📞 +7(900)123-45-67",
        2: "🍯 Петрова А.С.\n🏠 Золотая Пчела\n📞 +7(900)234-56-78",
        3: "🍯 Сидоров В.П.\n🏠 Лесная Пасека\n📞 +7(900)345-67-89",
    }.get(sample_num, "📞 Контакты по этому мёду уточняйте у организаторов.")

    remain = max(0, VOTE_LIMIT - user_votes[user_id])

    await update.message.reply_text(
        f"✅ *Голос за Мёд №{sample_num} принят!*\n\n"
        f"👤 Осталось голосов: *{remain}*\n\n"
        f"{beekeeper_info}\n\n"
        "➡️ Можете ввести следующий номер мёда.",
        parse_mode="Markdown",
    )


async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_votes()

    top = sorted(votes.items(), key=lambda x: x[1], reverse=True)[:5]
    text = "📊 *ТОП‑5:* \n\n"

    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    for i, (num, count) in enumerate(top):
        text += f"{medals[i]} Мёд №{num}: *{count}* голосов\n"

    if update.effective_user.id == ADMIN_ID:
        text += f"\n👥 Уникальных голосующих: {len(user_votes)}"

    await update.message.reply_text(text, parse_mode="Markdown")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Команда только для организатора.")
        return

    load_votes()

    text = "📈 *ПОЛНАЯ СТАТИСТИКА:*\n\n"
    for num in range(1, MAX_SAMPLES + 1):
        cnt = votes.get(num, 0)
        if cnt > 0:
            text += f"Мёд №{num}: {cnt}\n"

    text += f"\n👥 Уникальных голосующих: {len(user_votes)}"

    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Как голосовать:*\n\n"
        "1️⃣ Сканируйте QR‑код на баночке\n"
        "2️⃣ Напишите номер мёда (можно просто число, можно `Мёд 3`)\n"
        "3️⃣ У вас максимум 7 голосов\n"
        "4️⃣ Сразу после голоса получите контакты пчеловода\n\n"
        "*Команды:*\n"
        "/start или /menu — главное меню\n"
        "📊 Результаты — ТОП‑5\n"
        "/stats или 📈 Статистика — полная статистика (только для организатора)",
        parse_mode="Markdown",
        reply_markup=make_main_keyboard(),
    )


def main():
    load_votes()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", admin_stats))

    app.add_handler(MessageHandler(filters.Regex(r"^📊 Результаты$"), show_results))
    app.add_handler(MessageHandler(filters.Regex(r"^ℹ️ Помощь$"), help_command))
    app.add_handler(MessageHandler(filters.Regex(r"^🔄 Меню$"), start))
    app.add_handler(MessageHandler(filters.Regex(r"^📈 Статистика$"), admin_stats))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    print("🍯 Бот конкурса мёда запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()

