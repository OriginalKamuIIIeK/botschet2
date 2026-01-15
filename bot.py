import json
import os
import telebot
import telebot.apihelper
from datetime import datetime
import re
import threading
from flask import Flask


# ТВОИ ДАННЫЕ
# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
PORT = 10000  # Добавить эту строку

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот бухгалтера работает!"

@app.route('/health')
def health():
    return "OK", 200

# Запускаем Flask в отдельном потоке
def run_web_server():
    app.run(host='0.0.0.0', port=PORT, debug=False)

print(f"🚀 Запускаю веб-сервер на порту {PORT}...")
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()
TOKEN = "8114014716:AAFwW5y7O3goMXWtZm6scpxEj-5VloP37ro"  # ⚠️ ЗАМЕНИ!
MAIN_ADMIN = 7620190298


# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# ПУТИ ДЛЯ ХРАНЕНИЯ ДАННЫХ
BASE_PATH = "/data" if os.path.isdir("/data") else "."
GLOBAL_PATH = os.path.join(BASE_PATH, "global")
CHATS_PATH = os.path.join(BASE_PATH, "chats")

# Создаем папки если нет
os.makedirs(GLOBAL_PATH, exist_ok=True)
os.makedirs(CHATS_PATH, exist_ok=True)

# Файлы
ADMINS_FILE = os.path.join(GLOBAL_PATH, "admins.json")
SETTINGS_FILE = os.path.join(GLOBAL_PATH, "settings.json")

print(f"📁 База данных: {BASE_PATH}")
print(f"📁 Глобальные данные: {GLOBAL_PATH}")
print(f"📁 Данные чатов: {CHATS_PATH}")

# ========== РАБОТА С ДАННЫМИ ==========

def get_chat_filename(chat_id):
    """Получаем имя файла для чата"""
    return os.path.join(CHATS_PATH, f"chat_{chat_id}.json")

def load_chat_data(chat_id):
    """Загружаем данные чата"""
    chat_file = get_chat_filename(chat_id)
    
    try:
        if os.path.exists(chat_file):
            with open(chat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем старые значения
                for key in ['balance', 'total_earned', 'total_paid', 'rate', 'percent']:
                    if key in data:
                        data[key] = float(data[key])
                return data
    except Exception as e:
        print(f"❌ Ошибка загрузки данных чата {chat_id}: {e}")
    
    # Возвращаем данные по умолчанию
    return {
        "chat_id": chat_id,
        "chat_title": "Личный чат" if chat_id > 0 else "Группа",
        "balance": 0.0,
        "total_earned": 0.0,
        "total_paid": 0.0,
        "rate": 0,      # Можно установить разные курсы для разных чатов
        "percent": 0,    # И разные проценты
        "transactions": [],
        "payments": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def save_chat_data(chat_id, data):
    """Сохраняем данные чата"""
    chat_file = get_chat_filename(chat_id)
    
    try:
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения данных чата {chat_id}: {e}")
        return False

def load_global_admins():
    """Загружаем список глобальных админов"""
    try:
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r') as f:
                admins = json.load(f)
                # Добавляем главного админа если его нет
                if MAIN_ADMIN not in admins:
                    admins.append(MAIN_ADMIN)
                    save_global_admins(admins)
                return admins
    except:
        pass
    return [MAIN_ADMIN]

def save_global_admins(admins):
    """Сохраняем список глобальных админов"""
    try:
        with open(ADMINS_FILE, 'w') as f:
            json.dump(admins, f)
        return True
    except:
        return False

def is_global_admin(user_id):
    """Проверяем глобального админа"""
    admins = load_global_admins()
    return user_id in admins

def get_all_chats():
    """Получаем список всех чатов"""
    try:
        chat_files = [f for f in os.listdir(CHATS_PATH) if f.startswith("chat_")]
        chats = []
        for file in chat_files:
            try:
                chat_id = int(file[5:-5])  # chat_123456789.json -> 123456789
                data = load_chat_data(chat_id)
                chats.append({
                    "chat_id": chat_id,
                    "title": data.get("chat_title", "Неизвестно"),
                    "balance": data.get("balance", 0),
                    "last_activity": data.get("transactions", [])[-1]["time"] if data.get("transactions") else "Нет активности"
                })
            except:
                continue
        return chats
    except:
        return []

# ========== КОМАНДЫ ==========

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not is_global_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id)
    
    # Если это группа, обновляем название
    if message.chat.title:
        data["chat_title"] = message.chat.title
        save_chat_data(chat_id, data)
    
    is_group = chat_id < 0
    chat_type = "👥 ГРУППА" if is_group else "👤 ЛИЧНЫЙ ЧАТ"
    chat_name = message.chat.title if is_group else "ваш"
    
    help_text = f"""✅ *БОТ БУХГАЛТЕРА ЗАПУЩЕН*

{chat_type}: *{chat_name}*
💰 *Баланс чата:* {data['balance']:.2f} USDT

*ОСНОВНЫЕ КОМАНДЫ:*
➕ `+5000` - добавить 5000 в этот чат
💰 `выплата 1000` - выплатить из этого чата
📊 `/balance` - баланс этого чата
📈 `/stats` - статистика этого чата
🔢 `/setrate 0` - курс для этого чата
📌 `/setpercent 0` - процент для этого чата

*ГЛОБАЛЬНЫЕ КОМАНДЫ:*
🌐 `/allchats` - все чаты (только главный)
👑 `/addadmin 123456789` - добавить глобального админа
👥 `/admins` - список глобальных админов
"""
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

# +5000 - ТОЛЬКО ДЛЯ ТЕКУЩЕГО ЧАТА
@bot.message_handler(func=lambda m: m.text and m.text.startswith('+'))
def add_money(message):
    if not is_global_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id)
    
    try:
        amount = float(message.text[1:].strip().replace(',', '.'))
        
        usdt = amount / data['rate']
        fee = usdt * (data['percent'] / 100)
        net = usdt - fee
        
        data['balance'] += net
        data['total_earned'] += net
        
        transaction = {
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'operator': message.from_user.id,
            'amount_rub': amount,
            'amount_usdt': round(usdt, 2),
            'fee': round(fee, 2),
            'net': round(net, 2),
            'balance_after': round(data['balance'], 2)
        }
        
        data['transactions'].append(transaction)
        save_chat_data(chat_id, data)
        
        # Определяем тип чата для ответа
        chat_type = "группы" if chat_id < 0 else "чата"
        chat_name = message.chat.title if chat_id < 0 else "личного чата"
        
        response = f"""✅ *+{amount:,.2f} RUB в {chat_name}*
📊 *Курс чата:* {data['rate']} | *% чата:* {data['percent']}
💵 *В USDT:* {usdt:.2f}
📉 *Комиссия:* {fee:.2f}
📈 *Баланс {chat_type}:* {data['balance']:.2f} USDT
⏰ *Время:* {transaction['time']}"""
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# выплата 1000 - ТОЛЬКО ИЗ ТЕКУЩЕГО ЧАТА
@bot.message_handler(func=lambda m: m.text and ('выплата' in m.text.lower() or 'pay' in m.text.lower()))
def payment(message):
    if not is_global_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id)
    
    try:
        # Ищем число в сообщении
        text = message.text.lower()
        numbers = re.findall(r'\d+\.?\d*', text)
        
        if not numbers:
            bot.reply_to(message, "❌ Укажите сумму: выплата 500")
            return
        
        amount = float(numbers[0].replace(',', '.'))
        
        if amount > data['balance']:
            bot.reply_to(message, f"❌ Недостаточно средств в этом чате. Доступно: {data['balance']:.2f} USDT")
            return
        
        # Создаем выплату
        payment_data = {
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'operator': message.from_user.id,
            'amount': amount,
            'balance_before': data['balance']
        }
        
        # Обновляем баланс
        data['balance'] -= amount
        data['total_paid'] += amount
        data['payments'].append(payment_data)
        
        save_chat_data(chat_id, data)
        
        chat_type = "группы" if chat_id < 0 else "чата"
        chat_name = message.chat.title if chat_id < 0 else "личного чата"
        
        response = f"""💸 *Выплата из {chat_name}:* {amount:.2f} USDT
📊 *Было в {chat_type}:* {payment_data['balance_before']:.2f} USDT
📉 *Стало в {chat_type}:* {data['balance']:.2f} USDT
💰 *Всего выплачено из {chat_type}:* {data['total_paid']:.2f} USDT
⏰ *Время:* {payment_data['time']}"""
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# /balance - БАЛАНС ТЕКУЩЕГО ЧАТА
@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    if not is_global_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id)
    
    chat_type = "группы" if chat_id < 0 else "чата"
    chat_name = message.chat.title if chat_id < 0 else "Личный чат"
    
    response = f"""💰 *БАЛАНС {chat_name.upper()}*
📊 *Текущий баланс:* {data['balance']:.2f} USDT
📈 *Всего начислено:* {data['total_earned']:.2f} USDT
📉 *Всего выплачено:* {data['total_paid']:.2f} USDT
🔢 *Курс {chat_type}:* {data['rate']} RUB/USDT
📌 *Процент {chat_type}:* {data['percent']}%"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

# /stats - СТАТИСТИКА ТЕКУЩЕГО ЧАТА
@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    if not is_global_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id)
    transactions = data.get('transactions', [])
    payments = data.get('payments', [])
    
    # Статистика за сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    today_tx = [t for t in transactions if t.get('time', '').startswith(today)]
    today_payments = [p for p in payments if p.get('time', '').startswith(today)]
    
    chat_type = "группы" if chat_id < 0 else "чата"
    chat_name = message.chat.title if chat_id < 0 else "Личный чат"
    
    response = f"""📊 *СТАТИСТИКА {chat_name.upper()}*

*За сегодня ({today}):*
📥 Пополнений: {len(today_tx)}
💰 Сумма: {sum(t.get('net', 0) for t in today_tx):.2f} USDT
📤 Выплат: {len(today_payments)}
💸 Сумма выплат: {sum(p.get('amount', 0) for p in today_payments):.2f} USDT

*Общая статистика {chat_type}:*
📥 Всего пополнений: {len(transactions)}
📤 Всего выплат: {len(payments)}
💰 Баланс: {data['balance']:.2f} USDT
🔢 Курс: {data['rate']}
📌 Процент: {data['percent']}%"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

# /setrate - УСТАНОВИТЬ КУРС ДЛЯ ТЕКУЩЕГО ЧАТА
@bot.message_handler(commands=['setrate'])
def setrate_cmd(message):
    if not is_global_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    
    try:
        rate = float(message.text.split()[1])
        data = load_chat_data(chat_id)
        data['rate'] = rate
        save_chat_data(chat_id, data)
        
        chat_type = "группы" if chat_id < 0 else "чата"
        chat_name = message.chat.title if chat_id < 0 else "чата"
        
        bot.reply_to(message, f"✅ Курс для {chat_name} установлен: 1 USDT = {rate} RUB")
    except:
        bot.reply_to(message, "❌ Используйте: /setrate 92.5")

# /setpercent - УСТАНОВИТЬ ПРОЦЕНТ ДЛЯ ТЕКУЩЕГО ЧАТА
@bot.message_handler(commands=['setpercent'])
def setpercent_cmd(message):
    if not is_global_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    
    try:
        percent = float(message.text.split()[1])
        data = load_chat_data(chat_id)
        data['percent'] = percent
        save_chat_data(chat_id, data)
        
        chat_type = "группы" if chat_id < 0 else "чата"
        chat_name = message.chat.title if chat_id < 0 else "чата"
        
        bot.reply_to(message, f"✅ Процент комиссии для {chat_name} установлен: {percent}%")
    except:
        bot.reply_to(message, "❌ Используйте: /setpercent 2.5")

# /allchats - ВСЕ ЧАТЫ (ТОЛЬКО ГЛАВНЫЙ АДМИН)
@bot.message_handler(commands=['allchats'])
def allchats_cmd(message):
    if message.from_user.id != MAIN_ADMIN:
        bot.reply_to(message, "❌ Только главный администратор может просматривать все чаты")
        return
    
    chats = get_all_chats()
    
    if not chats:
        bot.reply_to(message, "📭 Нет активных чатов")
        return
    
    total_balance = sum(chat['balance'] for chat in chats)
    total_chats = len(chats)
    
    response = f"""🌐 *ВСЕ АКТИВНЫЕ ЧАТЫ*

*Общая статистика:*
👥 Чатов всего: {total_chats}
💰 Общий баланс: {total_balance:.2f} USDT

*Список чатов:*\n"""
    
    for chat in chats:
        chat_type = "👥 Группа" if chat['chat_id'] < 0 else "👤 Личный"
        response += f"\n{chat_type} *{chat['title']}*\n"
        response += f"💰 Баланс: {chat['balance']:.2f} USDT\n"
        response += f"⏰ Активность: {chat['last_activity']}\n"
    
    bot.reply_to(message, response, parse_mode='Markdown')

# /addadmin - ДОБАВИТЬ ГЛОБАЛЬНОГО АДМИНА
@bot.message_handler(commands=['addadmin'])
def addadmin_cmd(message):
    if message.from_user.id != MAIN_ADMIN:
        bot.reply_to(message, "❌ Только главный администратор может добавлять админов")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "❌ Используйте: /addadmin 123456789")
            return
        
        new_admin_id = int(args[1])
        admins = load_global_admins()
        
        if new_admin_id in admins:
            bot.reply_to(message, "❌ Этот пользователь уже администратор")
            return
        
        admins.append(new_admin_id)
        if save_global_admins(admins):
            bot.reply_to(message, f"✅ Пользователь {new_admin_id} добавлен как глобальный администратор")
            
            # Уведомляем нового админа
            try:
                bot.send_message(
                    new_admin_id,
                    f"👋 Вас добавили как глобального администратора бота-бухгалтера\n\n"
                    f"Теперь вы можете управлять ботом в любых чатах!\n\n"
                    f"Доступные команды:\n"
                    f"+5000 - добавить сумму (в текущем чате)\n"
                    f"выплата 1000 - выплатить (из текущего чата)\n"
                    f"/balance - баланс текущего чата\n"
                    f"/stats - статистика текущего чата"
                )
            except:
                pass
        else:
            bot.reply_to(message, "❌ Ошибка сохранения списка админов")
            
    except ValueError:
        bot.reply_to(message, "❌ Неверный ID пользователя")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# /admins - СПИСОК ГЛОБАЛЬНЫХ АДМИНОВ
@bot.message_handler(commands=['admins'])
def admins_cmd(message):
    if message.from_user.id != MAIN_ADMIN:
        return
    
    admins = load_global_admins()
    if not admins:
        bot.reply_to(message, "📭 Нет администраторов")
        return
    
    admins_list = "\n".join([f"👤 {admin_id}" for admin_id in admins])
    bot.reply_to(message, f"👥 *Список глобальных администраторов:*\n{admins_list}", parse_mode='Markdown')

# /chatid - ПОКАЗАТЬ ID ЧАТА
@bot.message_handler(commands=['chatid'])
def chatid_cmd(message):
    chat_id = message.chat.id
    is_group = chat_id < 0
    chat_type = "Группа" if is_group else "Личный чат"
    chat_name = message.chat.title if is_group else "Ваш"
    
    bot.reply_to(message, f"""💬 *ИНФОРМАЦИЯ О ЧАТЕ*

*Тип:* {chat_type}
*Название:* {chat_name}
*ID чата:* `{chat_id}`

*Путь к данным:* `chat_{chat_id}.json`""", parse_mode='Markdown')

# /help - ПОМОЩЬ
@bot.message_handler(commands=['help'])
def help_cmd(message):
    if not is_global_admin(message.from_user.id):
        return
    
    help_text = """📋 *СПИСОК КОМАНД*

*ДЛЯ ТЕКУЩЕГО ЧАТА:*
➕ `+5000` - добавить 5000₽ в этот чат
💰 `выплата 1000` - выплатить из этого чата
📊 `/balance` - баланс этого чата
📈 `/stats` - статистика этого чата
🔢 `/setrate 92.5` - курс для этого чата
📌 `/setpercent 2.5` - процент для этого чата
💬 `/chatid` - ID этого чата

*ГЛОБАЛЬНЫЕ КОМАНДЫ:*
👑 `/addadmin 123456789` - добавить глобального админа
👥 `/admins` - список глобальных админов
🌐 `/allchats` - все чаты (только главный)
🆘 `/help` - помощь"""
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

# Запуск бота
print("=" * 50)
print("🚀 БОТ БУХГАЛТЕРА С МУЛЬТИЧАТОМ ЗАПУСКАЕТСЯ")
print(f"👑 Главный админ: {MAIN_ADMIN}")
print(f"📁 База данных: {BASE_PATH}")
print("=" * 50)

bot.infinity_polling(timeout=60, long_polling_timeout=5)
