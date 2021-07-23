import os
import random
import re

import requests
import logging

from apscheduler.triggers.interval import IntervalTrigger
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

import telebot
from telebot import types

# Data
load_dotenv('.env')
bot = telebot.AsyncTeleBot(os.getenv('bot_token'))

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


# Chat part
@bot.message_handler(commands=['start'])
def start_message(message):
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
    bot.send_message(message.chat.id, reply, reply_markup=markup)


@bot.message_handler(commands=['help'])
def get_help(message):
    help_message = "Начать использовать бот можно с командой /start.\n" \
                   "Для получения случайной пиццы нужно выбрать ресторан.\n"
    bot.reply_to(message, help_message)


@bot.message_handler(func=lambda message: True)
def get_random(message):
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
        bot.reply_to(message, result)
    else:
        bot.reply_to(message, "Что-то непонятное. Попробуйте /help")


# Request part
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


# Webhook setup
if "HEROKU" in list(os.environ.keys()):
    logger = telebot.logger
    telebot.logger.setLevel(logging.INFO)

    server = Flask(__name__)


    @server.route("/", methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200


    @server.route("/")
    def webhook():
        bot.remove_webhook()
        bot.set_webhook(url="https://randompizzabot.herokuapp.com/")
        return "?", 200


    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
else:
    bot.remove_webhook()
    bot.polling(none_stop=True)
