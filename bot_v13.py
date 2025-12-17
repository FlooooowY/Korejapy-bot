import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from dotenv import load_dotenv
import time

from models_sync import UserModel, PaymentModel, BroadcastModel, BirthdayMessageModel

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
    
    # Проверка ролей и автоматическая регистрация админов/продавцов
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        if db_user.role not in ['admin', 'creator']:
            UserModel.update_role(user.id, 'admin')
        # Админы автоматически зарегистрированы
        if not db_user.is_registered:
            from database_sync import SessionLocal
            session = SessionLocal()
            db_user.is_registered = True
            session.commit()
            session.close()
        welcome_text = f"👑 Добро пожаловать, @{user.username}!\nИспользуйте /menu"
        update.message.reply_text(welcome_text)
    elif user.username and user.username.lower() in [u.lower() for u in SELLER_USERNAMES]:
        if db_user.role not in ['seller', 'admin', 'creator']:
            UserModel.update_role(user.id, 'seller')
        # Продавцы автоматически зарегистрированы
        if not db_user.is_registered:
            from database_sync import SessionLocal
            session = SessionLocal()
            db_user.is_registered = True
            session.commit()
            session.close()
        welcome_text = f"🛍️ Добро пожаловать, @{user.username}!\nИспользуйте /menu"
        update.message.reply_text(welcome_text)
    else:
        # Для клиентов - обязательная регистрация
        # Проверяем is_registered (может быть None, 0 или False)
        if not db_user.is_registered or db_user.is_registered == 0:
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
            welcome_text = "✨ Добро пожаловать в Korejapy!\n\nИспользуйте /menu"
            update.message.reply_text(welcome_text)

def menu(update: Update, context: CallbackContext):
    """Главное меню"""
    user_id = update.effective_user.id
    user = UserModel.get_user(user_id)
    
    if not user:
        if update.message:
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
    
    # Отправляем новое сообщение и сохраняем его ID
    if update.message:
        msg = update.message.reply_text("📋 Главное меню:", reply_markup=reply_markup)
        user_menu_messages[user_id] = msg.message_id
    elif update.callback_query:
        try:
            update.callback_query.edit_message_text("📋 Главное меню:", reply_markup=reply_markup)
        except:
            msg = update.callback_query.message.reply_text("📋 Главное меню:", reply_markup=reply_markup)
            user_menu_messages[user_id] = msg.message_id

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

# Функция my_qr удалена - больше не используется QR код

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
            "Шаг 1/3: Введите ваше имя или ФИО\n"
            "Например: Иван Петров или ivan123"
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
                f"Имя: {user.profile_name or 'Не указано'}\n"
                f"Телефон: {user.phone_number or 'Не указан'}\n"
                f"Дата рождения: {birth_date_formatted}\n"
                f"💰 Баллов: {user.loyalty_points:.2f}\n"
                f"ID: {user.telegram_id}"
            )
            # Добавляем кнопки
            keyboard = [
                [InlineKeyboardButton("✏️ Изменить имя", callback_data="edit_name")],
                [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]
            ]
            query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("Профиль не заполнен. Используйте /start для регистрации")
        return
    
    # Изменить имя
    elif data == "edit_name":
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="my_profile")]]
        query.edit_message_text(
            "✏️ Изменение имени\n\n"
            "Введите новое имя:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['editing_name'] = True
        return
    
    # Кнопка "Назад в меню"
    elif data == "back_to_menu":
        menu(update, context)
        return
    
    elif data == "balance":
        user = UserModel.get_user(user_id)
        if user:
            keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
            query.edit_message_text(
                f"💰 Ваш баланс: {user.loyalty_points:.2f} баллов",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
# my_qr удалён
    
    # Обмен баллов для клиента
    elif data == "exchange_points":
        user = UserModel.get_user(user_id)
        if user:
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]]
            query.edit_message_text(
                f"💸 Обмен баллов на скидку\n\n"
                f"Ваш баланс: {user.loyalty_points:.2f} баллов\n"
                f"Курс: 5 баллов = 1 рубль\n\n"
                "Введите количество баллов для обмена:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['waiting_for_exchange_points'] = True
    
    # Списание баллов продавцом (по username/телефону/ID)
    elif data == "spend_points_seller":
        if is_seller(user_id):
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]]
            query.edit_message_text(
                "💸 Списание баллов\n\n"
                "Введите данные клиента:\n"
                "- Username (например: @ivan или ivan)\n"
                "- Номер телефона\n"
                "- ID клиента",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['waiting_for_client_search'] = True
    
    elif data == "add_payment":
        if is_seller(user_id):
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]]
            query.edit_message_text(
                "💰 Добавление оплаты\n\n"
                "Шаг 1/2: Введите данные клиента:\n"
                "- Username (@ivan или ivan)\n"
                "- Номер телефона\n"
                "- ID клиента",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['waiting_for_payment_client'] = True
    
# scan_qr удалён - больше не используется
    
    elif data == "manage_roles":
        if is_admin(user_id):
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]]
            query.edit_message_text(
                "👥 Управление ролями\n\n"
                "Отправьте команду в формате:\n"
                "/setrole <user_id> <role>\n\n"
                "Роли: creator, admin, seller, client",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif data == "broadcast":
        if is_admin(user_id):
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]]
            query.edit_message_text(
                "📢 Массовая рассылка\n\nОтправьте сообщение для рассылки",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['waiting_for_broadcast'] = True
    
    # Настройка рассылки в ДР
    elif data == "birthday_settings":
        if is_admin(user_id):
            try:
                # Получаем текущие настройки
                birthday_msg = BirthdayMessageModel.get_birthday_message()
                current_text = birthday_msg.message_text if birthday_msg else "Не настроено"
                has_photo = birthday_msg and birthday_msg.photo_file_id
                
                keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]]
                query.edit_message_text(
                    "🎂 Настройка рассылки в День Рождения\n\n"
                    f"Текущий текст:\n{current_text[:100]}...\n"
                    f"Фото: {'✅ Есть' if has_photo else '❌ Нет'}\n\n"
                    "Введите новый текст поздравления:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                context.user_data['birthday_setup_step'] = 'text'
            except Exception as e:
                logger.error(f"Ошибка настройки рассылки ДР: {e}")
                query.edit_message_text(
                    "❌ Ошибка настройки рассылки.\n"
                    "Попробуйте позже или обратитесь к разработчику."
                )

def handle_text(update: Update, context: CallbackContext):
    """Обработчик текста"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Изменение имени в профиле
    if context.user_data.get('editing_name'):
        if not text.strip():
            update.message.reply_text("❌ Имя не может быть пустым\nПопробуйте ещё раз:")
            return
        
        # Обновляем имя через модель
        try:
            from database_sync import SessionLocal, User
            session = SessionLocal()
            db_user = session.query(User).filter_by(telegram_id=user_id).first()
            if db_user:
                db_user.profile_name = text.strip()
                session.commit()
                update.message.reply_text(
                    f"✅ Имя успешно изменено на: {text.strip()}\n\n"
                    "Используйте /menu для возврата в меню"
                )
            else:
                update.message.reply_text("❌ Ошибка: пользователь не найден")
            session.close()
        except Exception as e:
            logger.error(f"Ошибка изменения имени: {e}")
            update.message.reply_text("❌ Ошибка при изменении имени. Попробуйте позже.")
        
        context.user_data.clear()
        return
    
    # Обработка регистрации - Шаг 1: Имя (ФИО или кастомное)
    elif context.user_data.get('registration_step') == 'name':
        # Проверка что имя не пустое
        if not text.strip():
            update.message.reply_text(
                "❌ Имя не может быть пустым\n"
                "Попробуйте ещё раз:"
            )
            return
        
        context.user_data['profile_name'] = text.strip()
        context.user_data['registration_step'] = 'phone'
        
        # Создаём кнопку для отправки телефона
        keyboard = [[KeyboardButton("📱 Отправить номер телефона", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        update.message.reply_text(
            f"✅ Отлично, {text}!\n\n"
            "Шаг 2/3: Поделитесь номером телефона\n"
            "Нажмите кнопку ниже 👇\n\n"
            "Telegram автоматически отправит ваш номер телефона",
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
        user = update.effective_user
        
        # Обновляем профиль (username берется автоматически из Telegram)
        UserModel.update_profile(user_id, profile_name, phone_number, birth_date)
        
        # Очищаем данные регистрации
        context.user_data.clear()
        
        # Формируем сообщение с данными
        profile_info = f"Имя: {profile_name}\n"
        profile_info += f"Телефон: {phone_number}\n"
        if user.username:
            profile_info += f"Username: @{user.username}\n"
        profile_info += f"Дата рождения: {text}\n"
        profile_info += f"ID: {user_id}"
        
        update.message.reply_text(
            "✅ Регистрация завершена!\n\n"
            "📋 Ваши данные:\n" + profile_info + "\n\n"
            "Теперь вы можете пользоваться всеми функциями бота.\n"
            "Используйте /menu для начала работы",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/menu")]], resize_keyboard=True)
        )
        return
    
    # Поиск клиента для добавления оплаты
    if context.user_data.get('waiting_for_payment_client'):
        # Ищем клиента по username/телефону/ID
        client = None
        
        # Попробуем найти по ID
        if text.isdigit():
            client = UserModel.get_user(int(text))
        # По номеру телефона
        elif text.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            phone = text.replace('+', '').replace(' ', '').replace('-', '')
            client = UserModel.find_user_by_phone(phone)
        # По username
        else:
            client = UserModel.find_user_by_username(text)
        
        if not client:
            update.message.reply_text(
                "❌ Клиент не найден\n\n"
                "Попробуйте ещё раз или используйте /menu для отмены"
            )
            return
        
        context.user_data['client_id'] = client.telegram_id
        context.user_data['waiting_for_payment_client'] = False
        context.user_data['waiting_for_payment_amount'] = True
        
        update.message.reply_text(
            f"✅ Клиент найден:\n"
            f"Имя: {client.profile_name or client.first_name}\n"
            f"ID: {client.telegram_id}\n\n"
            "Шаг 2/2: Введите сумму покупки (например: 1500)"
        )
        return
    
    # Обработка суммы после выбора клиента
    elif context.user_data.get('waiting_for_payment_amount'):
        try:
            amount = float(text.replace(',', '.'))
            if amount <= 0:
                update.message.reply_text("Сумма должна быть больше нуля")
                return
            
            client_id = context.user_data.get('client_id')
            client = UserModel.get_user(client_id)
            
            if not client:
                update.message.reply_text("Ошибка: клиент не найден")
                context.user_data.clear()
                return
            
            # Начисляем баллы
            points = amount * POINTS_PER_RUBLE
            UserModel.add_points(client_id, points)
            PaymentModel.create_payment(
                client_id=client.id,
                seller_id=user_id,
                amount=amount,
                points_earned=points
            )
            
            update.message.reply_text(
                f"✅ Оплата добавлена!\n\n"
                f"Клиент: {client.profile_name or client.first_name}\n"
                f"Сумма: {amount}₽\n"
                f"Баллов начислено: +{points:.2f}"
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
    
    # Поиск клиента для списания баллов продавцом
    elif context.user_data.get('waiting_for_client_search'):
        # Ищем клиента по username/телефону/ID
        client = None
        
        if text.isdigit():
            client = UserModel.get_user(int(text))
        elif text.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            phone = text.replace('+', '').replace(' ', '').replace('-', '')
            client = UserModel.find_user_by_phone(phone)
        else:
            client = UserModel.find_user_by_username(text)
        
        if not client:
            update.message.reply_text("❌ Клиент не найден\n\nПопробуйте ещё раз")
            return
        
        context.user_data['spend_client_id'] = client.telegram_id
        context.user_data['waiting_for_client_search'] = False
        context.user_data['waiting_for_spend_amount'] = True
        
        update.message.reply_text(
            f"✅ Клиент найден:\n"
            f"Имя: {client.profile_name or client.first_name}\n"
            f"Баланс: {client.loyalty_points:.2f} баллов\n\n"
            "Введите количество баллов для списания:"
        )
        return
    
    # Списание баллов продавцом
    elif context.user_data.get('waiting_for_spend_amount'):
        try:
            points = float(text.replace(',', '.'))
            if points <= 0:
                update.message.reply_text("Количество баллов должно быть больше нуля")
                return
            
            client_id = context.user_data.get('spend_client_id')
            client = UserModel.get_user(client_id)
            
            if not client:
                update.message.reply_text("Клиент не найден")
                context.user_data.clear()
                return
            
            if client.loyalty_points < points:
                update.message.reply_text(
                    f"❌ У клиента недостаточно баллов!\n"
                    f"Баланс: {client.loyalty_points:.2f}\n"
                    f"Запрошено: {points:.2f}"
                )
                context.user_data.clear()
                return
            
            # Списываем баллы
            discount = points / 5.0
            success = UserModel.spend_points(client_id, points)
            
            if success:
                updated_client = UserModel.get_user(client_id)
                update.message.reply_text(
                    f"✅ Баллы списаны!\n\n"
                    f"Клиент: {client.profile_name or client.first_name}\n"
                    f"Списано: {points:.2f} баллов\n"
                    f"Скидка: {discount:.2f} руб.\n"
                    f"Остаток: {updated_client.loyalty_points:.2f}"
                )
                
                # Уведомление клиента
                try:
                    context.bot.send_message(
                        chat_id=client_id,
                        text=f"💸 Использовано {points:.2f} баллов\nСкидка: {discount:.2f} руб."
                    )
                except:
                    pass
            else:
                update.message.reply_text("Ошибка при списании баллов")
            
            context.user_data.clear()
        except ValueError:
            update.message.reply_text("Пожалуйста, введите корректное число")
    
    # Обмен баллов (для клиента) - показываем информацию
    elif context.user_data.get('waiting_for_exchange_points'):
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
            
            # Показываем информацию для продавца
            user_info = f"ID: {user_id}"
            if user.profile_name:
                user_info += f"\nИмя: {user.profile_name}"
            if user.phone_number:
                user_info += f"\nТелефон: {user.phone_number}"
            if user.username:
                user_info += f"\nUsername: @{user.username}"
            
            update.message.reply_text(
                f"💸 Информация для обмена баллов\n\n"
                f"Баллов к обмену: {points:.2f}\n"
                f"Скидка: {discount_amount:.2f} руб.\n"
                f"Курс: 5 баллов = 1 рубль\n\n"
                f"📋 Сообщите продавцу:\n{user_info}\n\n"
                f"Продавец спишет баллы через свой интерфейс"
            )
            context.user_data.clear()
        except ValueError:
            update.message.reply_text("Пожалуйста, введите корректное число")
    
    # Пропуск фото для рассылки ДР
    elif text == '/skip' and context.user_data.get('birthday_setup_step') == 'photo':
        if is_admin(user_id):
            birthday_text = context.user_data.get('birthday_text')
            BirthdayMessageModel.update_birthday_message(birthday_text, None)
            update.message.reply_text(
                "✅ Настройки сохранены!\n\n"
                "Рассылка в ДР будет отправляться только с текстом (без фото)"
            )
            context.user_data.clear()
        return
    
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
    
    # Настройка текста для рассылки в ДР
    elif context.user_data.get('birthday_setup_step') == 'text':
        if is_admin(user_id):
            context.user_data['birthday_text'] = text
            context.user_data['birthday_setup_step'] = 'photo'
            update.message.reply_text(
                "✅ Текст сохранён!\n\n"
                "Теперь отправьте фото для поздравления\n"
                "(или отправьте /skip чтобы пропустить)"
            )
        return
    
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
    """Обработчик фотографий"""
    user_id = update.effective_user.id
    
    # Фото для рассылки в ДР
    if context.user_data.get('birthday_setup_step') == 'photo' and is_admin(user_id):
        photo = update.message.photo[-1]
        photo_file_id = photo.file_id
        birthday_text = context.user_data.get('birthday_text')
        
        BirthdayMessageModel.update_birthday_message(birthday_text, photo_file_id)
        
        update.message.reply_text(
            "✅ Настройки рассылки в ДР сохранены!\n\n"
            "Поздравления будут автоматически отправляться клиентам в день их рождения"
        )
        context.user_data.clear()


def handle_contact(update: Update, context: CallbackContext):
    """Обработчик контакта (номер телефона)"""
    user_id = update.effective_user.id
    user = update.effective_user
    
    if context.user_data.get('registration_step') == 'phone':
        contact = update.message.contact
        
        # Проверяем, что пользователь отправил свой номер
        if contact.user_id != user_id:
            update.message.reply_text("❌ Пожалуйста, отправьте ВАШ номер телефона")
            return
        
        phone_number = contact.phone_number
        context.user_data['phone_number'] = phone_number
        context.user_data['registration_step'] = 'birth_date'
        
        # Сохраняем также username из Telegram
        username_info = ""
        if user.username:
            username_info = f"Username: @{user.username}\n"
        
        update.message.reply_text(
            f"✅ Номер телефона сохранён: {phone_number}\n"
            f"{username_info}\n"
            "Шаг 3/3: Введите дату рождения\n"
            "Формат: ДД.ММ.ГГГГ (например: 25.12.1995)",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/menu")]], resize_keyboard=True)
        )


def send_birthday_greetings(context: CallbackContext):
    """Отправка поздравлений именинникам"""
    from datetime import datetime
    
    # Получаем пользователей с ДР сегодня
    birthday_users = UserModel.get_users_with_birthday_today()
    
    if not birthday_users:
        return
    
    # Получаем настройки рассылки
    birthday_msg = BirthdayMessageModel.get_birthday_message()
    
    if not birthday_msg or not birthday_msg.message_text:
        logger.warning("Настройки рассылки ДР не настроены")
        return
    
    sent = 0
    for user in birthday_users:
        try:
            if birthday_msg.photo_file_id:
                context.bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=birthday_msg.photo_file_id,
                    caption=birthday_msg.message_text
                )
            else:
                context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=birthday_msg.message_text
                )
            sent += 1
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка отправки ДР поздравления {user.telegram_id}: {e}")
    
    logger.info(f"Отправлено {sent} поздравлений с ДР")


def main():
    """Запуск бота"""
    # Инициализация БД
    from database_sync import init_db
    init_db()
    logger.info("База данных инициализирована")
    
    # Создание updater
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Настройка меню с быстрыми командами
    from telegram import BotCommand
    try:
        updater.bot.set_my_commands([
            BotCommand("start", "🏠 Начало работы"),
            BotCommand("menu", "📋 Главное меню"),
            BotCommand("balance", "💰 Мой баланс"),
        ])
        logger.info("Быстрые команды настроены")
    except Exception as e:
        logger.error(f"Ошибка настройки команд: {e}")
    
    # Регистрация обработчиков
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(Filters.contact, handle_contact))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    # Настройка автоматической рассылки ДР (каждый день в 10:00)
    from telegram.ext import JobQueue
    job_queue = updater.job_queue
    
    # Отправка поздравлений каждый день в 10:00 (36000 секунд = 10 часов)
    import datetime
    now = datetime.datetime.now()
    target_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
    
    if now > target_time:
        target_time += datetime.timedelta(days=1)
    
    delay = (target_time - now).total_seconds()
    
    job_queue.run_once(send_birthday_greetings, delay)
    job_queue.run_repeating(send_birthday_greetings, interval=86400, first=delay)
    logger.info("Автоматическая рассылка ДР настроена на 10:00 каждый день")
    
    # Запуск
    logger.info("Бот запущен")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

