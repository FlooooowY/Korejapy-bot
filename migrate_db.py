#!/usr/bin/env python3
"""
Скрипт миграции базы данных
Добавляет новые поля для профиля пользователя и рассылки в ДР
"""

import sqlite3
import sys

def migrate_database(db_path='korejapy_bot.db'):
    """Миграция базы данных"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"🔄 Начинаю миграцию базы данных: {db_path}")
        
        # Проверяем какие колонки уже есть
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Существующие колонки в таблице users: {existing_columns}")
        
        # Добавляем новые колонки в таблицу users
        migrations = []
        
        if 'profile_name' not in existing_columns:
            migrations.append("ALTER TABLE users ADD COLUMN profile_name TEXT")
        
        if 'phone_number' not in existing_columns:
            migrations.append("ALTER TABLE users ADD COLUMN phone_number TEXT")
        
        if 'birth_date' not in existing_columns:
            migrations.append("ALTER TABLE users ADD COLUMN birth_date TEXT")
        
        if 'is_registered' not in existing_columns:
            migrations.append("ALTER TABLE users ADD COLUMN is_registered BOOLEAN DEFAULT 0")
        
        # Выполняем миграции для users
        for migration in migrations:
            print(f"  ➕ Выполняю: {migration}")
            cursor.execute(migration)
        
        if migrations:
            print(f"✅ Добавлено {len(migrations)} новых колонок в таблицу users")
        else:
            print("✅ Таблица users уже актуальна")
        
        # Создаём таблицу birthday_messages если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS birthday_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL,
                photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Таблица birthday_messages создана/проверена")
        
        # Сохраняем изменения
        conn.commit()
        print("✅ Миграция успешно завершена!")
        
        # Показываем обновлённую структуру
        cursor.execute("PRAGMA table_info(users)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Обновлённые колонки в таблице users: {updated_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        return False

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'korejapy_bot.db'
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)

