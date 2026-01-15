import json
import os
import telebot
import telebot.apihelper
from datetime import datetime
import re

# ТВОИ ДАННЫЕ
TOKEN = "8274329230:AAE6NGyu5_R_RuiYvn6GB8HFAqMcbqTpvrw"
MAIN_ADMIN = 7620190298  # Твой ID (главный админ)

# Очистка вебхуков перед запуском
def clear_webhook(token):
    try:
        telebot.apihelper.API_URL = f"https://api.telegram.org/bot{token}/"
        telebot.apihelper._make_request(token, "deleteWebhook", {})
        print("✅ Вебхуки очищены")
    except:
        print("⚠️ Ошибка очистки вебхуков")

clear_webhook(TOKEN)

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Файлы для хранения
DATA_FILE = "data.json"
ADMINS_FILE = "admins.json"

# Загрузка данных
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем старые значения
                data['balance'] = float(data.get('balance', 0))
                data['total_earned'] = float(data.get('total_earned', 0))
                data['total_paid'] = float(data.get('total_paid', 0))
                data['rate'] = float(data.get('rate', 92.5))
                data['percent'] = float(data.get('percent', 2.5))
                return data
    except:
        pass
    return {
        "balance": 0.0,
        "total_earned": 0.0,
        "total_paid": 0.0,
        "rate": 92.5,
        "percent": 2.5,
        "transactions": [],
        "payments": []
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Загрузка админов
def load_admins():
    try:
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r') as f:
                admins = json.load(f)
                # Добавляем главного админа если его нет
                if MAIN_ADMIN not in admins:
                    admins.append(MAIN_ADMIN)
                    save_admins(admins)
                return admins
    except:
        pass
    return [MAIN_ADMIN]

def save_admins(admins):
    with open(ADMINS_FILE, 'w') as f:
        json.dump(admins, f)

# Проверка админа
def is_admin(user_id):
    admins = load_admins()
    return user_id in admins

# ================= КОМАНДЫ =================

# /start
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if is_admin(message.from_user.id):
        help_text = """✅ *БОТ БУХГАЛТЕРА ЗАПУЩЕН*

*ОСНОВНЫЕ КОМАНДЫ:*
➕ `+5000` - добавить 5000
💰 `выплата 1000` - выплатить 1000 USDT
📊 `/balance` - баланс
📈 `/stats` - статистика
🕐 `/last` - последняя операция

*НАСТРОЙКИ:*
🔢 `/setrate 0` - установить курс
📌 `/setpercent 0` - установить процент

*АДМИНИСТРАЦИЯ:*
👑 `/addadmin 123456789` - добавить админа
👥 `/admins` - список админов
        """
        bot.reply_to(message, help_text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ У вас нет доступа к боту")

# +5000
@bot.message_handler(func=lambda m: m.text and m.text.startswith('+'))
def add_money(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        amount = float(message.text[1:].strip().replace(',', '.'))
        data = load_data()
        
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
        
        if 'transactions' not in data:
            data['transactions'] = []
        data['transactions'].append(transaction)
        
        save_data(data)
        
        response = f"""✅ *+{amount:,.2f} *
📊 *Курс:* {data['rate']} | *%:* {data['percent']}
💵 *В USDT:* {usdt:.2f}
📉 *Комиссия:* {fee:.2f}
📈 *Баланс:* {data['balance']:.2f} USDT
⏰ *Время:* {transaction['time']}"""
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# выплата 1000
@bot.message_handler(func=lambda m: m.text and ('выплата' in m.text.lower() or 'pay' in m.text.lower()))
def payment(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Ищем число в сообщении
        text = message.text.lower()
        numbers = re.findall(r'\d+\.?\d*', text)
        
        if not numbers:
            bot.reply_to(message, "❌ Укажите сумму: выплата 500")
            return
        
        amount = float(numbers[0].replace(',', '.'))
        data = load_data()
        
        if amount > data['balance']:
            bot.reply_to(message, f"❌ Недостаточно средств. Доступно: {data['balance']:.2f} USDT")
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
        
        if 'payments' not in data:
            data['payments'] = []
        data['payments'].append(payment_data)
        
        save_data(data)
        
        response = f"""💸 *Выплата: {amount:.2f} USDT*
📊 *Было:* {payment_data['balance_before']:.2f} USDT
📉 *Стало:* {data['balance']:.2f} USDT
💰 *Выплачено всего:* {data['total_paid']:.2f} USDT
📌 *Осталось выплатить:* {data['balance']:.2f} USDT
⏰ *Время:* {payment_data['time']}"""
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# /balance
@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    data = load_data()
    response = f"""💰 *Текущий баланс:* {data['balance']:.2f} USDT
📈 *Всего начислено:* {data['total_earned']:.2f} USDT
📉 *Всего выплачено:* {data['total_paid']:.2f} USDT
🔢 *Курс:* {data['rate']} = 1 USDT
📌 *Процент:* {data['percent']}%"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

# /stats
@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    data = load_data()
    transactions = data.get('transactions', [])
    payments = data.get('payments', [])
    
    # Статистика за сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    today_tx = [t for t in transactions if t.get('time', '').startswith(today)]
    today_payments = [p for p in payments if p.get('time', '').startswith(today)]
    
    response = f"""📊 *СТАТИСТИКА*

*За сегодня ({today}):*
📥 Пополнений: {len(today_tx)}
💰 Сумма: {sum(t.get('net', 0) for t in today_tx):.2f} USDT
📤 Выплат: {len(today_payments)}
💸 Сумма выплат: {sum(p.get('amount', 0) for p in today_payments):.2f} USDT

*Общая статистика:*
📥 Всего пополнений: {len(transactions)}
📤 Всего выплат: {len(payments)}
💰 Баланс: {data['balance']:.2f} USDT"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

# /last
@bot.message_handler(commands=['last'])
def last_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    data = load_data()
    transactions = data.get('transactions', [])
    
    if not transactions:
        bot.reply_to(message, "📭 Нет операций")
        return
    
    last = transactions[-1]
    
    response = f"""📋 *ПОСЛЕДНЯЯ ОПЕРАЦИЯ*
➕ *Сумма:* {last.get('amount_rub', 0):,.2f} RUB
💵 *В USDT:* {last.get('amount_usdt', 0):.2f}
📉 *Комиссия:* {last.get('fee', 0):.2f}
📈 *Баланс после:* {last.get('balance_after', 0):.2f} USDT
⏰ *Время:* {last.get('time', 'Неизвестно')}"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

# /setrate
@bot.message_handler(commands=['setrate'])
def setrate_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        rate = float(message.text.split()[1])
        data = load_data()
        data['rate'] = rate
        save_data(data)
        bot.reply_to(message, f"✅ Курс установлен: 1 USDT = {rate}")
    except:
        bot.reply_to(message, "❌ Используйте: /setrate 92.5")

# /setpercent
@bot.message_handler(commands=['setpercent'])
def setpercent_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        percent = float(message.text.split()[1])
        data = load_data()
        data['percent'] = percent
        save_data(data)
        bot.reply_to(message, f"✅ Процент комиссии установлен: {percent}%")
    except:
        bot.reply_to(message, "❌ Используйте: /setpercent 2.5")

# /addadmin - ТОЛЬКО ДЛЯ ГЛАВНОГО АДМИНА
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
        admins = load_admins()
        
        if new_admin_id in admins:
            bot.reply_to(message, "❌ Этот пользователь уже администратор")
            return
        
        admins.append(new_admin_id)
        save_admins(admins)
        
        bot.reply_to(message, f"✅ Пользователь {new_admin_id} добавлен как администратор")
        
        # Уведомляем нового админа
        try:
            bot.send_message(
                new_admin_id,
                f"👋 Вас добавили как администратора бота-бухгалтера\n\n"
                f"Доступные команды:\n"
                f"+5000 - добавить сумму\n"
                f"выплата 1000 - сделать выплату\n"
                f"/balance - показать баланс\n"
                f"/stats - статистика"
            )
        except:
            pass
            
    except ValueError:
        bot.reply_to(message, "❌ Неверный ID пользователя")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# /admins - ТОЛЬКО ДЛЯ ГЛАВНОГО АДМИНА
@bot.message_handler(commands=['admins'])
def admins_cmd(message):
    if message.from_user.id != MAIN_ADMIN:
        return
    
    admins = load_admins()
    if not admins:
        bot.reply_to(message, "📭 Нет администраторов")
        return
    
    admins_list = "\n".join([f"👤 {admin_id}" for admin_id in admins])
    bot.reply_to(message, f"👥 *Список администраторов:*\n{admins_list}", parse_mode='Markdown')

# /help
@bot.message_handler(commands=['help'])
def help_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    help_text = """📋 *СПИСОК КОМАНД*

*ОПЕРАЦИИ:*
➕ `+5000` - добавить 5000₽
💰 `выплата 1000` - выплатить 1000 USDT

*ИНФОРМАЦИЯ:*
📊 `/balance` - баланс
📈 `/stats` - статистика
🕐 `/last` - последняя операция

*НАСТРОЙКИ:*
🔢 `/setrate 92.5` - установить курс
📌 `/setpercent 2.5` - установить процент

*АДМИНИСТРАЦИЯ:*
👑 `/addadmin 123456789` - добавить админа (только главный)
👥 `/admins` - список админов (только главный)
🆘 `/help` - помощь"""
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

# Запуск бота
print("=" * 50)
print("🚀 БОТ БУХГАЛТЕРА ЗАПУСКАЕТСЯ")
print(f"👑 Главный админ: {MAIN_ADMIN}")
print(f"💾 Файл данных: {DATA_FILE}")
print(f"👥 Файл админов: {ADMINS_FILE}")
print("=" * 50)

bot.infinity_polling(timeout=60, long_polling_timeout=5)
