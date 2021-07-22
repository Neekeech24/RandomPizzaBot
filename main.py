import os
import random
import re

import requests
import logging

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, request

import telebot
from telebot import types

# Data
load_dotenv('.env')
bot = telebot.TeleBot(os.getenv('bot_token'))
url_dict = {
    'pzz': 'http://pzz.by/api/v1/pizzas',
    'dominos': 'https://backend.dominos.by/api/products/?api_key=B3pl8vGDjMdh&lang=ru&city_id=5',
    'tempo': 'https://www.pizzatempo.by/menu/pizza.html',
    'dodo': 'https://dodopizza.by/minsk#pizzas'
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
    markup.add(pzz_btn, dominos_btn, tempo_btn, dodo_btn)
    reply = "Хочешь питсы, но не можешь определиться? Я помогу. \n" \
            "Откуда заказываем?"
    bot.send_message(message.chat.id, reply, reply_markup=markup)


@bot.message_handler(commands=['help'])
def get_help(message):
    help_message = "Начать использовать бот можно с командой /start.\n" \
                   "Для получения случайной пиццы нужно выбрать ресторан.\n" \
                   "Чтоб посмотреть историю результатов используйте /history."
    bot.reply_to(message, help_message)


@bot.message_handler(func=lambda message: True)
def get_random(message):
    if message.text == 'Пицца Лисицца':
        result = get_pzz()
    elif message.text == 'Домино\'с':
        result = get_dominos()
    elif message.text == 'Додо Пицца':
        result = get_dodo()
    elif message.text == 'Пицца Темпо':
        result = get_tempo()
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
    return random.choice(pizzas)


def get_dominos():
    response = requests.get(url_dict['dominos'])
    data = response.json().get('data')
    pizzas = []
    for key in data.keys():
        item = data.get(key)
        if item.get('product_category') == 'Pizza':
            pizzas.append(item.get('name'))
    return random.choice(pizzas)


def get_dodo():
    response = requests.get(url_dict['dodo'])
    soup = BeautifulSoup(response.text, features='lxml')

    pizza_section = soup.find('section', id='pizzas')
    search_kwargs = {
        'data-gtm-id': 'product-title'
    }
    pizza_list = pizza_section.find_all("div", **search_kwargs)
    pizzas = [item.get_text() for item in pizza_list]
    return random.choice(pizzas)


def get_tempo():
    response = requests.get(url_dict['tempo'])
    soup = BeautifulSoup(response.text, features='lxml')
    search_kwargs = {
        "class": re.compile("item group. novinka_")
    }
    pizza_div = soup.find_all("div", **search_kwargs)
    pizzas = [item.find("h3").find("span").get_text() for item in pizza_div]
    return random.choice(pizzas)


# Webhook setup
if "HEROKU" in list(os.environ.keys()):
    logger = telebot.logger
    telebot.logger.setLevel(logging.INFO)

    server = Flask(__name__)


    @server.route("/bot", methods=['POST', 'GET'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200


    @server.route("/")
    def webhook():
        bot.remove_webhook()
        bot.set_webhook(
            url="https://randompizzabot.herokuapp.com/bot")
        return "?", 200


    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
else:
    bot.remove_webhook()
    bot.polling(none_stop=True)
