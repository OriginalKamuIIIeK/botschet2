import json
import os
import telebot
import telebot.apihelper
from datetime import datetime
import re
import threading
import time
from flask import Flask

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
PORT = 10000

# ========== НАСТРОЙКИ ==========
TOKEN = "8114014716:AAFwW5y7O3goMXWtZm6scpxEj-5VloP37ro"
MAIN_ADMIN = 7656583864
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот бухгалтера работает (полная версия)!"

@app.route('/health')
def health():
    return "OK", 200

def run_web_server():
    app.run(host='0.0.0.0', port=PORT, debug=False)

print(f"🚀 Запускаю веб-сервер на порту {PORT}...")
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()
time.sleep(2)

# ========== СИСТЕМА ХРАНЕНИЯ ==========
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Файлы
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "global_settings.json")

# ========== РАБОТА С ДАННЫМИ ==========

def get_chat_file(chat_id):
    """Получаем путь к файлу данных чата"""
    if chat_id < 0:  # Группа
        return os.path.join(DATA_DIR, f"group_{abs(chat_id)}.json")
    else:  # Личный чат
        return os.path.join(DATA_DIR, f"chat_{chat_id}.json")

def load_chat_data(chat_id, chat_title=""):
    """Загружаем или создаем данные чата"""
    chat_file = get_chat_file(chat_id)
    
    try:
        if os.path.exists(chat_file):
            with open(chat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key in ['balance', 'total_earned', 'total_paid', 'rate', 'percent']:
                    if key in data:
                        data[key] = float(data[key])
                return data
    except Exception as e:
        print(f"Ошибка загрузки данных чата {chat_id}: {e}")
    
    # Создаем новые данные
    if chat_id < 0:  # Группа
        title = chat_title if chat_title else f"Группа {abs(chat_id)}"
        chat_type = "group"
    else:  # Личный чат
        title = "Личный чат"
        chat_type = "chat"
    
    default_data = {
        "chat_id": chat_id,
        "chat_type": chat_type,
        "chat_title": title,
        "balance": 0.0,
        "total_earned": 0.0,
        "total_paid": 0.0,
        "rate": 92.5,
        "percent": 2.5,
        "transactions": [],
        "payments": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    save_chat_data(chat_id, default_data)
    return default_data

def save_chat_data(chat_id, data):
    """Сохраняем данные чата"""
    chat_file = get_chat_file(chat_id)
    data["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Ошибка сохранения данных чата {chat_id}: {e}")
        return False

# ========== АДМИН-СИСТЕМА ==========

def load_admins():
    """Загружаем список глобальных админов"""
    try:
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r') as f:
                admins = json.load(f)
                if MAIN_ADMIN not in admins:
                    admins.append(MAIN_ADMIN)
                    save_admins(admins)
                return admins
    except:
        pass
    
    admins = [MAIN_ADMIN]
    save_admins(admins)
    return admins

def save_admins(admins):
    """Сохраняем список админов"""
    try:
        with open(ADMINS_FILE, 'w') as f:
            json.dump(admins, f)
        return True
    except:
        return False

def is_admin(user_id):
    """Проверяем админа"""
    admins = load_admins()
    return user_id in admins

def is_main_admin(user_id):
    """Проверяем главного админа"""
    return user_id == MAIN_ADMIN

# ========== КОМАНДЫ ==========

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет доступа к боту")
        return
    
    chat_id = message.chat.id
    chat_title = message.chat.title if message.chat.title else ""
    
    data = load_chat_data(chat_id, chat_title)
    
    is_group = chat_id < 0
    chat_type = "👥 ГРУППА" if is_group else "👤 ЛИЧНЫЙ ЧАТ"
    chat_name = chat_title if is_group else "Ваш"
    
    help_text = f"""✅ *БОТ БУХГАЛТЕРА ЗАПУЩЕН*

{chat_type}: *{chat_name}*
💰 *Баланс чата:* {data['balance']:.2f} USDT
🔢 *Курс:* {data['rate']} | *%:* {data['percent']}

*ОСНОВНЫЕ КОМАНДЫ:*
➕ `+5000` - добавить 5000₽ в этот чат
💰 `выплата 1000` - выплатить из этого чата
📊 `/balance` - баланс этого чата
📈 `/stats` - статистика этого чата
🔢 `/setrate 92.5` - курс для этого чата
📌 `/setpercent 2.5` - процент для этого чата
💬 `/chatid` - ID этого чата

*ГЛОБАЛЬНЫЕ КОМАНДЫ:*
🌐 `/allchats` - все чаты (только главный)
👑 `/addadmin 123456789` - добавить админа
👥 `/admins` - список админов
🆘 `/help` - помощь
🧪 `/test` - тест работы
"""
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['test'])
def test_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    chat_title = message.chat.title if message.chat.title else "Личный чат"
    
    bot.reply_to(message, 
        f"✅ *ТЕСТ ПРОЙДЕН*\n"
        f"👤 Ваш ID: `{message.from_user.id}`\n"
        f"💬 ID чата: `{chat_id}`\n"
        f"📛 Название: {chat_title}\n"
        f"📡 Бот работает: ДА",
        parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('+'))
def add_money(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id, message.chat.title)
    
    try:
        amount_text = message.text[1:].strip().replace(',', '.').replace(' ', '')
        if not amount_text:
            bot.reply_to(message, "❌ Укажите сумму: +5000")
            return
        
        amount = float(amount_text)
        
        if data['rate'] <= 0:
            bot.reply_to(message, "❌ Курс не установлен. Используйте /setrate 92.5")
            return
        
        usdt = amount / data['rate']
        fee = usdt * (data['percent'] / 100)
        net = usdt - fee
        
        data['balance'] += net
        data['total_earned'] += net
        
        transaction = {
            'id': len(data['transactions']) + 1,
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
        
        chat_type = "группы" if chat_id < 0 else "чата"
        chat_name = message.chat.title if chat_id < 0 else "личного чата"
        
        response = f"""✅ *+{amount:,.2f} RUB в {chat_name}*
📊 *Курс чата:* {data['rate']} | *% чата:* {data['percent']}
💵 *В USDT:* {usdt:.2f}
📉 *Комиссия:* {fee:.2f}
💰 *Чистыми:* {net:.2f}
📈 *Баланс {chat_type}:* {data['balance']:.2f} USDT
⏰ *Время:* {transaction['time']}"""
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат. Пример: +5000 или +1250.50")
    except ZeroDivisionError:
        bot.reply_to(message, "❌ Курс не может быть 0. Используйте /setrate 92.5")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(func=lambda m: m.text and ('выплата' in m.text.lower() or 'pay' in m.text.lower()))
def payment(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id, message.chat.title)
    
    try:
        text = message.text.lower()
        numbers = re.findall(r'\d+[.,]?\d*', text)
        
        if not numbers:
            bot.reply_to(message, "❌ Укажите сумму: выплата 500")
            return
        
        amount = float(numbers[0].replace(',', '.'))
        
        if amount > data['balance']:
            bot.reply_to(message, f"❌ Недостаточно средств в этом чате. Доступно: {data['balance']:.2f} USDT")
            return
        
        payment_data = {
            'id': len(data['payments']) + 1,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'operator': message.from_user.id,
            'amount': amount,
            'balance_before': data['balance']
        }
        
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
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id, message.chat.title)
    
    chat_type = "группы" if chat_id < 0 else "чата"
    chat_name = message.chat.title if chat_id < 0 else "Личный чат"
    
    response = f"""💰 *БАЛАНС {chat_name.upper()}*
📊 *Текущий баланс:* {data['balance']:.2f} USDT
📈 *Всего начислено:* {data['total_earned']:.2f} USDT
📉 *Всего выплачено:* {data['total_paid']:.2f} USDT
🔢 *Курс {chat_type}:* {data['rate']} RUB/USDT
📌 *Процент {chat_type}:* {data['percent']}%"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id, message.chat.title)
    
    # Статистика за сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    today_tx = [t for t in data['transactions'] if t.get('time', '').startswith(today)]
    today_payments = [p for p in data['payments'] if p.get('time', '').startswith(today)]
    
    # Вычисляем общую сумму пополнений в рублях
    total_rub = sum(t.get('amount_rub', 0) for t in data['transactions'])
    total_usdt = data['total_earned']
    
    # Вычисляем сегодняшние суммы
    today_rub = sum(t.get('amount_rub', 0) for t in today_tx)
    today_usdt = sum(t.get('net', 0) for t in today_tx)
    today_payments_usdt = sum(p.get('amount', 0) for p in today_payments)
    
    chat_type = "группы" if chat_id < 0 else "чата"
    chat_name = message.chat.title if chat_id < 0 else "Личный чат"
    
    response = f"""📊 *СТАТИСТИКА {chat_name.upper()}*

*За сегодня ({today}):*
📥 Пополнений: {len(today_tx)}
💰 Сумма в рублях: {today_rub:,.2f} ₽
💵 Сумма в USDT: {today_usdt:.2f} USDT
📤 Выплат: {len(today_payments)}
💸 Сумма выплат: {today_payments_usdt:.2f} USDT

*Общая статистика {chat_type}:*
📥 Всего пополнений: {len(data['transactions'])}
💰 Общая сумма пополнений: {total_rub:,.2f} ₽
💵 В USDT: {total_usdt:.2f} USDT
📤 Всего выплат: {len(data['payments'])}
💸 Сумма выплат: {data['total_paid']:.2f} USDT
📈 Текущий баланс: {data['balance']:.2f} USDT
🔢 Курс: {data['rate']} ₽/USDT
📌 Процент: {data['percent']}%"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['transactions'])
def transactions_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    data = load_chat_data(chat_id, message.chat.title)
    
    if not data['transactions']:
        bot.reply_to(message, "📭 Нет записей о пополнениях")
        return
    
    # Показываем последние 10 транзакций
    recent_tx = data['transactions'][-10:]
    
    chat_name = message.chat.title if chat_id < 0 else "Личный чат"
    response = f"""📋 *ПОСЛЕДНИЕ ПОПОЛНЕНИЯ {chat_name.upper()}*
Всего записей: {len(data['transactions'])}
Показано последних: {len(recent_tx)}
"""
    
    total_rub = 0
    total_usdt = 0
    
    for tx in recent_tx:
        rub = tx.get('amount_rub', 0)
        usdt = tx.get('net', 0)
        total_rub += rub
        total_usdt += usdt
        
        response += f"\n📅 {tx.get('time', '')}"
        response += f"\n➕ {rub:,.2f} ₽ → {usdt:.2f} USDT"
        response += f"\nКомиссия: {tx.get('fee', 0):.2f} USDT"
        response += f"\nБаланс после: {tx.get('balance_after', 0):.2f} USDT\n"
    
    response += f"\n📊 Итого за показанный период:"
    response += f"\n💰 {total_rub:,.2f} ₽"
    response += f"\n💵 {total_usdt:.2f} USDT"
    
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            bot.send_message(chat_id, part, parse_mode='Markdown')
    else:
        bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['setrate'])
def setrate_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    
    try:
        rate = float(message.text.split()[1])
        data = load_chat_data(chat_id, message.chat.title)
        data['rate'] = rate
        save_chat_data(chat_id, data)
        
        chat_name = message.chat.title if chat_id < 0 else "чата"
        bot.reply_to(message, f"✅ Курс для {chat_name} установлен: 1 USDT = {rate} RUB")
    except:
        bot.reply_to(message, "❌ Используйте: /setrate 92.5")

@bot.message_handler(commands=['setpercent'])
def setpercent_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    chat_id = message.chat.id
    
    try:
        percent = float(message.text.split()[1])
        data = load_chat_data(chat_id, message.chat.title)
        data['percent'] = percent
        save_chat_data(chat_id, data)
        
        chat_name = message.chat.title if chat_id < 0 else "чата"
        bot.reply_to(message, f"✅ Процент комиссии для {chat_name} установлен: {percent}%")
    except:
        bot.reply_to(message, "❌ Используйте: /setpercent 2.5")

@bot.message_handler(commands=['chatid'])
def chatid_cmd(message):
    chat_id = message.chat.id
    is_group = chat_id < 0
    chat_type = "Группа" if is_group else "Личный чат"
    chat_name = message.chat.title if is_group else "Ваш"
    
    bot.reply_to(message, 
        f"💬 *ИНФОРМАЦИЯ О ЧАТЕ*\n\n"
        f"*Тип:* {chat_type}\n"
        f"*Название:* {chat_name}\n"
        f"*ID чата:* `{chat_id}`\n\n"
        f"📁 *Файл данных:* `chat_{chat_id}.json`",
        parse_mode='Markdown')

@bot.message_handler(commands=['allchats'])
def allchats_cmd(message):
    if not is_main_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только главный администратор может просматривать все чаты")
        return
    
    try:
        chat_files = [f for f in os.listdir(DATA_DIR) if f.startswith('chat_') or f.startswith('group_')]
        chats = []
        
        for file in chat_files:
            try:
                if file.startswith('chat_'):
                    chat_id = int(file[5:-5])
                else:
                    chat_id = -int(file[6:-5])
                    
                data = load_chat_data(chat_id)
                last_tx = data['transactions'][-1] if data['transactions'] else None
                
                # Вычисляем общую сумму в рублях для этого чата
                total_rub = sum(t.get('amount_rub', 0) for t in data['transactions'])
                
                chats.append({
                    'id': chat_id,
                    'title': data['chat_title'],
                    'type': '👥 Группа' if chat_id < 0 else '👤 Личный',
                    'balance': data['balance'],
                    'total_rub': total_rub,
                    'rate': data['rate'],
                    'percent': data['percent'],
                    'last_active': data['last_active'],
                    'last_tx': last_tx['time'] if last_tx else 'Нет операций'
                })
            except:
                continue
        
        if not chats:
            bot.reply_to(message, "📭 Нет активных чатов")
            return
        
        chats.sort(key=lambda x: x['last_active'], reverse=True)
        
        total_balance = sum(c['balance'] for c in chats)
        total_rub_all = sum(c['total_rub'] for c in chats)
        response = f"""🌐 *ВСЕ АКТИВНЫЕ ЧАТЫ*

*Общая статистика:*
👥 Всего чатов: {len(chats)}
💰 Общий баланс: {total_balance:.2f} USDT
💵 Общая сумма пополнений: {total_rub_all:,.2f} ₽

*Список чатов:*\n"""
        
        for chat in chats[:10]:
            response += f"\n{chat['type']} *{chat['title']}*\n"
            response += f"💰 Баланс: {chat['balance']:.2f} USDT\n"
            response += f"💵 Пополнения: {chat['total_rub']:,.2f} ₽\n"
            response += f"🔢 Курс: {chat['rate']} | %: {chat['percent']}\n"
            response += f"🕐 Активность: {chat['last_active']}\n"
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['addadmin'])
def addadmin_cmd(message):
    if not is_main_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только главный администратор может добавлять админов")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "❌ Используйте: /addadmin 123456789")
            return
        
        new_admin_id = int(args[1])
        admins = load_admins()
        
        if new_admin_id in admins:
            bot.reply_to(message, "❌ Этот пользователь уже администратор")
            return
        
        admins.append(new_admin_id)
        save_admins(admins)
        
        bot.reply_to(message, f"✅ Пользователь {new_admin_id} добавлен как администратор")
        
        try:
            bot.send_message(
                new_admin_id,
                f"👋 Вас добавили как администратора бота-бухгалтера!\n\n"
                f"Теперь вы можете:\n"
                f"• Управлять ботом в любых чатах\n"
                f"• Добавлять деньги: +5000\n"
                f"• Выплачивать: выплата 1000\n"
                f"• Просматривать баланс: /balance\n\n"
                f"Добавьте бота в группу и напишите /start"
            )
        except:
            pass
            
    except ValueError:
        bot.reply_to(message, "❌ Неверный ID пользователя")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['admins'])
def admins_cmd(message):
    if not is_main_admin(message.from_user.id):
        return
    
    admins = load_admins()
    
    response = "👥 *Список администраторов:*\n\n"
    for admin_id in admins:
        response += f"• `{admin_id}`"
        if admin_id == MAIN_ADMIN:
            response += " 👑 (главный)"
        response += "\n"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    help_text = """📋 *СПИСОК КОМАНД*

*ДЛЯ ТЕКУЩЕГО ЧАТА:*
➕ `+5000` - добавить 5000₽ в этот чат
💰 `выплата 1000` - выплатить из этого чата
📊 `/balance` - баланс этого чата
📈 `/stats` - статистика этого чата (с рублями)
📋 `/transactions` - последние пополнения
🔢 `/setrate 92.5` - курс для этого чата
📌 `/setpercent 2.5` - процент для этого чата
💬 `/chatid` - ID этого чата

*ГЛОБАЛЬНЫЕ КОМАНДЫ:*
👑 `/addadmin 123456789` - добавить админа (только главный)
👥 `/admins` - список админов (только главный)
🌐 `/allchats` - все чаты (только главный)
🧪 `/test` - тест работы бота
🆘 `/help` - помощь"""
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ========== ЗАПУСК ==========
print("=" * 50)
print("🚀 БОТ БУХГАЛТЕРА ЗАПУЩЕН (ПОЛНАЯ ВЕРСИЯ)")
print(f"👑 Главный админ: {MAIN_ADMIN}")
print(f"📁 Директория данных: {DATA_DIR}")
print(f"🌐 Веб-сервер: http://0.0.0.0:{PORT}")
print("=" * 50)

try:
    bot.infinity_polling(timeout=60, long_polling_timeout=5)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    print("🔄 Перезапуск через 10 секунд...")
    time.sleep(10)
