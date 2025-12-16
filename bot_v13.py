import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from dotenv import load_dotenv
import time

from models_sync import UserModel, PaymentModel, BroadcastModel
from qr_generator import generate_qr_code, generate_spend_qr_code, parse_qr_code, decode_qr_from_image

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
POINTS_PER_RUBLE = 0.01  # 1% от суммы покупки в баллы

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
        [InlineKeyboardButton("💸 Списать баллы", callback_data="spend_points")],
    ]
    
    # Команды для продавцов и админов
    if user.role in ['seller', 'admin', 'creator']:
        keyboard.append([InlineKeyboardButton("💰 Добавить оплату", callback_data="add_payment")])
        keyboard.append([InlineKeyboardButton("📷 Сканировать QR", callback_data="scan_qr")])
    
    # Команды для админов
    if user.role in ['admin', 'creator']:
        keyboard.append([InlineKeyboardButton("👥 Управление ролями", callback_data="manage_roles")])
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
    
    elif data == "spend_points":
        # Если продавец - сканирует QR код обмена
        if is_seller(user_id):
            query.edit_message_text(
                "💸 Списание баллов (для продавца)\n\n"
                "Отправьте фотографию QR кода обмена баллов от клиента"
            )
            context.user_data['waiting_for_spend_qr'] = True
        else:
            # Если клиент - вводит количество баллов
            user = UserModel.get_user(user_id)
            if user:
                query.edit_message_text(
                    f"💸 Обмен баллов на скидку\n\n"
                    f"Ваш баланс: {user.loyalty_points:.2f} баллов\n"
                    f"Курс: 5 баллов = 1 рубль\n\n"
                    "Введите количество баллов для обмена:"
                )
                context.user_data['waiting_for_spend_points'] = True
    
    elif data == "add_payment":
        if is_seller(user_id):
            query.edit_message_text(
                "💰 Добавление оплаты\n\n"
                "Отправьте сумму покупки числом (например: 1500)"
            )
            context.user_data['waiting_for_amount'] = True
    
    elif data == "scan_qr":
        if is_seller(user_id):
            query.edit_message_text(
                "📷 Сканирование QR кода\n\n"
                "Отправьте фотографию QR кода покупателя или введите его ID:"
            )
            context.user_data['waiting_for_qr'] = True
    
    elif data == "manage_roles":
        if is_admin(user_id):
            query.edit_message_text(
                "👥 Управление ролями\n\n"
                "Отправьте команду в формате:\n"
                "/setrole <user_id> <role>\n\n"
                "Роли: creator, admin, seller, client"
            )
    
    elif data == "broadcast":
        if is_admin(user_id):
            query.edit_message_text("📢 Массовая рассылка\n\nОтправьте сообщение для рассылки")
            context.user_data['waiting_for_broadcast'] = True

def handle_text(update: Update, context: CallbackContext):
    """Обработчик текста"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Обработка суммы для оплаты (первый шаг)
    if context.user_data.get('waiting_for_amount'):
        try:
            amount = float(text.replace(',', '.'))
            if amount <= 0:
                update.message.reply_text("Сумма должна быть больше нуля")
                return
            
            context.user_data['payment_amount'] = amount
            context.user_data['waiting_for_amount'] = False
            context.user_data['waiting_for_qr_photo'] = True
            
            update.message.reply_text(
                f"✅ Сумма: {amount} руб.\n\n"
                "Теперь отправьте фотографию QR кода покупателя или введите его ID:"
            )
        except ValueError:
            update.message.reply_text("Пожалуйста, введите корректную сумму (число)")
    
    # Обработка ID клиента после ввода суммы
    elif context.user_data.get('waiting_for_qr_photo') and not context.user_data.get('waiting_for_qr'):
        # Пытаемся распарсить QR код или получить ID напрямую
        client_id = None
        try:
            qr_data = parse_qr_code(text)
            if qr_data.get('valid'):
                client_id = qr_data['user_id']
            else:
                client_id = int(text)
        except:
            update.message.reply_text("Неверный формат. Введите ID покупателя или QR код")
            return
        
        if client_id:
            amount = context.user_data.get('payment_amount')
            if amount:
                # Обрабатываем оплату сразу
                client = UserModel.get_user(client_id)
                if not client:
                    update.message.reply_text("Клиент не найден")
                    context.user_data.clear()
                    return
                
                points = amount * POINTS_PER_RUBLE
                UserModel.add_points(client_id, points)
                PaymentModel.create_payment(
                    client_id=client.id,
                    seller_id=user_id,
                    amount=amount,
                    points_earned=points
                )
                
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
    
    # Списание баллов (обмен) - клиент вводит количество
    elif context.user_data.get('waiting_for_spend_points'):
        try:
            points = float(text.replace(',', '.'))
            if points <= 0:
                update.message.reply_text("Количество баллов должно быть больше нуля")
                return
            
            user = UserModel.get_user(user_id)
            if not user:
                update.message.reply_text("Пользователь не найден")
                context.user_data.clear()
                return
            
            if user.loyalty_points < points:
                update.message.reply_text(
                    f"❌ Недостаточно баллов!\n"
                    f"Ваш баланс: {user.loyalty_points:.2f}\n"
                    f"Запрошено: {points:.2f}"
                )
                context.user_data.clear()
                return
            
            # Курс обмена: 5 баллов = 1 рубль
            discount_amount = points / 5.0
            
            # Генерируем QR код для обмена
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Данные для QR кода обмена
                qr_data = f"KOREJAPY_SPEND_{user_id}_{points}"
                qr_image = loop.run_until_complete(generate_spend_qr_code(user_id, points, qr_data))
                
                update.message.reply_photo(
                    photo=qr_image,
                    caption=(
                        f"💸 QR код для обмена баллов\n\n"
                        f"Баллов к обмену: {points:.2f}\n"
                        f"Скидка: {discount_amount:.2f} руб.\n"
                        f"Курс: 5 баллов = 1 рубль\n\n"
                        f"Покажите этот QR код продавцу"
                    )
                )
                context.user_data.clear()
            except Exception as e:
                logger.error(f"Ошибка генерации QR для обмена: {e}")
                update.message.reply_text("Ошибка при генерации QR кода")
                context.user_data.clear()
        except ValueError:
            update.message.reply_text("Пожалуйста, введите корректное число")
    
    # Обработка QR кода в текстовом виде
    elif context.user_data.get('waiting_for_qr'):
        # Пытаемся распарсить QR код или получить ID напрямую
        client_id = None
        try:
            qr_data = parse_qr_code(text)
            if qr_data.get('valid'):
                client_id = qr_data['user_id']
            else:
                client_id = int(text)
        except:
            update.message.reply_text("Неверный формат. Введите ID покупателя или QR код")
            return
        
        if client_id:
            update.message.reply_text(
                f"✅ ID покупателя: {client_id}\n\n"
                "Введите сумму покупки:"
            )
            context.user_data['client_id'] = client_id
            context.user_data['waiting_for_qr'] = False
            context.user_data['waiting_for_amount_after_qr'] = True
    
    # Обработка суммы после QR
    elif context.user_data.get('waiting_for_amount_after_qr'):
        try:
            amount = float(text.replace(',', '.'))
            if amount <= 0:
                update.message.reply_text("Сумма должна быть больше нуля")
                return
            
            client_id = context.user_data.get('client_id')
            if client_id:
                client = UserModel.get_user(client_id)
                if not client:
                    update.message.reply_text("Клиент не найден")
                    context.user_data.clear()
                    return
                
                points = amount * POINTS_PER_RUBLE
                UserModel.add_points(client_id, points)
                PaymentModel.create_payment(
                    client_id=client.id,
                    seller_id=user_id,
                    amount=amount,
                    points_earned=points
                )
                
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
        except ValueError:
            update.message.reply_text("Пожалуйста, введите корректную сумму (число)")
    
    # Команда setrole
    elif text.startswith('/setrole'):
        if is_admin(user_id):
            parts = text.split()
            if len(parts) == 3:
                try:
                    target_user_id = int(parts[1])
                    role = parts[2]
                    
                    if role not in ['creator', 'admin', 'seller', 'client']:
                        update.message.reply_text("Неверная роль. Доступные: creator, admin, seller, client")
                        return
                    
                    UserModel.update_role(target_user_id, role)
                    update.message.reply_text(f"✅ Роль пользователя {target_user_id} изменена на {role}")
                except ValueError:
                    update.message.reply_text("Неверный формат. Используйте: /setrole <user_id> <role>")
            else:
                update.message.reply_text("Неверный формат. Используйте: /setrole <user_id> <role>")
    
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

def handle_photo(update: Update, context: CallbackContext):
    """Обработчик фотографий (QR коды)"""
    user_id = update.effective_user.id
    
    if not is_seller(user_id):
        return
    
    # Обработка QR кода после ввода суммы (через "Добавить оплату")
    if context.user_data.get('waiting_for_qr_photo'):
        photo = update.message.photo[-1]  # Берем фото наибольшего размера
        file = context.bot.get_file(photo.file_id)
        
        # Скачиваем фото
        import io
        bio = io.BytesIO()
        file.download(out=bio)
        photo_bytes = bio.getvalue()
        
        # Распознаем QR код
        update.message.reply_text("🔍 Обрабатываю QR код...")
        qr_result = decode_qr_from_image(photo_bytes)
        
        if qr_result.get('valid'):
            client_id = qr_result['user_id']
            amount = context.user_data.get('payment_amount')
            
            if amount:
                # Обрабатываем оплату сразу
                client = UserModel.get_user(client_id)
                if not client:
                    update.message.reply_text("Клиент не найден")
                    context.user_data.clear()
                    return
                
                points = amount * POINTS_PER_RUBLE
                UserModel.add_points(client_id, points)
                PaymentModel.create_payment(
                    client_id=client.id,
                    seller_id=user_id,
                    amount=amount,
                    points_earned=points
                )
                
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
        else:
            update.message.reply_text(
                f"❌ {qr_result.get('error', 'Не удалось распознать QR код')}\n\n"
                "Попробуйте отправить фото еще раз или введите ID покупателя вручную:"
            )
    
    # Обработка QR кода через "Сканировать QR" (сначала QR, потом сумма)
    elif context.user_data.get('waiting_for_qr'):
        photo = update.message.photo[-1]
        file = context.bot.get_file(photo.file_id)
        
        import io
        bio = io.BytesIO()
        file.download(out=bio)
        photo_bytes = bio.getvalue()
        
        update.message.reply_text("🔍 Обрабатываю QR код...")
        qr_result = decode_qr_from_image(photo_bytes)
        
        if qr_result.get('valid'):
            client_id = qr_result['user_id']
            context.user_data['client_id'] = client_id
            update.message.reply_text(
                f"✅ QR код распознан!\nID покупателя: {client_id}\n\n"
                "Введите сумму покупки:"
            )
            context.user_data['waiting_for_qr'] = False
            context.user_data['waiting_for_amount_after_qr'] = True
        else:
            update.message.reply_text(
                f"❌ {qr_result.get('error', 'Не удалось распознать QR код')}\n\n"
                "Попробуйте отправить фото еще раз или введите ID покупателя вручную:"
            )
    
    # Обработка QR кода обмена баллов (для продавца)
    elif context.user_data.get('waiting_for_spend_qr'):
        photo = update.message.photo[-1]
        file = context.bot.get_file(photo.file_id)
        
        import io
        bio = io.BytesIO()
        file.download(out=bio)
        photo_bytes = bio.getvalue()
        
        update.message.reply_text("🔍 Обрабатываю QR код обмена...")
        qr_result = decode_qr_from_image(photo_bytes)
        
        if qr_result.get('valid') and qr_result.get('type') == 'spend':
            client_id = qr_result['user_id']
            points = qr_result['points']
            
            client = UserModel.get_user(client_id)
            if not client:
                update.message.reply_text("Клиент не найден")
                context.user_data.clear()
                return
            
            if client.loyalty_points < points:
                update.message.reply_text(
                    f"❌ У клиента недостаточно баллов!\n"
                    f"Баланс клиента: {client.loyalty_points:.2f}\n"
                    f"Запрошено: {points:.2f}"
                )
                context.user_data.clear()
                return
            
            # Списываем баллы
            success = UserModel.spend_points(client_id, points)
            if success:
                discount_amount = points / 5.0
                updated_client = UserModel.get_user(client_id)
                update.message.reply_text(
                    f"✅ Баллы списаны!\n\n"
                    f"Клиент: {client.first_name}\n"
                    f"Списано баллов: {points:.2f}\n"
                    f"Скидка: {discount_amount:.2f} руб.\n"
                    f"Остаток баллов: {updated_client.loyalty_points:.2f}"
                )
                
                # Уведомление клиента
                try:
                    context.bot.send_message(
                        chat_id=client_id,
                        text=(
                            f"💸 Баллы использованы!\n\n"
                            f"Списано: {points:.2f} баллов\n"
                            f"Скидка: {discount_amount:.2f} руб.\n"
                            f"Остаток: {updated_client.loyalty_points:.2f} баллов"
                        )
                    )
                except:
                    pass
            else:
                update.message.reply_text("Ошибка при списании баллов")
            
            context.user_data.clear()
        else:
            update.message.reply_text(
                f"❌ {qr_result.get('error', 'Неверный QR код. Это не QR код обмена баллов')}\n\n"
                "Попробуйте отправить фото еще раз."
            )

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
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    
    # Запуск
    logger.info("Бот запущен")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

