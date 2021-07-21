import random
import requests
import telebot
from telebot import types

# Data
bot = telebot.TeleBot('1906246200:AAHuut8WEMqNeyi22v47joub9IFjDWK4oyo')
url_dict = {
    'pzz': 'http://pzz.by/api/v1/pizzas',
    'dominos': 'https://backend.dominos.by/api/products/?api_key=B3pl8vGDjMdh&lang=ru&city_id=5'
}

history_dict = {
    'Лисицца': [],
    'Доминос': []
}


# Chat part
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup()
    markup.row_width = 2
    pzz_btn = types.InlineKeyboardButton(text='Лисицца', callback_data='get_pzz')
    dominos_btn = types.InlineKeyboardButton(text='Доминос', callback_data='get_dominos')
    markup.add(pzz_btn, dominos_btn)
    reply = "Хочешь питсы, но не можешь определиться? Я помогу. \n" \
            "Откуда заказываем?"
    bot.send_message(message.chat.id, reply, reply_markup=markup)


@bot.message_handler(commands=['history'])
def get_history(message):
    reply = ""
    for key in history_dict.keys():
        if history_dict[key]:
            reply += f"{key}:\n -"
            reply += "\n -".join(history_dict[key])
            reply += "\n"
        else:
            reply += f"Пока нет результатов из {key} \n"
    bot.reply_to(message, reply)


@bot.message_handler(commands=['help'])
def get_help(message):
    help_message = "Начать использовать бот можно с командой /start.\n" \
                   "Для получения случайной пиццы нужно выбрать ресторан.\n" \
                   "Чтоб посмотреть историю результатов используйте /history."
    bot.reply_to(message, help_message)


@bot.message_handler(func=lambda message: True)
def get_random(message):
    if message.text == 'Лисицца':
        result = get_pzz()
    elif message.text == 'Доминос':
        result = get_dominos()
    else:
        result = None

    if result:
        history_dict[message.text].append(result)
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


bot.polling(none_stop=True, interval=0)
