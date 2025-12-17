#!/usr/bin/env python3
"""
Миграция таблицы birthday_messages: photo_path -> photo_file_id
"""

import sqlite3
import sys

def migrate_birthday_table(db_path='korejapy_bot.db'):
    """Миграция таблицы birthday_messages"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Миграция таблицы birthday_messages...")
        
        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='birthday_messages'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("  ℹ️ Таблица birthday_messages не существует, создаём...")
            cursor.execute("""
                CREATE TABLE birthday_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT NOT NULL,
                    photo_file_id TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  ✅ Таблица birthday_messages создана")
        else:
            # Проверяем колонки
            cursor.execute("PRAGMA table_info(birthday_messages)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Переименовываем photo_path в photo_file_id если нужно
            if 'photo_path' in columns and 'photo_file_id' not in columns:
                print("  🔄 Переименовываем photo_path -> photo_file_id...")
                cursor.execute("ALTER TABLE birthday_messages RENAME COLUMN photo_path TO photo_file_id")
                print("  ✅ Колонка переименована")
            elif 'photo_file_id' in columns:
                print("  ✅ Колонка photo_file_id уже существует")
            else:
                print("  ➕ Добавляем колонку photo_file_id...")
                cursor.execute("ALTER TABLE birthday_messages ADD COLUMN photo_file_id TEXT")
                print("  ✅ Колонка photo_file_id добавлена")
            
            # Добавляем updated_at если нет
            if 'updated_at' not in columns:
                print("  ➕ Добавляем колонку updated_at...")
                cursor.execute("ALTER TABLE birthday_messages ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("  ✅ Колонка updated_at добавлена")
        
        conn.commit()
        print("\n✅ Миграция birthday_messages завершена!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'korejapy_bot.db'
    success = migrate_birthday_table(db_path)
    sys.exit(0 if success else 1)

