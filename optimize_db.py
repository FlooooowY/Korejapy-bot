#!/usr/bin/env python3
"""
Оптимизация базы данных - добавление индексов для ускорения запросов
"""

import sqlite3
import sys

def optimize_database(db_path='korejapy_bot.db'):
    """Оптимизация базы данных"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🚀 Оптимизация базы данных...")
        
        # Добавляем индексы для таблицы users
        indexes = [
            ("idx_users_telegram_id", "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)"),
            ("idx_users_username", "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"),
            ("idx_users_phone", "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)"),
            ("idx_users_role", "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)"),
            ("idx_users_birth_date", "CREATE INDEX IF NOT EXISTS idx_users_birth_date ON users(birth_date)"),
            ("idx_payments_client", "CREATE INDEX IF NOT EXISTS idx_payments_client ON payments(client_id)"),
            ("idx_payments_seller", "CREATE INDEX IF NOT EXISTS idx_payments_seller ON payments(seller_id)"),
        ]
        
        created = 0
        for idx_name, query in indexes:
            try:
                cursor.execute(query)
                print(f"  ✅ Индекс {idx_name} создан")
                created += 1
            except Exception as e:
                print(f"  ℹ️ Индекс {idx_name} уже существует")
        
        # VACUUM - оптимизация и дефрагментация БД
        print("\n🔧 Выполняю VACUUM (дефрагментация)...")
        cursor.execute("VACUUM")
        
        # ANALYZE - обновление статистики для оптимизатора запросов
        print("📊 Выполняю ANALYZE (обновление статистики)...")
        cursor.execute("ANALYZE")
        
        conn.commit()
        
        # Показываем размер БД
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        size = cursor.fetchone()[0]
        size_mb = size / 1024 / 1024
        
        print(f"\n✅ Оптимизация завершена!")
        print(f"📦 Размер БД: {size_mb:.2f} МБ")
        print(f"🎯 Создано индексов: {created}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка оптимизации: {e}")
        return False

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'korejapy_bot.db'
    success = optimize_database(db_path)
    sys.exit(0 if success else 1)

