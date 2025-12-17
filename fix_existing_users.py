#!/usr/bin/env python3
"""
Скрипт для автоматической регистрации существующих админов и продавцов
"""

import sqlite3

ADMIN_USERNAMES = ['flooooooooooowy', 'katrinzagora']
SELLER_USERNAMES = ['fublat_666', 'shad0w_04', 'mikk4u']

def fix_users(db_path='korejapy_bot.db'):
    """Помечаем админов и продавцов как зарегистрированных"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Обновление существующих пользователей...")
        
        # Получаем всех пользователей
        cursor.execute("SELECT id, telegram_id, username, role FROM users")
        users = cursor.fetchall()
        
        updated = 0
        
        for user_id, telegram_id, username, role in users:
            should_register = False
            
            # Проверяем админов
            if username and username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
                should_register = True
                if role not in ['admin', 'creator']:
                    cursor.execute("UPDATE users SET role = ? WHERE id = ?", ('admin', user_id))
                    print(f"  👑 {username} (ID: {telegram_id}) -> роль изменена на admin")
            
            # Проверяем продавцов
            elif username and username.lower() in [u.lower() for u in SELLER_USERNAMES]:
                should_register = True
                if role not in ['seller', 'admin', 'creator']:
                    cursor.execute("UPDATE users SET role = ? WHERE id = ?", ('seller', user_id))
                    print(f"  🛍️ {username} (ID: {telegram_id}) -> роль изменена на seller")
            
            # Помечаем как зарегистрированных
            if should_register:
                cursor.execute("UPDATE users SET is_registered = 1 WHERE id = ?", (user_id,))
                print(f"  ✅ {username} (ID: {telegram_id}) -> помечен как зарегистрированный")
                updated += 1
        
        conn.commit()
        print(f"\n✅ Обновлено пользователей: {updated}")
        
        # Показываем итоговую статистику
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        stats = cursor.fetchall()
        print("\n📊 Статистика пользователей:")
        for role, count in stats:
            print(f"  {role}: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == '__main__':
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'korejapy_bot.db'
    success = fix_users(db_path)
    sys.exit(0 if success else 1)

