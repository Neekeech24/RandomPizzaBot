import os
import random
import logging
import re

import requests
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_webhook
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher

# Bot setup
load_dotenv('.env')

bot = Bot(os.getenv('BOT_TOKEN'))
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ----- SETTINGS -----


BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print('You have forgot to set BOT_TOKEN')
    quit()

HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')

# webhook settings
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# webserver settings
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.getenv('PORT'))

# ----- DATA -----


url_dict = {
    'pzz': 'http://pzz.by/api/v1/pizzas',
    'dominos': 'https://backend.dominos.by/api/products/?api_key=B3pl8vGDjMdh&lang=ru&city_id=5',
    'tempo': 'https://www.pizzatempo.by/menu/pizza.html',
    'dodo': 'https://dodopizza.by/minsk#pizzas'
}
pizzas = {
    'Лисицца': [],
    'Доминос': [],
    'Темпо': [],
    'Додо': []
}
order_dict = {}


def get_pzz():
    response = requests.get(url_dict['pzz'])
    data = response.json().get('response').get('data')
    pizzas = [item.get('title') for item in data]
    return pizzas


def get_dominos():
    response = requests.get(url_dict['dominos'])
    data = response.json().get('data')
    pizzas = []
    for key in data.keys():
        item = data.get(key)
        if item.get('product_category') == 'Pizza':
            pizzas.append(item.get('name'))
    return pizzas


def get_dodo():
    response = requests.get(url_dict['dodo'])
    soup = BeautifulSoup(response.text, features='lxml')

    pizza_section = soup.find('section', id='pizzas')
    search_kwargs = {
        'data-gtm-id': 'product-title'
    }
    pizza_list = pizza_section.find_all("div", **search_kwargs)
    pizzas = [item.get_text() for item in pizza_list]
    return pizzas


def get_tempo():
    response = requests.get(url_dict['tempo'])
    soup = BeautifulSoup(response.text, features='lxml')
    search_kwargs = {
        "class": re.compile("item group. novinka_")
    }
    pizza_div = soup.find_all("div", **search_kwargs)
    pizzas = [item.find("h3").find("span").get_text() for item in pizza_div]
    return pizzas


# ----- CHAT -----


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    markup = types.ReplyKeyboardMarkup()
    markup.row_width = 2
    pzz_btn = types.InlineKeyboardButton(text='Пицца Лисицца')
    dominos_btn = types.InlineKeyboardButton(text='Домино\'с')
    tempo_btn = types.InlineKeyboardButton(text='Пицца Темпо')
    dodo_btn = types.InlineKeyboardButton(text='Додо Пицца')
    full_random = types.InlineKeyboardButton(text='Полностью случайный выбор')
    markup.add(pzz_btn, dominos_btn, tempo_btn, dodo_btn, full_random)
    reply = "Хочешь питсы, но не можешь определиться? Я помогу. \n" \
            "Откуда заказываем?"
    await bot.send_message(message.chat.id, reply, reply_markup=markup)


@dp.message_handler(commands=['help'])
async def get_help(message):
    help_message = "Начать использовать бот можно с командой /start.\n" \
                   "Для получения случайной пиццы нужно выбрать ресторан.\n"
    await message.reply(help_message)


@dp.message_handler()
async def get_random(message: types.Message):
    if message.text == 'Пицца Лисицца':
        result = random.choice(pizzas['Лисицца'])
    elif message.text == 'Домино\'с':
        result = random.choice(pizzas['Доминос'])
    elif message.text == 'Додо Пицца':
        result = random.choice(pizzas['Додо'])
    elif message.text == 'Пицца Темпо':
        result = random.choice(pizzas['Темпо'])
    elif message.text == 'Полностью случайный выбор':
        rest = random.choice(list(pizzas.keys()))
        result = f"{rest}: {random.choice(pizzas[rest])}"
    else:
        result = None

    if result:
        await message.reply(result)
    else:
        await message.reply("Что-то непонятное. Попробуйте /help")


async def on_startup(dp):
    logging.warning(
        'Starting connection. ')
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


async def on_shutdown(dp):
    logging.warning('Bye! Shutting down webhook connection')


def main():
    logging.basicConfig(level=logging.INFO)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )


# ----- SCHEDULER -----


scheduler = BackgroundScheduler()


@scheduler.scheduled_job(IntervalTrigger(days=1))
def job():
    print('Menu updated')
    pizzas.update({
        'Доминос': get_dominos(),
        'Додо': get_dodo(),
        'Темпо': get_tempo(),
        'Лисицца': get_pzz()
    })


scheduler.start()
job()
