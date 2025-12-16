import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from dotenv import load_dotenv
import time

from models_sync import UserModel, PaymentModel, BroadcastModel
from qr_generator import generate_qr_code, parse_qr_code

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
ADMIN_USERNAMES = ['flooooooooooowy', 'katrinzagora']
SELLER_USERNAMES = ['fublat_666', 'shad0w_04', 'mikk4u']
POINTS_PER_RUBLE = 0.1

# Вспомогательные функции
def is_admin(user_id: int) -> bool:
    """Проверка админа"""
    user = UserModel.get_user(user_id)
    return user and (user.role in ['admin', 'creator'] or user_id in ADMIN_IDS)

def is_seller(user_id: int) -> bool:
    """Проверка продавца"""
    user = UserModel.get_user(user_id)
    return user and (user.role in ['seller', 'admin', 'creator'] or user_id in ADMIN_IDS)

# Обработчики команд
def start(update: Update, context: CallbackContext):
    """Обработчик /start"""
    user = update.effective_user
    
    # Создаем пользователя
    db_user = UserModel.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Отправляем логотип
    try:
        with open('photo_2025-12-12_18-51-23.jpg', 'rb') as logo:
            update.message.reply_photo(
                photo=logo,
                caption="🎌 KOREJAPY 🎌\nМагазин аниме в Краснодаре"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки логотипа: {e}")
    
    # Проверка ролей
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        if db_user.role not in ['admin', 'creator']:
            UserModel.update_role(user.id, 'admin')
            welcome_text = (
                "👑 Добро пожаловать, Администратор!\n\n"
                f"Здравствуйте, @{user.username}!\n"
                "Вам автоматически назначена роль администратора.\n\n"
                "Используйте /menu для начала работы."
            )
        else:
            welcome_text = f"👑 С возвращением, @{user.username}!\nИспользуйте /menu"
    elif user.username and user.username.lower() in [u.lower() for u in SELLER_USERNAMES]:
        if db_user.role not in ['seller', 'admin', 'creator']:
            UserModel.update_role(user.id, 'seller')
            welcome_text = (
                "🛍️ Добро пожаловать, Продавец!\n\n"
                f"Здравствуйте, @{user.username}!\n"
                "Используйте /menu для начала работы."
            )
        else:
            welcome_text = f"🛍️ С возвращением, @{user.username}!\nИспользуйте /menu"
    else:
        welcome_text = (
            "✨ Добро пожаловать в Korejapy!\n\n"
            "Мы рады приветствовать вас в нашей программе лояльности!\n\n"
            "🎁 При каждой покупке вы получаете 10% баллами\n"
            "Используйте /menu"
        )
    
    update.message.reply_text(welcome_text)

def menu(update: Update, context: CallbackContext):
    """Главное меню"""
    user_id = update.effective_user.id
    user = UserModel.get_user(user_id)
    
    if not user:
        update.message.reply_text("Сначала используйте /start")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton("📱 Мой QR код", callback_data="my_qr")],
    ]
    
    if user.role in ['seller', 'admin', 'creator']:
        keyboard.append([InlineKeyboardButton("💰 Добавить оплату", callback_data="add_payment")])
    
    if user.role in ['admin', 'creator']:
        keyboard.append([InlineKeyboardButton("📢 Массовая рассылка", callback_data="broadcast")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("📋 Главное меню:", reply_markup=reply_markup)

def balance(update: Update, context: CallbackContext):
    """Показать баланс"""
    user_id = update.effective_user.id
    user = UserModel.get_user(user_id)
    
    if user:
        update.message.reply_text(
            f"💰 Ваш баланс: {user.loyalty_points:.2f} баллов"
        )
    else:
        update.message.reply_text("Пользователь не найден")

def my_qr(update: Update, context: CallbackContext):
    """Генерация QR кода"""
    user_id = update.effective_user.id
    user = UserModel.get_user(user_id)
    
    if not user:
        update.message.reply_text("Пользователь не найден")
        return
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        qr_image = loop.run_until_complete(generate_qr_code(user_id, user.username))
        update.message.reply_photo(
            photo=qr_image,
            caption=f"📱 Ваш QR код\nID: {user_id}"
        )
    except Exception as e:
        logger.error(f"Ошибка генерации QR: {e}")
        update.message.reply_text("Ошибка при генерации QR кода")

def button_callback(update: Update, context: CallbackContext):
    """Обработчик кнопок"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "balance":
        user = UserModel.get_user(user_id)
        if user:
            query.edit_message_text(f"💰 Ваш баланс: {user.loyalty_points:.2f} баллов")
    
    elif data == "my_qr":
        user = UserModel.get_user(user_id)
        if user:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                qr_image = loop.run_until_complete(generate_qr_code(user_id, user.username))
                query.message.reply_photo(photo=qr_image, caption=f"📱 Ваш QR код\nID: {user_id}")
            except:
                query.edit_message_text("Ошибка генерации QR")
    
    elif data == "add_payment":
        query.edit_message_text(
            "💰 Добавление оплаты\n\n"
            "Введите ID клиента и сумму через пробел:\n"
            "Например: 123456789 1500"
        )
        context.user_data['waiting_for_payment'] = True
    
    elif data == "broadcast":
        query.edit_message_text("📢 Массовая рассылка\n\nОтправьте сообщение для рассылки")
        context.user_data['waiting_for_broadcast'] = True

def handle_text(update: Update, context: CallbackContext):
    """Обработчик текста"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Оплата
    if context.user_data.get('waiting_for_payment'):
        try:
            parts = text.split()
            client_id = int(parts[0])
            amount = float(parts[1])
            
            client = UserModel.get_user(client_id)
            if not client:
                update.message.reply_text("Клиент не найден")
                return
            
            points = amount * POINTS_PER_RUBLE
            UserModel.add_points(client_id, points)
            PaymentModel.create_payment(
                client_id=client.id,
                seller_id=user_id,
                amount=amount,
                points_earned=points
            ))
            
            update.message.reply_text(
                f"✅ Оплата добавлена!\n"
                f"Клиент: {client.first_name}\n"
                f"Сумма: {amount}₽\n"
                f"Баллов: +{points:.2f}"
            )
            
            # Уведомление клиента
            try:
                context.bot.send_message(
                    chat_id=client_id,
                    text=f"💰 Оплата {amount}₽\nНачислено: {points:.2f} баллов"
                )
            except:
                pass
            
            context.user_data.clear()
        except:
            update.message.reply_text("Неверный формат. Используйте: ID СУММА")
    
    # Рассылка
    elif context.user_data.get('waiting_for_broadcast'):
        if is_admin(user_id):
            users = UserModel.get_all_users()
            sent = 0
            for user in users:
                try:
                    context.bot.send_message(chat_id=user.telegram_id, text=text)
                    sent += 1
                    time.sleep(0.05)
                except:
                    pass
            update.message.reply_text(f"✅ Отправлено: {sent} из {len(users)}")
            context.user_data.clear()

def main():
    """Запуск бота"""
    # Инициализация БД
    from database_sync import init_db
    init_db()
    logger.info("База данных инициализирована")
    
    # Создание updater
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Регистрация обработчиков
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("myqr", my_qr))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    # Запуск
    logger.info("Бот запущен")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

