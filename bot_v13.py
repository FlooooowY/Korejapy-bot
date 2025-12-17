import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from dotenv import load_dotenv
import time

from models_sync import UserModel, PaymentModel, BroadcastModel, BirthdayMessageModel
from telegram import KeyboardButton, ReplyKeyboardMarkup

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

# ID последнего сообщения меню для редактирования
user_menu_messages = {}

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
        welcome_text = f"👑 Добро пожаловать, @{user.username}!\nИспользуйте /menu"
    elif user.username and user.username.lower() in [u.lower() for u in SELLER_USERNAMES]:
        if db_user.role not in ['seller', 'admin', 'creator']:
            UserModel.update_role(user.id, 'seller')
        welcome_text = f"🛍️ Добро пожаловать, @{user.username}!\nИспользуйте /menu"
    else:
        welcome_text = "✨ Добро пожаловать в Korejapy!\n\nИспользуйте /menu"
    
    # Проверяем регистрацию
    if not db_user.is_registered and db_user.role == 'client':
        keyboard = [
            [InlineKeyboardButton("📝 Зарегистрироваться", callback_data="start_registration")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "📝 Для использования бота необходимо пройти регистрацию.\n\n"
            "Это займет всего минуту!",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(welcome_text)

def menu(update: Update, context: CallbackContext):
    """Главное меню"""
    user_id = update.effective_user.id
    user = UserModel.get_user(user_id)
    
    if not user:
        update.message.reply_text("Сначала используйте /start")
        return
    
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton("📊 Мой баланс", callback_data="balance")],
    ]
    
    # Команды для клиентов
    if user.role == 'client':
        keyboard.append([InlineKeyboardButton("💸 Обменять баллы", callback_data="exchange_points")])
    
    # Команды для продавцов и админов
    if user.role in ['seller', 'admin', 'creator']:
        keyboard.append([InlineKeyboardButton("💰 Добавить оплату", callback_data="add_payment")])
        keyboard.append([InlineKeyboardButton("💸 Списать баллы", callback_data="spend_points_seller")])
    
    # Команды для админов
    if user.role in ['admin', 'creator']:
        keyboard.append([InlineKeyboardButton("👥 Управление ролями", callback_data="manage_roles")])
        keyboard.append([InlineKeyboardButton("📢 Массовая рассылка", callback_data="broadcast")])
        keyboard.append([InlineKeyboardButton("🎂 Настройка рассылки ДР", callback_data="birthday_settings")])
    
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
    
    # Регистрация
    if data == "start_registration":
        query.edit_message_text(
            "📝 Регистрация профиля\n\n"
            "Шаг 1/3: Введите ваше имя (только английскими буквами)\n"
            "Например: Ivan"
        )
        context.user_data['registration_step'] = 'name'
        return
    
    # Мой профиль
    elif data == "my_profile":
        user = UserModel.get_user(user_id)
        if user and user.is_registered:
            from datetime import datetime
            birth_date_formatted = "Не указана"
            if user.birth_date:
                try:
                    dt = datetime.strptime(user.birth_date, '%Y-%m-%d')
                    birth_date_formatted = dt.strftime('%d.%m.%Y')
                except:
                    birth_date_formatted = user.birth_date
            
            profile_text = (
                f"👤 Ваш профиль\n\n"
                f"Имя: {user.profile_name}\n"
                f"Телефон: {user.phone_number}\n"
                f"Дата рождения: {birth_date_formatted}\n"
                f"💰 Баллов: {user.loyalty_points:.2f}\n"
                f"ID: {user.telegram_id}"
            )
            query.edit_message_text(profile_text)
        else:
            query.edit_message_text("Профиль не заполнен. Используйте /start для регистрации")
        return
    
    elif data == "balance":
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
    
    # Обработка регистрации - Шаг 1: Имя
    if context.user_data.get('registration_step') == 'name':
        # Проверка на английские буквы
        if not text.replace(' ', '').isalpha() or not all(ord(c) < 128 for c in text):
            update.message.reply_text(
                "❌ Пожалуйста, используйте только английские буквы\n"
                "Попробуйте ещё раз:"
            )
            return
        
        context.user_data['profile_name'] = text
        context.user_data['registration_step'] = 'phone'
        
        # Создаём кнопку для отправки телефона
        keyboard = [[KeyboardButton("📱 Отправить номер телефона", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        update.message.reply_text(
            f"✅ Отлично, {text}!\n\n"
            "Шаг 2/3: Поделитесь номером телефона\n"
            "Нажмите кнопку ниже 👇",
            reply_markup=reply_markup
        )
        return
    
    # Обработка регистрации - Шаг 3: Дата рождения
    elif context.user_data.get('registration_step') == 'birth_date':
        # Проверка формата даты (DD.MM.YYYY или DD-MM-YYYY или DD/MM/YYYY)
        import re
        from datetime import datetime
        
        # Пробуем разные форматы
        date_formats = ['%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d']
        birth_date = None
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(text, fmt)
                birth_date = date_obj.strftime('%Y-%m-%d')
                break
            except:
                continue
        
        if not birth_date:
            update.message.reply_text(
                "❌ Неверный формат даты\n"
                "Используйте формат: ДД.ММ.ГГГГ (например: 25.12.1995)\n"
                "Попробуйте ещё раз:"
            )
            return
        
        # Сохраняем профиль
        profile_name = context.user_data.get('profile_name')
        phone_number = context.user_data.get('phone_number')
        
        UserModel.update_profile(user_id, profile_name, phone_number, birth_date)
        
        # Очищаем данные регистрации
        context.user_data.clear()
        
        update.message.reply_text(
            "✅ Регистрация завершена!\n\n"
            "Теперь вы можете пользоваться всеми функциями бота.\n"
            "Используйте /menu для начала работы",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/menu")]], resize_keyboard=True)
        )
        return
    
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

def handle_contact(update: Update, context: CallbackContext):
    """Обработчик контакта (номер телефона)"""
    user_id = update.effective_user.id
    
    if context.user_data.get('registration_step') == 'phone':
        contact = update.message.contact
        
        # Проверяем, что пользователь отправил свой номер
        if contact.user_id != user_id:
            update.message.reply_text("❌ Пожалуйста, отправьте ВАШ номер телефона")
            return
        
        phone_number = contact.phone_number
        context.user_data['phone_number'] = phone_number
        context.user_data['registration_step'] = 'birth_date'
        
        update.message.reply_text(
            f"✅ Номер телефона сохранён: {phone_number}\n\n"
            "Шаг 3/3: Введите дату рождения\n"
            "Формат: ДД.ММ.ГГГГ (например: 25.12.1995)",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/menu")]], resize_keyboard=True)
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
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.contact, handle_contact))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    # Запуск
    logger.info("Бот запущен")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

