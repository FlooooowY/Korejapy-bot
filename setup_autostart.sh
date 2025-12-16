#!/bin/bash

# Скрипт для настройки автозапуска бота на Linux сервере
# Использование: ./setup_autostart.sh

echo "================================================"
echo "   Настройка автозапуска Korejapy Bot"
echo "================================================"
echo ""

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Ошибка: Скрипт должен быть запущен от root"
    echo "Используйте: sudo ./setup_autostart.sh"
    exit 1
fi

# Определение пути к боту
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BOT_DIR="$SCRIPT_DIR"
BOT_FILE="$BOT_DIR/bot_v13.py"

# Проверка существования файла бота
if [ ! -f "$BOT_FILE" ]; then
    echo "❌ Ошибка: Файл bot.py не найден в $BOT_DIR"
    exit 1
fi

echo "📁 Директория бота: $BOT_DIR"
echo "🐍 Файл бота: $BOT_FILE"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: Python3 не установлен"
    echo "Установите: apt install python3 python3-pip"
    exit 1
fi

PYTHON_PATH=$(which python3)
echo "✅ Python найден: $PYTHON_PATH"
echo ""

# Создание systemd service файла
SERVICE_FILE="/etc/systemd/system/korejapy-bot.service"

echo "⚙️  Создание systemd службы..."
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Korejapy Telegram Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$BOT_DIR
ExecStart=$PYTHON_PATH $BOT_FILE
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=korejapy-bot

# Ограничения ресурсов (опционально)
# MemoryLimit=512M
# CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service файл создан: $SERVICE_FILE"
echo ""

# Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload
echo "✅ systemd перезагружен"
echo ""

# Включение автозапуска
echo "🔧 Включение автозапуска..."
systemctl enable korejapy-bot
echo "✅ Автозапуск включен"
echo ""

# Запуск бота
echo "🚀 Запуск бота..."
systemctl start korejapy-bot
sleep 2

# Проверка статуса
echo ""
echo "================================================"
echo "   Статус бота"
echo "================================================"
systemctl status korejapy-bot --no-pager -l
echo ""

# Проверка, запущен ли бот
if systemctl is-active --quiet korejapy-bot; then
    echo "✅ Бот успешно запущен!"
else
    echo "⚠️  Бот не запустился. Проверьте логи:"
    echo "   journalctl -u korejapy-bot -n 50"
fi

echo ""
echo "================================================"
echo "   📋 Полезные команды"
echo "================================================"
echo ""
echo "  Просмотр статуса:"
echo "    systemctl status korejapy-bot"
echo ""
echo "  Просмотр логов (в реальном времени):"
echo "    journalctl -u korejapy-bot -f"
echo ""
echo "  Просмотр последних 50 строк логов:"
echo "    journalctl -u korejapy-bot -n 50"
echo ""
echo "  Перезапуск бота:"
echo "    systemctl restart korejapy-bot"
echo ""
echo "  Остановка бота:"
echo "    systemctl stop korejapy-bot"
echo ""
echo "  Отключить автозапуск:"
echo "    systemctl disable korejapy-bot"
echo ""
echo "================================================"
echo "   ✅ Настройка завершена!"
echo "================================================"
echo ""
echo "Бот будет автоматически запускаться:"
echo "  ✅ При загрузке сервера"
echo "  ✅ При перезагрузке"
echo "  ✅ При сбоях (автоматический перезапуск через 10 сек)"
echo ""

