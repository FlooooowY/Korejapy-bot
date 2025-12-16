#!/bin/bash
# Исправление установки на сервере

echo "🔧 Установка системных библиотек для Pillow..."
apt update
apt install -y python3-dev libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev

echo "📦 Установка Python пакетов..."
pip3 install --upgrade pip
pip3 install python-telegram-bot==20.7 python-dotenv sqlalchemy aiosqlite qrcode Pillow aiofiles

echo "✅ Готово!"

