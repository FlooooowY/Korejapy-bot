#!/bin/bash

# Скрипт автоматической установки Korejapy Bot
# Для Ubuntu/Debian

echo "================================================"
echo "   Установка Korejapy Bot"
echo "================================================"

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка необходимых пакетов
echo "📦 Установка Python и зависимостей..."
apt install -y python3 python3-pip git nano htop

# Переход в домашнюю директорию
cd /root

# Клонирование репозитория
echo "📥 Загрузка бота с GitHub..."
if [ -d "Korejapy-bot" ]; then
    echo "⚠️  Папка Korejapy-bot уже существует, удаляем..."
    rm -rf Korejapy-bot
fi
git clone https://github.com/FlooooowY/Korejapy-bot.git
cd Korejapy-bot

# Установка Python зависимостей
echo "📦 Установка Python библиотек..."
pip3 install python-telegram-bot python-dotenv sqlalchemy aiosqlite qrcode Pillow aiofiles --break-system-packages

# Создание systemd службы
echo "⚙️  Настройка автозапуска..."
cat > /etc/systemd/system/korejapy-bot.service << 'EOF'
[Unit]
Description=Korejapy Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Korejapy-bot
ExecStart=/usr/bin/python3 /root/Korejapy-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
systemctl daemon-reload

# Включение автозапуска
systemctl enable korejapy-bot

# Запуск бота
echo "🚀 Запуск бота..."
systemctl start korejapy-bot

# Ожидание запуска
sleep 3

# Проверка статуса
echo ""
echo "================================================"
echo "   ✅ Установка завершена!"
echo "================================================"
echo ""
systemctl status korejapy-bot --no-pager
echo ""
echo "📋 Полезные команды:"
echo "  systemctl status korejapy-bot    - Статус бота"
echo "  systemctl restart korejapy-bot   - Перезапуск"
echo "  systemctl stop korejapy-bot      - Остановка"
echo "  journalctl -u korejapy-bot -f    - Просмотр логов"
echo ""
echo "🎉 Бот работает 24/7!"
echo "================================================"

