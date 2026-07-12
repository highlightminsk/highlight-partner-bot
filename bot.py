import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("PARTNER_BOT_TOKEN")
MANAGER_CHAT_ID = os.environ.get("MANAGER_CHAT_ID")  # Telegram группа Highlight Media

# Шаги анкеты
(
    COMPANY_NAME,
    NICHE,
    WEBSITE,
    TASK,
    BUDGET,
    CONTACT_NAME,
    CONTACT_PHONE,
    COMMENT,
) = range(8)

# Партнёры: partner_id → название студии
PARTNERS = {
    "ws1": "WebStudio ONE",
    "ws2": "Digital Factory",
    "ws3": "Студия Прайм",
    # Добавляй новых партнёров сюда
}


def get_partner_id(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("partner_id", "unknown")


def get_partner_name(partner_id: str) -> str:
    return PARTNERS.get(partner_id, f"Партнёр ({partner_id})")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    partner_id = args[0] if args else None

    if not partner_id or partner_id not in PARTNERS:
        await update.message.reply_text(
            "❌ Ссылка недействительна.\n\n"
            "Пожалуйста, используйте персональную ссылку, "
            "которую вы получили от Highlight Media."
        )
        return ConversationHandler.END

    context.user_data["partner_id"] = partner_id
    partner_name = get_partner_name(partner_id)

    await update.message.reply_text(
        f"👋 Добро пожаловать в партнёрский портал *Highlight Media*!\n\n"
        f"Студия: *{partner_name}*\n\n"
        f"Заполните анкету на клиента — мы свяжемся с ним в течение рабочего дня.\n\n"
        f"Введите *название компании клиента*:",
        parse_mode="Markdown"
    )
    return COMPANY_NAME


async def company_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["company_name"] = update.message.text.strip()
    await update.message.reply_text("🏢 В какой *сфере* работает клиент?\n(например: ресторан, строительство, медицина)", parse_mode="Markdown")
    return NICHE


async def niche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["niche"] = update.message.text.strip()
    await update.message.reply_text("🌐 Укажите *сайт* клиента (если есть, или напишите «нет»):", parse_mode="Markdown")
    return WEBSITE


async def website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["website"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton("SMM", callback_data="task_SMM"),
         InlineKeyboardButton("Реклама", callback_data="task_Реклама")],
        [InlineKeyboardButton("Стратегия", callback_data="task_Стратегия"),
         InlineKeyboardButton("Брендинг", callback_data="task_Брендинг")],
        [InlineKeyboardButton("Видео", callback_data="task_Видео"),
         InlineKeyboardButton("Комплекс", callback_data="task_Комплекс")],
    ]
    await update.message.reply_text(
        "🎯 Какая *задача* стоит перед клиентом?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return TASK


async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_value = query.data.replace("task_", "")
    context.user_data["task"] = task_value

    keyboard = [
        [InlineKeyboardButton("$500–1000", callback_data="budget_$500–1000")],
        [InlineKeyboardButton("$1000–3000", callback_data="budget_$1000–3000")],
        [InlineKeyboardButton("$3000+", callback_data="budget_$3000+")],
        [InlineKeyboardButton("Бюджет не определён", callback_data="budget_low")],
    ]
    await query.edit_message_text(
        "💰 Какой *маркетинговый бюджет* у клиента в месяц?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return BUDGET


async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    budget_value = query.data.replace("budget_", "")

    # Фильтр: клиент с бюджетом ниже $500 нам не подходит
    if budget_value == "low":
        await query.edit_message_text(
            "⚠️ К сожалению, этот клиент не подходит под наш формат работы.\n\n"
            "Highlight Media работает с бюджетами от $500/мес.\n\n"
            "Если у клиента изменится бюджет — возвращайтесь, будем рады помочь! 🙌"
        )
        return ConversationHandler.END

    context.user_data["budget"] = budget_value
    await query.edit_message_text(
        "👤 Введите *имя контактного лица* (представителя клиента):",
        parse_mode="Markdown"
    )
    return CONTACT_NAME


async def contact_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact_name"] = update.message.text.strip()
    await update.message.reply_text("📞 Укажите *телефон или Telegram* контактного лица:", parse_mode="Markdown")
    return CONTACT_PHONE


async def contact_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact_phone"] = update.message.text.strip()
    await update.message.reply_text(
        "💬 Добавьте *комментарий* для Highlight Media\n"
        "(что важно знать о клиенте, особые пожелания или напишите «нет»):",
        parse_mode="Markdown"
    )
    return COMMENT


async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["comment"] = update.message.text.strip()

    data = context.user_data
    partner_id = get_partner_id(context)
    partner_name = get_partner_name(partner_id)

    # Карточка лида для менеджера
    card = (
        f"🤝 *Новая заявка от партнёра!*\n\n"
        f"🏢 *Партнёр:* {partner_name}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏷 *Компания клиента:* {data.get('company_name')}\n"
        f"📌 *Сфера:* {data.get('niche')}\n"
        f"🌐 *Сайт:* {data.get('website')}\n"
        f"🎯 *Задача:* {data.get('task')}\n"
        f"💰 *Бюджет:* {data.get('budget')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Контакт:* {data.get('contact_name')}\n"
        f"📞 *Телефон/TG:* {data.get('contact_phone')}\n"
        f"💬 *Комментарий:* {data.get('comment')}"
    )

    # Сохраняем partner_id до очистки
    saved_partner_id = partner_id

    # Отправляем в Telegram группу Highlight Media
    await context.bot.send_message(
        chat_id=MANAGER_CHAT_ID,
        text=card,
        parse_mode="Markdown"
    )

    # Автоответ партнёру с кнопкой добавить нового клиента
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить нового клиента", callback_data=f"new_client_{saved_partner_id}")]
    ])

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ *Заявка принята!*\n\n"
        f"Компания: *{data.get('company_name')}*\n"
        f"Задача: *{data.get('task')}*\n"
        f"Бюджет: *{data.get('budget')}*\n\n"
        f"Наш менеджер свяжется с клиентом в течение рабочего дня.\n\n"
        f"Спасибо за сотрудничество! 🙌\n"
        f"_Highlight Media_",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    return ConversationHandler.END


async def new_client_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partner_id = query.data.replace("new_client_", "")

    if partner_id not in PARTNERS:
        await query.edit_message_text("❌ Ошибка идентификации партнёра. Обратитесь в Highlight Media.")
        return ConversationHandler.END

    context.user_data["partner_id"] = partner_id
    partner_name = get_partner_name(partner_id)

    await query.edit_message_text(
        f"👋 Добавляем нового клиента\n"
        f"Студия: *{partner_name}*\n\n"
        f"Введите *название компании клиента*:",
        parse_mode="Markdown"
    )
    return COMPANY_NAME


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    partner_id = get_partner_id(context)
    if not partner_id or partner_id not in PARTNERS:
        await update.message.reply_text(
            "❌ Вы не авторизованы.\n\n"
            "Используйте персональную ссылку от Highlight Media."
        )
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить нового клиента", callback_data=f"new_client_{partner_id}")],
        [InlineKeyboardButton("📞 Связаться с нами", url="https://t.me/highlight_media")]
    ])
    await update.message.reply_text(
        f"🏢 *Партнёрский портал Highlight Media*\n"
        f"Студия: *{get_partner_name(partner_id)}*\n\n"
        f"Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Анкета отменена. Используйте вашу партнёрскую ссылку чтобы начать заново.")
    context.user_data.clear()
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(new_client_button, pattern="^new_client_"),
        ],
        states={
            COMPANY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, company_name)],
            NICHE: [MessageHandler(filters.TEXT & ~filters.COMMAND, niche)],
            WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, website)],
            TASK: [CallbackQueryHandler(task, pattern="^task_")],
            BUDGET: [CallbackQueryHandler(budget, pattern="^budget_")],
            CONTACT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_name)],
            CONTACT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_phone)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))
    app.run_polling()


if __name__ == "__main__":
    main()
