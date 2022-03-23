import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from git import Repo
import os.path
from time import sleep
import pathlib
import configparser

# автоматизированная проверка
# def pull_from_repo(repo_path):
#     repo = Repo(repo_path)
#     origin = repo.remote('origin')
#     origin.pull()
#
#
# def push_to_repo(repo_path, message):
#     repo = Repo(repo_path)
#     repo.git.add(all=True)
#     repo.index.commit(message)
#     origin = repo.remote('origin')
#     origin.push()
#
#
# @bot.message_handler(commands=['1570status_do_not_use'])
# def status_1570_message(message):
#     with open('testcheck/1570_init_check.txt', 'w') as request_file:
#         request_file.write("init check")
#     push_to_repo('testcheck', 'init check 1570')
#     while True:
#         pull_from_repo('testcheck/')
#         if '1570_check_result.txt' in os.listdir('testcheck'):
#             with open('testcheck/1570_check_result.txt', 'r') as answer_file:
#                 report = answer_file.read()
#             file_to_rem = pathlib.Path("testcheck/1570_check_result.txt")
#             file_to_rem.unlink()
#             push_to_repo('testcheck', 'response 1570 check result')
#             break
#         else:
#             sleep(5)
#     bot.send_message(message.chat.id, str(report))

config = configparser.ConfigParser()
config.read('config.ini')
telegram_api_token = config['telegram']['telegram_api_token']
bot = telebot.TeleBot(token=telegram_api_token)


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


def get_list(filename):
    with open(filename, 'r') as service_list:
        return service_list.read().split('\n')


def generate_button_list(list_of_service: list, ok_text="Успешно", fail_text="Ошибки", cat_name=False):
    button_list = []
    for service in list_of_service:
        service_name = service[:4]
        if cat_name:
            service = service[5:]
        button_list.append(InlineKeyboardButton(service, callback_data=service_name))
        button_list.append(InlineKeyboardButton(ok_text, callback_data=f"{service_name}_ok"))
        button_list.append(InlineKeyboardButton(fail_text, callback_data=f"{service_name}_neok"))
    button_list.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    return button_list


def generate_button_list_from_keyboard(inline_keyboard):
    button_list = []
    for service in inline_keyboard:
        if service[0]['text'] != "Сгенерировать отчет":
            button_list.append(InlineKeyboardButton(service[0]['text'], callback_data=service[0]['callback_data']))
            button_list.append(InlineKeyboardButton(service[1]['text'], callback_data=service[1]['callback_data']))
            button_list.append(InlineKeyboardButton(service[2]['text'], callback_data=service[2]['callback_data']))
        else:
            button_list.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    return button_list


def generate_report(inline_keyboard):
    report = ''
    inline_keyboard = inline_keyboard[:-1]
    for item in inline_keyboard:
        if item[1]['text'] != "Успешно":
            report += f"{item[0]['text']} {item[1]['text']}\n"
        else:
            report += f"{item[0]['text']} - ?\n"
    return report


def update_button_list(inline_keyboard, change='', ok_text="Успешно", fail_text="Ошибки"):
    button_list = generate_button_list_from_keyboard(inline_keyboard)
    service_name, service_change_status = change.split('_')
    if service_change_status == 'otm':
        for idx, service in enumerate(button_list):
            if service.callback_data == 'generate_report':
                button_list[idx] = InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report")
                continue
            if service.callback_data == service_name + '_status':
                button_list[idx] = InlineKeyboardButton(ok_text, callback_data=f"{service_name}_ok")
            if service.callback_data == service_name + '_otm':
                button_list[idx] = InlineKeyboardButton(fail_text, callback_data=f"{service_name}_neok")
        return button_list
    if service_change_status == 'ok':
        status = '✅'
    elif service_change_status == 'neok':
        status = '❌'
    else:
        return button_list
    for idx, service in enumerate(button_list):
        if service.callback_data == 'generate_report':
            button_list[idx] = InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report")
            continue
        if service.callback_data == service_name + '_ok':
            button_list[idx] = InlineKeyboardButton(status, callback_data=f"{service_name}_status")
        if service.callback_data == service_name + '_neok':
            button_list[idx] = InlineKeyboardButton("Отмена", callback_data=f"{service_name}_otm")
    return button_list


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "'osstatus' для меню статуса сервисов")


@bot.message_handler(commands=['status'])
def status_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = get_list(filename='service_types.txt')
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
    else:
        service_file = f'{message.text}_service_list.txt'
        bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    button_list = generate_button_list(get_list(filename=service_file))
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.send_message(message.chat.id, "Статус сервисов", reply_markup=reply_markup)


@bot.message_handler(commands=['list'])
def list_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = get_list(filename='service_types.txt')
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
    else:
        service_file = f'{message.text}_service_list.txt'
        bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    services_list = get_list(filename=service_file)
    str_service_list = '\n'.join(services_list)
    bot.send_message(message.chat.id, str_service_list)


@bot.message_handler(commands=['addservice'])
def add_service_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = get_list(filename='service_types.txt')
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
    else:
        service_file = f'{message.text}_service_list.txt'
        bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Название нового сервиса", reply_markup=keyboard)
    bot.register_next_step_handler(message, add_os, service_type=service_file)


def add_os(message, service_type):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Добавление сервиса отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    with open(service_type, 'a') as service_list:
        service_list.write(f"\n{message.text}")
    bot.send_message(message.chat.id, "Сервис добавлен", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['deleteservice'])
def delete_os_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = get_list(filename='service_types.txt')
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
    else:
        service_file = f'{message.text}_service_list.txt'
        bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    services_list = get_list(filename=service_file)
    for service in services_list:
        button = telebot.types.KeyboardButton(text=service)
        keyboard.add(button)
    button = telebot.types.KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите сервис для удаления", reply_markup=keyboard)
    bot.register_next_step_handler(message, delete_os, service_file=service_file)


def delete_os(message, service_file):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Удаление сервиса отменено", reply_markup=telebot.types.ReplyKeyboardRemove())
        return 0
    with open(service_file, 'r') as os_service_list_file:
        services = os_service_list_file.readlines()
    for i in range(len(services)):
        if services[i] == message.text or services[i] == f"{message.text}\n":
            services.pop(i)
            if i != 0:
                services[i-1] = services[i-1].replace('\n', '')
            break
    with open(service_file, 'w') as os_service_list_file:
        os_service_list_file.writelines(services)
    bot.send_message(message.chat.id, "Сервис удален", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['survey'])
def survey_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = get_list(filename='service_types.txt')
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
    else:
        service_file = f'{message.text}_users.txt'
        bot.send_message(message.chat.id, "Тип выбран", reply_markup=telebot.types.ReplyKeyboardRemove())
    button_list = generate_button_list(get_list(filename=service_file), ok_text="Да", fail_text="Нет", cat_name=True)
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
    button_list = update_button_list(call.message.json['reply_markup']['inline_keyboard'], call.data, ok_text, fail_text)
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.edit_message_text(text=call.message.html_text,
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
