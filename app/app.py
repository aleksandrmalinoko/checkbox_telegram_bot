import base64

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import configparser
import yaml
import io

config = configparser.ConfigParser()
config.read('config.ini')
telegram_api_token = config['telegram']['telegram_api_token']
token_bytes: bytes = base64.b64decode(telegram_api_token.encode('ascii'))
token: str = token_bytes.decode('ascii')
bot = telebot.TeleBot(token=token)
with open("config_data.yaml", 'r') as stream:
    config_data = yaml.safe_load(stream)


def build_menu(buttons,
               n_cols,
               header_buttons='',
               footer_buttons=''):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def generate_button_list(names: list, ok_text="Успешно", fail_text="Ошибки"):
    button_list = []
    idx = 0
    for name in names:
        idx += 1
        button_list.append(InlineKeyboardButton(name, callback_data=idx))
        button_list.append(InlineKeyboardButton(ok_text, callback_data=f"{idx}_ok"))
        button_list.append(InlineKeyboardButton(fail_text, callback_data=f"{idx}_fail"))
    button_list.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    return button_list


def generate_button_list_from_keyboard(inline_keyboard):
    button_list = []
    for name in inline_keyboard:
        if name[0]['text'] != "Сгенерировать отчет":
            button_list.append(InlineKeyboardButton(name[0]['text'], callback_data=name[0]['callback_data']))
            button_list.append(InlineKeyboardButton(name[1]['text'], callback_data=name[1]['callback_data']))
            button_list.append(InlineKeyboardButton(name[2]['text'], callback_data=name[2]['callback_data']))
        else:
            button_list.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    return button_list


def generate_report(inline_keyboard):
    report = ''
    inline_keyboard = inline_keyboard[:-1]
    for item in inline_keyboard:
        if item[2]['text'] == "Отмена":
            report += f"{item[0]['text']} {item[1]['text']}\n"
        else:
            report += f"{item[0]['text']} - ?\n"
    return report


def update_button_list(inline_keyboard, change='', ok_text="Успешно", fail_text="Ошибки"):
    button_list = generate_button_list_from_keyboard(inline_keyboard)
    element_name, element_change_status = change.split('_')
    if element_change_status == 'otm':
        for idx, service in enumerate(button_list):
            if service.callback_data == 'generate_report':
                button_list[idx] = InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report")
                continue
            if service.callback_data == f'{element_name}_status':
                button_list[idx] = InlineKeyboardButton(ok_text, callback_data=f"{element_name}_ok")
            if service.callback_data == f'{element_name}_otm':
                button_list[idx] = InlineKeyboardButton(fail_text, callback_data=f"{element_name}_fail")
        return button_list
    if element_change_status == 'ok':
        status = '✅'
    elif element_change_status == 'fail':
        status = '❌'
    else:
        return button_list
    for idx, service in enumerate(button_list):
        if service.callback_data == 'generate_report':
            button_list[idx] = InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report")
            continue
        if service.callback_data == f'{element_name}_ok':
            button_list[idx] = InlineKeyboardButton(status, callback_data=f"{element_name}_status")
        if service.callback_data == f'{element_name}_fail':
            button_list[idx] = InlineKeyboardButton("Отмена", callback_data=f"{element_name}_otm")
    return button_list


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "'osstatus' для меню статуса сервисов")


@bot.message_handler(commands=['status'])
def status_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = config_data['platform'].keys()
    for type_service in service_types:
        button = telebot.types.KeyboardButton(text=type_service)
        keyboard.add(button)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_status)


def service_type_status(message):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    button_list = generate_button_list(config_data['platform'][message.text]['services'])
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.send_message(message.chat.id, "Статус сервисов", reply_markup=reply_markup)


@bot.message_handler(commands=['list'])
def list_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = config_data['platform'].keys()
    for type_service in service_types:
        button = telebot.types.KeyboardButton(text=type_service)
        keyboard.add(button)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_list)


def service_type_list(message):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    services_list = config_data['platform'][message.text]['services']
    str_service_list = '\n'.join(services_list)
    bot.send_message(message.chat.id, str_service_list)


@bot.message_handler(commands=['addservice'])
def add_service_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = config_data['platform'].keys()
    for type_service in service_types:
        button = telebot.types.KeyboardButton(text=type_service)
        keyboard.add(button)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_add)


def service_type_add(message):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Название нового сервиса", reply_markup=keyboard)
    bot.register_next_step_handler(message, add_os, service_type=message.text)


def add_os(message, service_type):
    if message.text == "Отмена":
        bot.send_message(
            message.chat.id, "Добавление сервиса отменено",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        return 0
    config_data['platform'][service_type]['services'].append(message.text)
    with io.open('config_data.yaml', 'w', encoding='utf8') as outfile:
        yaml.dump(config_data, outfile, default_flow_style=False, allow_unicode=True)
    bot.send_message(message.chat.id, "Сервис добавлен", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['deleteservice'])
def delete_os_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = config_data['platform'].keys()
    for type_service in service_types:
        button = telebot.types.KeyboardButton(text=type_service)
        keyboard.add(button)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_delete)


def service_type_delete(message):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    services_list = config_data['platform'][message.text]['services']
    for service in services_list:
        button = telebot.types.KeyboardButton(text=service)
        keyboard.add(button)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите сервис для удаления", reply_markup=keyboard)
    bot.register_next_step_handler(message, delete_os, service_type=message.text)


def delete_os(message, service_type):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Удаление сервиса отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    config_data['platform'][service_type]['services'].remove(message.text)
    with io.open('config_data.yaml', 'w', encoding='utf8') as outfile:
        yaml.dump(config_data, outfile, default_flow_style=False, allow_unicode=True)
    bot.send_message(message.chat.id, "Сервис удален", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['survey'])
def survey_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = config_data['platform'].keys()
    for type_service in service_types:
        button = telebot.types.KeyboardButton(text=type_service)
        keyboard.add(button)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите команду", reply_markup=keyboard)
    bot.register_next_step_handler(message, team_type_survey)


def team_type_survey(message):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    button_list = generate_button_list(config_data['platform'][message.text]['users'], ok_text="Да", fail_text="Нет")
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.send_message(message.chat.id, "Опрос", reply_markup=reply_markup)


@bot.callback_query_handler(func=lambda call: not call.data.startswith('generate_report'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    if call.message.html_text == "Статус сервисов":
        ok_text = "Успешно"
        fail_text = "Ошибки"
    else:
        ok_text = "Да"
        fail_text = "Нет"
    button_list = update_button_list(
        call.message.json['reply_markup']['inline_keyboard'],
        change=call.data,
        ok_text=ok_text,
        fail_text=fail_text
    )
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.edit_message_text(
        text=call.message.html_text,
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=reply_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('generate_report'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    report_message = generate_report(call.message.json['reply_markup']['inline_keyboard'])
    bot.send_message(chat_id=call.message.chat.id, text=report_message)


bot.infinity_polling()
