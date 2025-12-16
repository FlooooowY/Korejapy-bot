# Деплой Korejapy Bot на сервер 24/7

## Вариант 1: VPS/VDS сервер (Рекомендуется)

### Шаг 1: Арендуйте сервер

**Популярные провайдеры:**
- **Timeweb** (от 200₽/мес) - timeweb.com
- **REG.RU** (от 150₽/мес) - reg.ru
- **DigitalOcean** ($6/мес) - digitalocean.com

**Минимальные требования:**
- 512 MB RAM
- 1 CPU
- 10 GB диск
- Ubuntu 20.04 или новее

### Шаг 2: Подключитесь к серверу

Windows (PowerShell):
```powershell
ssh root@ваш_ip_сервера
```

Введите пароль, который прислал провайдер.

### Шаг 3: Установите Python

```bash
apt update
apt install python3 python3-pip git -y
```

### Шаг 4: Загрузите бота на сервер

**Вариант А: Через Git (если код на GitHub)**
```bash
cd /root
git clone ваш_репозиторий
cd MFDigitalBot
```

**Вариант Б: Через FileZilla/SCP**
1. Скачайте FileZilla: filezilla-project.org
2. Подключитесь к серверу (SFTP)
3. Загрузите всю папку MFDigitalBot

**Вариант В: Простой способ - создайте файлы на сервере**
```bash
mkdir /root/korejapy_bot
cd /root/korejapy_bot
nano bot.py
# Вставьте код бота (Ctrl+Shift+V), затем Ctrl+X, Y, Enter
nano database.py
# Вставьте код
nano models.py
# Вставьте код
nano qr_generator.py
# Вставьте код
nano requirements.txt
# Вставьте зависимости
```

### Шаг 5: Установите зависимости

```bash
pip3 install -r requirements.txt
```

### Шаг 6: Настройте автозапуск с systemd

Создайте файл службы:
```bash
nano /etc/systemd/system/korejapy-bot.service
```

Вставьте:
```ini
[Unit]
Description=Korejapy Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/korejapy_bot
ExecStart=/usr/bin/python3 /root/korejapy_bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Сохраните (Ctrl+X, Y, Enter).

### Шаг 7: Запустите бота

```bash
# Перезагрузите systemd
systemctl daemon-reload

# Включите автозапуск
systemctl enable korejapy-bot

# Запустите бота
systemctl start korejapy-bot

# Проверьте статус
systemctl status korejapy-bot
```

### Шаг 8: Управление ботом

```bash
# Просмотр логов
journalctl -u korejapy-bot -f

# Остановить бота
systemctl stop korejapy-bot

# Перезапустить бота
systemctl restart korejapy-bot

# Статус
systemctl status korejapy-bot
```

---

## Вариант 2: PythonAnywhere (Бесплатно, но с ограничениями)

### Шаг 1: Регистрация
1. Зайдите на pythonanywhere.com
2. Создайте бесплатный аккаунт

### Шаг 2: Загрузка кода
1. Dashboard → Files
2. Upload files: bot.py, database.py, models.py, qr_generator.py, requirements.txt, photo.jpg

### Шаг 3: Установка зависимостей
1. Dashboard → Consoles → Bash
```bash
pip3 install --user -r requirements.txt
```

### Шаг 4: Запуск
1. Dashboard → Tasks
2. Добавьте задачу: `python3 /home/yourname/bot.py`
3. Установите запуск каждые 24 часа

**Минусы:**
- Нужно перезапускать каждые 24 часа
- Ограниченная скорость

---

## Вариант 3: Heroku (Бесплатно, но сложнее)

### Шаг 1: Подготовьте файлы

Создайте `Procfile` в папке с ботом:
```
worker: python bot.py
```

Создайте `runtime.txt`:
```
python-3.11.0
```

### Шаг 2: Установите Heroku CLI
Скачайте с heroku.com/cli

### Шаг 3: Деплой
```bash
cd путь_к_папке_бота
heroku login
heroku create korejapy-bot
git init
git add .
git commit -m "Initial commit"
git push heroku master
heroku ps:scale worker=1
```

---

## 🎯 Какой вариант выбрать?

| Вариант | Цена | Сложность | Надежность |
|---------|------|-----------|------------|
| **VPS/VDS** | ~200₽/мес | Средняя | ⭐⭐⭐⭐⭐ |
| **PythonAnywhere** | Бесплатно | Легко | ⭐⭐⭐ |
| **Heroku** | Бесплатно | Сложно | ⭐⭐⭐⭐ |

**Рекомендация:** VPS/VDS от Timeweb или REG.RU

---

## 📝 Полезные команды для сервера

```bash
# Проверить, работает ли Python
python3 --version

# Проверить процессы Python
ps aux | grep python

# Убить процесс (если нужно)
pkill -f bot.py

# Просмотр использования ресурсов
htop

# Скачать файл с сервера на ПК
scp root@ip:/root/korejapy_bot/korejapy_bot.db ./

# Загрузить файл на сервер с ПК
scp ./bot.py root@ip:/root/korejapy_bot/
```

---

## 🔧 Обновление бота на сервере

```bash
# Подключитесь к серверу
ssh root@ip

# Остановите бота
systemctl stop korejapy-bot

# Обновите файлы (через git или вручную)
cd /root/korejapy_bot
nano bot.py  # Внесите изменения

# Запустите бота
systemctl start korejapy-bot

# Проверьте логи
journalctl -u korejapy-bot -f
```

---

## 🆘 Устранение проблем

### Бот не запускается
```bash
# Проверьте логи
journalctl -u korejapy-bot -n 50

# Попробуйте запустить вручную
cd /root/korejapy_bot
python3 bot.py
```

### Нет зависимостей
```bash
pip3 install python-telegram-bot python-dotenv sqlalchemy aiosqlite qrcode Pillow aiofiles
```

### База данных заблокирована
```bash
rm korejapy_bot.db
python3 bot.py  # База создастся заново
```

---

## ✅ Готово!

После настройки бот будет работать 24/7 автоматически, даже после перезагрузки сервера.

