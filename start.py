from config import *
import sqlite3
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string
import time
import threading
import psutil
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
import asyncio
from aiogram import executor
import aiosqlite
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
import asyncio 
import math
import requests
import aiohttp
import threading
import asyncio
import os
from termcolor import colored
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.functions.account import ReportPeerRequest
import random
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import SessionPasswordNeededError
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError, FloodWaitError
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.types import Channel, Chat, InputPeerChannel, InputPeerChat
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonOther, InputReportReasonSpam, Channel, Chat




def create_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timeout DATETIME,
            white_list TEXT,
            username TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api (
            api_id TEXT,
            api_hash TEXT,
            session TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            days_subscription INTEGER NOT NULL,
            max_activations INTEGER NOT NULL,
            activations_count INTEGER DEFAULT 0,
            used_by TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            expiration_date DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT,
            session TEXT,
            status TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

create_database()

# миграция: добавить username если нет
try:
    _conn = sqlite3.connect('database.db')
    _cur = _conn.cursor()
    _cur.execute("PRAGMA table_info(users)")
    _cols = [c[1] for c in _cur.fetchall()]
    if "username" not in _cols:
        _cur.execute("ALTER TABLE users ADD COLUMN username TEXT")
        _conn.commit()
    _conn.close()
except Exception as _e:
    print(f"[migration] {_e}")



# ....... хз



bot = Bot(token=api_token)
logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()

dp = Dispatcher(bot, storage=storage)





async def check_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()
        if existing_user:
            return True
        else:
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()
            try:
                await bot.send_message(
                    log_chat_id,
                    f'<b>👤 Зарегистрирован новый <a href="tg://user?id={user_id}">пользователь</a></b>\nID: <code>{user_id}</code>',
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Log error: {e}")
            return False
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
        return False
    finally:
        conn.close()

async def check_subcribe_status(id):
	try:
		chat = await bot.get_chat(id)
		name = chat.full_name
		username = chat.username
	except Exception:
		name = "Пользователь"
		username = None
	username_str = f"/ @{username}" if username else ""
	if int(id) in admin:
		status = (
			f"<b>📱 Ваш профиль\n\n"
			f"🗣 Имя: {name}\n"
			f"🗄 Данные: id {id} {username_str}\n"
			f"♾ Запросов: Бесконечно\n"
			f"👑 Статус: Админ\n\n"
			f"🛠 by @vkwed"
		)
		return status
	conn = sqlite3.connect('database.db')
	cursor = conn.cursor()
	cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (id,))
	subscription = cursor.fetchone()
	conn.close()
	if subscription:
		try:
			date = datetime.strptime(subscription[0], '%Y-%m-%d %H:%M:%S.%f')
			if datetime.now() <= date:
				sub_text = f"До {date.strftime('%Y-%m-%d %H:%M')}"
			else:
				sub_text = "Истекла"
		except Exception:
			sub_text = "Истекла"
	else:
		sub_text = "Отсутствует"
	status = (
		f"<b>📱 Ваш профиль\n\n"
		f"🗣 Имя: {name}\n"
		f"🗄 Данные: id {id} {username_str}\n"
		f"💎 Подписка: {sub_text}\n"
		f"♾ Запросов: {sub_text if sub_text != 'Отсутствует' else '0'}\n\n"
		f"🛠 by @vkwed"
	)
	return status

async def subscribe_check(id):
	if int(id) in admin:
		return True
	conn = sqlite3.connect('database.db')
	cursor = conn.cursor()
	cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (id,))
	subscription = cursor.fetchone()
	conn.close()
	if subscription:
		try:
			date = datetime.strptime(subscription[0], '%Y-%m-%d %H:%M:%S.%f')
			if datetime.now() <= date:
				return True
		except Exception:
			pass
	return False

async def is_blacklisted(user_id):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM blacklist WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception:
        return False

async def save_history(target, session, status, reason=""):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (target, session, status, reason) VALUES (?, ?, ?, ?)",
            (target, session, status, reason)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"history save error: {e}")

@dp.message_handler(commands=['start'])

async def home(message: types.Message):

	if message.chat.type != types.ChatType.PRIVATE:

		return 

		

	markup = types.InlineKeyboardMarkup(row_width=2)

	markup.add(types.InlineKeyboardButton(f"💸 Купить", callback_data=f"buy"))

	markup.add(types.InlineKeyboardButton(f"👤 Профиль", callback_data=f"profile"))

	

	button = types.InlineKeyboardMarkup(row_width=2)

	

	profile = types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile")

	

	owner = types.InlineKeyboardButton(text="💎 Руководство", url="https://t.me/vkwed")

	

	channel = types.InlineKeyboardButton(text="🔍 Канал", url="https://t.me/Webkisska")

	

	botnet = types.InlineKeyboardButton(text="💼 Ботнет", callback_data="botnet")

	button.add(profile, owner, channel, botnet)

	await check_user(message.from_user.id)

	



	if await subscribe_check(message.from_user.id):

		with open('banner.jpg', 'rb') as banner1:

			await bot.send_photo(

            chat_id=message.from_user.id,

            photo=banner1,

            caption='<b>Приветствуем вас в WebKiss Snoser! 🪓</b>',            

            reply_markup=button,

            parse_mode='HTML'

        )

	else:

		with open('banner.jpg', 'rb') as banner2:

			await bot.send_photo(

            chat_id=message.from_user.id,

            photo=banner2,

            caption='<b>🥀 У вас отсутствует подписка! Приобретите её по кнопке ниже.</b>',            

            reply_markup=markup,

            parse_mode='HTML'

        )

		

		

@dp.callback_query_handler(lambda call: call.data == 'profile')

async def profile(call: types.CallbackQuery):

	text = await check_subcribe_status(call.from_user.id)

	check = await subscribe_check(call.from_user.id)

	markup = types.InlineKeyboardMarkup(row_width=1)

	if check:

		pass  # продлить убрано

		

	# promo убрано

		

	markup.add(types.InlineKeyboardButton(f"Меню", callback_data=f"back"))

	

	await bot.edit_message_caption(

            chat_id=call.message.chat.id,

            message_id=call.message.message_id,

            caption=text,

            reply_markup=markup,

            parse_mode="HTML"

        )

        

        

@dp.callback_query_handler(lambda call: call.data == 'buy')

async def buy(call: types.CallbackQuery):

    markup = types.InlineKeyboardMarkup()

    subscription_options = [

        ("💊 3 дня - 1$", "buy_3"),

        ("💊 7 дней - 2.5$", "buy_7"),

        ("💊 31 день - 5$", "buy_31"),

        ("💊 Навсегда - 10$", "lifetime"),

        ("Назад", "back")

    ]

    for option_text, callback_data in subscription_options:

        markup.add(types.InlineKeyboardButton(option_text, callback_data=callback_data))

    

    await bot.edit_message_caption(

        chat_id=call.message.chat.id,

        message_id=call.message.message_id,

        caption="<b>💎 Оплата через @send\n⌛️ Выберите срок подписки:</b>",

        reply_markup=markup,

        parse_mode="HTML"

    )

    

    

    

@dp.callback_query_handler(lambda call: call.data == 'back')

async def back_to_main(call: types.CallbackQuery, state: FSMContext):

    check = await subscribe_check(call.from_user.id)

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(types.InlineKeyboardButton(f"💸 Купить", callback_data=f"buy"))

    markup.add(types.InlineKeyboardButton(f"👤 Профиль", callback_data=f"profile"))

    

    button = types.InlineKeyboardMarkup(row_width=2)

    

    profile = types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile")

    owner = types.InlineKeyboardButton(text="💎 Руководство", url="https://t.me/LooseTag")

    channel = types.InlineKeyboardButton(text="🔍 Канал", url="https://t.me/+xkzgygu2lKViYjky")

    botnet = types.InlineKeyboardButton(text="💼 Ботнет", callback_data="botnet")

    button.add(profile, owner, channel, botnet)

    

    if check:

        await bot.edit_message_caption(

            chat_id=call.message.chat.id,

            message_id=call.message.message_id,

            caption=f"<b>Приветствуем вас в Psyhomania Snoser! 🪓</b>",

            reply_markup=button,

            parse_mode="HTML"

        )

    else:

        await bot.edit_message_caption(

            chat_id=call.message.chat.id,

            message_id=call.message.message_id,

            caption=f"<b>🥀 У вас отсутствует подписка! Приобретите её по кнопке ниже.</b>",

            reply_markup=markup,

            parse_mode="HTML"

        )

		

	

   



async def generate_payment_link(payment_system, amount):

    api_url = "https://pay.crypt.bot/api/createInvoice"

    headers = {"Crypto-Pay-API-Token": Crypto_Pay_API_Token}

    data = {

        "asset": payment_system,

        "amount": float(amount)

    }



    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code == 200:

        json_data = response.json()

        invoice = json_data.get("result")

        payment_link = invoice.get("pay_url")

        invoice_id = invoice.get("invoice_id")

        return payment_link, invoice_id

    else:

        return None, None



async def get_invoice_status(invoice_id):

    api_url = f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}"

    headers = {"Crypto-Pay-API-Token": Crypto_Pay_API_Token}



    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:

        json_data = response.json()

        if json_data.get("ok"):

            invoices = json_data.get("result")

            if invoices and 'items' in invoices and invoices['items']:

                status = invoices['items'][0]['status']

                payment_link = invoices['items'][0]['pay_url']

                amount = Decimal(invoices['items'][0]['amount'])

                value = invoices['items'][0]['asset']

                return status, payment_link, amount, value



    return None, None, None, None



async def get_exchange_rates():

    api_url = "https://pay.crypt.bot/api/getExchangeRates"

    headers = {"Crypto-Pay-API-Token": Crypto_Pay_API_Token}



    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:

        json_data = response.json()

        if json_data.get("ok"):

            return json_data["result"]

    return []



async def convert_to_crypto(amount, asset):

    rates = await get_exchange_rates()

    rate = None

    for exchange_rate in rates:

        if exchange_rate["source"] == asset and exchange_rate["target"] == 'USD':

            rate = Decimal(str(exchange_rate["rate"]))

            break



    if rate is None:

        raise Exception(f"<b>🎲 Не удалось найти курс обмена для {asset}</b>", parse_mode="HTML")



    amount = Decimal(str(amount))

    return amount / rate 

    

    

@dp.callback_query_handler(lambda call: call.data.startswith('buy_'))

async def subscription_duration_selected(call: types.CallbackQuery):

    duration = call.data

    markup = types.InlineKeyboardMarkup()

    currency_options = [

        ("💵 USDT", "currency_USDT_" + duration),

        ("💎 TON", "currency_TON_" + duration),

        ("💰 NOT", "currency_NOT_" + duration),

        ("🪙 BTC", "currency_BTC_" + duration),

        ("💶 ETH", "currency_ETH_" + duration),

        ("Назад", "buy")

    ]

    for option_text, callback_data in currency_options:

        markup.add(types.InlineKeyboardButton(option_text, callback_data=callback_data))

    

    await bot.edit_message_caption(

        chat_id=call.message.chat.id,

        message_id=call.message.message_id,

        caption="<b>💸  Выберите валюту для оплаты:</b>",

        reply_markup=markup,

        parse_mode="HTML"

    )

    

@dp.callback_query_handler(lambda call: call.data.startswith('currency_'))

async def currency_selected(call: types.CallbackQuery):

    parts = call.data.split('_')

    currency = parts[1]

    duration_parts = parts[2:]

    duration = "_".join(duration_parts)



    amount = get_amount_by_duration(duration.replace('buy_', ''))



    try:

        converted_amount = await convert_to_crypto(amount, currency)

        payment_link, invoice_id = await generate_payment_link(currency, converted_amount)

        if payment_link and invoice_id:

            markup = types.InlineKeyboardMarkup()

            oplata = types.InlineKeyboardButton("💰  Оплатить", url=f"{payment_link}")

            check_payment_button = types.InlineKeyboardButton("💸  Проверить оплату", callback_data=f"check_payment:{call.from_user.id}:{invoice_id}")

            markup.add(oplata, check_payment_button)

            

            await bot.edit_message_caption(

                chat_id=call.message.chat.id,

                message_id=call.message.message_id,

                caption=f"<b>💸  Счет для оплаты:</b>\n{payment_link}",

                reply_markup=markup,

                parse_mode="HTML"

            )

        else:

            await bot.edit_message_caption(

                chat_id=call.message.chat.id,

                message_id=call.message.message_id,

                caption="<b>❌  Не удалось создать счет для оплаты. Пожалуйста, попробуйте позже.</b>",

                parse_mode="HTML"

            )

    except Exception as e:

        await bot.edit_message_caption(

            chat_id=call.message.chat.id,

            message_id=call.message.message_id,

            caption=str(e)

        )



def get_amount_by_duration(duration):

    prices = {

        '3': 1,

        '7': 2.5,

        '31': 5,

        'lifetime': 10

    }

    return prices.get(duration, 0)

    

  

@dp.callback_query_handler(lambda call: call.data.startswith('check_payment:'))

async def check_payment(call: types.CallbackQuery):

    _, user_id_str, invoice_id_str = call.data.split(':')

    user_id = int(user_id_str)

    invoice_id = invoice_id_str

    

    if user_id == call.from_user.id:

        status, payment_link, amount, value = await get_invoice_status(invoice_id)

        

        if status == "paid":

            duration_days = get_duration_by_amount(amount)

            

            expiration_date = datetime.now() + timedelta(days=duration_days)

            await add_subscription(user_id, expiration_date)

            await bot.send_message(

                log_chat_id,

                f"<b>💸 Была <a href='tg:/openmessage?user_id={user_id}'>куплена</a> подписка\n==========</b>\n"

                f"<b>Покупатель: {user_id}</b>\n"

                f"<b>Количество дней: {duration_days}</b>\n"

                f"<b>Статус:</b> {status}\n"

                f"<b>Ссылка для оплаты:</b> {payment_link}\n"

                f"<b>Цена:</b> {amount} {value}",

                parse_mode="HTML"

            )

            await bot.edit_message_caption(

                chat_id=call.message.chat.id,

                message_id=call.message.message_id, 

                caption="<b>✅ Оплата подтверждена! Подписка активирована. Спасибо за покупку.</b>",

                parse_mode="HTML"

            )

            await home(call.message)

        else:

            await bot.answer_callback_query(call.id, "❌ Оплата не найдена. Попробуйте позже!")

    else:

        await bot.answer_callback_query(call.id, "❌ Вы не можете проверить эту оплату.", show_alert=True)



def get_duration_by_amount(amount):

    amount = round(amount, 2)

    if amount <= 1:

        return 3

    elif amount <= 2.5:

        return 7

    elif amount <= 5:

        return 31

    elif amount <= 10:

        return 365 * 99  

    else:

        return 0

        

        

class MyState(StatesGroup):

	link = State()

	promo = State()

 

 

        

        

@dp.callback_query_handler(lambda call: call.data == 'promo')

async def handle_inline_button_click2(call: types.CallbackQuery):   



	with open('banner.jpg', 'rb') as had:

		await bot.send_photo(call.message.chat.id, had, "<b>🎁 Введите промокод в чат:</b>", parse_mode="HTML")

	await MyState.promo.set()

	



def is_user_in_promocode(user_id, promo_code):

    with sqlite3.connect('database.db') as conn:

        cursor = conn.cursor()



        user_id_str = str(user_id)



        cursor.execute('''

            SELECT 1

            FROM promocodes

            WHERE code = ?

            AND (

                used_by = ? OR                  -- ID единственный в поле

                used_by LIKE ? OR               -- ID в начале

                used_by LIKE ? OR               -- ID в конце

                used_by LIKE ?                  -- ID в середине

            )

        ''', (

            promo_code,

            user_id_str,

            f'{user_id_str},%',

            f'%,{user_id_str}',

            f'%,{user_id_str},%'

        ))



        result = cursor.fetchone()

        return result is not None





















@dp.message_handler(state=MyState.promo)

async def soso(message: types.Message, state: FSMContext):

    try:

        with sqlite3.connect('database.db') as conn:

            cursor = conn.cursor()

            cursor.execute("SELECT * FROM promocodes WHERE code = ?", (message.text,))

            promocode = cursor.fetchone()

            

            cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id = ?", (message.from_user.id,))

            expiration_date = cursor.fetchone()



            if expiration_date and expiration_date[0]:

                

                expiration_date = datetime.strptime(expiration_date[0], '%Y-%m-%d %H:%M:%S.%f')

            else:

                expiration_date = datetime.now()



            if promocode is not None:

                already_used = is_user_in_promocode(message.from_user.id, message.text)



                if already_used:

                    await message.reply("<b>❌️ Вы уже использовали данный промокод.</b>", parse_mode="HTML")

                    await home(message)

                    await state.finish()

                    return

                elif promocode[4] >= promocode[3]:

                    await message.reply("<b>❌️ Данный промокод использовали макс. количество раз.</b>", parse_mode="HTML")

                    await home(message)

                    await state.finish()

                    return

                else:

                    

                    new_expiration_date = expiration_date + timedelta(days=promocode[2])

                    

                    new_expiration_date_str = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S.%f')



                    

                    cursor.execute("INSERT OR REPLACE INTO subscriptions (user_id, expiration_date) VALUES (?, ?)", (message.from_user.id, new_expiration_date_str))



                    cursor.execute('''

                        UPDATE promocodes 

                        SET used_by = 

                            CASE 

                                WHEN used_by IS NULL OR used_by = '' THEN ?

                                ELSE used_by || ',' || ? 

                            END,

                            activations_count = activations_count + 1

                        WHERE id = ?

                    ''', (str(message.from_user.id), str(message.from_user.id), promocode[0]))



                    conn.commit()



                    await message.reply(f"<b>✅️ Подписка продлена на {promocode[2]} дней!</b>", parse_mode="HTML")



                    await bot.send_message(

                        log_chat_id,

                        f"🩸 <a href='tg:/openmessage?user_id={message.from_user.id}'>Пользователь</a> ввел промокод <code>{message.text}</code>\n"

                        f"<b>🔔 Дни подписки:</b> <code>{promocode[2]}</code>\n"

                        f"<b>🔔 Осталось активаций:</b> <code>{promocode[3] - (1 + promocode[4])}</code>",

                        parse_mode="HTML"

                    )



                    await home(message)

                    await state.finish()



            else:

                await message.reply("<b>❌️ Неверный промокод.</b>", parse_mode="HTML")

                await home(message)

                await state.finish()



    except sqlite3.Error as e:

        print(f"Ошибка при обработке промокода: {e}")

        await message.reply("<b>❌️ Ошибка при обработке промокода.</b>", parse_mode="HTML")

        await home(message)

        await state.finish()

        

        

        

      

@dp.callback_query_handler(lambda call: call.data == 'botnet')

async def botnet(call: types.CallbackQuery, state: FSMContext):

    if not await subscribe_check(call.from_user.id):

        await state.finish()

        return

    

    await call.message.answer("<b>Отправьте @username или ID аккаунта нарушителя:</b>", parse_mode="HTML")

    await MyState.link.set()

	

session_locks = {}

lock = asyncio.Lock()

	

	

@dp.message_handler(state=MyState.link)

async def links(message: types.Message, state: FSMContext):
    target = str(message.text).strip().lstrip("@")
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    print(f"Получен таргет от пользователя {message.from_user.id}: {target}")

    await message.answer("<b>Обрабатываем жалобы на аккаунт...</b>", parse_mode="HTML")
    await state.finish()

    failed_sessions = 0
    successful_sessions = 0

    cursor.execute("SELECT white_list FROM users")
    white_list = [row[0] for row in cursor.fetchall()]

    async def send_complaint(client, peer):
        try:
            await client(ReportPeerRequest(
                peer=peer,
                reason=InputReportReasonSpam(),
                message="Реклама сноса аккаунтов за деньги, спам в чатах"
            ))
            return True
        except Exception as e:
            print(f"Ошибка жалобы с сессии {client.session.filename}: {e}")
            return False

    async def process_session(session_file):
        nonlocal successful_sessions, failed_sessions
        session_path = os.path.join(sessions_folder, session_file)
        if not os.path.exists(session_path) or not session_file.endswith('.session'):
            return
        session2 = session_file.split('.')[0]
        try:
            cursor.execute('SELECT api_id, api_hash FROM api WHERE session = ?', (session2,))
            api = cursor.fetchone()
            api_id = int(api[0]); api_hash = str(api[1])
        except Exception as e:
            print(f"Нет API для {session_file}: {e}")
            failed_sessions += 1
            return

        client = TelegramClient(session_path, api_id=api_id, api_hash=api_hash,
                                auto_reconnect=True, connection_retries=2, timeout=15, request_retries=1)
        try:
            await asyncio.wait_for(client.connect(), timeout=20)
            if not await asyncio.wait_for(client.is_user_authorized(), timeout=20):
                print(f"Сессия {session_file} не авторизована")
                failed_sessions += 1
                return

            try:
                entity = await client.get_entity(target)
            except Exception as e:
                print(f"Не найдена сущность {target} с сессии {session_file}: {e}")
                failed_sessions += 1
                return

            ok = await send_complaint(client, entity)
            if ok:
                successful_sessions += 1
                print(f"Жалоба отправлена на {target} с сессии {session_file}")
                await save_history(target, session_file, "OK")
            else:
                failed_sessions += 1
                await save_history(target, session_file, "FAIL")
        finally:
            try: await client.disconnect()
            except: pass

    for session_file in os.listdir(sessions_folder):
        await process_session(session_file)

    print(f"Итог: успешных - {successful_sessions}, неудачных - {failed_sessions}")
    await message.answer(
        f"<b>✅ Отправка завершена!</b>\n"
        f"🩸 Успешные сессии: {successful_sessions}\n"
        f"🩸 Неудачные сессии: {failed_sessions}",
        parse_mode="HTML"
    )
    await home(message)
    await state.finish()
    # await bot.send_message(log_chat_id,

    # f"<b>Жалоба на аккаунт!</b>\nТаргет: {target}\nОтправитель: {message.from_user.id}\n"

    # f"Удачно: {successful_sessions}\nНеудачно: {failed_sessions}",

    # parse_mode="HTML")


    async def send_complaint(client, peer, message_id):

        try:

            await client(ReportPeerRequest(peer=peer, reason=InputReportReasonSpam(), message="Реклама сноса аккаунтов за деньги, спам"))

            return True

        except Exception as e:

            print(f"Ошибка при отправке жалобы с сессии {client.session.filename}: {e}")

            nonlocal failed_sessions

            failed_sessions += 1

            return False

    

    async def process_session(session_file):

        nonlocal successful_sessions, failed_sessions

        

        session_path = os.path.join(sessions_folder, session_file)

        

        print(f"Обработка сессии {session_file}")

        

        if not os.path.exists(session_path):

            print(f"Сессия {session_file} не найдена.")

            return

        

        if not session_file.endswith('.session'):

            print(f"Сессия {session_file} не имеет окончания .session.")

            return

        

        if session_file not in session_locks:

            session_locks[session_file] = asyncio.Lock()

        

        async with session_locks[session_file]:

            connected = False

            session2 = session_file.split('.')[0]

            try:

                cursor.execute('SELECT api_id, api_hash FROM api WHERE session = ?', (session2,))

                api = cursor.fetchone()

                api_id = int(api[0])

                api_hash = str(api[1])

            except Exception as e:

                print(f"Ошибка при получении API для сессии {session_file}: {e}")

                failed_sessions += 1

                return

            

            print(f"Подключение сессии {session_file} с API_ID: {api_id}")

            

            client = TelegramClient(session_path, api_id=api_id, api_hash=api_hash,
                        auto_reconnect=True, connection_retries=2, timeout=15, request_retries=1)

            

            try:

                await client.connect()

                try:
                    authorized = await asyncio.wait_for(client.is_user_authorized(), timeout=20)
                except asyncio.TimeoutError:
                    print(f"Сессия {session_file} — таймаут авторизации")
                    failed_sessions += 1
                    return
                if authorized:

                    connected = True

                    print(f"Сессия {session_file} подключена и авторизована.")

                else:

                    failed_sessions += 1

                    print(f"Сессия {session_file} не авторизована.")

                    return

                    

                try:

                    entity = await client.get_entity(chat)

                    peer = await client.get_input_entity(entity)

                    

                    if isinstance(entity, (Channel, Chat)):

                        try:

                            message_info = await client.get_messages(entity, ids=int(message_id))

                            

                            if message_info:

                                from_id = message_info.sender_id

                                print(f"Сообщение найдено от {from_id}.")

                                

                                if int(from_id) in white_list or int(from_id) in admin :

                                    failed_sessions += 1

                                    print(f"Сообщение от пользователя {from_id} в белом списке, пропускаем.")

                                    return

                                

                                all_sent = True

                                for _ in range(count):

                                    if not await send_complaint(client, peer, message_id):

                                        all_sent = False

                                        

                                if all_sent:

                                    successful_sessions += 1

                                    print(f"Жалоба успешно отправлена с сессии {session_file}.")

                                else:

                                    failed_sessions += 1

                                    print(f"Не удалось отправить жалобу с сессии {session_file}.")

                            else:

                                failed_sessions += 1

                                print(f"Сообщение с ID {message_id} не найдено.")

                                return

                                

                        except Exception as e:

                            failed_sessions += 1

                            print(f"Ошибка при получении сообщения с сессии {session_file}: {e}")

                            

                except Exception as e:

                    failed_sessions += 1

                    print(f"Ошибка при получении сущности с сессии {session_file}: {e}")

                    

            finally:

                await client.disconnect()

                print(f"Сессия {session_file} отключена.")

                            

    for session_file in os.listdir(sessions_folder):

        await process_session(session_file)

        

    print(f"Отправка завершена: успешных сессий - {successful_sessions}, неудачных - {failed_sessions}")

    

    await message.answer(f"<b>✅️ Отправка завершена!</b>\n"

                         f"🩸 Успешные сессии: {successful_sessions}\n"

                         f"🩸 Неудачные сессии: {failed_sessions}", parse_mode="HTML")

    await home(message)

    await state.finish()

    

    # await bot.send_message(log_chat_id, f"<b>Отправлена жалоба!\n\nЦель: {message.text}\nОтравитель: id {message.from_user.id}\nУдачно сессий: {successful_sessions}\nНеудачно сессий: {failed_sessions}</b>", parse_mode="HTML")


	

	

	

	

	

	

	

	

	

	

@dp.message_handler(commands=['history'])
async def history_cmd(message: types.Message):
    if int(message.from_user.id) not in admin:
        return
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT target, session, status, created_at FROM history ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await message.answer("<b>История пуста.</b>", parse_mode="HTML")
        return
    text = "<b>📜 Последние 20 жалоб:</b>\n\n"
    for target, session, status, created in rows:
        text += f"🎯 <code>{target}</code> | {session} | {status} | {created}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message_handler(commands=['admin'])

async def admin_panel(message: types.Message):

	if int(message.chat.id) not in admin:

		return

		

	if message.from_user.id != message.chat.id:

		return

		

		

	markup = types.InlineKeyboardMarkup(row_width=1)

	send_sub = types.InlineKeyboardButton("🩸 Выдать подписку", callback_data='send1_sub')

	white = types.InlineKeyboardButton("🩸 Добавить вайт-лист", callback_data='white')
	black = types.InlineKeyboardButton("🚫 Чёрный список", callback_data='blacklist')

	

	markup.add(send_sub, white, black)

		

	await bot.send_message(message.chat.id, "<b>💞 Админ-доступ панель:</b>", reply_markup=markup, parse_mode="HTML")

	

	



class GiveSubState(StatesGroup):

    WaitingForUserData = State()

    White = State()
    Blacklist = State()
    BlacklistRemove = State()



@dp.callback_query_handler(lambda call: call.data == 'blacklist')
async def blacklist_menu(call: types.CallbackQuery, state: FSMContext):
    if int(call.from_user.id) not in admin:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Добавить в ЧС", callback_data='bl_add'))
    markup.add(types.InlineKeyboardButton("➖ Убрать из ЧС", callback_data='bl_remove'))
    markup.add(types.InlineKeyboardButton("📋 Список ЧС", callback_data='bl_list'))
    await bot.send_message(call.from_user.id, "<b>🚫 Управление чёрным списком:</b>", reply_markup=markup, parse_mode="HTML")

@dp.callback_query_handler(lambda call: call.data == 'bl_add')
async def bl_add(call: types.CallbackQuery, state: FSMContext):
    await bot.send_message(call.from_user.id, "<b>✍ Укажите ID пользователя для ЧС:</b>", parse_mode="HTML")
    await GiveSubState.Blacklist.set()

@dp.callback_query_handler(lambda call: call.data == 'bl_remove')
async def bl_remove(call: types.CallbackQuery, state: FSMContext):
    await bot.send_message(call.from_user.id, "<b>✍ Укажите ID пользователя для удаления из ЧС:</b>", parse_mode="HTML")
    await GiveSubState.BlacklistRemove.set()

@dp.callback_query_handler(lambda call: call.data == 'bl_list')
async def bl_list(call: types.CallbackQuery, state: FSMContext):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, reason, added_at FROM blacklist ORDER BY added_at DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await bot.send_message(call.from_user.id, "<b>Чёрный список пуст.</b>", parse_mode="HTML")
        return
    text = "<b>🚫 Чёрный список:</b>\n\n"
    for uid, reason, added in rows:
        text += f"<code>{uid}</code> | {reason or '-'} | {added}\n"
    await bot.send_message(call.from_user.id, text, parse_mode="HTML")

@dp.message_handler(state=GiveSubState.Blacklist)
async def bl_add_process(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO blacklist (user_id, reason) VALUES (?, ?)", (uid, "added by admin"))
        conn.commit()
        conn.close()
        await message.answer(f"<b>✅ Пользователь {uid} добавлен в ЧС.</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"<b>❌ Ошибка: {e}</b>", parse_mode="HTML")
    await state.finish()
    await admin_panel(message)

@dp.message_handler(state=GiveSubState.BlacklistRemove)
async def bl_remove_process(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blacklist WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()
        await message.answer(f"<b>✅ Пользователь {uid} удалён из ЧС.</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"<b>❌ Ошибка: {e}</b>", parse_mode="HTML")
    await state.finish()
    await admin_panel(message)

@dp.callback_query_handler(lambda call: call.data == 'send1_sub')

async def sub(call: types.CallbackQuery, state: FSMContext):

	await bot.send_message(call.from_user.id, "<b>✍ Укажите @username или ID и кол-во дней через пробел:</b>", parse_mode="HTML")

	await GiveSubState.WaitingForUserData.set()

	

	

@dp.message_handler(state=GiveSubState.WaitingForUserData)
async def process_subscription_data(message: types.Message, state: FSMContext):
    if not message.text:
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("<b>❌ Формат: @username ДНИ или ID ДНИ</b>", parse_mode="HTML")
        return
    target_raw, days_raw = parts[0], parts[1]
    try:
        days = int(days_raw)
    except ValueError:
        await message.answer("<b>❌ Количество дней должно быть числом.</b>", parse_mode="HTML")
        return

    user_id = None
    if target_raw.startswith("@") or not target_raw.lstrip("-").isdigit():
        uname = target_raw.lstrip("@").lower()
        try:
            chat = await bot.get_chat("@" + uname)
            user_id = chat.id
        except Exception as e:
            await message.answer(f"<b>❌ Не удалось найти @{uname}: {e}</b>", parse_mode="HTML")
            await state.finish()
            await admin_panel(message)
            return
    else:
        user_id = int(target_raw)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    try:
        base = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f') if row else datetime.now()
    except Exception:
        base = datetime.now()
    expiration_date = base + timedelta(days=days)

    try:
        await add_subscription(user_id, expiration_date)
    except Exception:
        await state.finish()
        await message.answer("<b>🤖 Ошибка! Не удалось выдать подписку.</b>", parse_mode="HTML")
        await admin_panel(message)
        return

    try:
        await bot.send_message(user_id, f"<b>✅ Вам выдана подписка на {days} дней.\n✅ Пропишите /start чтобы активировать</b>", parse_mode='HTML')
        await message.reply(f"<b>🛡 Подписка выдана (id {user_id}) на {days} дней!</b>", parse_mode="HTML")
    except Exception:
        await message.reply(f"<b>🛡 Подписка выдана (id {user_id}), но пользователь не получил уведомление.</b>", parse_mode="HTML")

    try:
        await bot.send_message(log_chat_id, f"🤖 Админ {message.from_user.id} выдал подписку id {user_id} до {expiration_date} ({days} дней)", parse_mode="HTML")
    except Exception:
        pass

    await state.finish()
    await admin_panel(message)


async def add_subscription(user_id, expiration_date):
    try:
        async with aiosqlite.connect('database.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT OR REPLACE INTO subscriptions (user_id, expiration_date) VALUES (?, ?)",
                    (user_id, expiration_date)
                )
                await conn.commit()
    except sqlite3.Error as db_error:
        raise Exception(f"Ошибка базы данных при добавлении подписки: {db_error}")


@dp.callback_query_handler(lambda call: call.data == 'white')
async def sub2(call: types.CallbackQuery, state: FSMContext):
    await bot.send_message(call.from_user.id, "<b>✍ Укажите @username или ID для внесения в белый лист:</b>", parse_mode="HTML")
    await GiveSubState.White.set()


@dp.message_handler(state=GiveSubState.White)
async def proccess_whitelist(message: types.Message, state: FSMContext):
    raw = message.text.strip()
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        if raw.startswith("@"):
            uname = raw.lstrip("@").lower()
            cursor.execute("INSERT OR REPLACE INTO users (user_id, white_list, username) VALUES (?, ?, ?)",
                           (-hash(uname) & 0x7FFFFFFF, "yes", uname))
            conn.commit()
            await bot.send_message(message.from_user.id, f"<b>✅ @{uname} добавлен в белый список.</b>", parse_mode="HTML")
        elif raw.lstrip("-").isdigit():
            uid = int(raw)
            cursor.execute("INSERT OR REPLACE INTO users (user_id, white_list) VALUES (?, ?)",
                           (uid, "yes"))
            conn.commit()
            await bot.send_message(message.from_user.id, f"<b>✅ ID {uid} добавлен в белый список.</b>", parse_mode="HTML")
        else:
            await bot.send_message(message.from_user.id, "<b>❌ Укажите @username или ID.</b>", parse_mode="HTML")
    except Exception as e:
        await bot.send_message(message.from_user.id, f"<b>❌ Ошибка: {e}</b>", parse_mode="HTML")
    finally:
        conn.close()
    await state.finish()
    await admin_panel(message)


@dp.message_handler(commands=['setpromo'])
async def promo_set(message: types.Message):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    user_id = message.from_user.id
    if int(user_id) not in admin:
        return
    text = message.text.split(" ")
    try:
        code = text[1]
        days = text[2]
        acti = text[3]
        cursor.execute(
            "INSERT INTO promocodes (code, days_subscription, max_activations) VALUES (?, ?, ?)",
            (str(code), int(days), int(acti))
        )
        conn.commit()
        await message.answer("<b>🔑 Промокод успешно создан!</b>", parse_mode="HTML")
        await home(message)
    except sqlite3.IntegrityError:
        await message.answer("<b>❌ Промокод с таким кодом уже существует!</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"<b>Ошибка: {e}</b>", parse_mode="HTML")
    finally:
        conn.close()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
