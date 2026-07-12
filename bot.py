import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("PARTNER_BOT_TOKEN")
MANAGER_CHAT_ID = os.environ.get("MANAGER_CHAT_ID")

PARTNERS = {
    "ws1": "WebStudio ONE",
    "ws2": "Digital Factory",
    "ws3": "Студия Прайм",
}

# Шаги анкеты
STEPS = ["company_name", "niche", "website", "task", "budget", "contact_name", "contact_phone", "comment"]


def get_partner_name(partner_id):
    return PARTNERS.get(partner_id, f"Партнёр ({partner_id})")


async def show_menu(update, context):
    partner_id = context.user_data.get("partner_id")
    partner_name = get_partner_name(partner_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить нового клиента", callback_data="start_form")],
        [InlineKeyboardButton("📞 Связаться с нами", url="https://t.me/highlight_media")],
    ])
    text = (
        f"🏢 *Партнёрский портал Highlight Media*\n"
        f"Студия: *{partner_name}*\n\n"
        f"Выберите действие:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    args = context.args
    partner_id = args[0] if args else context.user_data.get("partner_id")

    if not partner_id or partner_id not in PARTNERS:
        await update.message.reply_text(
            "❌ Ссылка недействительна.\n\n"
            "Используйте персональную ссылку от Highlight Media."
        )
        return

    context.user_data["partner_id"] = partner_id
    context.user_data["step"] = None
    context.user_data["form"] = {}
    await show_menu(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start_form":
        if not context.user_data.get("partner_id"):
            await query.edit_message_text("❌ Сначала откройте бота по вашей партнёрской ссылке.")
            return
        context.user_data["step"] = "company_name"
        context.user_data["form"] = {}
        await query.edit_message_text(
            "📝 *Новая заявка*\n\nВведите *название компании клиента*:",
            parse_mode="Markdown"
        )
        return

    if data == "menu":
        context.user_data["step"] = None
        await show_menu(update, context)
        return

    if data.startswith("task_"):
        context.user_data["form"]["task"] = data.replace("task_", "")
        context.user_data["step"] = "budget"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("$500–1000", callback_data="budget_$500–1000")],
            [InlineKeyboardButton("$1000–3000", callback_data="budget_$1000–3000")],
            [InlineKeyboardButton("$3000+", callback_data="budget_$3000+")],
            [InlineKeyboardButton("Не определён", callback_data="budget_Не определён")],
        ])
        await query.edit_message_text(
            "💰 *Бюджет клиента в месяц?*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    if data.startswith("budget_"):
        context.user_data["form"]["budget"] = data.replace("budget_", "")
        context.user_data["step"] = "contact_name"
        await query.edit_message_text(
            "👤 Введите *имя контактного лица* клиента:",
            parse_mode="Markdown"
        )
        return


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    # Не авторизован
    if not context.user_data.get("partner_id"):
        await update.message.reply_text(
            "❌ Используйте вашу персональную ссылку для входа."
        )
        return

    step = context.user_data.get("step")

    # Нет активного шага — показываем меню
    if not step:
        await show_menu(update, context)
        return

    text = update.message.text.strip()
    form = context.user_data.setdefault("form", {})

    if step == "company_name":
        form["company_name"] = text
        context.user_data["step"] = "niche"
        await update.message.reply_text(
            "🏷 В какой *сфере* работает клиент?\n(например: ресторан, строительство, медицина)",
            parse_mode="Markdown"
        )

    elif step == "niche":
        form["niche"] = text
        context.user_data["step"] = "website"
        await update.message.reply_text(
            "🌐 Укажите *сайт* клиента (если нет — напишите «нет»):",
            parse_mode="Markdown"
        )

    elif step == "website":
        form["website"] = text
        context.user_data["step"] = "task"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("SMM", callback_data="task_SMM"),
             InlineKeyboardButton("Реклама", callback_data="task_Реклама")],
            [InlineKeyboardButton("Стратегия", callback_data="task_Стратегия"),
             InlineKeyboardButton("Брендинг", callback_data="task_Брендинг")],
            [InlineKeyboardButton("Видео", callback_data="task_Видео"),
             InlineKeyboardButton("Комплекс", callback_data="task_Комплекс")],
        ])
        await update.message.reply_text(
            "🎯 *Задача клиента?*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    elif step == "contact_name":
        form["contact_name"] = text
        context.user_data["step"] = "contact_phone"
        await update.message.reply_text(
            "📞 *Телефон или Telegram* контактного лица:",
            parse_mode="Markdown"
        )

    elif step == "contact_phone":
        form["contact_phone"] = text
        context.user_data["step"] = "comment"
        await update.message.reply_text(
            "💬 *Комментарий* для Highlight Media\n(особые пожелания или напишите «нет»):",
            parse_mode="Markdown"
        )

    elif step == "comment":
        form["comment"] = text
        context.user_data["step"] = None

        partner_id = context.user_data.get("partner_id")
        partner_name = get_partner_name(partner_id)

        card = (
            f"🤝 *Новая заявка от партнёра!*\n\n"
            f"🏢 *Партнёр:* {partner_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏷 *Компания:* {form.get('company_name')}\n"
            f"📌 *Сфера:* {form.get('niche')}\n"
            f"🌐 *Сайт:* {form.get('website')}\n"
            f"🎯 *Задача:* {form.get('task')}\n"
            f"💰 *Бюджет:* {form.get('budget')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Контакт:* {form.get('contact_name')}\n"
            f"📞 *Телефон/TG:* {form.get('contact_phone')}\n"
            f"💬 *Комментарий:* {form.get('comment')}"
        )

        await context.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=card,
            parse_mode="Markdown"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить нового клиента", callback_data="start_form")],
            [InlineKeyboardButton("📞 Связаться с нами", url="https://t.me/highlight_media")],
        ])

        await update.message.reply_text(
            f"✅ *Заявка принята!*\n\n"
            f"Компания: *{form.get('company_name')}*\n"
            f"Задача: *{form.get('task')}*\n"
            f"Бюджет: *{form.get('budget')}*\n\n"
            f"Наш менеджер свяжется с клиентом в течение рабочего дня.\n\n"
            f"Спасибо за сотрудничество! 🙌\n"
            f"_Highlight Media_",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

        context.user_data["form"] = {}


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    if not context.user_data.get("partner_id"):
        await update.message.reply_text("❌ Используйте вашу персональную ссылку для входа.")
        return
    context.user_data["step"] = None
    await show_menu(update, context)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
