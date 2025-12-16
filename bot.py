import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext
)
from dotenv import load_dotenv
import asyncio

from database import init_db
from models import UserModel, PaymentModel, BroadcastModel
from qr_generator import generate_qr_code, parse_qr_code, decode_qr_from_image

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
BOT_TOKEN = os.getenv('BOT_TOKEN', '8570438178:AAEW3bEsIdF9iwVjA3Q1sFo5w1NrCyuJVpQ')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
ADMIN_USERNAMES = ['flooooooooooowy', 'katrinzagora']  # Админы по username (lowercase)
SELLER_USERNAMES = ['fublat_666', 'shad0w_04', 'mikk4u']  # Продавцы по username (lowercase)
POINTS_PER_RUBLE = 0.01  # 1% от суммы покупки в баллы


# Вспомогательные функции для проверки ролей
async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом или создателем"""
    user = await UserModel.get_user(user_id)
    if not user:
        return False
    return user.role in ['admin', 'creator'] or user_id in ADMIN_IDS


async def is_seller(user_id: int) -> bool:
    """Проверка, является ли пользователь продавцом"""
    user = await UserModel.get_user(user_id)
    if not user:
        return False
    return user.role in ['seller', 'admin', 'creator'] or user_id in ADMIN_IDS


async def is_creator(user_id: int) -> bool:
    """Проверка, является ли пользователь создателем"""
    user = await UserModel.get_user(user_id)
    if not user:
        return user_id in ADMIN_IDS
    return user.role == 'creator' or user_id in ADMIN_IDS


# Обработчики команд
def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Создаем или обновляем пользователя
    db_user = await UserModel.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Отправляем логотип
    try:
        with open('photo_2025-12-12_18-51-23.jpg', 'rb') as logo:
            await update.message.reply_photo(
                photo=logo,
                caption="🎌 KOREJAPY 🎌\nМагазин аниме в Краснодаре"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки логотипа: {e}")
    
    # Проверяем, является ли пользователь админом или продавцом по username
    logger.info(f"=== ПРОВЕРКА РОЛИ ===")
    logger.info(f"Username: {user.username}")
    logger.info(f"Username lower: {user.username.lower() if user.username else 'None'}")
    logger.info(f"Current role: {db_user.role}")
    logger.info(f"Admin usernames: {ADMIN_USERNAMES}")
    logger.info(f"Seller usernames: {SELLER_USERNAMES}")
    
    # Проверка на админа
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        logger.info(f"Username {user.username} в списке админов!")
        
        # Если еще не админ - повышаем
        if db_user.role not in ['admin', 'creator']:
            await UserModel.update_role(user.id, 'admin')
            logger.info(f"Роль изменена на admin для {user.username}")
            welcome_text = (
                "👑 Добро пожаловать, Администратор!\n\n"
                f"Здравствуйте, @{user.username}!\n"
                "Вам автоматически назначена роль администратора.\n\n"
                "📋 Доступные функции:\n"
                "• Массовая рассылка\n"
                "• Управление ролями\n"
                "• Добавление оплаты\n"
                "• Сканирование QR кодов\n\n"
                "Используйте /menu для начала работы."
            )
        else:
            welcome_text = (
                "👑 С возвращением, Администратор!\n\n"
                f"Рады видеть вас снова, @{user.username}!\n\n"
                f"Ваша роль: {db_user.role}\n"
                "Используйте /menu для доступа к функциям."
            )
    # Проверка на продавца
    elif user.username and user.username.lower() in [u.lower() for u in SELLER_USERNAMES]:
        logger.info(f"✅ Username {user.username} в списке продавцов!")
        
        # Если еще не продавец - назначаем
        if db_user.role not in ['seller', 'admin', 'creator']:
            await UserModel.update_role(user.id, 'seller')
            logger.info(f"Роль изменена на seller для {user.username}")
            welcome_text = (
                "🛍️ Добро пожаловать, Продавец!\n\n"
                f"Здравствуйте, @{user.username}!\n"
                "Вам автоматически назначена роль продавца.\n\n"
                "📋 Доступные функции:\n"
                "• Добавление оплаты\n"
                "• Сканирование QR кодов\n"
                "• Начисление баллов клиентам\n\n"
                "Используйте /menu для начала работы."
            )
        else:
            welcome_text = (
                "🛍️ С возвращением!\n\n"
                f"Рады видеть вас снова, @{user.username}!\n\n"
                f"Ваша роль: {db_user.role}\n"
                "Используйте /menu для доступа к функциям."
            )
    else:
        logger.info(f"❌ Username {user.username} - НЕ найден в списках админов/продавцов")
        logger.info(f"Сравнение с продавцами:")
        for seller in SELLER_USERNAMES:
            logger.info(f"  '{user.username.lower() if user.username else 'None'}' == '{seller}' ? {user.username and user.username.lower() == seller}")
        welcome_text = (
            "✨ Добро пожаловать в Korejapy!\n\n"
            "Мы рады приветствовать вас в нашей программе лояльности!\n\n"
            "🎁 При каждой покупке вы получаете 10% баллами\n"
            "💳 Баллы можно использовать для скидок\n"
            "📱 Ваш личный QR код для быстрой оплаты\n\n"
            "Используйте /menu для просмотра ваших возможностей."
        )
    
    await update.message.reply_text(welcome_text)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    user_id = update.effective_user.id
    user = await UserModel.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Сначала используйте /start")
        return
    
    keyboard = []
    
    # Команды для всех
    keyboard.append([InlineKeyboardButton("📊 Мой баланс", callback_data="balance")])
    keyboard.append([InlineKeyboardButton("📱 Мой QR код", callback_data="my_qr")])
    keyboard.append([InlineKeyboardButton("💸 Списать баллы", callback_data="spend_points")])
    
    # Проверяем права
    is_admin_user = await is_admin(user_id)
    is_seller_user = await is_seller(user_id)
    
    # Команды для продавцов (включая админов)
    if is_seller_user or is_admin_user:
        keyboard.append([InlineKeyboardButton("💰 Добавить оплату", callback_data="add_payment")])
        keyboard.append([InlineKeyboardButton("📷 Сканировать QR", callback_data="scan_qr")])
    
    # Команды для админов
    if is_admin_user:
        keyboard.append([InlineKeyboardButton("👥 Управление ролями", callback_data="manage_roles")])
        keyboard.append([InlineKeyboardButton("📢 Массовая рассылка", callback_data="broadcast")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 Главное меню:", reply_markup=reply_markup)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать баланс баллов"""
    user_id = update.effective_user.id
    user = await UserModel.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Пользователь не найден")
        return
    
    balance_text = (
        f"💰 Ваш баланс баллов: {user.loyalty_points:.2f}\n\n"
        f"Используйте баллы для получения скидок и специальных предложений!"
    )
    await update.message.reply_text(balance_text)


async def my_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация QR кода для клиента"""
    user_id = update.effective_user.id
    user = await UserModel.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Пользователь не найден")
        return
    
    try:
        qr_image = await generate_qr_code(user_id, user.username)
        qr_text = (
            f"📱 Ваш QR код для оплаты\n\n"
            f"Покажите этот код продавцу при оплате.\n"
            f"Ваш ID: {user_id}"
        )
        await update.message.reply_photo(
            photo=qr_image,
            caption=qr_text
        )
    except Exception as e:
        logger.error(f"Ошибка генерации QR: {e}")
        await update.message.reply_text("Ошибка при генерации QR кода")


async def check_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка информации о себе"""
    user = update.effective_user
    db_user = await UserModel.get_user(user.id)
    
    info = (
        f"🔍 Информация о вашем аккаунте:\n\n"
        f"👤 Username: @{user.username}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"👨‍💼 Роль: {db_user.role if db_user else 'Не найден'}\n"
        f"💰 Баллы: {db_user.loyalty_points if db_user else 0}\n\n"
        f"📋 Проверка прав:\n"
        f"• В списке админов: {'✅' if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES] else '❌'}\n"
        f"• В списке продавцов: {'✅' if user.username and user.username.lower() in [u.lower() for u in SELLER_USERNAMES] else '❌'}\n"
    )
    await update.message.reply_text(info)


# Обработчики callback
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "balance":
        user = await UserModel.get_user(user_id)
        if user:
            await query.edit_message_text(
                f"💰 Ваш баланс: {user.loyalty_points:.2f} баллов"
            )
    
    elif data == "my_qr":
        user = await UserModel.get_user(user_id)
        if user:
            try:
                qr_image = await generate_qr_code(user_id, user.username)
                await query.message.reply_photo(
                    photo=qr_image,
                    caption=f"📱 Ваш QR код\nID: {user_id}"
                )
            except Exception as e:
                await query.edit_message_text("Ошибка при генерации QR кода")
    
    elif data == "add_payment":
        if await is_seller(user_id):
            await query.edit_message_text(
                "💰 Добавление оплаты\n\n"
                "Отправьте сумму покупки числом (например: 1500)"
            )
            context.user_data['waiting_for_amount'] = True
    
    elif data == "scan_qr":
        if await is_seller(user_id):
            await query.edit_message_text(
                "📷 Сканирование QR кода\n\n"
                "Отправьте фотографию QR кода покупателя"
            )
            context.user_data['waiting_for_qr'] = True
    
    elif data == "manage_roles":
        if await is_admin(user_id):
            await query.edit_message_text(
                "👥 Управление ролями\n\n"
                "Отправьте команду в формате:\n"
                "/setrole <user_id> <role>\n\n"
                "Роли: creator, admin, seller, client"
            )
    
    elif data == "broadcast":
        if await is_admin(user_id):
            await query.edit_message_text(
                "📢 Массовая рассылка\n\n"
                "Отправьте сообщение, которое хотите разослать всем пользователям"
            )
            context.user_data['waiting_for_broadcast'] = True
    
    elif data == "spend_points":
        user = await UserModel.get_user(user_id)
        if user:
            await query.edit_message_text(
                f"💸 Списание баллов\n\n"
                f"Ваш баланс: {user.loyalty_points:.2f}\n\n"
                "Введите количество баллов для списания:"
            )
            context.user_data['waiting_for_spend_points'] = True


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Обработка суммы для оплаты
    if context.user_data.get('waiting_for_amount'):
        try:
            amount = float(text.replace(',', '.'))
            if amount <= 0:
                await update.message.reply_text("Сумма должна быть больше нуля")
                return
            
            context.user_data['payment_amount'] = amount
            context.user_data['waiting_for_amount'] = False
            context.user_data['waiting_for_qr_photo'] = True
            
            await update.message.reply_text(
                f"✅ Сумма: {amount} руб.\n\n"
                "Теперь отправьте фотографию QR кода покупателя или введите его ID:"
            )
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректную сумму (число)")
    
    # Обработка массовой рассылки
    elif context.user_data.get('waiting_for_broadcast'):
        if await is_admin(user_id):
            message_text = text
            await update.message.reply_text("Начинаю рассылку...")
            
            users = await UserModel.get_all_users()
            sent_count = 0
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_text
                    )
                    sent_count += 1
                    await asyncio.sleep(0.05)  # Защита от лимитов Telegram
                except Exception as e:
                    logger.error(f"Ошибка отправки пользователю {user.telegram_id}: {e}")
            
            broadcast = await BroadcastModel.create_broadcast(user_id, message_text)
            await BroadcastModel.update_sent_count(broadcast.id, sent_count)
            
            await update.message.reply_text(
                f"✅ Рассылка завершена!\nОтправлено: {sent_count} из {len(users)}"
            )
            context.user_data['waiting_for_broadcast'] = False
    
    # Обработка списания баллов
    elif context.user_data.get('waiting_for_spend_points'):
        try:
            points = float(text.replace(',', '.'))
            if points <= 0:
                await update.message.reply_text("Количество баллов должно быть больше нуля")
                return
            
            user = await UserModel.get_user(user_id)
            if not user:
                await update.message.reply_text("Пользователь не найден")
                context.user_data.clear()
                return
            
            if user.loyalty_points < points:
                await update.message.reply_text(
                    f"❌ Недостаточно баллов!\n"
                    f"Ваш баланс: {user.loyalty_points:.2f}\n"
                    f"Запрошено: {points:.2f}"
                )
                context.user_data.clear()
                return
            
            success = await UserModel.spend_points(user_id, points)
            if success:
                user = await UserModel.get_user(user_id)
                await update.message.reply_text(
                    f"✅ Баллы списаны!\n\n"
                    f"Списано: {points:.2f} баллов\n"
                    f"Остаток: {user.loyalty_points:.2f} баллов"
                )
            else:
                await update.message.reply_text("Ошибка при списании баллов")
            
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректное число")
    
    # Обработка суммы после распознавания QR
    elif context.user_data.get('waiting_for_amount_after_qr'):
        try:
            amount = float(text.replace(',', '.'))
            if amount <= 0:
                await update.message.reply_text("Сумма должна быть больше нуля")
                return
            
            client_id = context.user_data.get('client_id')
            if client_id:
                await process_payment(update, context, client_id, amount, user_id)
            else:
                await update.message.reply_text("Ошибка: ID клиента не найден")
                context.user_data.clear()
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректную сумму (число)")
    
    # Обработка ID клиента или QR кода в текстовом виде
    elif context.user_data.get('waiting_for_client_id'):
        client_id = None
        
        # Пытаемся распарсить QR код
        qr_data = parse_qr_code(text)
        if qr_data.get('valid'):
            client_id = qr_data['user_id']
        else:
            # Пытаемся получить ID напрямую
            try:
                client_id = int(text)
            except ValueError:
                await update.message.reply_text("Неверный формат. Введите ID покупателя или QR код")
                return
        
        # Проверяем наличие суммы оплаты
        if 'payment_amount' in context.user_data:
            amount = context.user_data['payment_amount']
            await process_payment(update, context, client_id, amount, user_id)
        else:
            context.user_data['client_id'] = client_id
            await update.message.reply_text(
                f"✅ ID покупателя: {client_id}\n\n"
                "Введите сумму покупки:"
            )
            context.user_data['waiting_for_amount_after_qr'] = True
            context.user_data['waiting_for_client_id'] = False
    
    # Обработка команды setrole
    elif text.startswith('/setrole'):
        if await is_admin(user_id):
            parts = text.split()
            if len(parts) == 3:
                try:
                    target_user_id = int(parts[1])
                    role = parts[2]
                    
                    if role not in ['creator', 'admin', 'seller', 'client']:
                        await update.message.reply_text("Неверная роль. Доступные: creator, admin, seller, client")
                        return
                    
                    await UserModel.update_role(target_user_id, role)
                    await update.message.reply_text(f"✅ Роль пользователя {target_user_id} изменена на {role}")
                except ValueError:
                    await update.message.reply_text("Неверный формат. Используйте: /setrole <user_id> <role>")
            else:
                await update.message.reply_text("Неверный формат. Используйте: /setrole <user_id> <role>")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фотографий (QR коды)"""
    user_id = update.effective_user.id
    
    if not await is_seller(user_id):
        return
    
    if context.user_data.get('waiting_for_qr_photo'):
        photo = update.message.photo[-1]  # Берем фото наибольшего размера
        file = await context.bot.get_file(photo.file_id)
        
        # Скачиваем фото
        photo_bytes = await file.download_as_bytearray()
        
        # Распознаем QR код
        await update.message.reply_text("🔍 Обрабатываю QR код...")
        qr_result = decode_qr_from_image(photo_bytes)
        
        if qr_result.get('valid'):
            client_id = qr_result['user_id']
            context.user_data['client_id'] = client_id
            
            # Если есть сумма, сразу обрабатываем оплату
            if 'payment_amount' in context.user_data:
                amount = context.user_data['payment_amount']
                await process_payment(update, context, client_id, amount, user_id)
            else:
                await update.message.reply_text(
                    f"✅ QR код распознан!\nID покупателя: {client_id}\n\n"
                    "Теперь введите сумму покупки:"
                )
                context.user_data['waiting_for_amount_after_qr'] = True
        else:
            await update.message.reply_text(
                f"❌ {qr_result.get('error', 'Не удалось распознать QR код')}\n\n"
                "Попробуйте отправить фото еще раз или введите ID покупателя вручную:"
            )
            context.user_data['waiting_for_client_id'] = True
        
        context.user_data['waiting_for_qr_photo'] = False
    
    elif context.user_data.get('waiting_for_qr'):
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        
        await update.message.reply_text("🔍 Обрабатываю QR код...")
        qr_result = decode_qr_from_image(photo_bytes)
        
        if qr_result.get('valid'):
            client_id = qr_result['user_id']
            context.user_data['client_id'] = client_id
            await update.message.reply_text(
                f"✅ QR код распознан!\nID покупателя: {client_id}\n\n"
                "Введите сумму покупки:"
            )
            context.user_data['waiting_for_amount_after_qr'] = True
        else:
            await update.message.reply_text(
                f"❌ {qr_result.get('error', 'Не удалось распознать QR код')}\n\n"
                "Попробуйте отправить фото еще раз или введите ID покупателя:"
            )
            context.user_data['waiting_for_client_id'] = True
        
        context.user_data['waiting_for_qr'] = False


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                         client_id: int, amount: float, seller_id: int):
    """Обработка оплаты"""
    client = await UserModel.get_user(client_id)
    
    if not client:
        await update.message.reply_text(f"Пользователь с ID {client_id} не найден")
        context.user_data.clear()
        return
    
    # Начисляем баллы (10% от суммы)
    points_earned = amount * POINTS_PER_RUBLE
    await UserModel.add_points(client_id, points_earned)
    
    # Создаем запись об оплате
    await PaymentModel.create_payment(
        client_id=client.id,
        seller_id=seller_id,
        amount=amount,
        points_earned=points_earned
    )
    
    await update.message.reply_text(
        f"✅ Оплата добавлена!\n\n"
        f"Клиент: {client.first_name or 'Без имени'}\n"
        f"Сумма: {amount} руб.\n"
        f"Начислено баллов: {points_earned:.2f}"
    )
    
    # Уведомляем клиента
    try:
        updated_client = await UserModel.get_user(client_id)
        await context.bot.send_message(
            chat_id=client_id,
            text=(
                f"💰 Оплата зарегистрирована!\n\n"
                f"Сумма: {amount} руб.\n"
                f"Начислено баллов: {points_earned:.2f}\n"
                f"Ваш баланс: {updated_client.loyalty_points:.2f}"
            )
        )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления клиенту: {e}")
    
    context.user_data.clear()


def main():
    """Запуск бота"""
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("myqr", my_qr))
    application.add_handler(CommandHandler("checkme", check_me))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Инициализация БД
    async def post_init(app: Application):
        await init_db()
        logger.info("База данных инициализирована")
    
    application.post_init = post_init
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

