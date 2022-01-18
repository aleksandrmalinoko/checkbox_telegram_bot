import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from git import Repo
import os.path
from time import sleep
import pathlib
import configparser


def pull_from_repo(repo_path):
    repo = Repo(repo_path)
    origin = repo.remote('origin')
    origin.pull()


def push_to_repo(repo_path, message):
    repo = Repo(repo_path)
    repo.git.add(all=True)
    repo.index.commit(message)
    origin = repo.remote('origin')
    origin.push()


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


def get_list_of_service(filename='os_service_list.txt'):
    with open(filename, 'r') as service_list:
        return service_list.read().split('\n')


def generate_button_list(list_of_service: list):
    button_list = []
    for service in list_of_service:
        service_name = service[:4]
        button_list.append(InlineKeyboardButton(service, callback_data=service_name))
        button_list.append(InlineKeyboardButton("Успешно", callback_data=f"{service_name}_ok"))
        button_list.append(InlineKeyboardButton("Ошибки", callback_data=f"{service_name}_neok"))
    return button_list


def generate_button_list_from_keyboard(inline_keyboard):
    button_list = []
    for service in inline_keyboard:
        button_list.append(InlineKeyboardButton(service[0]['text'], callback_data=service[0]['callback_data']))
        button_list.append(InlineKeyboardButton(service[1]['text'], callback_data=service[1]['callback_data']))
        button_list.append(InlineKeyboardButton(service[2]['text'], callback_data=service[2]['callback_data']))
    return button_list


def update_button_list(inline_keyboard, change=''):
    button_list = generate_button_list_from_keyboard(inline_keyboard)
    service_name, service_change_status = change.split('_')
    if service_change_status == 'otm':
        for idx, service in enumerate(button_list):
            if service.callback_data == service_name + '_status':
                button_list[idx] = InlineKeyboardButton("Успешно", callback_data=f"{service_name}_ok")
            if service.callback_data == service_name + '_otm':
                button_list[idx] = InlineKeyboardButton("Ошибки", callback_data=f"{service_name}_neok")
        return button_list
    if service_change_status == 'ok':
        status = '✅'
    elif service_change_status == 'neok':
        status = '❌'
    else:
        return button_list
    for idx, service in enumerate(button_list):
        if service.callback_data == service_name + '_ok':
            button_list[idx] = InlineKeyboardButton(status, callback_data=f"{service_name}_status")
        if service.callback_data == service_name + '_neok':
            button_list[idx] = InlineKeyboardButton("Отмена", callback_data=f"{service_name}_otm")
    return button_list


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "'osstatus' для меню статуса сервисов")


@bot.message_handler(commands=['osstatus'])
def os_status_message(message):
    button_list = generate_button_list(get_list_of_service(filename='os_service_list.txt'))
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.send_message(message.chat.id, "Статус сервисов", reply_markup=reply_markup)


@bot.message_handler(commands=['oslist'])
def os_list_message(message):
    services_list = get_list_of_service(filename='os_service_list.txt')
    str_service_list = '\n'.join(services_list)
    bot.send_message(message.chat.id, str_service_list)


@bot.message_handler(commands=['1570status_do_not_use'])
def status_1570_message(message):
    with open('testcheck/1570_init_check.txt', 'w') as request_file:
        request_file.write("init check")
    push_to_repo('testcheck', 'init check 1570')
    while True:
        pull_from_repo('testcheck/')
        if '1570_check_result.txt' in os.listdir('testcheck'):
            with open('testcheck/1570_check_result.txt', 'r') as answer_file:
                report = answer_file.read()
            file_to_rem = pathlib.Path("testcheck/1570_check_result.txt")
            file_to_rem.unlink()
            push_to_repo('testcheck', 'response 1570 check result')
            break
        else:
            sleep(5)
    bot.send_message(message.chat.id, str(report))


@bot.message_handler(commands=['addos'])
def add_os_message(message):
    bot.send_message(message.from_user.id, "Название нового ОС")
    bot.register_next_step_handler(message, add_os)


def add_os(message):
    if message.text[0] == '/':
        bot.send_message(message.from_user.id, "Добавление сервиса отменено")
    with open("os_service_list.txt", 'a') as os_service_list:
        os_service_list.write(f"\n{message.text}")
    bot.send_message(message.from_user.id, "Сервис добавлен")


@bot.message_handler(commands=['deleteos'])
def delete_os_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    services_list = get_list_of_service(filename='os_service_list.txt')
    for service in services_list:
        button = telebot.types.KeyboardButton(text=service)
        keyboard.add(button)
    bot.send_message(message.chat.id, "Название ОС для удаления", reply_markup=keyboard)
    bot.register_next_step_handler(message, delete_os)


def delete_os(message):
    if message.text[0] == '/':
        bot.send_message(message.from_user.id, "Удаление сервиса отменено")
    with open("os_service_list.txt", 'r') as os_service_list_file:
        services = os_service_list_file.readlines()
    for i in range(len(services)):
        if services[i] == message.text or services[i] == f"{message.text}\n":
            services.pop(i)
            if i != 0:
                services[i-1] = services[i-1].replace('\n', '')
            break
    with open("os_service_list.txt", 'w') as os_service_list_file:
        os_service_list_file.writelines(services)
    bot.send_message(message.from_user.id, "Сервис удален", reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    button_list = update_button_list(call.message.json['reply_markup']['inline_keyboard'], call.data)
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.edit_message_text(text="Статус сервисов",
                          chat_id=call.message.chat.id,
                          message_id=call.message.id,
                          reply_markup=reply_markup
                          )


bot.infinity_polling()
# bot.stop_bot()
